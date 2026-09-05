"""
PLUGIN :: ONLINE DISCOVERY v5
=============================
NEW vs v4
- STRICT ENGLISH-ONLY OUTPUT: yt-dlp titles are transliterated to English
  when 'unidecode' is installed (pip install unidecode), otherwise stripped
  to plain ASCII. Emojis/Windows-icons/CJK never reach the screen, so
  nothing can overflow the modal or corrupt other panels anymore.
- BOX CLAMPING: all modal prints clipped to interior cells; row list cannot
  paint outside its window; footer/header fixed.
- Bottom status bar now only during active downloads (no more permanent
  overlay on the SESSION panel).
Kept: browse-folder saving, friendly filenames, url->file index,
permanent cache + instant replay, live %, stall watchdog, retry chain,
:pl playlists, :cache info/clear/open/dir.
"""

import os
import re
import json
import time
import shutil
import hashlib
import platform
import sys
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
APP_DIR        = (Path(sys.executable).resolve().parent
                  if getattr(sys, "frozen", False)
                  else Path(__file__).resolve().parents[1])
LEGACY_CACHE   = Path.home() / ".sweetvibe_cache" / "online"
INDEX_FILE     = Path.home() / ".sweetvibe_cache" / "index.json"
CONFIG_FILE    = Path.home() / ".sweetvibe_plugin_config.json"
PLAYLISTS_FILE = Path.home() / ".sweetvibe_playlists.json"
ERROR_LOG_FILE = Path.home() / ".sweetvibe_cache" / "last_download_error.txt"

AUDIO_EXTS    = ["mp3", "m4a", "webm", "opus", "ogg", "wav", "flac"]
PROGRESS_RE   = re.compile(r"\[download\]\s+([\d.]+)%")
YT_ID_RE      = re.compile(r"(?:v=|youtu\.be/|shorts/)([\w\-]{11})")
STALL_SECONDS = 90
NET_ARGS = ["--newline", "--no-warnings", "--no-playlist",
            "--socket-timeout", "25", "--retries", "6",
            "--fragment-retries", "10", "--concurrent-fragments", "4"]
_wf = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0


def _yt_dlp_command():
    """Find yt-dlp installed by the guided installer or available on PATH."""
    bundled = APP_DIR / "yt-dlp.exe"
    if bundled.is_file():
        return [str(bundled)]
    found = shutil.which("yt-dlp")
    if found:
        return [found]
    candidates = [
        Path(sys.executable).parent / "Scripts" / "yt-dlp.exe",
    ]
    for root in (
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python",
        Path(os.environ.get("APPDATA", "")) / "Python",
    ):
        try:
            candidates.extend(root.glob("Python*/Scripts/yt-dlp.exe"))
        except OSError:
            pass
    for candidate in candidates:
        if candidate.is_file():
            return [str(candidate)]
    return None


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
    player.add_log("Online plugin v5 loaded (:yt | :pl | :cache)"
                   + (" [unidecode]" if _translit else " [ascii-mode]"))
    player.plugin_hooks["on_command"].append(handle_command)
    player.plugin_hooks["on_play_request"].append(handle_play_request)
    player.plugin_hooks["on_draw"].append(on_draw)
    player.plugin_hooks["on_key"].append(on_key)
    player.plugin_hooks["on_tick"].append(on_tick)


# ==========================================================================
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

def _valid_audio(p):
    try:
        return p.is_file() and p.stat().st_size > 1024 and \
               p.suffix.lower().lstrip(".") in AUDIO_EXTS
    except Exception:
        return False

def cached_file_for(url):
    if not url: return None
    ent = _index_data().get(url)
    if ent:
        p = Path(ent.get("p", ""))
        if _valid_audio(p): return p
    vid = _video_id(url)
    best = None
    try:
        for f in LEGACY_CACHE.glob(vid + ".*"):
            if not _valid_audio(f): continue
            prio = AUDIO_EXTS.index(f.suffix.lower().lstrip("."))
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
    best = None
    try:
        for f in Path(base).parent.glob(Path(base).name + ".*"):
            if f.suffix.lower() in (".part", ".ytdl", ".tmp", ".json"): continue
            if _valid_audio(f) and (best is None or
                                    f.stat().st_mtime > best.stat().st_mtime):
                best = f
    except Exception: pass
    return best


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
    try:
        yt_dlp = _yt_dlp_command()
        if not yt_dlp:
            _player.add_log("yt-dlp is not installed. Run the setup wizard.")
            return
        cmd = yt_dlp + ["ytsearch12:" + query, "--dump-json",
               "--flat-playlist", "--skip-download", "--no-warnings",
               "--ignore-errors"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True,
                                 encoding="utf-8", errors="replace",
                                 creationflags=_wf, timeout=60)
        except FileNotFoundError:
            _player.add_log("yt-dlp missing!  pip install -U yt-dlp"); return
        except subprocess.TimeoutExpired:
            _player.add_log("Search timed out."); return
        tracks = []
        for line in (res.stdout or "").splitlines():
            line = line.strip()
            if not line: continue
            try:
                d = json.loads(line)
                title = d.get("title") or ""
                who   = d.get("uploader") or d.get("channel") or ""
                dur   = d.get("duration") or 0
                url   = d.get("webpage_url") or d.get("original_url")
                if not url and d.get("id"):
                    url = "https://www.youtube.com/watch?v=" + d["id"]
                if not url: continue
                # ---- SANITIZE: English-only, emoji-free ----
                t_en = english(title, "")
                a_en = english(who, "")
                if not t_en:
                    t_en = "(untitled) " + _video_id(url)[:6]
                label = "[Y] " + t_en + (" - " + a_en if a_en else "")
                tracks.append(("online", label, url, dur))
            except Exception: pass
        if seq != ENG.search_seq: return          # stale; newer search ran
        sc_state["results"] = tracks
        if tracks:
            _player.add_log("Found %d tracks." % len(tracks))
        else:
            details = (res.stderr or res.stdout or "").strip().splitlines()
            _player.add_log("No tracks found.")
            for line in details[-2:]:
                if line.strip():
                    _player.add_log("   | " + english(line.strip(), "?")[:46])
    except Exception as e:
        if seq == ENG.search_seq:
            _player.add_log("Search Error: " + english(str(e), "?")[:24])
    finally:
        if seq == ENG.search_seq:
            sc_state["is_loading"] = False

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


