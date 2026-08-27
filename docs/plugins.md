# SweetVibe Plugin Development Guide

SweetVibe now features a full-fledged plugin architecture that allows you to hook into the main application loop, modify player state, handle input, and draw custom UI elements to the terminal screen!

## How Plugins Work

SweetVibe automatically scans the `plugins` folder located in the same directory as the executable (or `main.py`).
It looks for any Python file (`.py`) or package (a folder containing `__init__.py`). 
When a plugin is found, it is dynamically imported, and if it has a `setup(player)` function, that function is executed.

## The `setup` Function

Your plugin must define a `setup(player)` function at the module level.
The `player` argument is an instance of the `KityPlayer` class, which holds the entire state of the music player, including playback controls, the display, and plugin hooks.

```python
def setup(player):
    # This is called when the plugin is loaded!
    player.add_log("Hello from my awesome plugin!")
```

## Plugin Hooks

You can register your own functions to be called during specific events in the SweetVibe lifecycle by appending them to the lists in `player.plugin_hooks`.

Available hooks:
- `"on_play_request"`: Called with `(item)` before a track is played. `item` is a tuple like `('file', 'name', 'path', 0)`. If your hook returns `True`, the main application will skip its default playback logic, allowing you to handle playback yourself (useful for online streaming)!
- `"on_play"`: Called with `(filepath)` when a local song starts playing.
- `"on_stop"`: Called with no arguments when playback stops.
- `"on_draw"`: Called with `(screen)` at the end of the draw loop. You can use this to draw custom UI on top of the player.
- `"on_key"`: Called with `(key_str, action)` when a key is pressed. `key_str` is the raw key, and `action` is the bound SweetVibe action (if any).
- `"on_tick"`: Called with no arguments every single frame (~100 times per second).
- `"on_command"`: Called with `(cmd, raw_text)` when a user types a command starting with `:` in the command bar (e.g. `:youtube lofi`). If your hook returns `True`, the player considers the command handled.

### Adding Online Music (Custom Playlist Items)
You can inject non-file items into the playlist (e.g. online streams) by appending to `player.display_playlist` and handling them with `on_play_request`:
```python
# Add an online track
player.display_playlist.insert(0, ('url', 'My Online Stream', 'http://example.com/stream.mp3', 0))

def my_play_request(item):
    if item[0] == 'url':
        url = item[2]
        # ... Do your own playback logic (e.g. VLC, downloading, etc) ...
        player.add_log(f"Streaming from: {url}")
        return True # Tell the player we handled it!
    return False
```

### Example Plugin

Save the following code as `hello_plugin.py` in your `plugins` folder.

```python
# plugins/hello_plugin.py

def on_song_played(filepath):
    # We can do something when a song plays!
    pass

def on_custom_key(key_str, action):
    # If the user presses 'x', print a log message
    if key_str == 'x':
        # player instance is available in the closure or you can store it globally
        pass

def custom_draw(screen):
    # Draw custom text at the top left corner!
    from asciimatics.screen import Screen
    screen.print_at(" Plugin Active! ", 0, 0, Screen.COLOUR_RED, Screen.A_BOLD, bg=Screen.COLOUR_WHITE)

def setup(player):
    player.add_log("My Custom Plugin is loading...")
    
    # Register our hooks
    player.plugin_hooks["on_play"].append(on_song_played)
    player.plugin_hooks["on_draw"].append(custom_draw)
    
    # Example of a closure to capture the player instance
    def key_handler(key_str, action):
        if key_str == 'p':
            player.add_log("Plugin key 'p' was pressed!")
            
    player.plugin_hooks["on_key"].append(key_handler)
```

## Useful Player Attributes

The `player` object has many attributes you can access or modify:
- `player.is_playing` (bool): True if a song is currently playing.
- `player.volume` (int): The current volume (0-100).
- `player.change_volume(delta)`: Adjust volume by `delta`.
- `player.add_log(msg)`: Add a message to the logging panel.
- `player.metadata`: A dictionary with keys like `'title'`, `'artist'`, `'samplerate'`.
- `player.screen`: The asciimatics Screen instance, used for drawing.
- `player.current_filepath`: Pathlib object pointing to the currently playing song.

Enjoy building extensions for SweetVibe!
