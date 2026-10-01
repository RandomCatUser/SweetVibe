"""
PLUGIN :: ONLINE DISCOVERY v7
=============================
NEW in v7 -- NO BUNDLED yt-dlp.exe (yt-dlp runs as a Python library)
- v6 shipped a standalone yt-dlp.exe next to the player and shelled out to it,
  scraping "[download] 62% of 4.98MiB" out of stdout for the progress bar.
  A large self-contained .exe shipped inside an installer is exactly what
  antivirus/PUA heuristics flag, so the release looked suspicious.
- v7 imports yt_dlp in-process instead.  Nothing extra is shipped, no console
  window flashes up, there is no PATH lookup to get wrong and no subprocess to
  supervise.
- Progress now arrives through progress_hooks (downloaded_bytes / total_bytes /
  speed / eta) and the download path comes from YoutubeDL.prepare_filename(),
  which is exact, so the old "newest file matching the title" glob is only a
  fallback.
- ALL yt-dlp output is captured by _QuietLog.  A TUI must never let a library
  write to the console, or the asciimatics screen is corrupted.
- The stall watchdog cannot kill an in-process download, so it now trips a flag
  that the progress hook honours by raising _Aborted, unwinding the download.
- Requires pip install yt-dlp (still optional); the rest of the plugin loads
  and the player starts normally when it is missing.

v6 notes kept below.
NEW in v6 -- PLAYABILITY FIX (no ffmpeg, no extra binaries)
- The audio engine (just_playback/miniaudio) only decodes mp3 / wav / flac /
  ogg-vorbis / ogg-opus.  YouTube streams are WebM+Opus or M4A+AAC, so a raw
  download was saved as .webm and then died with a cryptic "MA_ERROR".
- v6 remuxes WebM/Matroska (Opus) -> Ogg Opus in PURE PYTHON: the EBML
  container is read, the Opus packets are repacked into Ogg pages with correct
  granule positions.  Nothing is re-encoded, so it needs no converter at all.
- The source container is deleted again as soon as the .opus twin is verified,
  so one download is one file (no more "track.webm" + "track.opus" pairs).
- Downloads now prefer a stream we can decode (Opus first), every cached /
  queued / browsed file is checked for playability, and unplayable WebM files
  (old downloads included) are repaired automatically on play.

v5 notes kept below.
STRICT ENGLISH-ONLY OUTPUT: yt-dlp titles are transliterated to English
when 'unidecode' is installed (pip install unidecode), otherwise stripped
to plain ASCII. Emojis/Windows-icons/CJK never reach the screen, so
nothing can overflow the modal or corrupt other panels anymore.
BOX CLAMPING: all modal prints clipped to interior cells; row list cannot
paint outside its window; footer/header fixed.
Bottom status bar now only during active downloads (no more permanent
overlay on the SESSION panel).
Kept: browse-folder saving, friendly filenames, url->file index,
permanent cache + instant replay, live %, stall watchdog, retry chain,
:pl playlists, :cache info/clear/open/dir.
"""

import os
import re
import json
import time
import zlib
import mmap
import struct
import random
import hashlib
import platform
import threading
import subprocess
import unicodedata
from pathlib import Path

# optional transliteration (pip install unidecode) -------------------------
try:
    from unidecode import unidecode as _translit
except Exception:
    _translit = None

_player        = None
LEGACY_CACHE   = Path.home() / ".sweetvibe_cache" / "online"
INDEX_FILE     = Path.home() / ".sweetvibe_cache" / "index.json"
CONFIG_FILE    = Path.home() / ".sweetvibe_plugin_config.json"
PLAYLISTS_FILE = Path.home() / ".sweetvibe_playlists.json"
ERROR_LOG_FILE = Path.home() / ".sweetvibe_cache" / "last_download_error.txt"

AUDIO_EXTS    = ["mp3", "m4a", "webm", "opus", "ogg", "wav", "flac"]
# what the audio engine can DECODE: just_playback -> miniaudio handles these
# and nothing else (.webm and .m4a blow up with "MA_ERROR" at load time)
PLAYABLE_EXTS = ("mp3", "ogg", "opus", "wav", "flac")
REMUX_EXTS    = ("webm", "mkv")   # containers holding Opus we can repack
YT_ID_RE      = re.compile(r"(?:v=|youtu\.be/|shorts/)([\w\-]{11})")
STALL_SECONDS = 90

# yt-dlp runs as an ordinary in-process Python library: no yt-dlp.exe is
# shipped, no console window is opened and no stdout is scraped. Progress
# arrives through progress_hooks and diagnostics through the logger below.
NET_OPTS = {
    "quiet": True, "no_warnings": True, "noprogress": True,
    "noplaylist": True, "overwrites": True,
    "socket_timeout": 25, "retries": 6,
    "fragment_retries": 10, "concurrent_fragment_downloads": 4,
}


def _ytdlp():
    """The yt_dlp module, or None when it is not installed.

    Imported lazily so the rest of the plugin still loads (and the player
    still starts) on a machine that never installed the online extras."""
    try:
        import yt_dlp
        return yt_dlp
    except Exception:
        return None


class _QuietLog:
    """Captures yt-dlp diagnostics instead of letting them reach the console.

    Essential for a TUI: without this, yt-dlp writes to stdout/stderr and
    corrupts the asciimatics screen."""

    def __init__(self):
        self.lines = []

    def debug(self, msg):  pass    # yt-dlp is very chatty at debug level
    def info(self, msg):   pass    # progress is delivered via progress_hooks

    def warning(self, msg):
        if msg:
            self.lines.append(str(msg))

    def error(self, msg):
        if msg:
            self.lines.append(str(msg))


class _Aborted(Exception):
    """Raised inside a progress hook to cancel a stalled download."""


def _fmt_bytes(n):
    try:
        n = float(n)
    except (TypeError, ValueError):
        return ""
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unit == "GiB":
            return ("%d%s" % (n, unit)) if unit == "B" else ("%.2f%s" % (n, unit))
        n /= 1024
    return ""


