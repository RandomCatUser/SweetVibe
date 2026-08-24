
<img src="https://socialify.git.ci/RandomCatUser/SweetVibe/image?description=1&font=JetBrains+Mono&language=1&name=1&pattern=Floating+Cogs&theme=Dark" alt="SweetVibe" width="640" height="320" />

# SweetVibe Music Player

SweetVibe is a sleek, terminal-based (TUI) music player built with Python. It features a retro-modern aesthetic, robust audio playback, a dynamic audio visualizer, and full in-app keybind customization. 

## Features

* **Retro TUI:** High-performance terminal interface using `asciimatics`.
* **Native Audio Engine:** Uses `just_playback` for reliable, low-latency audio playback without external dependencies like FFmpeg.
* **Custom Keybinds:** Fully customizable keybindings via an in-app editor. Change any action, add multiple keys, or reset to defaults.
* **Dynamic UI:** The help menu and bottom status bar dynamically read from your custom keybinds, so the hints always match your configuration.
* **Smart Library:** Flawless CJK (Chinese, Japanese, Korean) character support without visual artifacts or "bleeding." Includes a PC-wide scanner to find all audio files.
* **Dynamic Spectrum:** An advanced 4-harmonic audio visualizer with falling peak caps that reacts to your music.
* **Auto-Updates:** Checks the latest GitHub release and downloads the Windows installer when a newer version is available.

## Quick Start

### For Developers

If you want to run the script directly:

1. **Install Dependencies:**
   ```bash
   pip install asciimatics tinytag just_playback
   ```
2. **Run the App:**
   ```bash
   python main.py
   ```

### Build Windows EXE

Run `build.ps1` in PowerShell from the project folder. It creates the portable app in `dist\release\SweetVibe` and creates `dist\installer\Setup_Windows_x64.exe` when Inno Setup 6 is installed.

## Default Controls

All controls can be customized in-app. Below are the factory defaults.

| Key | Action |
| --- | --- |
| `↑` / `↓` | Navigate library |
| `ENTER` | Open folder / Play file |
| `SPACE` | Play / Pause |
| `→` / `←` | Seek +10s / -10s |
| `+` / `-` | Volume Up / Down |
| `M` | Mute / Unmute |
| `TAB` | Cycle Mode (Browse / PC-Scan) |
| `S` | Toggle Shuffle |
| `R` | Toggle Repeat |
| `BACKSPACE` / `ESC` / `CTRL+B` | Go back / Exit mode |
| `CTRL+F` / `/` | Search / Filter songs |
| `CTRL+O` / `P` | Open Path / Command Bar |
| `Q` / `CTRL+C` | Quit Player |

## In-App Keybind Editor

SweetVibe includes a built-in keybind editor. Open the command bar (`CTRL+O` or `P`) and type `:keybinds`.

* **↑ / ↓:** Navigate the action list.
* **ENTER:** Bind a new key to the selected action (press any key to bind it).
* **BACKSPACE:** Remove the last bound key from the selected action.
* **D:** Delete the last bound key (alternative to backspace).
* **R:** Reset ALL keybinds to factory defaults (requires confirmation).
* **ESC / CTRL+B:** Close the editor.

*Note: The editor automatically saves to `~/.sweetvibe_keybinds` (a plain-text file). You can also edit this file manually!*

## Command Bar Commands

Open the command bar by pressing `CTRL+O` or `P`, or typing `/` or `CTRL+F` for search.

* `:help` - Open the Help & Shortcuts menu.
* `:about` - View About SweetVibe.
* `:update` - Download and install the latest version from GitHub.
* `:keybinds` - Open the in-app keybind editor.
* *(Or type any folder path like `C:\Music` to jump straight to it)* 

## License

Distributed under the `Apache License 2.0`. See `LICENSE` for more information.
