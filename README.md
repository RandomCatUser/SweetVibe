`README.MD`
<img src="https://socialify.git.ci/RandomCatUser/SweetVibe/image?description=1&font=JetBrains+Mono&language=1&name=1&pattern=Floating+Cogs&theme=Dark" alt="SweetVibe" width="640" height="320" />

# SweetVibe Music Player

SweetVibe is a sleek, terminal-based (TUI) music player built with Python. It features a retro-modern aesthetic, automatic audio engine setup, and CJK character support for international song titles.

## Features

* Retro TUI: High-performance terminal interface using asciimatics.
* Auto-Engine Setup: Automatically downloads and configures ffplay.exe on first launch if missing.
* Smart Library: Supports CJK (Chinese, Japanese, Korean) characters without visual artifacts or "bleeding."
* Dynamic Spectrum: Visualizer that reacts to your music.
* Shuffle Mode: Easily toggle random playback.

## Quick Start

### For Developers

If you want to run the script directly:

1. Install Dependencies:
`pip install asciimatics tinytag requests`


2. Run the App:
`python main.py`


## Controls

| Key | Action |
| --- | --- |
| UP / DOWN | Navigate library |
| ENTER | Play selected song |
| SPACE | Pause / Resume |
| S | Toggle Shuffle |
| Q | Quit Player |

## Video
![Watch the SweetVibe Preview Video](https://github.com/RandomCatUser/SweetVibe/blob/main/ReadmeAssests/Preview.mp4)

## License

Distributed under the `Apache License 2.0`. See LICENSE for more information.
