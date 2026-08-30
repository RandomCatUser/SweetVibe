# SweetVibe Source Code Guide

This document explains how the SweetVibe codebase is organized so you can
customize the source safely and know exactly where to look for the thing you
want to change.

Most customization falls into two categories:

- **Configuration without code** - edit files SweetVibe reads at runtime
  (keybindings, colors, spectrum mode). See
  [docs/keybindings.md](keybindings.md) and [docs/spectrum.md](spectrum.md).
- **Code changes** - edit `main.py` or write a plugin. See
  [docs/plugins.md](plugins.md) and the layout below.

---

## Repository layout

```text
main.py              The entire player application (single file).
main.spec            PyInstaller build configuration.
build.bat            Windows build script (PyInstaller + Inno Setup).
build.ps1            PowerShell build script (same, alternative).
setup.iss            Inno Setup installer script.
keybindings.json     Reference copy of default controls (informational).
ico.ico              Application icon.
installer.ico        Installer icon.
uninstaller.ico      Uninstaller icon.
README.md            Project readme.
LICENSE              Apache 2.0 license.
songs/               Bundled local music folder.
plugins/             Loaded automatically at startup (see plugins.md).
  online.py              YouTube search/download plugin.
  setup_yt_dlp.py        yt-dlp setup helper.
  setup_online.ps1       Online feature setup script (used by installer).
docs/                This documentation set.
dist/                Build output (executable + installer).
build/               PyInstaller intermediate build files.
```

### `main.py` - a single-file application

The whole player lives in one file, `main.py` (~2000 lines). It is organized
roughly top to bottom as:

1. **Imports and optional dependencies** (lines ~1-35). Core imports are
   `asciimatics`, `tinytag`, `just_playback`; if any are missing the app exits
   with a message. `numpy` + `soundfile` are optional and only enable the
   real audio-reactive spectrum.

2. **Constants** (lines ~37-110). This is one of the most useful sections to
   customize:
   - `AUDIO_EXTS` - accepted file extensions for scanning.
   - `CURRENT_VERSION` - reported version string.
   - `SPECTRUM_AUTO` / `SPECTRUM_REACTIVE` / `SPECTRUM_SCRIPT` - spectrum mode
     identifiers.
   - `COLOR_MAP` - color name -> asciimatics color value.
   - `DEFAULT_COLORS` - the five spectrum bar colors.
   - `DEFAULT_KEYBINDS` - default action -> keys mapping.

3. **Global helpers** (`print_goodbye`, `check_for_updates_async`, ...).

4. **`class KityPlayer`** (line 180) - the core. It stores all state in
   `__init__` and exposes methods for playback, navigation, scanning, settings,
   and drawing. This is the object given to plugins.

5. **The `demo` function and main loop** (bottom of the file) - creates the
   asciimatics `Screen`, instantiates `KityPlayer`, and runs the event loop.

6. `if __name__ == "__main__"` - installs the SIGINT handler and wraps
   `demo` in `Screen.wrapper`.

---

## How the app boots

The entry point is:

```python
Screen.wrapper(demo)          # sets up terminal, calls demo(screen)
```

`demo` creates the player:

```python
player = KityPlayer(screen)
```

`KityPlayer.__init__` does, in order:

1. Stores the asciimatics `Screen` and resolves the music folder
   (`APP_DIR / "songs"`).
2. Initializes empty state: `all_items`, `display_playlist`,
   `current_index`, playback flags, volume, metadata.
3. Kicks off a background thread that checks GitHub for updates.
4. Loads keybindings and color settings from `~/.sweetvibe_keybinds`.
5. Creates the `Playback` object (from `just_playback`).
6. Starts the spectrum analysis thread.
7. Builds the `plugin_hooks` dictionary.
8. Scans the music folder (`update_file_list`).
9. Loads plugins from `plugins/` (`load_plugins`).

Then the main loop alternates three jobs every frame:

```python
event = screen.get_event()    # input
player.draw()                 # paint the UI
for hook in plugin_hooks["on_tick"]:  # per-frame plugin work
```

---

## Customization cheatsheet

| What you want | Where to look |
| --- | --- |
| Change accepted audio extensions | `AUDIO_EXTS` constant (main.py:37) |
| Change the default volume | `self.volume = 65` in `__init__` |
| Change default keybindings | `DEFAULT_KEYBINDS` (main.py:90) |
| Change spectrum colors | `DEFAULT_COLORS` / `COLOR_MAP` (main.py:57-74) |
| Add / change commands | the command `if cmd == ...` block in `demo` |
| Change the music folder | `self.base_dir = APP_DIR / "songs"` |
| Add a feature without touching core | write a plugin (see plugins.md) |
| Change the visualizer behavior | `cycle_spectrum_mode` and `spectrum_loop` |
| Change the UI panels/layout | `draw()` and its helper draw methods |
| Change the about / help text | `show_about` / `show_help` drawing code |

---

## Where the plugin hooks are invoked

The hook calls are spread through `main.py`:

- `on_play_request` - in `play_index` (before default playback).
- `on_play` - right after a local song starts.
- `on_stop` - in `stop`.
- `on_draw` - at the end of `draw()`.
- `on_key` - in the main event loop when a key is pressed.
- `on_command` - in the command-bar Enter handler.
- `on_tick` - the end of the main loop, every frame.

If you are debugging a plugin, these are the exact call sites to inspect.

---

## Building an executable / installer

The release build has two steps: PyInstaller produces a portable application,
then Inno Setup wraps it into an installer. A full walkthrough (including the
Trojan-false-positive fix) is in [docs/building.md](building.md).