def _fmt_eta(seconds):
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return ""
    if s <= 0:
        return "00:00"
    h, rem = divmod(s, 3600)
    return "%d:%02d:%02d" % (h, rem // 60, rem % 60) if h \
        else "%02d:%02d" % (rem // 60, rem % 60)


class Engine:
    def __init__(self):
        self.downloads, self.locks = {}, {}
        self.lock_guard = threading.Lock()
        self.search_seq = 0
        self.banner_text, self.banner_color, self.banner_until = "", "green", 0.0

    def set_banner(self, text, color="green"):
        self.banner_text, self.banner_color = text, color
        self.banner_until = time.time() + 5

ENG = Engine()

sc_state = {"show_modal": False, "mode": "input", "query": "",
            "results": [], "selected_idx": 0, "is_loading": False,
            "loading_frame": 0}


def setup(player):
    global _player
    _player = player
    try: LEGACY_CACHE.mkdir(parents=True, exist_ok=True)
    except Exception: pass
    player.add_log("Online plugin v7 loaded (:yt | :pl | :cache)"
                   + (" [unidecode]" if _translit else " [ascii-mode]"))
    player.plugin_hooks["on_command"].append(handle_command)
    player.plugin_hooks["on_play_request"].append(handle_play_request)
    player.plugin_hooks["on_draw"].append(on_draw)
    player.plugin_hooks["on_key"].append(on_key)
    player.plugin_hooks["on_tick"].append(on_tick)


# TEXT SANITIZER -- English only, no emoji, terminal-safe
_EMOJI_RANGES = (
    (0x1F000, 0x1FAFF),   # emoji, pictographs, game pieces
    (0x2600,  0x27BF),    # misc symbols, dingbats
    (0x2190,  0x21FF),    # arrows
    (0x2B00,  0x2BFF),    # misc symbols/arrows
    (0xFE00,  0xFE0F),    # variation selectors
    (0x1F900, 0x1F9FF),   # supplemental symbols
    (0x2070,  0x209F),
    (0x2460,  0x24FF),    # enclosed alphanumerics
)

def _is_bad_char(ch):
    o = ord(ch)
    if o > 0x7E or o < 0x20:                 # anything non-printable-ASCII
        return True
    return False

def _strip_marks(s):
    return "".join(c for c in s if not unicodedata.combining(c))

def english(text, fallback="(untitled)"):
    """Force terminal-safe English text. Transliterates if possible."""
    s = str(text)
    if _translit is not None:
        try:
            s = _translit(s)
        except Exception:
            pass
    s = _strip_marks(unicodedata.normalize("NFKD", s))
    s = "".join(" " if _is_bad_char(c) else c for c in s)
    s = re.sub(r"\s+", " ", s).strip()
    return s if s else fallback


# ==========================================================================
# Width helpers (still needed for typed input before sanitizing)
# ==========================================================================
def _cw(ch):
    if unicodedata.combining(ch): return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1

def dwidth(s):  return sum(_cw(c) for c in s)

def dw_truncate(s, maxw):
    out, w = [], 0
    for ch in s:
        c = _cw(ch)
        if w + c > maxw: break
        out.append(ch); w += c
    return "".join(out)

def dw_tail(s, maxw):
    out, w = [], 0
    for ch in reversed(s):
        c = _cw(ch)
        if w + c > maxw: break
        out.append(ch); w += c
    return "".join(reversed(out))

def row_line(left, right, total):
    rw = dwidth(right)
    if dwidth(left) + rw + 1 > total:
        left = dw_truncate(left, max(0, total - rw - 1))
    gap = max(total - dwidth(left) - rw, 0)
    return left + " " * gap + right

def center_fit(text, w):
    t = dw_truncate(text, w)
    pad = max(w - dwidth(t), 0)
    return " " * (pad // 2) + t + " " * (pad - pad // 2)

def fit_exact(text, w):
    t = dw_truncate(text, w)
    return t + " " * (w - dwidth(t))

def shorten_path(p, n):
    s = str(p)
    if dwidth(s) <= n: return s
    parts = [x for x in re.split(r"[\\/]+", s) if x]
    tail, cur = [], ""
    for seg in reversed(parts):
        seg_ascii = english(seg, "folder")
        trial = "/".join([seg_ascii] + tail)
        if dwidth(trial) > n - 4:
            break
        tail.insert(0, seg_ascii); cur = trial
    if not tail: return dw_truncate(s, n)
    return ".../" + cur


# ==========================================================================
# Safe draw -- clamp everything to the physical screen AND caller-given box
# ==========================================================================
def _p(screen, Scr, x, y, text, fg, attr=None, bg=None):
    """Clipped print: never past screen edge, never negative coords."""
    try:
        w, h = screen.width, screen.height
        x, y = int(x), int(y)
        if y < 0 or y >= h or x >= w or x < 0: return
        text = "".join(" " if _is_bad_char(c) else c for c in str(text))
        text = dw_truncate(text, w - x)
        if bg is not None:
            screen.print_at(text, x, y, fg, attr or Scr.A_NORMAL, bg=bg)
        elif attr is not None:
            screen.print_at(text, x, y, fg, attr)
        else:
            screen.print_at(text, x, y, fg)
    except Exception:
        pass


# ==========================================================================
# Download-target resolution (BROWSE-folder aware)
# ==========================================================================
_br_cache = {"dir": None, "ts": 0.0}
_BR_HINTS = ["browse_dir", "browse_folder", "browser_dir", "browser_folder",
             "current_folder", "current_dir", "current_directory",
             "current_path", "active_folder", "active_dir", "base_folder",
             "root_folder", "music_folder", "songs_folder", "start_folder"]

def detect_browse_dir():
    now = time.time()
    if now - _br_cache["ts"] < 1.0:
        return _br_cache["dir"]
    _br_cache["ts"] = now

    def usable(v):
        try:
            return isinstance(v, (str, Path)) and \
                   Path(os.path.expandvars(str(v))).expanduser().is_dir()
        except Exception:
            return False

    cand = None
    for a in _BR_HINTS:
        v = getattr(_player, a, None)
        if callable(v): continue
        if usable(v):
            cand = Path(os.path.expandvars(str(v))).expanduser(); break
    if cand is None:
        try:
            for a in dir(_player):
                la = a.lower()
                if a.startswith("_"): continue
                if not any(t in la for t in ("folder", "directory", "browse")):
                    continue
                try: v = getattr(_player, a)
                except Exception: continue
                if callable(v): continue
                if usable(v):
                    cand = Path(os.path.expandvars(str(v))).expanduser(); break
        except Exception:
            pass
    _br_cache["dir"] = cand
    return cand


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception:
        return default

def _atomic_json(path, data):
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)

def _writable_dir(path):
    try:
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".sweetvibe_write_test"
        probe.write_bytes(b"")
        probe.unlink()
        return path
    except (OSError, PermissionError):
        return None

def get_download_dir():
    cfg = _load_json(CONFIG_FILE, {})
    pinned = cfg.get("download_dir")
    if pinned:
        p = _writable_dir(pinned)
        if p: return p
    env = os.environ.get("SWEETVIBE_DOWNLOAD_DIR")
    if env:
        p = _writable_dir(env)
        if p: return p
    br = detect_browse_dir()
    if br:
        p = _writable_dir(br)
        if p: return p
    try:
        p = _writable_dir(Path.cwd())
        if p: return p
    except Exception: pass
    return _writable_dir(Path.home() / "Music" / "SweetVibe") or Path.home()

def set_download_dir(raw):
    raw = (raw or "").strip().strip('"')
    cfg = _load_json(CONFIG_FILE, {})
    if not raw or raw.lower() == "reset":
        cfg.pop("download_dir", None)
        try: _atomic_json(CONFIG_FILE, cfg)
        except Exception: pass
        _player.add_log("Pin cleared. Target = " + str(get_download_dir()))
        return True
    p = Path(os.path.expandvars(raw)).expanduser()
    try: p.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        _player.add_log("Can't use '" + raw[:30] + "': " + str(e)[:20])
        return False
    cfg["download_dir"] = str(p.resolve())
    try: _atomic_json(CONFIG_FILE, cfg)
    except Exception: pass
    _player.add_log("Download target pinned -> " + str(p))
    return True


_idx_lock  = threading.Lock()
_idx_cache = {"data": None, "mtime": 0.0}

def _index_data():
    try: mt = INDEX_FILE.stat().st_mtime
    except OSError: mt = 0.0
    with _idx_lock:
        if _idx_cache["data"] is None or mt != _idx_cache["mtime"]:
            _idx_cache["data"]  = _load_json(INDEX_FILE, {})
            _idx_cache["mtime"] = mt
        return _idx_cache["data"]

def _index_set(url, path):
    with _idx_lock:
        data = _idx_cache["data"]
        if data is None: data = _load_json(INDEX_FILE, {})
        data[url] = {"p": str(Path(path).resolve()), "t": time.time()}
        _idx_cache.update(data=data, mtime=time.time())
        try:
            INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
            _atomic_json(INDEX_FILE, data)
        except Exception: pass


# ==========================================================================
# Cache lookup / naming
# ==========================================================================
def _video_id(url):
    m = YT_ID_RE.search(url or "")
    return m.group(1) if m else hashlib.md5((url or "?").encode()).hexdigest()[:12]

def _suffix(p):
    try:
        return Path(p).suffix.lower().lstrip(".")
    except Exception:
        return ""

def _valid_audio(p):
    """A real audio file on disk (any container we allow into the index)."""
    try:
        p = Path(p)
        return p.is_file() and p.stat().st_size > 1024 and _suffix(p) in AUDIO_EXTS
    except Exception:
        return False

def playable(p):
    """True when the audio engine can actually DECODE this file.
    just_playback -> miniaudio reads mp3/ogg/opus/wav/flac only; .webm and
    .m4a raise 'MA_ERROR' the moment load_file() touches them."""
    try:
        p = Path(p)
        return p.is_file() and p.stat().st_size > 1024 and _suffix(p) in PLAYABLE_EXTS
    except Exception:
        return False

def cached_file_for(url):
    if not url: return None
    ent = _index_data().get(url)
    if ent:
        p = Path(ent.get("p", ""))
        if _valid_audio(p): return p          # repaired later if undecodable
    vid = _video_id(url)
    best = None
    try:
        for f in LEGACY_CACHE.glob(vid + ".*"):
            if not _valid_audio(f): continue
            # a decodable copy always wins over an undecodable one
            prio = (0 if playable(f) else 1, AUDIO_EXTS.index(_suffix(f)))
            if best is None or prio < best[0]: best = (prio, f)
    except Exception: pass
    return best[1] if best else None

def safe_filename(name, fallback="track"):
    s = str(name).strip()
    for pre in ("[Y]", "[?]", "[YT]"):
        if s.startswith(pre): s = s[len(pre):].strip()
    s = english(s, fallback)                       # -> plain English
    s = re.sub(r'[\\/:*?"<>|]+', "_", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    if len(s) > 90: s = s[:90].rstrip(" .")
    return s or fallback

def find_downloaded(base):
    """Newest file yt-dlp produced for this title, preferring a decodable one
    that belongs to that same download (a half-repaired title can have both)."""
    cands = []
    try:
        for f in Path(base).parent.glob(Path(base).name + ".*"):
            if _suffix(f) in ("part", "ytdl", "tmp", "json"): continue
            if _valid_audio(f): cands.append(f)
    except Exception:
        return None
    if not cands: return None
    def _mt(f):
        try: return f.stat().st_mtime
        except OSError: return 0.0
    # newest file wins (that is what the download just wrote); a decodable copy
    # is only used when it is just as new, so a stale .opus can never mask a
    # re-downloaded .webm - that one must go through remux again.
    best = max(cands, key=_mt)
    if playable(best):
        return best
    tied = [f for f in cands if playable(f) and abs(_mt(f) - _mt(best)) <= 0.05]
    return max(tied, key=_mt) if tied else best


# ==========================================================================
# PLAYABILITY REPAIR :: pure-Python WebM/Matroska (Opus) -> Ogg Opus
# --------------------------------------------------------------------------
# No ffmpeg, no DLL, no re-encode: we read the EBML container, pull the Opus
# packets out of it and repack them into Ogg pages with correct granule
# positions.  A 4 MB track is done in a fraction of a second, the audio is
# identical, and the result decodes natively in the player.
# ==========================================================================
class RemuxError(Exception):
    pass


def _bitrev8(b):
    b = ((b & 0xF0) >> 4) | ((b & 0x0F) << 4)
    b = ((b & 0xCC) >> 2) | ((b & 0x33) << 2)
    b = ((b & 0xAA) >> 1) | ((b & 0x55) << 1)
    return b


_OGG_BITS = bytes(_bitrev8(i) for i in range(256))
_OPUS_MS  = (10, 20, 40, 60) * 3 + (10, 20, 10, 20) + (2.5, 5, 10, 20) * 4


def _ogg_crc(page):
    """Ogg's CRC-32 (poly 0x04C11DB7, init 0, no reflection).  zlib does the
    byte crunching after every byte is bit-reversed - checked field by field
    against pages muxed by ffmpeg."""
    v = zlib.crc32(page.translate(_OGG_BITS), 0xFFFFFFFF) ^ 0xFFFFFFFF
    v = ((v & 0xFFFF0000) >> 16) | ((v & 0x0000FFFF) << 16)
    v = ((v & 0xFF00FF00) >> 8) | ((v & 0x00FF00FF) << 8)
    v = ((v & 0xF0F0F0F0) >> 4) | ((v & 0x0F0F0F0F) << 4)
    v = ((v & 0xCCCCCCCC) >> 2) | ((v & 0x33333333) << 2)
    v = ((v & 0xAAAAAAAA) >> 1) | ((v & 0x55555555) << 1)
    return v


def _ogg_page(flag, granule, serial, pageno, laces, payload):
    seg = bytes(laces)
    page = bytearray(b"OggS\x00" + bytes([flag & 0xFF]) +
                     struct.pack("<Q", granule & 0xFFFFFFFFFFFFFFFF) +
                     struct.pack("<I", serial & 0xFFFFFFFF) +
                     struct.pack("<I", pageno & 0xFFFFFFFF) +
                     b"\x00\x00\x00\x00" + bytes([len(seg)]) + seg)
    page += payload
    struct.pack_into("<I", page, 22, _ogg_crc(bytes(page)))
    return bytes(page)


def _lace_all(data):
    full, rem = divmod(len(data), 255)
    return [255] * full + [rem]


# --- EBML (WebM) reading --------------------------------------------------
def _ebml_id(buf, i):
    b = buf[i]
    if not b: raise RemuxError("bad EBML id")
    mask, ln = 0x80, 1
    while ln < 8 and not (b & mask):
        mask >>= 1; ln += 1
    return int.from_bytes(buf[i:i + ln], "big"), ln


def _ebml_size(buf, i):
    b = buf[i]
    if not b: raise RemuxError("bad EBML size")
    mask, ln = 0x80, 1
    while ln < 8 and not (b & mask):
        mask >>= 1; ln += 1
    val = b & (0xFF >> ln)
    for k in range(1, ln):
        val = (val << 8) | buf[i + k]
    return val, ln, val == (1 << (7 * ln)) - 1     # every data bit set = unknown


def _ebml_elem(buf, i, end):
    """-> (element id, payload start, payload end), or None when done."""
    if i + 1 >= end: return None
    eid, idlen = _ebml_id(buf, i)
    size, slen, unknown = _ebml_size(buf, i + idlen)
    start = i + idlen + slen
    if start >= end: return None
    stop = end if unknown else min(start + size, end)
    if stop < start: raise RemuxError("bad EBML size")
    return eid, start, stop


def _uint(buf, a, b, default=0):
    if b <= a: return default
    v = 0
    for i in range(a, min(b, a + 8)):
        v = (v << 8) | buf[i]
    return v


def _sint(buf, a, b, default=0):
    if b <= a: return default
    n = min(b - a, 8)
    v = _uint(buf, a, a + n)
    if buf[a] & 0x80: v -= 1 << (8 * n)
    return v


def _vint(buf, i):
    b = buf[i]
    if not b: raise RemuxError("bad block vint")
    mask, ln = 0x80, 1
    while ln < 8 and not (b & mask):
        mask >>= 1; ln += 1
    v = b & (0xFF >> ln)
    for k in range(1, ln):
        v = (v << 8) | buf[i + k]
    return v, ln


def _opus_samples(pkt):
    """Decoded length of one Opus packet, in 48 kHz samples (RFC 6771 toc)."""
    toc = pkt[0]
    c = toc & 3
    if c == 0: frames = 1
    elif c == 1: frames = 2
    elif c == 2: frames = 3
    else:
        if len(pkt) < 2 or (toc >> 2) & 1:
            raise RemuxError("unsupported Opus packet framing")
        frames = pkt[1]
    return int(_OPUS_MS[toc >> 3] * 48) * frames


def _block_frames(buf, start, stop, track):
    """Un-lace one Matroska block -> [packets]; None for other tracks."""
    num, ln = _vint(buf, start)
    if num != track: return None
    j = start + ln + 2                                 # track + timecode
    if j >= stop: raise RemuxError("truncated block")
    lacing = buf[j] & 0x06
    j += 1
    if lacing == 0:                                    # plain single packet
        return [bytes(buf[j:stop])]
    if lacing == 0x02:                                 # Xiph lacing
        sizes, k, total = [], j, 0
        while True:
            if k >= stop: raise RemuxError("bad Xiph lacing")
            s = 0
            while k < stop and buf[k] == 255:
                s += 255; k += 1
            if k >= stop: raise RemuxError("bad Xiph lacing")
            s += buf[k]; k += 1
            sizes.append(s); total += s
            if k + total == stop: break
            if k + total > stop: raise RemuxError("bad Xiph lacing")
        frames, m = [], k
        for s in sizes:
            frames.append(bytes(buf[m:m + s])); m += s
        return frames
    if lacing == 0x04:                                 # fixed-size lacing
        avail = stop - j - 1
        for n in (buf[j] + 1, buf[j]):
            if n > 0 and avail % n == 0:
                size = avail // n
                return [bytes(buf[j + 1 + p * size:j + 1 + (p + 1) * size])
                        for p in range(n)]
        raise RemuxError("bad fixed lacing")
    raise RemuxError("EBML lacing is not supported")   # never seen in the wild


# --- Ogg Opus writing -----------------------------------------------------
class _OggOpusWriter:
    """Packet queue -> Ogg pages.  Packets are never split across pages, so a
    page's granule position is simply the decoded-sample count so far."""

    def __init__(self, fh, opus_head):
        self.fh      = fh
        self.serial  = random.randrange(1 << 32)
        self.pageno  = 0
        self.laces   = []
        self.payload = bytearray()
        self.gran    = 0
        self.total   = 0
        self.trim_ns = 0
        self._write(0x02, 0, [len(opus_head)], opus_head)             # BOS
        tags = (b"OpusTags" + struct.pack("<I", 9) + b"sweetvibe" +
                struct.pack("<I", 0))
        self._write(0x00, 0, _lace_all(tags), tags)

    def _write(self, flag, gran, laces, payload):
        self.fh.write(_ogg_page(flag, gran, self.serial, self.pageno,
                                laces, payload))
        self.pageno += 1

    def add(self, pkt):
        need = len(pkt) // 255 + 1
        if self.laces and len(self.laces) + need > 255:
            self._flush(0x00)
        full, rem = divmod(len(pkt), 255)
        self.laces += [255] * full + [rem]
        self.payload += pkt
        self.total += _opus_samples(pkt)
        self.gran = self.total

    def _flush(self, flag):
        if not self.laces: return
        self._write(flag, self.gran, self.laces, self.payload)
        self.laces = []
        self.payload = bytearray()

    def close(self):
        if self.total <= 0:
            raise RemuxError("no audio frames found")
        gran = self.total
        if self.trim_ns > 0:                 # DiscardPadding is in nanoseconds
            gran = max(0, gran - int(self.trim_ns * 48000 / 1e9))
        self.gran = gran
        self._flush(0x04)                    # EOS


def _opus_head(priv, channels):
    if priv[:8] == b"OpusHead" and len(priv) >= 19:
        return bytes(priv)                   # keep pre-skip / mapping as muxed
    if not 1 <= channels <= 2:
        raise RemuxError("Opus track without a usable header")
    return (b"OpusHead" + bytes([1, channels]) + struct.pack("<H", 0) +
            struct.pack("<I", 48000) + struct.pack("<h", 0) + bytes([0]))


def _find_opus_track(buf, start, end):
    i = start
    while i < end:
        el = _ebml_elem(buf, i, end)
        if el is None: break
        eid, ps, pe = el
        if eid == 0xAE:                                # TrackEntry
            num, priv, ch, codec = 0, b"", 1, b""
            j = ps
            while j < pe:
                sub = _ebml_elem(buf, j, pe)
                if sub is None: break
                sid, ss, se = sub
                if   sid == 0xD7:   num    = _uint(buf, ss, se)
                elif sid == 0x86:    codec = bytes(buf[ss:se])
                elif sid == 0x63A2:  priv  = bytes(buf[ss:se])
                elif sid == 0xE0:                           # Audio
                    k = ss
                    while k < se:
                        a = _ebml_elem(buf, k, se)
                        if a is None: break
                        if a[0] == 0x9F:
                            ch = _uint(buf, a[1], a[2], 1) or 1
                        k = a[2]
                j = se
            if codec[:7] == b"A_OPUS" or priv[:8] == b"OpusHead":
                return {"num": num, "priv": priv, "ch": ch}
        i = pe
    return None


def _walk_cluster(buf, start, end, track, out):
    i = start
    while i < end:
        el = _ebml_elem(buf, i, end)
        if el is None: break
        eid, ps, pe = el
        if eid == 0x1F43B675:                           # next Cluster
            return i                                    # (unknown-size case)
        if eid == 0xA3:                                 # SimpleBlock
            for fr in _block_frames(buf, ps, pe, track) or ():
                if fr: out.add(fr)
        elif eid == 0xA0:                               # BlockGroup
            j = ps
            while j < pe:
                sub = _ebml_elem(buf, j, pe)
                if sub is None: break
                if sub[0] == 0xA1:
                    for fr in _block_frames(buf, sub[1], sub[2], track) or ():
                        if fr: out.add(fr)
                elif sub[0] == 0x75A2:                  # DiscardPadding (ns)
                    pad = _sint(buf, sub[1], sub[2])
                    if pad > 0: out.trim_ns = pad
                j = sub[2]
        i = pe
    return i


def remux_to_ogg(src, dst):
    """Rewrite a WebM/Matroska file holding Opus audio as an Ogg Opus file.
    True on success; raises RemuxError when the file cannot be remuxed."""
    src, dst = Path(src), Path(dst)
    if src.stat().st_size < 64:
        raise RemuxError("file too small")
    tmp = Path(str(dst) + ".part")
    with open(src, "rb") as fh:
        mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            n, seg, i = len(mm), None, 0
            while i < n:                                 # locate the Segment
                el = _ebml_elem(mm, i, n)
                if el is None: break
                if el[0] == 0x18538067:
                    seg = (el[1], el[2]); break
                i = el[2]
            if seg is None: raise RemuxError("not a WebM/Matroska file")
            s0, s1 = seg

            track, i = None, s0                          # Info / Tracks first
            while i < s1:
                el = _ebml_elem(mm, i, s1)
                if el is None: break
                eid, ps, pe = el
                if eid == 0x1654AE6B:
                    track = _find_opus_track(mm, ps, pe)
                    if track: break
                elif eid == 0x1F43B675:
                    break                                # clusters before us
                i = pe
            if not track: raise RemuxError("no Opus audio track")

            with open(tmp, "wb") as out:
                wr = _OggOpusWriter(out,
                                    _opus_head(track["priv"], track["ch"]))
                i = s0
                while i < s1:
                    el = _ebml_elem(mm, i, s1)
                    if el is None: break
                    eid, ps, pe = el
                    if eid == 0x1F43B675:                # Cluster
                        i = _walk_cluster(mm, ps, pe, track["num"], wr)
                        continue
                    i = pe
                wr.close()
        finally:
            mm.close()
    os.replace(str(tmp), str(dst))
    return True


def ensure_playable(path):
    """Return a path the audio engine can decode, remuxing WebM/MKV (Opus)
    on the fly when needed.  None when nothing can be done for that file."""
    try:
        p = Path(path)
    except Exception:
        return None
    if not p.is_file():
        return None
    if playable(p):
        return p
    if _suffix(p) not in REMUX_EXTS:
        return None
    dst = p.with_suffix(".opus")
    try:
        if playable(dst) and dst.stat().st_mtime >= p.stat().st_mtime:
            return dst                                   # already repaired
        if remux_to_ogg(p, dst) and playable(dst):
            return dst
    except Exception:
        pass
    try:
        tmp = Path(str(dst) + ".part")
        if tmp.is_file(): tmp.unlink()
    except Exception:
        pass
    return None


def _prune_container(src, dst):
    """Drop the raw WebM/MKV once its remuxed twin is verified on disk.
    Without this every single download left TWO files in the target folder
    (the .webm the download wrote plus the .opus we remuxed out of it).
    Guarded hard: the .opus must be playable AND at least as new as the
    source, so a pre-existing stale .opus can never make us throw away the
    copy that actually holds the audio."""
    try:
        src, dst = Path(src), Path(dst)
        if src.suffix.lower() not in [".%s" % e for e in REMUX_EXTS]:
            return False
        if src.resolve() == dst.resolve():
            return False
        if not playable(dst):
            return False
        try:
            if dst.stat().st_mtime + 0.05 < src.stat().st_mtime:
                return False                     # dst is stale, not ours
        except OSError:
            return False
        src.unlink()
    except Exception:
        return False
    try:
        _player.add_log("Removed source .%s (kept .%s)"
                        % (_suffix(src) or "?", _suffix(dst) or "?"))
    except Exception:
        pass
    return True


# ==========================================================================
# Commands
# ==========================================================================
def handle_command(cmd, raw_text):
    low = cmd.strip().lower()
    if low == ":pl" or low.startswith(":pl ") or low == ":pls" or low.startswith(":pls "):
        handle_playlist_command(raw_text); return True
    if low == ":cache" or low.startswith(":cache "):
        handle_cache_command(raw_text);    return True
    if low.startswith(":sc") or low.startswith(":yt"):
        q = raw_text[3:].strip()
        sc_state.update(show_modal=True, results=[], selected_idx=0,
                        loading_frame=0)
        if q:
            start_search(q)
        else:
            sc_state.update(query="", mode="input", is_loading=False)
        return True
    return False


def start_search(query):
    ENG.search_seq += 1
    sc_state.update(mode="results", is_loading=True, results=[],
                    selected_idx=0, query=query)
    threading.Thread(target=search_worker, args=(query, ENG.search_seq),
                     daemon=True).start()

def search_worker(query, seq):
    ytdlp = _ytdlp()
    if ytdlp is None:
        _player.add_log("yt-dlp module missing. pip install yt-dlp")
        return
    log = _QuietLog()
    opts = dict(NET_OPTS, logger=log, skip_download=True,
                extract_flat="in_playlist", ignoreerrors=True)
    try:
        with ytdlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info("ytsearch12:" + query, download=False)
    except Exception as e:
        if seq == ENG.search_seq:
            _player.add_log("Search Error: " + english(str(e), "?")[:24])
            sc_state["is_loading"] = False
        return

    tracks = []
    for d in (info or {}).get("entries") or []:
        try:
            if not d:
                continue
            title = d.get("title") or ""
            who   = d.get("uploader") or d.get("channel") or ""
            dur   = d.get("duration") or 0
            url   = d.get("webpage_url") or d.get("original_url")
            if not url and d.get("id"):
                url = "https://www.youtube.com/watch?v=" + d["id"]
            if not url:
                continue
            # ---- SANITIZE: English-only, emoji-free ----
            t_en = english(title, "")
            a_en = english(who, "")
            if not t_en:
                t_en = "(untitled) " + _video_id(url)[:6]
            label = "[Y] " + t_en + (" - " + a_en if a_en else "")
            tracks.append(("online", label, url, dur))
        except Exception:
            pass

    if seq != ENG.search_seq: return              # stale; newer search ran
    sc_state["results"] = tracks
    sc_state["is_loading"] = False
    if tracks:
        _player.add_log("Found %d tracks." % len(tracks))
    else:
        _player.add_log("No tracks found.")
        for line in (log.lines or ["nothing matched"])[-2:]:
            if str(line).strip():
                _player.add_log("   | " + english(str(line).strip(), "?")[:46])

def on_tick():
    if sc_state["show_modal"]:
        sc_state["loading_frame"] += 1

def format_duration(seconds):
    try: s = int(seconds or 0)
    except (TypeError, ValueError): return "--:--"
    if s <= 0: return "LIVE"
    h, rem = divmod(s, 3600)
    return "%d:%02d:%02d" % (h, rem // 60, rem % 60) if h \
        else "%d:%02d" % (s // 60, s % 60)


# ==========================================================================
# ONE download pipeline
# ==========================================================================
def handle_play_request(item):
    try:
        if item[0] == "file":
            return _repair_browsed_file(item)
        if item[0] != "online": return False
        url = item[2]
        assert isinstance(url, str) and url
    except Exception:
        return False

    st = ENG.downloads.get(url)
    if st and st.get("status") == "running":
        _player.add_log("Already fetching that track...")
        threading.Thread(target=_wait_then_finish, args=(item,),
                         daemon=True).start()
        return True
    if st and st.get("status") == "failed" and \
            time.time() - st.get("ts_failed", 0) < 8:
        _player.add_log("Just failed - press again to retry.")
        return True

    threading.Thread(target=_resolve_worker, args=(item,), daemon=True).start()
    return True


_NO_REPAIR = set()

def _repair_browsed_file(item):
    """Auto-repair on play: a WebM/MKV the engine cannot decode (old v5
    downloads, playlist entries, anything from the BROWSE list) is remuxed to
    Ogg Opus first; the second pass then plays it like any other file."""
    try:
        p = Path(item[2])
    except Exception:
        return False
    if not p.is_file() or playable(p):
        return False
    if str(p) in _NO_REPAIR:
        _player.add_log("Can't decode .%s (need mp3/ogg/opus/wav/flac)."
                        % (_suffix(p) or "?"))
        return False
    _player.add_log("Repairing " + _short(p.name, 28) + " ...")
    fixed = ensure_playable(p)
    if not fixed or fixed == p:
        _NO_REPAIR.add(str(p))
        _player.add_log("Can't decode .%s (need mp3/ogg/opus/wav/flac)."
                        % (_suffix(p) or "?"))
        return False
    try:
        idx = _player.display_playlist.index(item)
    except ValueError:
        idx = None
    for lst in (_player.display_playlist, _player.all_items):
        for i, it in enumerate(lst):
            try:
                if it[0] == "file" and Path(it[2]) == p:
                    lst[i] = ("file", it[1], fixed, it[3])
            except Exception:
                pass
    if idx is None:
        _player.add_log("Repaired -> " + fixed.name)
        return False
    _player.add_log("Repaired -> " + fixed.name + "  playing.")
    try:
        _player.play_index(idx)          # second pass sees a playable path
    except Exception as e:
        _player.add_log("Playback Error: " + english(str(e), "?")[:22])
    return True


def _resolve_worker(item):
    url = item[2]
    with ENG.lock_guard:
        lock = ENG.locks.setdefault(url, threading.Lock())
    if not lock.acquire(blocking=False):
        _wait_then_finish(item); return
    try:
        hit = cached_file_for(url)
        if hit:
            good = ensure_playable(hit)
            if good:
                if good != hit:
                    _index_set(url, good)
                    _prune_container(hit, good)    # legacy download leftovers
                _player.add_log("CACHED - instant play.")
                ENG.set_banner(">> Instant: " + _short(item[1]))
                _finalize(item, good); return
            _player.add_log("Cached copy can't be decoded - re-downloading...")

        dd        = get_download_dir()
        base_name = safe_filename(item[1], "youtube_track")
        base      = dd / base_name
        if any(dd.glob(Path(base).name + ".*")):
            base = dd / (base_name + " [" + _video_id(url)[:6] + "]")

        st = {"status": "running", "pct": 0, "size": "", "speed": "",
              "eta": "", "name": _short(item[1]), "phase": "connecting",
              "file": None}
        ENG.downloads[url] = st
        ok, path, err = _run_download(url, base, st)

        if ok and path:
            st["phase"] = "converting"
            good = ensure_playable(path)
            if not good:
                st.update(status="failed", ts_failed=time.time())
                _player.add_log("STREAM SAVED BUT UNPLAYABLE:")
                _player.add_log("   | this stream is .%s - the player only"
                                % (_suffix(path) or "?"))
                _player.add_log("   | decodes mp3/ogg/opus/wav/flac.")
                _player.add_log("Tip: pick another result.")
                ENG.set_banner("X Unplayable: " + _short(item[1], 24), "red")
                return
            _prune_container(path, good)          # one download = one file
            path = good
            _index_set(url, path)
            st.update(status="done", pct=100, file=path)
            ENG.set_banner("OK Saved: " + _short(path.name, 30))
            _player.add_log("Saved -> " + path.name +
                            "   (" + shorten_path(path.parent, 40) + ")")
            _finalize(item, path)
        else:
            st.update(status="failed", ts_failed=time.time())
            _save_download_error(url, err)
            _player.add_log("STREAM FAILED:")
            for ln in err: _player.add_log("   | " + english(ln, "?")[:46])
            _player.add_log("Full error saved to .sweetvibe_cache/last_download_error.txt")
            if any(code in " ".join(err) for code in ("403", "Forbidden")):
                _player.add_log("Tip: This video was blocked by YouTube. Try another result.")
            ENG.set_banner("X Failed: " + _short(item[1], 26), "red")
    except Exception as e:
        _player.add_log("DL Error: " + english(str(e), "?")[:24])
    finally:
        try: lock.release()
        except RuntimeError: pass


def _wait_then_finish(item):
    url, deadline = item[2], time.time() + 600
    while time.time() < deadline:
        st = ENG.downloads.get(url)
        if st is None or st.get("status") == "done":
            path = (st or {}).get("file") or cached_file_for(url)
            path = path and ensure_playable(path)
            if path: _finalize(item, path)
            return
        if st and st.get("status") == "failed":
            _player.add_log("That download failed upstream.")
            return
        time.sleep(0.4)


def _run_download(url, base, st):
    """Grab only a stream we can decode (Opus first) - no external converter.
    The WebM source is repacked to Ogg Opus by ensure_playable() afterwards."""
    ytdlp = _ytdlp()
    if ytdlp is None:
        return False, None, ["yt-dlp module missing. pip install yt-dlp"]

    outtmpl = str(base) + ".%(ext)s"
    fmt_chain = ["bestaudio[acodec=opus]/bestaudio[ext=webm]/"
                        "bestaudio[acodec=mp3]/bestaudio[ext=mp3]/"
                        "bestaudio/bestaudio*/best"]

    for afmt in fmt_chain:
        log = _QuietLog()
        ps = {"last_seen": time.time(), "killed": False, "path": None}

        def _hook(d, ps=ps, st=st):
            if ps["killed"]:
                raise _Aborted()
            status = d.get("status")
            if status == "downloading":
                ps["last_seen"] = time.time()
                done  = d.get("downloaded_bytes") or 0
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if total:
                    st["pct"] = min(int(done * 100 / total), 99)
                    st["size"] = _fmt_bytes(total)
                if d.get("speed"):
                    st["speed"] = _fmt_bytes(d["speed"]) + "/s"
                if d.get("eta") is not None:
                    st["eta"] = _fmt_eta(d["eta"])
                st["phase"] = "downloading"
            elif status == "finished":
                ps["last_seen"] = time.time()
                st["pct"] = min(st.get("pct", 0), 99)
                st["phase"] = "downloading"

        def _watchdog(ps=ps):
            """Cannot kill an in-process download, so it trips a flag the
            progress hook honours (raising _Aborted unwinds the download)."""
            while True:
                time.sleep(5)
                if ps["last_seen"] is None:
                    return
                if time.time() - ps["last_seen"] > STALL_SECONDS:
                    ps["killed"] = True
                    return

        opts = dict(NET_OPTS, format=afmt, outtmpl=outtmpl,
                    logger=log, progress_hooks=[_hook])
        wd = threading.Thread(target=_watchdog, daemon=True); wd.start()
        try:
            with ytdlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                # exact path the library will write, then the tolerant glob
                try:
                    ps["path"] = Path(ydl.prepare_filename(info))
                except Exception:
                    ps["path"] = None
            ps["last_seen"] = None                       # release the watchdog
        except _Aborted:
            ps["last_seen"] = None
            return False, None, ["(aborted: stalled %ds)" % STALL_SECONDS]
        except Exception as e:
            ps["last_seen"] = None
            # yt-dlp reports the same failure through BOTH the raised
            # exception and the logger, so de-duplicate before logging.
            err = []
            for line in [str(e)] + list(log.lines):
                line = str(line).strip()
                if line and line not in err:
                    err.append(line)
            joined = " ".join(err).lower()
            if any(t in joined for t in ("403", "forbidden", "unavailable")):
                err.append("This video was blocked by YouTube.")
            return False, None, (err[-8:] or ["Unknown error"])
        finally:
            ps["last_seen"] = None
            wd.join(timeout=2)

        path = None
        try:
            cand = ps["path"]
            if cand is not None and _valid_audio(cand):
                path = cand
            else:
                path = find_downloaded(base)          # fallback scan
        except Exception:
            path = None
        if path:
            return True, path, []
        return False, None, ([l for l in log.lines if str(l).strip()][-8:]
                             or ["yt-dlp finished but no audio file was written"])

    return False, None, ["Unknown error"]

def _save_download_error(url, errors):
    try:
        ERROR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        ERROR_LOG_FILE.write_text(
            "URL: " + str(url) + "\n" + "\n".join(errors) + "\n",
            encoding="utf-8")
    except Exception:
        pass


def _finalize(item, path):
    new_item = ("file", item[1], Path(path), item[3])
    ci = getattr(_player, "current_index", 0)
    dp, ai = _player.display_playlist, _player.all_items
    still_here = 0 <= ci < len(dp) and dp[ci][2] == item[2]
    swapped = 0
    for lst in (dp, ai):
        for i, it in enumerate(lst):
            try:
                if it[0] == "online" and it[2] == item[2]:
                    lst[i] = new_item; swapped += 1
            except Exception: pass
    if swapped == 0:
        _player.add_log("Ready, but queue slot vanished.")
        return
    if still_here:
        try: _player.play_index(ci)
        except Exception as e:
            _player.add_log("Playback Error: " + english(str(e), "?")[:22])
    else:
        _player.add_log("Download complete - waiting in queue.")

def _short(name, n=34):
    return dw_truncate(english(name, ""), n - 3) + "..." \
        if dwidth(str(name)) > n else english(name, "")


# ==========================================================================
# Playlists (:pl ...)
# ==========================================================================
def _serialize(item):
    try:
        if item[0] == "online":
            return {"k": "online", "n": english(item[1]), "u": str(item[2]),
                    "d": float(item[3] or 0)}
        return {"k": "file", "n": english(item[1]), "p": str(Path(item[2])),
                "d": float(item[3] or 0)}
    except Exception:
        return None

def _deserialize(entry):
    try:
        if entry.get("k") == "online":
            return ("online", entry["n"], entry["u"], entry.get("d", 0)), False
        p = Path(entry["p"])
        if _valid_audio(p):
            return ("file", entry["n"], p, entry.get("d", 0)), False
        hit = None
        try:
            sibs = [p] if _suffix(p) not in REMUX_EXTS else \
                   [p.with_suffix(".opus")]        # source already pruned
            for d in {get_download_dir(), p.parent}:
                for base in sibs:
                    for f in d.glob(base.name):
                        if _valid_audio(f): hit = f; break
                    if hit: break
                if hit: break
        except Exception: pass
        return (("file", entry["n"], hit, entry.get("d", 0)), hit is None)
    except Exception:
        return None, False

def handle_playlist_command(raw_text):
    parts  = raw_text.split(None, 2)
    sub    = parts[1].lower() if len(parts) > 1 else ""
    amount = parts[2].strip() if len(parts) > 2 else ""
    pl     = _load_json(PLAYLISTS_FILE, {})

    def save():
        try: _atomic_json(PLAYLISTS_FILE, pl); return True
        except Exception as e:
            _player.add_log("Save Failed: " + str(e)[:24]); return False

    if sub == "list":
        if not pl:
            _player.add_log("No playlists yet. Save: :pl save mymix"); return
        buf = ""
        for name, items in pl.items():
            seg = "* %s (%d)  " % (name, len(items))
            if len(buf) + len(seg) > 56: _player.add_log(buf.strip()); buf = ""
            buf += seg
        if buf: _player.add_log(buf.strip())
        _player.add_log("%d playlist(s)." % len(pl))

    elif sub == "save":
        if not amount: _player.add_log("Usage: :pl save <name>"); return
        pl[amount] = [e for e in map(_serialize, _player.display_playlist) if e]
        if save():
            _player.add_log("Saved '%s' (%d tracks)." % (amount, len(pl[amount])))

    elif sub in ("load", "play"):
        items, missing = [], 0
        for e in pl.get(amount, []):
            it, miss = _deserialize(e)
            if it: items.append(it)
            missing += 1 if miss else 0
        if not items:
            _player.add_log("'" + amount + "' empty/missing (:pl list)."); return
        if sub == "load":
            _player.display_playlist.extend(items)
            _player.all_items.extend(items)
            _player.add_log("+ Added %d from '%s'." % (len(items), amount))
        else:
            _player.display_playlist[:] = items
            _player.all_items[:] = items
            _player.add_log("Queue <- '" + amount + "'. Playing...")
            try: _player.play_index(0)
            except Exception as e:
                _player.add_log("Play Error: " + english(str(e), "?")[:22])

    elif sub == "del":
        if pl.pop(amount, None) is not None and save():
            _player.add_log("Deleted '" + amount + "'.")
        else: _player.add_log("No such playlist.")

    elif sub == "view":
        for i, e in enumerate(pl.get(amount, [])[:25]):
            _player.add_log("%2d. %s" % (i + 1, _short(e.get("n", "?"), 46)))
    else:
        _player.add_log(":pl list|save X|load X|play X|view X|del X")


def handle_cache_command(raw_text):
    bits = raw_text.split()
    sub  = bits[1].lower() if len(bits) > 1 else ""

    if sub == "info":
        dd = get_download_dir()
        mb = files = 0
        try:
            for f in dd.iterdir():
                if f.is_file() and f.suffix.lower().lstrip(".") in AUDIO_EXTS:
                    files += 1; mb += f.stat().st_size
        except Exception: pass
        br = detect_browse_dir()
        _player.add_log("Target    : " + str(dd))
        if br: _player.add_log("[BROWSE]  : " + str(br))
        _player.add_log("Audio here: %d file(s), %.1f MB | index: %d" %
                        (files, mb / 1048576, len(_index_data())))
    elif sub == "clear":
        protected = set()
        try:
            cur = _player.display_playlist[_player.current_index]
            if cur[0] == "file": protected.add(Path(cur[2]).resolve())
        except Exception: pass
        n = 0
        for f in LEGACY_CACHE.glob("*"):
            try:
                if f.is_file() and f.resolve() not in protected:
                    f.unlink(); n += 1
            except Exception: pass
        _player.add_log("Wiped %d legacy temp file(s). Music folders untouched." % n)
    elif sub == "open":
        dd = get_download_dir()
        try:
            if os.name == "nt": os.startfile(str(dd))                 # noqa
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(dd)])
            else: subprocess.Popen(["xdg-open", str(dd)])
        except Exception as e:
            _player.add_log("Open failed: " + str(e)[:24])
    elif sub == "dir":
        arg = " ".join(bits[2:])
        if arg: set_download_dir(arg)
        else:   _player.add_log("Target: " + str(get_download_dir()) +
                                "  (pin: :cache dir <path> | reset)")
    else:
        _player.add_log(":cache info|clear|open|dir [<path>|reset]")


# ==========================================================================
# Drawing -- everything clamped INSIDE its box
# ==========================================================================
def on_draw(screen):
    from asciimatics.screen import Screen
    try: _draw_status_bar(screen, Screen)
    except Exception: pass
    if not sc_state["show_modal"]:
        return
    try: _draw_modal(screen, Screen)
    except Exception: pass


def _draw_status_bar(screen, Scr):
    """ONLY while a download runs. One line, clamped. Never lingers."""
    running = [(u, s) for u, s in ENG.downloads.items()
               if s.get("status") == "running"]
    if not running: return
    _, st = running[0]
    phase = st.get("phase")
    if phase == "converting":
        body = "* Converting..."
    elif phase == "connecting":
        body = "- Connecting..."
    else:
        filled = int(min(max(st.get("pct", 0), 0) / 100 * 12, 12))
        g = "#" * filled + "." * (12 - filled)
        body = ("%3d%% [%s] %s %s" % (st.get("pct", 0), g,
                st.get("speed", ""), st.get("eta", ""))).rstrip()
    w, h = screen.width, screen.height
    _p(screen, Scr, 0, h - 1,
       row_line("[YT] " + st.get("name", ""), body, min(w - 1, 78)),
       Scr.COLOUR_YELLOW, Scr.A_BOLD, Scr.COLOUR_BLACK)


def _draw_modal(screen, Scr):
    w, h = screen.width, screen.height
    bw = max(min(76, w - 4), 30)
    bh = max(min(21, h - 2), 13)
    bx, by = (w - bw) // 2, (h - bh) // 2
    px, pw = bx + 1, bw - 2                     # usable interior columns

    if hasattr(_player, "draw_box"):
        try:
            _player.draw_box(bx, by, bw, bh, " YOUTUBE DISCOVERY ",
                             Scr.COLOUR_RED, rounded=True,
                             bg=Scr.COLOUR_BLACK)
        except Exception:
            pass
    _p(screen, Scr, px, by + 1, center_fit("- YouTube Search -", pw),
       Scr.COLOUR_WHITE, Scr.A_BOLD)
    _p(screen, Scr, px, by + 2, "-" * (pw - 2), Scr.COLOUR_RED)

    # INPUT ---------------------------------------------------------------
    if sc_state["mode"] == "input":
        _p(screen, Scr, px, by + 5,
           center_fit("Type what you want to hear:", pw),
           Scr.COLOUR_CYAN, Scr.A_BOLD)
        iw = max(min(bw - 12, 54), 16)
        ix, iy = bx + (bw - iw) // 2, by + 8
        if hasattr(_player, "draw_box"):
            try: _player.draw_box(ix, iy, iw, 3, "", Scr.COLOUR_WHITE)
            except Exception: pass
        max_q = iw - 4
        shown = dw_tail(sc_state["query"], max_q - 1)
        cursor = "_" if int(time.time() * 2) % 2 == 0 else " "
        pad_l = max(max_q - dwidth(shown) - 1, 0)
        _p(screen, Scr, ix + 2, iy + 1, " " * pad_l + shown + cursor,
           Scr.COLOUR_YELLOW, Scr.A_BOLD)
        tgt = shorten_path(get_download_dir(), 24)
        _p(screen, Scr, px, by + bh - 3,
           center_fit("(downloads follow your BROWSE folder)", pw),
           Scr.COLOUR_CYAN)
        _p(screen, Scr, px, by + bh - 2,
           center_fit("ENTER search | CTRL+B close | SAVE-> " + tgt, pw),
           Scr.COLOUR_WHITE)
        return

    ry = by + 5
    # LOADING ---------------------------------------------------------------
    if sc_state["is_loading"]:
        fr = "-|/\\"[(sc_state["loading_frame"] // 4) % 4]
        _p(screen, Scr, px, ry + 3,
           center_fit(fr + " Searching: '" +
                      dw_tail(sc_state["query"], 30) + "'", pw),
           Scr.COLOUR_YELLOW, Scr.A_BOLD)
        _p(screen, Scr, px, by + bh - 2,
           center_fit("CTRL+B cancel", pw), Scr.COLOUR_WHITE)
        return

    items = sc_state["results"]
    foot_y = by + bh - 2                                # last usable line
    max_rows = max(foot_y - ry, 1)                      # rows MUST fit above foot

    # EMPTY ------------------------------------------------------------------
    if not items:
        _p(screen, Scr, px, ry + 3,
           center_fit("No results for '" +
                      dw_tail(sc_state["query"], 30) + "'.", pw),
           Scr.COLOUR_RED, Scr.A_BOLD)
        _p(screen, Scr, px, foot_y,
           center_fit("CTRL+B new search", pw), Scr.COLOUR_WHITE)
        return

    # RESULTS ----------------------------------------------------------------
    n = len(items)
    sel = sc_state["selected_idx"]
    start = min(max(0, sel - (max_rows - 1)), max(0, n - max_rows))

    for row, i in enumerate(range(start, min(start + max_rows, n))):
        it = items[i]
        s_sel = (i == sel)
        dur    = format_duration(it[3])
        right  = "[" + dur + "]"
        star   = "*" if cached_file_for(it[2]) else " "
        arrow  = ">>" if s_sel else "  "
        avail_t = pw - dwidth(arrow) - dwidth(star) - 1 - dwidth(right)
        disp = dw_truncate(it[1], max(avail_t, 6))
        line = fit_exact(row_line(arrow + star + " " + disp, right, pw), pw)

        if s_sel:
            _p(screen, Scr, px, ry + row, line, Scr.COLOUR_BLACK,
               Scr.A_BOLD, Scr.COLOUR_YELLOW)
        else:
            _p(screen, Scr, px, ry + row, line, Scr.COLOUR_WHITE)

    fl  = "[%d-%d / %d]" % (start + 1, min(start + max_rows, n), n)
    frt = "UP/DN move  ENTER play  CTRL+B again"
    _p(screen, Scr, px, foot_y, fit_exact(row_line(fl, frt, pw), pw),
       Scr.COLOUR_CYAN)


# ==========================================================================
# Keys
# ==========================================================================
_ENTER = {"enter", "\r", "\n"}

def on_key(key_str, action):
    if not sc_state["show_modal"]:
        return False
    ks = (key_str or "").lower()
    close = ks in ("ctrl+b", "escape", "esc", "\x1b")

    if sc_state["mode"] == "input":
        if close:
            sc_state["show_modal"] = False; return True
        if action == "enter" or ks in _ENTER:
            if sc_state["query"].strip():
                start_search(sc_state["query"].strip())
            return True
        if action == "backspace" or ks in ("backspace", "\b", "^h", "ctrl+h"):
            sc_state["query"] = sc_state["query"][:-1]; return True
        if ks == "space":
            sc_state["query"] += " "; return True
        if key_str and len(key_str) == 1 and key_str.isprintable():
            sc_state["query"] += key_str
        return True

    if sc_state["mode"] == "results":
        if close:
            sc_state["show_modal"] = False; return True
        if action == "up":
            sc_state["selected_idx"] = max(0, sc_state["selected_idx"] - 1)
            return True
        if action == "down":
            sc_state["selected_idx"] = min(
                len(sc_state["results"]) - 1, sc_state["selected_idx"] + 1)
            return True
        if action == "enter" or ks in _ENTER:
            if sc_state["results"] and not sc_state["is_loading"]:
                item = sc_state["results"][sc_state["selected_idx"]]
                sc_state["show_modal"] = False
                _player.display_playlist.insert(0, item)
                _player.all_items.insert(0, item)
                _player.current_index = 0
                threading.Thread(target=_kickoff, args=(0,),
                                 daemon=True).start()
            return True
        return True
    return False


def _kickoff(index):
    try: _player.play_index(index)
    except Exception as e:
        _player.add_log("Kickoff Error: " + english(str(e), "?")[:22])