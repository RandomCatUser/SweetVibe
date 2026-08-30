# SweetVibe Plugin Development Guide

SweetVibe has a plugin system that lets you extend the player without editing
`main.py`. You can hook into the main loop, modify player state, handle input,
run code on every frame, and draw custom UI onto the terminal screen.

This guide walks you through the plugin API step by step, from a hello-world
plugin to a working example that injects streamable items into the queue.

---

## Table of contents

1. [How plugins load](#how-plugins-load)
2. [The `setup(player)` function](#the-setupplayer-function)
3. [Plugin hooks (the event API)](#plugin-hooks-the-event-api)
4. [A guided example: log on song start](#a-guided-example-log-on-song-start)
5. [Drawing custom UI](#drawing-custom-ui)
6. [Adding your own commands](#adding-your-own-commands)
7. [Injecting non-file / online items](#injecting-non-file--online-items)
8. [Player attributes and methods](#player-attributes-and-methods)
9. [The item tuple format](#the-item-tuple-format)
10. [Troubleshooting](#troubleshooting)

---

## How plugins load

At startup, SweetVibe scans the `plugins` folder located in the same directory
as the executable (when frozen) or next to `main.py` (when running from source).

It loads:

- every `.py` file in that folder, and
- every subfolder that contains an `__init__.py` (a Python package).

Each loaded module is executed, and if it exposes a top-level function named
`setup`, SweetVibe calls it once with a single argument: the player instance.

The player instance is of type `KityPlayer` (defined in `main.py`). It holds
the entire state of the app - playback, the display, the queue, settings, and
the plugin hooks. Keep a reference to it (for example store it in a module-level
variable) so your plugin functions can reach it later:

```python
_player = None  # module-level reference to the player

def setup(player):
    global _player
    _player = player
```

If a plugin fails to import or `setup` raises, SweetVibe logs a short error and
keeps going. It never crashes the player because of a plugin.

---

## The `setup(player)` function

Your plugin **must** define a `setup(player)` function at module level. It is
called exactly once per launch, and it is where you register your hooks.

```python
# plugins/hello_plugin.py

def setup(player):
    player.add_log("Hello from my plugin!")
```

`add_log(msg)` appends a timestamped line to the in-app logging panel
(`player.logs`). It is the easiest way to confirm a plugin loaded.

---

## Plugin hooks (the event API)

Hooks are stored in `player.plugin_hooks`, which is a dictionary mapping an
event name to a **list of callables**. You register your function by appending
it to the list for the event you care about:

```python
player.plugin_hooks["on_play"].append(my_callback)
```

The available hooks and their call signatures:

| Hook | Called with | When |
| --- | --- | --- |
| `on_play_request` | `(item)` | Before a track starts. Return `True` to take over playback yourself. |
| `on_play` | `(filepath)` | A local song actually started playing. |
| `on_stop` | *(nothing)* | Playback stopped. |
| `on_draw` | `(screen)` | At the end of every draw loop - draw custom UI here. |
| `on_key` | `(key_str, action)` | Every key press. Return `True` to consume the key. |
| `on_tick` | *(nothing)* | Every frame (~100 times per second). |
| `on_command` | `(cmd, raw_text)` | A user typed a `:` command. Return `True` to mark it handled. |

### Detailed semantics

- **`on_play_request(item)`** - Called inside `play_index` *before* the default
  local-file playback logic runs. If *any* handler returns `True`, the default
  playback is skipped so you can handle the item yourself (for example, stream
  or download a remote URL). This is how the bundled `online.py` plugin works.

- **`on_play(filepath)`** - Fired with the resolved path string after a local
  song successfully starts playing. Useful for notifications, logging, or
  visualizing metadata.

- **`on_stop()`** - Fired when playback stops. No arguments.

- **`on_draw(screen)`** - Called at the very end of `draw()`, after everything
  else has been painted. `screen` is the asciimatics `Screen` instance. Use it
  to draw overlays. Be careful: anything you draw can be overwritten on the next
  frame, so draw here every frame.

- **`on_key(key_str, action)`** - Called for each key press. `key_str` is the
  raw normalized key string (for example `"a"`, `"up"`, `"ctrl+b"`, `"enter"`),
  and `action` is the SweetVibe action bound to that key via keybinds (or
  `None`). If a handler returns `True`, SweetVibe treats the key as consumed and
  ignores it. Returning `False`/`None` lets normal handling proceed. This is how
  plugins build modals that capture all keys while open.

- **`on_tick()`** - Called on every frame with no arguments. Great for timers,
  animations, or state that needs to update ~100 times per second. Keep it
  cheap; it runs very often.

- **`on_command(cmd, raw_text)`** - Called when a user submits a command in the
  command bar (typed with `Ctrl+O` / `P`, then `Enter`). `cmd` is the lowercased
  text including the leading `:` (for example `:yt lofi` becomes
  `cmd == ":yt lofi"`), and `raw_text` is the original untrimmed text. If a
  handler returns `True`, the command is considered handled and the player's
  built-in commands are skipped.

---

## A guided example: log on song start

Create `plugins/song_logger.py`:

```python
# plugins/song_logger.py

def on_song_started(filepath):
    print("A song started:", filepath)
    # 'player' is not an argument here - use the module global if you need it.
    # Better: capture the player in a closure inside setup().

def setup(player):
    player.plugin_hooks["on_play"].append(on_song_started)
    player.add_log("song_logger plugin loaded")
```

If your handler needs the player instance, define it inside `setup` so it can
close over the local `player` argument:

```python
# plugins/song_logger.py

def setup(player):
    def on_song_started(filepath):
        player.add_log("Now playing: " + str(filepath))
    player.plugin_hooks["on_play"].append(on_song_started)
```

---

## Drawing custom UI

Register an `on_draw` handler. Use asciimatics `Screen.print_at` to put text on
the terminal. Always clamp to `screen.width` / `screen.height`; drawing past the
edge can throw inside the render loop.

```python
# plugins/draw_demo.py
from asciimatics.screen import Screen

def draw(screen):
    player.add_log("x")            # no - too slow, called every frame
    screen.print_at(" Plugin Active! ",
                    min(0, 0), 0, Screen.COLOUR_RED, Screen.A_BOLD)

def setup(player):
    player.plugin_hooks["on_draw"].append(draw)
```

For a proper text box with a title, the player also provides
`player.draw_box(x, y, w, h, title, color, attr, rounded, clear, bg)` which
draws a border box and can clear its area. The bundled `online.py` plugin uses
this to build its YouTube modal.

```python
from asciimatics.screen import Screen

def draw(screen):
    # x, y, w, h, title, color, rounded
    player.draw_box(4, 2, 40, 10, " MY BOX ",
                    Screen.COLOUR_CYAN, rounded=True)

def setup(player):
    player.plugin_hooks["on_draw"].append(draw)
```

---

## Adding your own commands

Use an `on_command` handler. Check for your prefix, act, then return `True` so
the player treats it as handled.

```python
def setup(player):
    def handle(cmd, raw_text):
        if cmd.startswith(":hello"):
            name = cmd[7:].strip() or "world"
            player.add_log("Hello, " + name + "!")
            return True
        return False
    player.plugin_hooks["on_command"].append(handle)
```

Now typing `:hello Peter` in the command bar prints `Hello, Peter!`.

---

## Injecting non-file / online items

The queue (`player.display_playlist` and `player.all_items`) holds items as
tuples. Local files are `('file', name, path, duration)`; you can inject any
other kind by changing the first element, for example `('online', label, url,
duration)`, and handling it in `on_play_request`.

```python
def setup(player):
    # 1. Put a custom item at the top of the queue
    player.display_playlist.insert(
        0, ("online", "My Stream", "https://example.com/stream.mp3", 0))
    player.all_items.insert(0,
        ("online", "My Stream", "https://example.com/stream.mp3", 0))

    # 2. Teach the player how to "play" it
    def play_request(item):
        if item[0] == "online":
            player.add_log("Streaming from: " + str(item[2]))
            # ... your own playback logic here (download, stream, etc.) ...
            return True          # tell SweetVibe we handled it
        return False             # let the default path handle it

    player.plugin_hooks["on_play_request"].append(play_request)
```

Important: matching items must be consistent between the two lists. `online.py`
inserts into both `display_playlist` and `all_items` when a result is chosen.

---

## Player attributes and methods

The `player` object (`KityPlayer`) exposes the fields and methods below. Feel
free to read or modify them.

### State

| Attribute | Type | Description |
| --- | --- | --- |
| `player.is_playing` | bool | `True` while a track plays. |
| `player.volume` | int | Master volume, 0-100. |
| `player.is_muted` | bool | Whether audio is muted. |
| `player.repeat` | bool | Repeat toggle. |
| `player.shuffle` | bool | Shuffle toggle. |
| `player.mode` | str | Current mode: `"BROWSE"` or `"PC_SCAN"`. |
| `player.current_index` | int | Index of the selected item in `display_playlist`. |
| `player.current_filepath` | Path or None | Path of the current track. |
| `player.duration` | float | Duration (seconds) of the current track. |
| `player.metadata` | dict | Keys: `title`, `artist`, `album`, `samplerate`, `bitrate`. |
| `player.spectrum_mode` | str | One of `"auto"`, `"reactive"`, `"script"`. |
| `player.custom_colors` | dict | `color_1` .. `color_5` -> color name string. |
| `player.keybinds` | dict | action -> list of key strings. |
| `player.display_playlist` | list | The currently shown/queued items (tuples). |
| `player.all_items` | list | The full unfiltered item list. |
| `player.plugin_hooks` | dict | All hook lists - append callbacks here. |
| `player.logs` | list | Recent log lines (capped). |
| `player.screen` | Screen | The asciimatics `Screen` instance. |

### Methods

| Method | Signature / notes |
| --- | --- |
| `player.add_log(msg)` | Append a timestamped log line. |
| `player.change_volume(delta)` | Adjust volume by `delta` (clamped 0-100). |
| `player.toggle_mute()` | Toggle muted state. |
| `player.play_index(index, resume=False, seek_to=None)` | Start playing the item at `index`. |
| `player.toggle_pause()` | Pause or resume. |
| `player.seek(seconds)` | Seek forward/backward by `seconds` (can be negative). |
| `player.stop(reset_seek=True)` | Stop playback. |
| `player.navigate_into()` | Enter the open folder. |
| `player.navigate_up()` | Go to the parent folder / back to Browse. |
| `player.cycle_mode()` | Toggle Browse / PC-Scan. |
| `player.add_keybind(action, key_str)` | Bind `key_str` to an action (also saves). |
| `player.get_action(key_str)` | Return the action bound to `key_str`, or `None`. |
| `player.get_display_width(text)` | Character width including East-Asian wide chars. |
| `player.truncate_text(text, max_width)` | Truncate text to a display width with `...`. |
| `player.pad_text(text, total_width)` | Pad text to a display width. |
| `player.draw_box(x, y, w, h, title="", color, attr, rounded, clear, bg)` | Draw a titled border box. |

The full list of public methods (in source order) is: `get_display_width`,
`truncate_text`, `pad_text`, keybind helpers (`load_keybinds`,
`save_keybinds`, `reset_keybinds`, `add_keybind`, `remove_last_keybind`,
`remove_keybind_at`, `get_action`, `format_key_display`,
`format_keys_list`), `cycle_spectrum_mode`, file scanning
(`count_audio_files`, `start_pc_scan`), `perform_update`, `update_file_list`,
`apply_filter`, `add_log`, volume/playback (`change_volume`, `toggle_mute`,
`play_index`, `navigate_into`, `navigate_up`, `cycle_mode`, `stop`,
`toggle_pause`, `seek`), `draw_box`, `update_scroll`, `get_footer_hint`,
and the draw methods (`draw`, `draw_settings`). Prefer these helpers over
touching internals directly.

---

## The item tuple format

Each entry in `display_playlist` / `all_items` is a 4-tuple:

```python
(kind, name, payload, duration)
```

- `kind` - a string tag. `"file"` and `"folder"` are built in. Plugins may use
  any other string (for example `"online"`) as a custom tag and handle it in
  `on_play_request`.
- `name` - the display name.
- `payload` - for `"file"` this is the `Path`; for other kinds it is up to you
  (for example a URL string).
- `duration` - length in seconds (used for progress display).

In `on_play_request`, recover values positionally:

```python
def play_request(item):
    kind, name, payload, duration = item
    if kind == "online":
        url = payload
        return True
    return False
```

---

## Troubleshooting

- **My plugin did not load.** Check the log panel in-app for a line like
  `Plugin err <name>: ...`. Capture the real exception in your module so it
  appears in the log.
- **My `on_key` handler runs but the player still reacts.** Ensure your handler
  returns `True` to consume the key. Returning nothing lets the key fall
  through to the default handler.
- **Drawing past the edge crashes the render.** Always clamp coordinates to
  `screen.width` and `screen.height` before calling `print_at`.
- **My custom queue item is skipped and never plays.** You must handle its
  `kind` in an `on_play_request` handler and return `True`; otherwise the
  default path treats it like a missing file.
- **`on_tick` is very heavy.** It fires every frame. Move expensive work to a
  background thread and only update fast state here.

---

For a real-world reference implementation, read `plugins/online.py` - it uses
`on_command`, `on_play_request`, `on_draw`, `on_key`, and `on_tick` together to
build a complete YouTube search and download flow.

For a shorter example of a read-only modal (combining `on_command`, `on_draw`,
and `on_key` with CJK/wide-character-safe drawing), read `plugins/lyrics.py` -
it opens lyric text from track metadata with `:lyric`.

For an overview of the whole source layout, see
[docs/architecture.md](architecture.md).