def _resolve_worker(item):
    url = item[2]
    with ENG.lock_guard:
        lock = ENG.locks.setdefault(url, threading.Lock())
    if not lock.acquire(blocking=False):
        _wait_then_finish(item); return
    try:
        hit = cached_file_for(url)
        if hit:
            _player.add_log("CACHED - instant play.")
            ENG.set_banner(">> Instant: " + _short(item[1]))
            _finalize(item, hit); return

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
            if path: _finalize(item, path)
            return
        if st and st.get("status") == "failed":
            _player.add_log("That download failed upstream.")
            return
        time.sleep(0.4)


def _run_download(url, base, st):
    outtmpl = str(base) + ".%(ext)s"
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    fmt_chain = []
    if ffmpeg_ok:
        fmt_chain.append(["-x", "--audio-format", "mp3",
                          "-f", "bestaudio/bestaudio*/best"])
    fmt_chain.append(["-f", "bestaudio/bestaudio*/best"])

    err_tail = []
    yt_dlp = _yt_dlp_command()
    if not yt_dlp:
        return False, None, ["yt-dlp is not installed. Run the setup wizard."]
    for afmt in fmt_chain:
        cmd = yt_dlp + NET_ARGS + afmt + \
              ["--force-overwrites", "-o", outtmpl, "--", url]
        ps = {"last_seen": time.time(), "killed": False}
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True,
                                    encoding="utf-8", errors="replace",
                                    bufsize=1, creationflags=_wf)
        except FileNotFoundError:
            return False, None, ["yt-dlp could not be started. Run the setup wizard."]

        def _watchdog(proc=proc, ps=ps):
            while True:
                time.sleep(5)
                if proc.poll() is not None: return
                if time.time() - ps["last_seen"] > STALL_SECONDS:
                    ps["killed"] = True
                    try: proc.kill()
                    except Exception: pass
                    return

        wd = threading.Thread(target=_watchdog, daemon=True); wd.start()
        for raw in proc.stdout:
            line = raw.rstrip()
            if not line: continue
            m = PROGRESS_RE.search(line)
            if m:
                ps["last_seen"] = time.time()
                st["pct"] = min(int(float(m.group(1))), 99)
                st["phase"] = "downloading"
                for pat, key in ((r"of\s+~?\s*([\d.]+\w+)", "size"),
                                 (r"at\s+([\d.]+\w+/s)", "speed"),
                                 (r"ETA\s+([\d:]+)", "eta")):
                    mm = re.search(pat, line)
                    if mm: st[key] = mm.group(1)
            elif "already been downloaded" in line:
                ps["last_seen"] = time.time(); st["pct"] = 99
            elif "[ExtractAudio]" in line or "Destination:" in line:
                ps["last_seen"] = time.time(); st["phase"] = "converting"
            elif "ERROR" in line.upper():
                err_tail.append(line.strip())
        rc = proc.wait(); wd.join(timeout=2)

        path = find_downloaded(base)
        if rc == 0 and path:
            return True, path, []
        if ps["killed"]:
            err_tail.append("(aborted: stalled %ds)" % STALL_SECONDS); break
        joined = " ".join(err_tail).lower()
        recoverable = any(t in joined for t in (
            "403", "forbidden", "unavailable", "postprocessor", "ffmpeg",
            "requested format", "conversion failed"))
        if recoverable and len(fmt_chain) > 1 and afmt is fmt_chain[0]:
            _player.add_log("Retrying without conversion...")
            err_tail = []
            continue
        break

    return False, None, (err_tail[-8:] or ["Unknown error"])

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
            for d in {get_download_dir(), p.parent}:
                for f in d.glob(p.name):
                    if _valid_audio(f): hit = f; break
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