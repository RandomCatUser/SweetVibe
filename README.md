
# SweetVibe Music Player

SweetVibe is a terminal music player for Windows and Python. It provides local music browsing, PC-wide scanning, playlists, audio visualization, customizable keybindings, automatic updates, and optional YouTube discovery with yt-dlp.

## Features

- Terminal interface built with `asciimatics`.
- Audio playback through `just_playback`.
- Browse the included `songs` folder or scan the PC for audio files.
- Audio spectrum visualization with automatic, reactive, and script modes.
- Search, filter, shuffle, repeat, seek, volume, and mute controls.
- In-app keybinding editor saved to `~/.sweetvibe_keybinds`.
- YouTube search and downloads through the Python plugin in `plugins/online.py`.
- Download caching, progress reporting, retry handling, playlists, and download-folder selection.
- Background GitHub release update checks.

## Run From Source

Install the required packages:

```bash
python -m pip install asciimatics tinytag just_playback numpy soundfile
```

`numpy` and `soundfile` enable the real audio-reactive spectrum and are optional. To enable YouTube features when running from source, install yt-dlp:

```bash
python -m pip install --user --upgrade yt-dlp
```

Start the player from the project folder:

```bash
python main.py
```

The application automatically loads Python plugins from `plugins/`. A plugin must contain a `setup(player)` function. See [docs/plugins.md](docs/plugins.md) for the plugin API.

## Windows Build

Requirements:

- Python with the project dependencies installed.
- PyInstaller available as `pyinstaller`.
- Inno Setup 6 installed as `ISCC.exe`.

Run either build script from the project folder:

```bat
build.bat
```

```powershell
.\build.ps1
```

The build performs two steps:

1. PyInstaller creates the portable application in `dist\SweetVibe`.
2. Inno Setup creates `dist\installer\Setup_Windows_x64.exe`.

The PyInstaller bundle includes the Python files in `plugins/`, including the online music installer helpers. The installer copies those files and then offers a guided online-music setup after installation. If Python is not installed, it downloads and installs Python 3.12 for the current user. It then runs the bundled Python setup, which asks whether to install or update yt-dlp. The setup can be skipped and run again later if needed.

## Default Controls

All controls can be customized in the keybinding editor.

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

| Command | Description |
| --- | --- |
| `:help` | Show help and shortcuts |
| `:about` | Show application information |
| `:update` | Check for and install the latest GitHub release |
| `:keybinds` | Open the keybinding editor |
| `:yt <query>` | Search YouTube and choose a track |
| `:sc <query>` | Alias for YouTube search |
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
| `<folder path>` | Navigate directly to a folder |

YouTube downloads use the current Browse folder when possible. A download can be pinned with `:cache dir <path>`. If yt-dlp is unavailable, the player logs a setup message instead of crashing.

## Plugin Development

Plugins are ordinary Python files stored in `plugins/`. SweetVibe loads every `.py` file beside the executable or `main.py` and calls its `setup(player)` function. Plugin hooks support commands, key presses, drawing, ticks, playback requests, playback start, and playback stop.

Read the complete API guide in [docs/plugins.md](docs/plugins.md).

## License

Distributed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
