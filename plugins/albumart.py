"""
PLUGIN :: METADATA & ALBUM ART EXPORT v2
==========================================
Modern, export-first replacement for the old inline ASCII viewer.

Type :meta in the command bar to open the now-playing overlay showing
the song's metadata and whether an embedded cover exists.

Export the real embedded cover image to any folder you choose:
  :meta export "C:/Users/you/Pictures"   -> save cover into a folder
  :meta export "C:/Users/you/Pics/cov.png" -> save cover to a file path
  :export <path>                          -> shortcut form

If the target is a directory, the plugin writes a safe, unique filename
(artist - title.ext). If it is a file path, it writes exactly there.
The cover is saved using its original format (JPEG/PNG/...); if Pillow is
available it is also exported as an extra high-quality PNG copy.

Never paints outside its box and uses only asciimatics' 16-colour range,
so it can never crash the renderer.
"""

import os
import re
from pathlib import Path

try:
    import tinytag
except ImportError:
    tinytag = None

# ---------------------------------------------------------------------------
# Optional Pillow (used only for format detection / PNG re-encode on export)
# ---------------------------------------------------------------------------
_PIL = None
try:
    from PIL import Image as _Image
    _PIL = _Image
except ImportError:
    pass

_player = None

_ST = {"mode": "none", "title": "", "artist": "", "album": "", "length": "",
       "file": "", "idx": "", "has_art": False, "art_ext": "",
       "art_size": 0, "dims": "", "status": ""}


# ---------------------------------------------------------------------------
# Width helpers (CJK-aware)
# ---------------------------------------------------------------------------
def _dw(ch):
    import unicodedata
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def _dws(s):
    return sum(_dw(c) for c in str(s))


def _tr(s, mw):
    o, w = [], 0
    for c in str(s):
        cw = _dw(c)
        if w + cw > mw:
            break
        o.append(c); w += cw
    return "".join(o)


def _cp(screen, x, y, t, fg, attr=None, bg=None):
    try:
        sw, sh = screen.width, screen.height
        x, y = int(x), int(y)
        if y < 0 or y >= sh or x >= sw or x < 0:
            return
        t = _tr(t, sw - x)
        if bg is not None:
            screen.print_at(t, x, y, fg, attr or 0, bg=bg)
        elif attr is not None:
            screen.print_at(t, x, y, fg, attr)
        else:
            screen.print_at(t, x, y, fg)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Embedded cover extraction
# ---------------------------------------------------------------------------
def _extract_cover(src):
    """Return (data_bytes, mime) for the embedded cover, or (None, '')."""
    if tinytag is None:
        return None, ""
    try:
        tag = tinytag.TinyTag.get(str(src), image=True)
    except Exception:
        return None, ""
    art = getattr(tag, "images", None)
    if not art:
        return None, ""
    arts = []
    try:
        if hasattr(art, "as_dict"):
            ad = art.as_dict()
            if isinstance(ad, dict):
                for key in ("front_cover", "media", "other", "back_cover"):
                    v = ad.get(key)
                    if v:
                        arts.extend(v if isinstance(v, list) else [v])
        for cand in (getattr(art, "any", None),):
            if isinstance(cand, list):
                arts += cand
            elif cand is not None:
                arts.append(cand)
        if not arts:
            arts = [art]
    except Exception:
        arts = [art]
    for img in arts:
        try:
            d = img.get("data") if isinstance(img, dict) else img.data
        except Exception:
            continue
        if d:
            m = (img.get("mime_type", "") if isinstance(img, dict)
                 else getattr(img, "mime_type", "")) or ""
            return bytes(d), m
    return None, ""


def _mime_to_ext(mime, data):
    if mime:
        sub = mime.lower().split("/")[-1]
        clean = re.sub(r"[^a-z0-9]", "", sub)
        if clean in ("jpeg", "jpg"):
            return "jpg"
        if clean == "png":
            return "png"
        if clean in ("webp", "bmp", "gif"):
            return clean
    if data and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data and data[:2] == b"\xff\xd8":
        return "jpg"
    return "img"


# ---------------------------------------------------------------------------
# Safe file writing
# ---------------------------------------------------------------------------
def _safe_name(base, ext):
    name = "".join(c for c in base if c not in '\\/:*?"<>|')
    name = re.sub(r"\s+", " ", name).strip(" .") or "cover"
    name = name[:80].rstrip(" .")
    return name + "." + ext


