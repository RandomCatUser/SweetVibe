# Supported Defaults

This document covers two things:

1. **Default supported audio file extensions** (which files the player recognizes).
2. **The lyrics plugin's two follow-along features** (auto-scroll and switching with the music).

Both are handled by the built-in players and plugins, so they work out of the box.

---

## 1. Default audio file extensions

The player recognizes files by their extension (case-insensitive). Only matching
files show up in the file browser / playlists and are playable.

Defined once in `main.py` as `AUDIO_EXTS`:

| Extension | Format |
| --- | --- |
| `.mp3`  | MPEG Audio Layer 3 |
| `.wav`  | Waveform Audio |
| `.flac` | Free Lossless Audio Codec |
| `.m4a`  | MPEG-4 Audio |
| `.ogg`  | Ogg Vorbis / Opus container |
| `.opus` | Opus codec |
| `.aac`  | Advanced Audio Coding |

To extend the list, add entries to the `AUDIO_EXTS` set in `main.py`. The
recognized extensions apply across the whole interface: opening folders,
searching, and building playlists all respect this set.

---

## 2. Lyrics plugin features

The lyrics plugin (`plugins/lyrics.py`) shows the current track's embedded
lyrics in a modal. Two behaviors help you follow along with what's playing.

### 2a. Spotify-style auto-scroll

With the lyrics modal open, the current line is highlighted and kept near the
middle of the box, tracking playback in real time:

- **Timed (LRC) lyrics** (`[mm:ss.xx]` timestamps) sync to the exact wall-clock
  position of the song.
- **Untimed lyrics** advance proportionally to the song's duration.

- The footer shows whether it is busy following: `AUTO:AUTO` or `AUTO:MANUAL`.

Toggle it with:

| Command | Effect |
| --- | --- |
| `:lyric auto=1` / `:lyric auto` | Turn auto-scroll **on** (default) |
| `:lyric auto=0` | Turn auto-scroll **off** |

Manual Up/Down scrolling also disables auto-follow so the view stays put;
use `:lyric auto=1` to start following again. Toggle state is per-session.

### 2b. Switching with the music

If the lyrics modal is open and the currently playing song changes, the lyrics
automatically reload for the new track — you never have to close and re-open.

- It only switches when the modal is already open; a closed modal is left alone.
- Your auto-scroll on/off preference is preserved across song changes.

### 2c. Playback controls keep working

While the lyrics window is open you can still control the music without closing
it — the player's normal playback keys are passed straight through:

| Key | Action |
| --- | --- |
| `Space` | Play / pause |
| `+` / `=` | Volume up |
| `-` / `_` | Volume down |
| `→` / `←` | Seek forward / backward (±10s) |
| `m` | Mute / unmute |
| `↑` / `↓` | Scroll the lyrics (turns auto-follow off) |
| `Ctrl+B` / `Esc` | Close the lyrics window |

---

## Quick reference

```text
:lyric                 # show current song's lyrics
:lyric <path>          # show lyrics for a specific file
:lyric auto=1|auto     # resume auto-scroll (default)
:lyric auto=0          # stop auto-scroll (manual browsing)
```

Audio formats and the lyrics follow-along behavior both come enabled by default.
