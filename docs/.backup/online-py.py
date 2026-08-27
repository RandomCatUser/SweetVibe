import os
import time
import tempfile
import threading
import subprocess
from pathlib import Path

# Global reference to the main player
_player = None

# Comprehensive state for the Online Discovery Mini-App
sc_state = {
    "show_modal": False,
    "mode": "input",       # 'input' or 'results'
    "query": "",
    "results": [],
    "selected_idx": 0,
    "is_loading": False,
    "loading_frame": 0,
    "platform": "sc" # 'sc' or 'yt'
}

def setup(player):
    global _player
    _player = player
    player.add_log("Online plugin loaded! Use :sc or :yt")
    player.plugin_hooks["on_command"].append(handle_command)
    player.plugin_hooks["on_play_request"].append(handle_play_request)
    player.plugin_hooks["on_draw"].append(on_draw)
    player.plugin_hooks["on_key"].append(on_key)
    player.plugin_hooks["on_tick"].append(on_tick)

def handle_command(cmd, raw_text):
    if cmd.startswith(":sc") or cmd.startswith(":yt"):
        platform = cmd[:3].strip(":") # 'sc' or 'yt'
        query = raw_text[3:].strip()
        
        # Open instantly
        sc_state["platform"] = platform
        sc_state["show_modal"] = True
        sc_state["results"] = []
        sc_state["selected_idx"] = 0
        sc_state["loading_frame"] = 0
        
        if query:
            sc_state["query"] = query
            sc_state["mode"] = "results"
            sc_state["is_loading"] = True
            threading.Thread(target=search_online, args=(platform, query,), daemon=True).start()
        else:
            sc_state["query"] = ""
            sc_state["mode"] = "input"
            sc_state["is_loading"] = False
            
        return True
    return False

def search_online(platform, query):
    try:
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0
        prefix = "scsearch8:" if platform == 'sc' else "ytsearch8:"
        default_search = "scsearch" if platform == 'sc' else "ytsearch"
        
        cmd = ["yt-dlp", f"{prefix}{query}", "--dump-json", "--default-search", default_search, "--no-playlist"]
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
        
        if result.returncode != 0:
            _player.add_log(f"{platform.upper()} Search failed.")
            sc_state["is_loading"] = False
            return
        
        import json
        tracks = []
        for line in result.stdout.strip().split('\n'):
            if not line: continue
            try:
                data = json.loads(line)
                title = data.get('title', 'Unknown')
                uploader = data.get('uploader', 'Unknown Artist')
                duration = data.get('duration', 0)
                url = data.get('webpage_url', data.get('url'))
                if url:
                    # Store extra metadata in the tuple
                    tracks.append(('online', f"[{platform.upper()}] {title} - {uploader}", url, duration))
            except:
                pass
                
        if tracks:
            sc_state["results"] = tracks
        else:
            _player.add_log(f"No tracks found on {platform.upper()}.")
            
    except Exception as e:
        _player.add_log(f"Search Error: {str(e)[:20]}")
    
    sc_state["is_loading"] = False

def on_tick():
    if sc_state["show_modal"] and sc_state["is_loading"]:
        sc_state["loading_frame"] += 1

def format_duration(seconds):
    if not seconds: return "--:--"
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"