def _unique_path(folder, base, ext):
    cand = folder / _safe_name(base, ext)
    if not cand.exists():
        return cand
    stem, i = cand.stem, 1
    while True:
        cand = folder / ("%s_%d.%s" % (stem, i, ext))
        if not cand.exists():
            return cand
        i += 1


def _export_cover(src, target):
    """Export embedded cover to target (dir or file). Returns a message."""
    data, mime = _extract_cover(src)
    if not data:
        return "No album art embedded in this file.", False
    raw = str(target).strip().strip('"').strip("'")
    if not raw:
        return "Export path is empty.", False
    try:
        raw = os.path.expanduser(os.path.expandvars(raw))
        t = Path(raw)
    except Exception:
        return "Invalid path.", False
    is_dir_target = (t.is_dir() or str(t).endswith((os.sep, "/")) or not t.suffix)
    if is_dir_target:
        folder = t if t.is_dir() else t.parent
        if not t.suffix:
            folder = t
        ext = _mime_to_ext(mime, data)
        artist = _ST.get("artist", "").strip()
        title = _ST.get("title", "").strip()
        if artist and artist not in ("Unknown", "Unknown Artist"):
            base = "%s - %s" % (artist, title or os.path.basename(src))
        else:
            base = title or os.path.basename(src)
        out = _unique_path(folder, base, ext)
    else:
        out = t
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    except Exception as e:
        return "Export failed: %s" % str(e)[:40], False
    kb = len(data) / 1024.0
    msg = "Saved cover -> %s (%.1f KB, %s)" % (out.name, kb, _mime_to_ext(mime, data).upper())

    # If Pillow is present, also write a clean PNG copy for maximum compat
    if _PIL is not None and _mime_to_ext(mime, data) != "png":
        try:
            import io as _io
            im = _PIL.open(_io.BytesIO(data))
            png_target = out.with_suffix(".png")
            if not png_target.exists():
                im.save(png_target, "PNG")
                msg += "  (+ PNG copy)"
        except Exception:
            pass
    return msg, True


