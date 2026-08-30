# PLUGIN :: LYRICS
# Shows the lyrics stored in the current song's metadata inside a modal box.
#
#   Open with:  :lyric
#   Or target a specific file:  :lyric <path to audio file>
#
# Spotify-style auto-scroll:
#   - Timed (LRC) lyrics follow the exact timestamp of the playing song.
#   - Plain lyrics are auto-scrolled proportionally to the song duration.
#   - The active line is highlighted and kept near the middle of the box.
#   - Toggle with:  :lyric auto=1   (on)   :lyric auto=0   (off)
#   - Scrolling with Up/Down turns auto-scroll off; re-enable it with auto=1.
#
# CJK-aware rendering: Chinese, Japanese and Korean characters are preserved
# and laid out using their real terminal (double) width, so text always stays
# inside the box and never overflows, jumps, or breaks its borders.

import os
import re
import time as _time
import unicodedata
from pathlib import Path

import tinytag

# Modal state ---------------------------------------------------------------
MODE_NONE = "none"
MODE_VIEW = "view"
MODE_ERR  = "err"

_player = None

_st = {
    "mode": MODE_NONE,
    "lines": [],          # sanitized lyric lines (display order)
    "scroll": 0,          # first visible line index
    "title": "",          # header shown in the box title
    "source": "",         # short source path / message
    "error": "",
    # Auto-scroll state
    "auto": True,         # Spotify-style follow-along scrolling on/off
    "active": -1,         # currently active line index (-1 = none)
    "timeline": [],       # list of (time_seconds, line_index) in order
    "timed": False,       # True if lyrics carry real LRC timestamps
}


# Width helpers (CJK-aware) --------------------------------------------------
def _cw(ch):
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def dwidth(s):
    return sum(_cw(c) for c in str(s))


def dw_truncate(s, maxw):
    out, w = [], 0
    for ch in str(s):
        c = _cw(ch)
        if w + c > maxw:
            break
        out.append(ch)
        w += c
    return "".join(out)


