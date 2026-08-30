# Keybindings & Settings

SweetVibe lets you remap every key and store a few settings in a single
plain-text file. You can edit it by hand or use the in-app settings panel.

---

## The settings file

Everything lives in one file on your computer:

```text
~/.sweetvibe_keybinds
```

On Windows that is:

```text
C:\Users\<your user>\.sweetvibe_keybinds
```

The file is plain text (not JSON), so it is easy to read and edit. The app
creates it automatically on first run if it does not exist.

---

## File format

The file has two kinds of lines:

- **Keybinding lines**: `action=key1,key2,key3`
- **Settings lines**: `$setting_name=value` (start with `$`)

Lines that start with `#` are comments and are ignored. Blank lines are ignored.

Example file:

```text
# SweetVibe keybindings - format: action=key1,key2,key3
# Settings lines start with $: $setting_name=value

$spectrum_mode=auto
$color_1=blue
$color_2=cyan

up=up
down=down
enter=enter
play_pause=space
quit=q,ctrl+c
```

---

## Key names

Key strings are lowercase. Common ones:

| Key string | Meaning |
| --- | --- |
| `up` / `down` / `left` / `right` | Arrow keys |
| `enter` | Enter |
| `space` | Space bar |
| `esc` | Escape |
| `tab` | Tab |
| `backspace` | Backspace |
| `ctrl+b` / `ctrl+f` / ... | Control combos |
| single characters | e.g. `m`, `p`, `q`, `+`, `/` |

A single action can have multiple keys, separated by commas. For example,
`quit=q,ctrl+c` will quit when you press either `q` or `Ctrl+C`.

---

## Available actions

These are the actions SweetVibe understands (from `DEFAULT_KEYBINDS`):

| Action | Purpose | Default keys |
| --- | --- | --- |
| `up` / `down` | Navigate the list | `up` / `down` |
| `enter` | Open folder / play file | `enter` |
| `back` | Go back / close mode | `backspace, ctrl+b, esc` |
| `play_pause` | Play or pause | `space` |
| `volume_up` | Increase volume | `+, =` |
| `volume_down` | Decrease volume | `-, _` |
| `seek_forward` | Seek forward | `right` |
| `seek_backward` | Seek backward | `left` |
| `mute` | Mute / unmute | `m` |
| `search` | Open search / filter | `ctrl+f, /` |
| `open_path` | Open the command bar | `ctrl+o, p` |
| `shuffle` | Toggle shuffle | `ctrl+e, s` |
| `repeat` | Toggle repeat | `r` |
| `quit` | Quit the app | `q, ctrl+c` |
| `mode_switch` | Toggle Browse / PC-Scan | `tab` |
| `toggle_mouse` | Toggle mouse support | `ctrl+m` |
| `jump_music` | Jump to the music panel | `1` |
| `jump_docs` | Jump to the docs panel | `2` |

You can add a new action by giving it any name and binding a key; the app merges
your file with the built-in defaults, so unknown-but-custom actions are kept.

---

## Settings values

Settings lines start with `$`:

| Setting | Values | Purpose |
| --- | --- | --- |
| `$spectrum_mode` | `auto`, `reactive`, `script` | Visualizer mode (see spectrum.md) |
| `$color_1` .. `$color_5` | `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white` | Spectrum bar colors |

---

## Editing in the app

You do not have to edit the file by hand. Open the settings panel:

1. Press `Ctrl+O` (or `P`) to open the command bar.
2. Type `:settings` (or `:keybinds`) and press Enter.

In the settings panel you can remap keys interactively (it captures the next key
you press), change the spectrum mode, and pick custom colors. Everything you
change is written back to `~/.sweetvibe_keybinds` automatically.

There is also a **reset** option inside the panel that restores all defaults.

---

## Advanced notes

- The app merges your file with `DEFAULT_KEYBINDS`, so you never need to list
  every action - only the ones you want to change.
- Editing the file while the app is running has no effect until the next start,
  or until you use the in-app reset/save actions.
- The file is stored in your home directory, not next to the executable, so it
  survives app updates and reinstalls.

For the underlying code (loading, saving, merging, and pretty-printing keys),
see `load_keybinds`, `save_keybinds`, and `add_keybind` in `main.py`. The
reference copy of the defaults is in `keybindings.json` at the project root.