# ---------------------------------------------------------------------------
# Open / refresh the modal for the current song
# ---------------------------------------------------------------------------
def _open(player):
    src = getattr(player, "current_filepath", None)
    if not src:
        _ST.update(mode="error", title="Nothing is playing.", status="")
        return
    md = player.metadata or {}
    title = md.get("title", "") or os.path.basename(str(src))
    artist = md.get("artist", "") or "Unknown"
    album = md.get("album", "") or "Unknown"
    fl = player.duration or 0
    mm, ss = divmod(int(fl), 60)
    length = "%d:%02d" % (mm, ss)
    has_art = False
    art_ext, art_size, dims = "", 0, ""
    try:
        data, mime = _extract_cover(src)
        if data:
            has_art = True
            art_ext = _mime_to_ext(mime, data).upper()
            art_size = len(data)
            if _PIL is not None:
                try:
                    import io as _io
                    w, h = _PIL.open(_io.BytesIO(data)).size
                    dims = "%dx%d" % (w, h)
                except Exception:
                    pass
    except Exception:
        pass
    _ST.update(mode="view", title=title, artist=artist, album=album,
               length=length, file=os.path.basename(str(src)),
               idx="%d/%d" % (player.current_index + 1, len(player.display_playlist)) if player.display_playlist else "",
               has_art=has_art, art_ext=art_ext, art_size=art_size, dims=dims,
               status="")
    player.add_log("Metadata viewer opened")


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------
def _draw(screen):
    from asciimatics.screen import Screen as Scr
    if _ST["mode"] == "none":
        return
    w, h = screen.width, screen.height
    bw = max(46, min(80, w - 4))
    bh = max(18, min(h - 2, 24))
    bx = (w - bw) // 2
    by = (h - bh) // 2

    if _ST["mode"] == "error":
        try:
            _player.draw_box(bx, by, bw, 8, " META ", Scr.COLOUR_RED, rounded=True)
        except Exception:
            pass
        _cp(screen, bx + 2, by + 3, _tr(_ST["title"], bw - 4), Scr.COLOUR_RED, Scr.A_BOLD)
        _cp(screen, bx + 2, by + 5, "Type :meta export <path>  |  CTRL+B close", Scr.COLOUR_CYAN)
        return

    try:
        _player.draw_box(bx, by, bw, bh, " SONG METADATA ", Scr.COLOUR_MAGENTA, rounded=True)
    except Exception:
        pass

    rows = [
        ("TITLE  : ", _ST["title"], Scr.COLOUR_YELLOW, Scr.A_BOLD),
        ("ARTIST : ", _ST["artist"], Scr.COLOUR_CYAN, Scr.A_NORMAL),
        ("ALBUM  : ", _ST["album"], Scr.COLOUR_GREEN, Scr.A_NORMAL),
        ("LENGTH : ", _ST["length"], Scr.COLOUR_WHITE, Scr.A_NORMAL),
        ("FILE   : ", _ST["file"], Scr.COLOUR_WHITE, Scr.A_NORMAL),
        ("[TRACK : ", _ST["idx"] + "]", Scr.COLOUR_MAGENTA, Scr.A_BOLD),
    ]
    avail_w = bw - 4
    cy = by + 2
    for lbl, val, color, attr in rows:
        shown = _tr(lbl + val, avail_w)
        try:
            screen.print_at(" " * avail_w, bx + 2, cy)
            screen.print_at(shown, bx + 2, cy, color, attr)
        except Exception:
            pass
        cy += 1

    cy += 1
    if _ST["has_art"]:
        art_txt = "Art : embedded (%s, %s, %.1f KB)" % (
            _ST["art_ext"], _ST["dims"] or "?", _ST["art_size"] / 1024.0)
        _cp(screen, bx + 2, cy, _tr(art_txt, avail_w), Scr.COLOUR_GREEN, Scr.A_BOLD)
    else:
        _cp(screen, bx + 2, cy, _tr("Art : none embedded in this file", avail_w), Scr.COLOUR_RED)
    cy += 1
    if _ST["status"]:
        _cp(screen, bx + 2, cy, _tr("> " + _ST["status"], avail_w), Scr.COLOUR_CYAN)
        cy += 1

    hint = " :meta export <path>  |  CTRL+B close "
    try:
        screen.print_at(_tr(hint, bw - 2).center(bw - 2), bx + 1, by + bh - 1,
                        Scr.COLOUR_WHITE, Scr.A_BOLD, bg=Scr.COLOUR_MAGENTA)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------
_CLOSE = {"ctrl+b", "escape", "esc", "\x1b"}


def _on_key(key_str, action):
    if _ST["mode"] == "none":
        return False
    ks = (key_str or "").lower()
    if ks in _CLOSE:
        _ST["mode"] = "none"
        return True
    return True


# ---------------------------------------------------------------------------
# Command handling  :meta ...   :export ...
# ---------------------------------------------------------------------------
def _export_cmd(player, target):
    src = getattr(player, "current_filepath", None)
    if not src:
        _ST.update(mode="error", title="Nothing is playing.", status="")
        player.add_log("Meta: nothing to export")
        return
    msg, ok = _export_cover(src, target)
    _ST["status"] = msg
    if _ST["mode"] == "none":
        _open(player)
    player.add_log("Meta: " + msg)


def _on_command(cmd, raw_text):
    low = cmd.strip().lower()
    matches = low in (":meta", ":metadata", ":art", ":cover") or \
        low.startswith(":meta ") or low.startswith(":metadata ") or \
        low.startswith(":art ") or low.startswith(":cover ")
    if not matches:
        return False
    if _player is None:
        return True

    tgt = ""
    lowraw = raw_text.lower().strip()
    export_prefixes = (":meta export ", ":metadata export ", ":art export ",
                       ":cover export ", ":export ")
    for prefix in export_prefixes:
        if lowraw.startswith(prefix):
            tgt = raw_text[lowraw.find(prefix) + len(prefix):]
            tgt = tgt.strip()
            break

    if tgt:
        _export_cmd(_player, tgt)
    else:
        _open(_player)
    return True


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
def setup(player):
    global _player
    _player = player
    player.plugin_hooks["on_command"].append(_on_command)
    player.plugin_hooks["on_draw"].append(_draw)
    player.plugin_hooks["on_key"].append(_on_key)
    player.add_log("Metadata plugin loaded (:meta | :meta export <path>)" +
                   (" [Pillow]" if _PIL else ""))