def on_draw(screen):
    if not sc_state["show_modal"]:
        return

    from asciimatics.screen import Screen
    w, h = screen.width, screen.height
    box_w = min(74, w - 4)
    box_h = 18
    box_x, box_y = (w - box_w) // 2, (h - box_h) // 2
    
    # 1. Draw main container
    title = " SOUNDCLOUD DISCOVERY " if sc_state["platform"] == "sc" else " YOUTUBE DISCOVERY "
    color = Screen.COLOUR_MAGENTA if sc_state["platform"] == "sc" else Screen.COLOUR_RED
    if hasattr(_player, "draw_box"):
        _player.draw_box(box_x, box_y, box_w, box_h, title, color, rounded=True, bg=Screen.COLOUR_BLACK)
    
    # ASCII Art header
    logo = " ☁ SoundCloud " if sc_state["platform"] == "sc" else " ▶ YouTube "
    logo_color = Screen.COLOUR_YELLOW if sc_state["platform"] == "sc" else Screen.COLOUR_WHITE
    screen.print_at(logo.center(box_w - 2), box_x + 1, box_y + 2, logo_color, Screen.A_BOLD)
    screen.print_at("─" * (box_w - 4), box_x + 2, box_y + 3, color)
    
    if sc_state["mode"] == "input":
        # Draw search input box
        prompt = "Enter Search Query:"
        screen.print_at(prompt.center(box_w - 2), box_x + 1, box_y + 6, Screen.COLOUR_CYAN, Screen.A_BOLD)
        
        input_w = box_w - 12
        input_x = box_x + 6
        if hasattr(_player, "draw_box"):
            _player.draw_box(input_x, box_y + 8, input_w, 3, "", Screen.COLOUR_WHITE, rounded=False)
            
        display_q = sc_state["query"]
        if len(display_q) > input_w - 4:
            display_q = "..." + display_q[-(input_w - 7):]
            
        screen.print_at(" " + display_q, input_x + 1, box_y + 9, Screen.COLOUR_WHITE, Screen.A_BOLD)
        
        # Blinking cursor
        if int(time.time() * 2) % 2 == 0:
            screen.print_at("█", input_x + 2 + _player.get_display_width(display_q), box_y + 9, Screen.COLOUR_YELLOW)
            
        hint = " ENTER: Search  |  CTRL+B: Close "
        screen.print_at(hint.center(box_w - 4), box_x + 2, box_y + box_h - 2, Screen.COLOUR_WHITE, Screen.A_NORMAL)
        
    elif sc_state["mode"] == "results":
        if sc_state["is_loading"]:
            frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            f_char = frames[(sc_state["loading_frame"] // 3) % len(frames)]
            msg = f"{f_char} Searching for '{sc_state['query']}'..."
            screen.print_at(msg.center(box_w - 2), box_x + 1, box_y + 8, Screen.COLOUR_YELLOW, Screen.A_BOLD)
        
        elif not sc_state["results"]:
            msg = f"No results found for '{sc_state['query']}'."
            screen.print_at(msg.center(box_w - 2), box_x + 1, box_y + 8, Screen.COLOUR_RED, Screen.A_BOLD)
            hint = " CTRL+B: New Search "
            screen.print_at(hint.center(box_w - 4), box_x + 2, box_y + box_h - 2, Screen.COLOUR_WHITE, Screen.A_NORMAL)
            
        else:
            # Draw Results List
            list_start_y = box_y + 5
            max_items = 10
            for i, item in enumerate(sc_state["results"][:max_items]):
                is_sel = (i == sc_state["selected_idx"])
                fg = Screen.COLOUR_BLACK if is_sel else Screen.COLOUR_WHITE
                bg = Screen.COLOUR_YELLOW if is_sel else Screen.COLOUR_BLACK
                attr = Screen.A_BOLD if is_sel else Screen.A_NORMAL
                
                dur_str = format_duration(item[3])
                title_max_w = box_w - 14
                
                display_name = item[1]
                if _player.get_display_width(display_name) > title_max_w:
                    display_name = _player.truncate_text(display_name, title_max_w)
                    
                prefix = " >>" if is_sel else "   "
                line = f"{prefix} {display_name}"
                line = _player.pad_text(line, box_w - 10)
                line += f"[{dur_str}] "
                
                screen.print_at(line, box_x + 1, list_start_y + i, fg, attr, bg=bg)
                
            hint = " ↑↓: Navigate  |  ENTER: Play  |  CTRL+B: Search Again "
            screen.print_at(hint.center(box_w - 4), box_x + 2, box_y + box_h - 2, Screen.COLOUR_WHITE, Screen.A_BOLD)

def on_key(key_str, action):
    if not sc_state["show_modal"]:
        return False
        
    if sc_state["mode"] == "input":
        if action == "ctrl+b":
            sc_state["show_modal"] = False
            return True
            
        if action == "enter":
            if sc_state["query"].strip():
                sc_state["mode"] = "results"
                sc_state["is_loading"] = True
                sc_state["results"] = []
                threading.Thread(target=search_online, args=(sc_state["platform"], sc_state["query"],), daemon=True).start()
        elif action == "back" or key_str == "backspace":
            sc_state["query"] = sc_state["query"][:-1]
        elif key_str == "space":
            sc_state["query"] += " "
        elif key_str and len(key_str) == 1:
            sc_state["query"] += key_str
            
    elif sc_state["mode"] == "results":
        if action == "ctrl+b":
            sc_state["mode"] = "input"
            return True
            
        if not sc_state["is_loading"] and sc_state["results"]:
            if action == "up":
                sc_state["selected_idx"] = max(0, sc_state["selected_idx"] - 1)
            elif action == "down":
                sc_state["selected_idx"] = min(len(sc_state["results"]) - 1, sc_state["selected_idx"] + 1)
            elif action == "enter":
                item = sc_state["results"][sc_state["selected_idx"]]
                sc_state["show_modal"] = False
                
                # Add to playlist
                _player.display_playlist.insert(0, item)
                _player.all_items.insert(0, item)
                _player.current_index = 0
                _player.play_index(0)
                
    return True # Intercept all keys

def handle_play_request(item):
    if item[0] == 'online':
        sc_state["dl_status"] = "Init..."
        _player.add_log("Starting Online Stream...")
        threading.Thread(target=download_and_play, args=(item,), daemon=True).start()
        return True
    return False

def download_and_play(item):
    url = item[2]
    temp_dir = tempfile.gettempdir()
    out_file = os.path.join(temp_dir, "sweetvibe_online_temp.mp3")
    
    if os.path.exists(out_file):
        try: os.remove(out_file)
        except: pass
        
    try:
        flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if os.name == 'nt' else 0
        cmd = [
            "yt-dlp",
            "-f", "bestaudio[ext=mp3]/bestaudio[ext=m4a]/bestaudio",
            "--force-overwrites",
            "-o", out_file,
            url
        ]
        
        # Run process and wait
        _player.add_log("Fetching audio stream...")
        res = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
        
        if res.returncode == 0 and os.path.exists(out_file):
            _player.add_log("Ready! Playing track.")
            idx = _player.current_index
            if 0 <= idx < len(_player.display_playlist) and _player.display_playlist[idx] == item:
                # Morph into a file
                new_item = ('file', item[1], Path(out_file), 0)
                _player.display_playlist[idx] = new_item
                _player.play_index(idx)
        else:
            err = res.stderr.strip() if res.stderr else "Unknown Error"
            short_err = err.split('\n')[-1][:30]
            _player.add_log(f"Stream Failed: {short_err}")
    except Exception as e:
        _player.add_log(f"DL Error: {str(e)[:20]}")