def center_fit(text, w):
    t = dw_truncate(text, w)
    pad = max(w - dwidth(t), 0)
    return " " * (pad // 2) + t + " " * (pad - pad // 2)


# Clipped printer: never draw outside the screen or the box ------------------
def _p(screen, Scr, x, y, text, fg, attr=None, bg=None):
    try:
        w, h = screen.width, screen.height
        x, y = int(x), int(y)
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        text = dw_truncate(text, w - x)
        if bg is not None:
            screen.print_at(text, x, y, fg, attr or Scr.A_NORMAL, bg=bg)
        elif attr is not None:
            screen.print_at(text, x, y, fg, attr)
        else:
            screen.print_at(text, x, y, fg)
    except Exception:
        pass


# Sanitization: keep CJK, drop control characters and terminal escapes -------
_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07|\x1b[@-Z\\-_]")

def _sanitize(text):
    """Keep printable unicode (incl. CJK) but strip control/escape chars."""
    s = _ESCAPE_RE.sub("", text or "")
    out = []
    for ch in s:
        if ch == "\n":
            out.append(ch)
            continue
        o = ord(ch)
        if o == 0x1B:
            continue
        if (o < 0x20 and o != 0x09) or 0x7F <= o <= 0x9F:
            continue
        out.append(ch)
    return "".join(out)


def _split_to_lines(text):
    raw = _sanitize(text)
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    return raw.split("\n")


# Timeline building (for Spotify-style follow-along) --------------------------
_LRC_TIME_RE = re.compile(r"\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]")

def _parse_lrc_timestamps(line):
    """Return list of (start_seconds, text_without_tags) if line is LRC-timed."""
    text = line
    times = []
    while True:
        m = _LRC_TIME_RE.match(text)
        if not m:
            break
        min_, sec_, frac = m.group(1), m.group(2), m.group(3)
        sec = int(min_) * 60 + int(sec_)
        if frac:
            # two or three digits
            if len(frac) == 2:
                sec += int(frac) / 100.0
            else:
                sec += int(frac) / 1000.0
        times.append(sec)
        text = text[m.end():].lstrip()
    if not times:
        return None
    return times, text


def _build_timeline(lines, duration):
    """Build a list of (time_seconds, line_index) that defines the active line
    progressing with playback. Uses real LRC timestamps when present, otherwise
    estimates proportional timing from the song duration."""
    # 1) Detect / collect LRC-timed lines.
    timed_entries = []       # (time, line_index, text_without_tags)
    rebuilt = list(lines)    # cleaned display lines (LRC tags stripped)
    any_timed = False
    for idx, raw in enumerate(lines):
        parsed = _parse_lrc_timestamps(raw)
        if parsed is None:
            continue
        times, text = parsed
        text = text.strip()
        rebuilt[idx] = text
        any_timed = True
        for t in times:
            if text:
                timed_entries.append((t, idx, text))

    if any_timed and timed_entries:
        # Keep only the first timestamp per line for a clean sequence, but sort
        # by time and de-duplicate consecutive same-line entries.
        timed_entries.sort(key=lambda e: e[0])
        timeline = []
        last_idx = None
        last_time = None
        for t, idx, _txt in timed_entries:
            if idx == last_idx:
                continue
            if last_time is not None and t < last_time:
                break
            timeline.append((t, idx))
            last_idx = idx
            last_time = t
        if not timeline:
            timeline = [(0.0, 0)] if lines else []
        return rebuilt, timeline, True

    # 2) Untimed: estimate per-line timing from duration.
    timeline = []
    if duration > 0:
        # only meaningful (non-blank) lines get a time
        content_idx = [i for i, l in enumerate(lines) if l.strip()]
        if content_idx:
            seg = duration / len(content_idx)
            for k, idx in enumerate(content_idx):
                timeline.append((seg * k, idx))
    if not timeline and lines:
        timeline = [(0.0, 0)]
    return rebuilt, timeline, False


# Loading lyrics from metadata ------------------------------------------------
def _read_lyrics(path):
    try:
        tag = tinytag.TinyTag.get(str(path))
    except Exception as e:
        return None, "Could not read tags: %s" % str(e)[:40]

    lyrics = None
    try:
        ad = tag.as_dict()
    except Exception:
        ad = {}
    if isinstance(ad, dict):
        for k in ("lyrics", "otherlyrics", "other.lyrics", "unsyncedlyrics"):
            v = ad.get(k)
            if v:
                if isinstance(v, list):
                    v = "\n".join(str(x) for x in v)
                lyrics = v
                break
    if not lyrics:
        try:
            extra = dict(tag.extra or {})
            v = extra.get("lyrics") or extra.get("other.lyrics")
            if v:
                if isinstance(v, list):
                    v = "\n".join(str(x) for x in v)
                lyrics = v
        except Exception:
            pass
    if not lyrics:
        return None, "No lyrics found in the song metadata."
    return str(lyrics), None


def _open(player, path):
    src = path or getattr(player, "current_filepath", None)
    if not src:
        _show_error(player, "Nothing is playing. Play a song first.")
        return
    title = ""
    try:
        md = player.metadata
        title = str(md.get("title") or Path(src).name)
        artist = str(md.get("artist") or "")
        if artist and artist != "Unknown":
            title = title + " - " + artist
    except Exception:
        title = str(Path(src).name)

    lyrics, err = _read_lyrics(src)
    if err:
        _show_error(player, err)
        return

    lines = _split_to_lines(lyrics)
    if not lines or not any(l.strip() for l in lines):
        _show_error(player, "The lyric metadata is empty.")
        return

    duration = getattr(player, "duration", 0) or 0
    cleaned_lines, timeline, timed = _build_timeline(lines, duration)

    _st.update(mode=MODE_VIEW, lines=cleaned_lines, scroll=0, active=-1,
               title=title, source=str(src),
               timeline=timeline, timed=timed, auto=True)
    player.add_log("Lyrics loaded (%d lines%s)." %
                   (len(cleaned_lines), " [timed]" if timed else ""))


def _show_error(player, message):
    _st.update(mode=MODE_ERR, scroll=0, lines=[], error=message,
               title="LYRICS", source="")
    player.add_log("Lyrics: " + message)


def on_play(filepath):
    """When a new song starts playing, switch the open lyrics to match it."""
    if _st["mode"] == MODE_NONE:
        return
    if _player is None or not filepath:
        return
    keep_auto = _st["auto"]
    _open(_player, None)     # reload for the newly playing track
    _st["auto"] = keep_auto


# Command handling ------------------------------------------------------------
def _strip_prefix(raw, prefixes):
    for p in prefixes:
        if raw.lower().startswith(p + " "):
            return raw[len(p):].strip()
    return ""


def handle_command(cmd, raw_text):
    low = cmd.strip().lower()
    exact = ("lyric", "lyrics", "lyr")
    if low in (":" + e for e in exact):
        if _player is not None:
            _open(_player, None)
        return True

    arg = _strip_prefix(raw_text, (":lyric", ":lyrics", ":lyr"))
    if not arg and not (low.startswith(":lyric") or low.startswith(":lyrics")
                        or low.startswith(":lyr")):
        return False
    if _player is None:
        return True

    arg = arg.strip()
    # Toggle / set auto-scroll:  :lyric auto, :lyric auto=1, :lyric auto=0
    lowarg = arg.lower()
    if lowarg == "auto" or lowarg.startswith("auto="):
        value = lowarg.split("=", 1)[1] if "=" in lowarg else "1"
        _st["auto"] = value not in ("0", "off", "false")
        state = "ON" if _st["auto"] else "OFF"
        _player.add_log("Lyrics auto-scroll: %s" % state)
        return True

    # Path form:  :lyric <path>
    path_arg = arg.strip('"')
    if not path_arg:
        _open(_player, None)
    else:
        expanded = str(os.path.expanduser(os.path.expandvars(path_arg)))
        if os.path.isfile(expanded):
            _open(_player, expanded)
        else:
            _show_error(_player, "Path not found: " + path_arg)
    return True


# Auto-scroll -----------------------------------------------------------------
def _elapsed(player):
    """Current playback position in seconds (0 if not really playing)."""
    try:
        if getattr(player, "is_playing", False):
            return max(0.0, (time_now() - getattr(player, "start_time", 0.0)))
        return max(0.0, getattr(player, "elapsed_at_pause", 0.0))
    except Exception:
        return 0.0


def time_now():
    return _time.time()


def _clip_scroll(max_rows, n):
    lo, hi = 0, max(0, n - max_rows)
    if _st["scroll"] < lo:
        _st["scroll"] = lo
    elif _st["scroll"] > hi:
        _st["scroll"] = hi


def _box_dims(w, h):
    """Shared box geometry: returns (bw, bh, top, foot, max_rows)."""
    bw = max(min(78, w - 4), 34)
    bh = max(min(24, h - 2), 14)
    top = 2                       # first usable lyric row (below header)
    foot = bh - 1
    max_rows = max(foot - top, 1)
    return bw, bh, top, foot, max_rows


def _update_auto_scroll_elapsed(elapsed, max_rows, n):
    """Refresh _st['active'] and center-scroll around it for the given time."""
    timeline = _st["timeline"]
    active = -1
    if timeline:
        best = None
        for t, idx in timeline:
            if t <= elapsed:
                best = idx
            else:
                break
        active = best if best is not None else timeline[0][1]
    _st["active"] = active

    if active >= 0:
        # keep the active line ~40% down the visible window (Spotify style)
        target = int(max_rows * 0.40)
        _st["scroll"] = active - target
        _clip_scroll(max_rows, n)


def on_tick():
    if _st["mode"] != MODE_VIEW or not _st["auto"]:
        return
    try:
        w = _player.screen.width if (_player is not None and _player.screen) else 120
        h = _player.screen.height if (_player is not None and _player.screen) else 30
    except Exception:
        w, h = 120, 30
    _bw, _bh, top, foot, max_rows = _box_dims(w, h)
    _update_auto_scroll_elapsed(_elapsed(_player), max_rows, len(_st["lines"]))


# Drawing ---------------------------------------------------------------------
def on_draw(screen):
    from asciimatics.screen import Screen
    if _st["mode"] == MODE_NONE:
        return
    try:
        if _st["mode"] == MODE_ERR:
            _draw_error(screen, Screen)
        else:
            _draw_lyrics(screen, Screen)
    except Exception:
        pass


def _draw_lyrics(screen, Scr):
    w, h = screen.width, screen.height
    bw, bh, top, foot, max_rows = _box_dims(w, h)
    bx, by = (w - bw) // 2, (h - bh) // 2
    px, pw = bx + 1, bw - 2

    header = " LYRICS " + (("- " + _st["title"]) if _st["title"] else "")
    if _player is not None and hasattr(_player, "draw_box"):
        try:
            _player.draw_box(bx, by, bw, bh, header,
                             Scr.COLOUR_MAGENTA, rounded=True,
                             bg=Scr.COLOUR_BLACK)
        except Exception:
            pass

    _p(screen, Scr, px, by + 1, dw_truncate(_st["source"], pw - 2),
       Scr.COLOUR_CYAN)
    _p(screen, Scr, px, by + top - 1, "=" * (pw - 2), Scr.COLOUR_MAGENTA)

    slot_y = by + top
    foot_y = by + foot
    n = len(_st["lines"])
    start = min(max(0, _st["scroll"]), max(0, n - max_rows)) if n else 0

    active = _st["active"]
    for row, i in enumerate(range(start, min(start + max_rows, n))):
        shown = dw_truncate(_st["lines"][i], pw - 4)
        if i == active:
            # highlight the currently-sung line (Spotify style)
            _p(screen, Scr, px + 1, slot_y + row, shown,
               Scr.COLOUR_BLACK, Scr.A_BOLD, Scr.COLOUR_YELLOW)
        else:
            _p(screen, Scr, px + 1, slot_y + row, shown, Scr.COLOUR_WHITE)

    if n > max_rows:
        bar_visible = max_rows
        thumb_h = max(1, int(max_rows * bar_visible / max(n, 1)))
        thumb_y = int((bar_visible - thumb_h) *
                      start / max(n - bar_visible, 1))
        for k in range(thumb_h):
            _p(screen, Scr, bx + bw - 1, slot_y + thumb_y + k,
               "│", Scr.COLOUR_MAGENTA, Scr.A_BOLD)

    pos = "[%d-%d / %d]" % (start + 1, min(start + max_rows, n), n)
    autostr = "AUTO" if _st["auto"] else "MANUAL"
    hint = "AUTO:" + autostr + "  UP/DN scroll  CTRL+B close"
    _p(screen, Scr, bx + 1, foot_y, pos, Scr.COLOUR_MAGENTA, Scr.A_BOLD)
    _p(screen, Scr, px + 6, foot_y, hint, Scr.COLOUR_CYAN)


def _draw_error(screen, Scr):
    w, h = screen.width, screen.height
    bw = max(min(72, w - 4), 40)
    bh = 10
    bx, by = (w - bw) // 2, (h - bh) // 2
    px, pw = bx + 1, bw - 2
    if _player is not None and hasattr(_player, "draw_box"):
        try:
            _player.draw_box(bx, by, bw, bh, " LYRICS ",
                             Scr.COLOUR_RED, rounded=True,
                             bg=Scr.COLOUR_BLACK)
        except Exception:
            pass
    _p(screen, Scr, px, by + 3, center_fit(_st["error"], pw - 2),
       Scr.COLOUR_RED, Scr.A_BOLD)
    _p(screen, Scr, px, by + 5, center_fit("CTRL+B close", pw - 2),
       Scr.COLOUR_CYAN)


# Key handling ----------------------------------------------------------------
_CLOSE = {"ctrl+b", "escape", "esc", "\x1b"}

# Playback actions handled by the main loop; letting them through keeps music
# controls (pause, volume, seek, mute) working while the lyrics window is open.
_PASSTHROUGH = {"play_pause", "mute", "volume_up", "volume_down",
                "seek_forward", "seek_backward"}

def on_key(key_str, action):
    if _st["mode"] == MODE_NONE:
        return False
    ks = (key_str or "").lower()
    if ks in _CLOSE:
        _st["mode"] = MODE_NONE
        return True
    if _st["mode"] == MODE_VIEW:
        if action in _PASSTHROUGH:
            # Let the player handle music controls while we stay open.
            return False
        if action == "up" and _st["scroll"] > 0:
            # manual scroll turns auto-follow off so the view stays put
            _st["auto"] = False
            _st["scroll"] -= 1
            return True
        if action == "down":
            _st["auto"] = False
            _st["scroll"] += 1
            return True
    return True


# Setup -----------------------------------------------------------------------
def setup(player):
    global _player
    _player = player
    player.plugin_hooks["on_command"].append(handle_command)
    player.plugin_hooks["on_draw"].append(on_draw)
    player.plugin_hooks["on_key"].append(on_key)
    player.plugin_hooks["on_tick"].append(on_tick)
    player.plugin_hooks["on_play"].append(on_play)
    player.add_log("Lyrics plugin loaded (:lyric)")
