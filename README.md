# SweetVibe Music Player

SweetVibe is a terminal music player for Windows and Python. It provides local
music browsing, PC-wide scanning, playlists, audio visualization, customizable
keybindings, automatic updates, and optional YouTube discovery with yt-dlp.

## Features

- Terminal interface built with `asciimatics`.
- Audio playback through `just_playback`.
- Browse the included `songs` folder or scan the whole PC for audio files.
- Audio spectrum visualization with automatic, reactive, and script modes.
- Search, filter, shuffle, repeat, seek, volume, and mute controls.
- In-app keybinding editor saved to `~/.sweetvibe_keybinds`.
- YouTube search and downloads through the Python plugin in `plugins/online.py`.
- Download caching, progress reporting, retry handling, playlists, and
  download-folder selection.
- Background GitHub release update checks.

## Documentation

The project ships a documentation set under `docs/`:

| Document | What it covers |
| --- | --- |
| [docs/plugins.md](docs/plugins.md) | Write plugins - hooks, drawing, commands, online streams. |
| [docs/architecture.md](docs/architecture.md) | Source layout and where to customize code. |
| [docs/keybindings.md](docs/keybindings.md) | Remap keys and edit `~/.sweetvibe_keybinds`. |
| [docs/spectrum.md](docs/spectrum.md) | Spectrum modes and color customization. |
| [docs/building.md](docs/building.md) | Build the EXE/installer (and avoid AV false positives). |

## Run From Source

Install the required packages:

```bash
python -m pip install asciimatics tinytag just_playback numpy soundfile
```

`numpy` and `soundfile` enable the real audio-reactive spectrum and are
optional. To enable YouTube features when running from source, install yt-dlp:

```bash
python -m pip install --user --upgrade yt-dlp
```

Start the player from the project folder:

```bash
python main.py
```

The application automatically loads Python plugins from `plugins/`. A plugin
must contain a `setup(player)` function. See
[docs/plugins.md](docs/plugins.md) for the plugin API.

## Windows Build

Requirements:

- Python with the project dependencies installed.
- PyInstaller available as `pyinstaller`.
- Inno Setup 6 installed as `ISCC.exe`.
- yt-dlp on your PATH (it is bundled).

Run either build script from the project folder:

```bat
build.bat
```

```powershell
.\build.ps1
```

The build performs two steps:

1. PyInstaller creates the portable application in `dist\SweetVibe`.
2. Inno Setup creates `dist\installer\Setup_Windows_x64_v1.4.1.exe`.

A complete walkthrough is in [docs/building.md](docs/building.md), including
how UPX/version info affect antivirus false-positive detection.

## Default Controls

All controls can be customized in the keybinding editor (see
[docs/keybindings.md](docs/keybindings.md)).

| Key | Action |
| --- | --- |
| `Up` / `Down` | Navigate the library |
| `Enter` | Open a folder or play a file |
| `Space` | Play or pause |
| `Right` / `Left` | Seek forward or backward |
| `+` / `-` | Increase or decrease volume |
| `M` | Mute or unmute |
| `Tab` | Cycle Browse and PC-Scan modes |
| `S` | Toggle shuffle |
| `R` | Toggle repeat |
| `Backspace` / `Esc` / `Ctrl+B` | Go back or close the current mode |
| `Ctrl+F` / `/` | Search or filter songs |
| `Ctrl+O` / `P` | Open the command bar |
| `Q` / `Ctrl+C` | Quit |

## Command Bar

Open the command bar with `Ctrl+O` or `P`.

Built-in commands:

| Command | Description |
| --- | --- |
| `:help` | Show help and shortcuts |
| `:about` | Show application information |
| `:update` | Check for and install the latest GitHub release |
| `:keybinds` / `:settings` | Open the settings panel (keybinds + colors) |
| `<folder path>` | Navigate directly to a folder |

Commands provided by the online plugin (`plugins/online.py`):

| Command | Description |
| --- | --- |
| `:yt <query>` / `:sc <query>` | Search YouTube and choose a track |
| `:pl list` | List saved playlists |
| `:pl save <name>` | Save the current queue |
| `:pl load <name>` | Add a playlist to the queue |
| `:pl play <name>` | Replace the queue and play a playlist |
| `:pl view <name>` | Show playlist tracks |
| `:pl del <name>` | Delete a playlist |
| `:cache info` | Show the download target and cache information |
| `:cache dir` | Show the current download target |
| `:cache dir <path>` | Pin downloads to a folder |
| `:cache dir reset` | Remove the pinned download folder |
| `:cache open` | Open the download folder in Explorer |
| `:cache clear` | Remove legacy temporary cache files |

YouTube downloads use the current Browse folder when possible. A download can
be pinned with `:cache dir <path>`. If yt-dlp is unavailable, the player logs a
setup message instead of crashing.

Commands provided by the lyrics plugin (`plugins/lyrics.py`):

| Command | Description |
| --- | --- |
| `:lyric` / `:lyrics` / `:lyr` | Show the current song's lyrics from its metadata |
| `:lyric <path>` | Show lyrics for a specific audio file |
| `:lyric auto=0` | Turn off Spotify-style auto-scroll |
| `:lyric auto=1` / `:lyric auto` | Turn auto-scroll back on |

Lyrics are read from the metadata embedded in the track and shown in a modal.
Auto-scroll follows the playing audio: timed (LRC) lyrics sync to the exact
timestamp, and untimed lyrics advance proportionally to the song duration. The
current line is highlighted and kept near the middle. When the song changes,
the open lyrics switch to the new track automatically. Scrolling with Up/Down
switches to manual browsing (auto turns off); use `:lyric auto=1` to resume.
Playback controls still work while the window is open (Space = play/pause,
+/- volume, ←/→ seek, m = mute). Chinese, Japanese, and Korean characters are
preserved and kept inside the box.

## Plugin Development

Plugins are ordinary Python files stored in `plugins/`. SweetVibe loads every
`.py` file (or package) beside the executable or `main.py` and calls its
`setup(player)` function. Plugin hooks support commands, key presses,
drawing, ticks, playback requests, playback start, and playback stop.

Read the complete API guide in [docs/plugins.md](docs/plugins.md).

## License

Distributed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
