# Audio Spectrum & Colors

SweetVibe draws an audio visualizer with configurable modes and colors. This
guide explains the three spectrum modes and how to customize the look - both
from the in-app settings and by editing the source.

---

## Spectrum modes

There are three modes. Use the in-app settings panel or set
`$spectrum_mode=...` in `~/.sweetvibe_keybinds`:

| Mode | Identifier | Behavior |
| --- | --- | --- |
| Auto | `auto` | Picks the best mode automatically. |
| Reactive | `reactive` | Real-time visualization driven by the actual audio. Requires `numpy` and `soundfile`. |
| Script | `script` | A scripted/animated fallback that does not need audio analysis. |

`cycle_spectrum_mode()` in `main.py` cycles through
Auto -> Reactive -> Script. If you choose Reactive without `numpy` + `soundfile`
installed, the player logs a note and falls back to the script animation instead
of crashing.

---

## Setting the mode

**In the app:** open the settings panel (`:settings` or `:keybinds` in the
command bar) and use the spectrum-mode control.

**By file:** edit `~/.sweetvibe_keybinds` (see keybindings.md):

```text
$spectrum_mode=reactive
```

**In code:** change the constant in `main.py`:

```python
SPECTRUM_AUTO = "auto"
SPECTRUM_REACTIVE = "reactive"
SPECTRUM_SCRIPT = "script"
```

---

## Custom colors

The spectrum is drawn as bars up to five colors, stored in `DEFAULT_COLORS`:

```python
DEFAULT_COLORS = {
    "color_1": "blue",
    "color_2": "cyan",
    "color_3": "green",
    "color_4": "yellow",
    "color_5": "red",
}
```

Each maps through `COLOR_MAP` to an asciimatics color value:

```python
COLOR_MAP = {
    "black":    Screen.COLOUR_BLACK,
    "red":      Screen.COLOUR_RED,
    "green":    Screen.COLOUR_GREEN,
    "yellow":   Screen.COLOUR_YELLOW,
    "blue":     Screen.COLOUR_BLUE,
    "magenta":  Screen.COLOUR_MAGENTA,
    "cyan":     Screen.COLOUR_CYAN,
    "white":    Screen.COLOUR_WHITE,
}
```

### Changing colors without code

Edit `~/.sweetvibe_keybinds`:

```text
$color_1=magenta
$color_2=cyan
$color_3=white
$color_4=yellow
$color_5=red
```

or pick colors in the in-app settings panel.

### Changing the default palette

Edit `DEFAULT_COLORS` in `main.py`. Any value must be a valid key in
`COLOR_MAP`, or the renderer falls back to a built-in default for that slot.

---

## Customizing the visualizer behavior

If you want to change *how* the spectrum behaves (bar count, smoothing, peak
markers), edit `KityPlayer` in `main.py`:

| Setting | Location | Typical value |
| --- | --- | --- |
| Number of bars | `self.fixed_bar_count` | `32` |
| Smoothing | `self.smoothing` | `0.15` |
| Peak marker lists | `self.peak_bars`, `self.peak_vel` | reset on each new track |
| Analysis loop | `spectrum_loop()` | reads samples and fills `raw_spectrum` |
| Bar rendering | `draw()` (the visualizer section) | maps colors + heights |

The analysis thread (`spectrum_loop`) opens the current file with `soundfile`
when Reactive mode is active and computes the frequency bins. The draw code at
`main.py:1174-1200` maps bin heights to the five colors via `pos_factor`.

---

For the keybinding controls themselves, see
[docs/keybindings.md](keybindings.md). For the overall source layout, see
[docs/architecture.md](architecture.md).
