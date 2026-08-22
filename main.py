import os
import sys
import time
import json
import random
import math
import signal
import string
import threading
import subprocess
import unicodedata
import urllib.request
from pathlib import Path
from datetime import datetime

# Dependencies: pip install asciimatics tinytag just_playback
try:
    from asciimatics.screen import Screen
    from asciimatics.exceptions import ResizeScreenError
    from asciimatics.event import MouseEvent
    from tinytag import TinyTag
    from just_playback import Playback
except ImportError:
    print("Missing dependencies. Please run: pip install asciimatics tinytag just_playback")
    sys.exit(1)

AUDIO_EXTS = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.opus', '.aac'}

APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent

# Default keybindings. These will be written to keybindings.json
DEFAULT_KEYBINDS = {
    "up": ["up"],
    "down": ["down"],
    "enter": ["enter"],
    "back": ["backspace", "ctrl+b", "esc"],
    "play_pause": ["space"],
    "volume_up": ["+", "="],
    "volume_down": ["-", "_"],
    "seek_forward": ["right"],
    "seek_backward": ["left"],
    "mute": ["m"],
    "search": ["ctrl+f", "/"],
    "open_path": ["ctrl+o", "p"],
    "shuffle": ["ctrl+e", "s"],
    "repeat": ["r"],
    "quit": ["q", "ctrl+c"],
    "mode_switch": ["tab"],
    "toggle_mouse": ["ctrl+m"],
    "jump_music": ["1"],
    "jump_docs": ["2"]
}

class QuitApplication(Exception):
    """Custom exception to trigger a graceful, styled exit."""
    pass

def print_goodbye():
    """Restore terminal state and print a stylish farewell message."""
    try:
        sys.stdout.write("\033[?25h")
        sys.stdout.write("\033[0m")
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
        lines = [
            "",
            "  \033[38;5;213m+-----------------------------------------------+\033[0m",
            "  \033[38;5;213m|                                               |\033[0m",
            "  \033[38;5;213m|       ~ SweetVibe says goodbye for now! ~      |\033[0m",
            "  \033[38;5;213m|          Nyaa~ Thanks for listening! <3        |\033[0m",
            "  \033[38;5;213m|                                               |\033[0m",
            "  \033[38;5;213m|        Developed by: Dihan Ramanayaka         |\033[0m",
            "  \033[38;5;213m|          Licensed under Apache License 2.0     |\033[0m",
            "  \033[38;5;213m|                                               |\033[0m",
            "  \033[38;5;213m+-----------------------------------------------+\033[0m",
            "",
            "  \033[38;5;39m~ See you next time! ~\033[0m",
            "",
        ]
        for line in lines:
            sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except Exception:
        pass

def check_for_updates_async(player):
    """Background thread to check GitHub for the latest commit."""
    try:
        url = "https://api.github.com/repos/RandomCatUser/SweetViben/commits/main"
        req = urllib.request.Request(url, headers={'User-Agent': 'SweetVibe-Player'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            latest_sha = data['sha']
        
        local_sha = "none"
        ver_file = Path.home() / ".sweetvibe_version"
        if ver_file.exists():
            local_sha = ver_file.read_text().strip()
            
        if local_sha != latest_sha:
            player.update_available = True
            player.latest_sha = latest_sha
            player.add_log("Update available! Type :update in cmd bar.")
        else:
            player.add_log("SweetVibe is up to date.")
    except Exception:
        pass

class KityPlayer:
    def __init__(self, screen):
        self.screen = screen
        self.base_dir = APP_DIR / "songs"
        self.current_dir = self.base_dir if self.base_dir.exists() else APP_DIR
        
        self.all_items = []          
        self.display_playlist = []   
        self.current_index = -1
        self.scroll_offset = 0
        self.current_filepath = None  
        
        self.is_playing = False
        self.repeat = False
        self.shuffle = False
        self.search_query = ""
        self.volume = 65
        self.is_muted = False
        self.mouse_enabled = False
        
        self.mode = "BROWSE"
        self.scanning = False
        self.scan_found = 0
        self.scan_thread = None
        
        self.update_available = False
        self.latest_sha = ""
        threading.Thread(target=check_for_updates_async, args=(self,), daemon=True).start()
        
        self.keybinds = self.load_keybinds()
        
        try:
            self.playback = Playback()
            self.audio_err = None
        except Exception as e:
            self.playback = None
            self.audio_err = str(e)
            
        self.start_time = 0
        self.elapsed_at_pause = 0
        self.duration = 0
        self.metadata = {
            "title": "None", 
            "artist": "Unknown", 
            "album": "Unknown", 
            "samplerate": "0Hz",
            "bitrate": "0kbps"
        }
        
        self.fixed_bar_count = 32
        self.last_bars = [0.0] * self.fixed_bar_count
        self.target_bars = [0.0] * self.fixed_bar_count
        self.smoothing = 0.15 
        
        self.cat_frames = [
            "  /\\_/\\  \n ( ^.^ ) \n  > o <  ",
            "  /\\_/\\  \n ( -.- ) \n  > o <  ",
            "  /\\_/\\  \n ( >.< ) \n  > v <  ",
            "  /\\_/\\  \n ( @.@ ) \n  > w <  "
        ]
        self.cat_idx = 0
        self.last_cat_update = time.time()
        
        self.input_mode = None 
        self.input_text = ""
        self.show_help = False
        self.help_page = 0
        self.show_about = False
        self.logs = ["System Booted Successfully", "Welcome to SweetVibe"]
        
        if self.audio_err:
            self.logs.append(f"Audio Init Err: {self.audio_err}")

        self.update_file_list()
        self.add_log(f"Scanned: {len(self.all_items)} items")

    def get_display_width(self, text):
        width = 0
        for char in text:
            if unicodedata.east_asian_width(char) in ('W', 'F'):
                width += 2
            else:
                width += 1
        return width

    def truncate_text(self, text, max_width):
        if self.get_display_width(text) <= max_width:
            return text
        target = max_width - 3
        if target <= 0: return "." * max_width
        current_width = 0
        result = ""
        for char in text:
            char_w = 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
            if current_width + char_w > target: break
            result += char
            current_width += char_w
        return result + "..."

    def pad_text(self, text, total_width):
        current_w = self.get_display_width(text)
        if current_w >= total_width: return text
        return text + (" " * (total_width - current_w))

    def load_keybinds(self):
        """Loads keybinds from keybindings.json. Creates it if it doesn't exist."""
        kb_file = APP_DIR / "keybindings.json"
        if not kb_file.exists():
            try:
                kb_file.write_text(json.dumps(DEFAULT_KEYBINDS, indent=4))
            except Exception:
                pass
            return DEFAULT_KEYBINDS
        try:
            data = json.loads(kb_file.read_text())
            # Clean up deprecated keys from older versions
            for deprecated in ["help", "about", "update"]:
                if deprecated in data:
                    del data[deprecated]
            return data
        except:
            return DEFAULT_KEYBINDS

    def get_action(self, key_str):
        if not key_str: return None
        for action, keys in self.keybinds.items():
            if key_str in keys:
                return action
        return None

    def count_audio_files(self, path, max_depth=2):
        """Quickly counts audio files under a folder (bounded depth)."""
        count = 0
        try:
            for dirpath, _, filenames in os.walk(path, onerror=lambda e: None):
                parts = Path(dirpath).parts
                if any(part.startswith('.') for part in parts): continue
                if 'node_modules' in parts or '.git' in parts: continue
                depth = len(Path(dirpath).relative_to(path).parts)
                if depth > max_depth: continue
                for f in filenames:
                    if Path(f).suffix.lower() in AUDIO_EXTS:
                        count += 1
        except Exception:
            pass
        return count

    def async_count_folders(self, folders):
        """Runs in background to prevent UI from freezing on large/slow drives."""
        if not folders: return
        def worker():
            time.sleep(0.1)  # Let the UI render the folder list first
            updated = False
            for name, path, _ in folders:
                count = self.count_audio_files(path, max_depth=2)
                for i, item in enumerate(self.all_items):
                    if item[0] == 'folder' and item[1] == name and item[2] == path:
                        if item[3] != count:
                            self.all_items[i] = ('folder', name, path, count)
                            updated = True
                        break
            # Re-apply filter only if user is not actively typing in search
            if updated and self.input_mode != 'search':
                self.apply_filter()
        threading.Thread(target=worker, daemon=True).start()

    def start_pc_scan(self):
        if self.scanning: return
        self.scanning = True
        self.scan_found = 0
        self.all_items = []
        self.display_playlist = []
        self.current_index = -1
        self.add_log("Scanning entire PC for music...")
        
        def worker():
            files = []
            roots = []
            home = str(Path.home())
            roots.append(home)
            if os.name == 'nt':
                for drive in string.ascii_uppercase:
                    if drive != 'C':
                        if os.path.exists(f"{drive}:\\"):
                            roots.append(f"{drive}:\\")
                    else:
                        roots.append("C:\\Users")
                        roots.append("C:\\Downloads")
                        roots.append("C:\\Music")
            else:
                roots.append('/media')
                roots.append('/mnt')
                if sys.platform == 'darwin':
                    roots.append('/Volumes')

            for root in roots:
                if not os.path.exists(root): continue
                for dirpath, _, filenames in os.walk(root, onerror=lambda e: None):
                    parts = Path(dirpath).parts
                    if any(part.startswith('.') for part in parts):
                        continue
                    if 'node_modules' in parts or '.git' in parts or '.cache' in parts:
                        continue
                    if 'Windows' in parts or 'Program Files' in parts or '$Recycle.Bin' in parts:
                        continue
                    for f in filenames:
                        if Path(f).suffix.lower() in AUDIO_EXTS:
                            files.append(Path(dirpath) / f)
                            self.scan_found += 1
                            
            if self.mode != "PC_SCAN":
                self.scanning = False
                return
            self.all_items = [('file', f.name, f, 0) for f in sorted(files, key=lambda x: x.name.lower())]
            self.scanning = False
            self.apply_filter()
            if self.all_items:
                self.current_index = 0
            self.add_log(f"PC Scan complete: {len(self.all_items)} files")
            
        self.scan_thread = threading.Thread(target=worker, daemon=True)
        self.scan_thread.start()

    def perform_update(self):
        self.add_log("Downloading update...")
        try:
            contents_url = "https://api.github.com/repos/RandomCatUser/SweetViben/contents/"
            req = urllib.request.Request(contents_url, headers={'User-Agent': 'SweetVibe-Player'})
            with urllib.request.urlopen(req, timeout=5) as response:
                contents = json.loads(response.read().decode())
            raw_url = None
            for item in contents:
                if item['name'].endswith('.py'):
                    if item['name'] == Path(sys.argv[0]).name:
                        raw_url = item['download_url']
                        break
            if not raw_url:
                for item in contents:
                    if item['name'].endswith('.py'):
                        raw_url = item['download_url']
                        break
            if raw_url:
                req = urllib.request.Request(raw_url, headers={'User-Agent': 'SweetVibe-Player'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    new_code = response.read().decode()
                current_file = Path(sys.argv[0]).resolve()
                current_file.write_text(new_code)
                ver_file = Path.home() / ".sweetvibe_version"
                ver_file.write_text(self.latest_sha)
                self.add_log("Update successful! Restarting...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            self.add_log(f"Update failed: {str(e)[:20]}")

    def update_file_list(self):
        try:
            if not self.current_dir.exists():
                self.current_dir = Path.cwd()
            
            if self.mode == "PC_SCAN":
                self.start_pc_scan()
            else:
                folders = []
                files = []
                try:
                    for f in self.current_dir.iterdir():
                        try:
                            if f.is_dir() and not f.name.startswith('.'):
                                # Add with 0 count initially to prevent UI freeze
                                folders.append((f.name, f, 0)) 
                            elif f.suffix.lower() in AUDIO_EXTS:
                                files.append((f.name, f, 0))
                        except (PermissionError, OSError):
                            continue
                except (PermissionError, OSError):
                    self.add_log("Permission denied")
                
                folders.sort(key=lambda x: x[0].lower())
                files.sort(key=lambda x: x[0].lower())
                
                self.all_items = []
                if self.current_dir != self.current_dir.parent:
                    self.all_items.append(('folder', '..', self.current_dir.parent, 0))
                for name, path, count in folders:
                    self.all_items.append(('folder', name, path, count))
                for name, path, _ in files:
                    self.all_items.append(('file', name, path, 0))
                
                # Start background counting for the folders
                self.async_count_folders(folders)
            
            self.apply_filter()
            
            if self.current_filepath:
                for i, item in enumerate(self.display_playlist):
                    if item[0] == 'file' and item[2] == self.current_filepath:
                        self.current_index = i
                        return
            if self.current_index >= len(self.display_playlist):
                self.current_index = max(0, len(self.display_playlist) - 1) if self.display_playlist else -1
            elif self.current_index < 0 and self.display_playlist:
                self.current_index = 0
        except Exception as e:
            self.add_log(f"Scan Err: {str(e)[:30]}")

    def apply_filter(self):
        filtered = self.all_items[:]
        query = self.input_text if (self.input_mode == 'search') else self.search_query
        if query:
            filtered = [item for item in filtered if query.lower() in item[1].lower()]
        if self.shuffle:
            up = [i for i in filtered if i[0] == 'folder' and i[1] == '..']
            folders = [i for i in filtered if i[0] == 'folder' and i[1] != '..']
            files = [i for i in filtered if i[0] == 'file']
            random.shuffle(files)
            random.shuffle(folders)
            filtered = up + folders + files
            
        self.display_playlist = filtered
        if not self.display_playlist:
            self.current_index = -1
        elif self.current_index < 0:
            self.current_index = 0
        elif self.current_index >= len(self.display_playlist):
            self.current_index = len(self.display_playlist) - 1

    def add_log(self, msg):
        now = datetime.now().strftime('%H:%M')
        self.logs.append(f"[{now}] {msg}")
        if len(self.logs) > 4: self.logs.pop(0)

    def change_volume(self, delta):
        self.volume = max(0, min(100, self.volume + delta))
        if self.playback:
            vol_val = 0.0 if self.is_muted else (self.volume / 100.0)
            try: self.playback.set_volume(vol_val)
            except: pass
        self.add_log(f"Volume: {self.volume}%")

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.playback:
            vol_val = 0.0 if self.is_muted else (self.volume / 100.0)
            try: self.playback.set_volume(vol_val)
            except: pass
        self.add_log("Muted" if self.is_muted else "Unmuted")

    def play_index(self, index, resume=False, seek_to=None):
        if not self.playback or not self.display_playlist: return
        if index < 0 or index >= len(self.display_playlist):
            index = 0
        item = self.display_playlist[index]
        if item[0] != 'file':
            for i, it in enumerate(self.display_playlist):
                if it[0] == 'file':
                    index = i
                    item = it
                    break
            else:
                return

        self.stop(reset_seek=(not resume and seek_to is None))
        self.current_index = index
        filename = item[1]
        filepath = item[2]
        self.current_filepath = filepath
        
        try:
            tag = TinyTag.get(str(filepath))
            self.duration = tag.duration or 0
            self.metadata["title"] = tag.title or filename
            self.metadata["artist"] = tag.artist or "Unknown Artist"
            self.metadata["samplerate"] = f"{tag.samplerate/1000:.1f}kHz" if tag.samplerate else "44.1kHz"
        except Exception:
            self.duration = 0
            self.metadata["title"] = filename
            self.metadata["artist"] = "Unknown"
            self.metadata["samplerate"] = "44.1kHz"

        if seek_to is not None: 
            self.elapsed_at_pause = max(0, min(self.duration, seek_to))
        elif not resume: 
            self.elapsed_at_pause = 0
        
        self.start_time = time.time() - self.elapsed_at_pause
        vol_val = 0.0 if self.is_muted else (self.volume / 100.0)
        try: self.playback.set_volume(vol_val)
        except: pass
        
        try:
            self.playback.load_file(str(filepath))
            self.playback.play()
            if self.elapsed_at_pause > 0:
                self.playback.seek(self.elapsed_at_pause)
            self.is_playing = True
            self.start_time = time.time() - self.elapsed_at_pause
            self.add_log(f"Playing: {filename[:30]}")
        except Exception as e:
            err_msg = str(e)
            if len(err_msg) > 45: err_msg = err_msg[:45] + "..."
            self.add_log(f"Err: {err_msg}")
            self.is_playing = False

    def navigate_into(self):
        if not self.display_playlist or self.current_index < 0: return
        item = self.display_playlist[self.current_index]
        if item[0] == 'folder':
            self.current_dir = item[2]
            self.mode = "BROWSE"
            self.update_file_list()
            self.add_log(f"Entered: {item[1]}")

    def navigate_up(self):
        if self.mode == "PC_SCAN":
            self.mode = "BROWSE"
            self.update_file_list()
            self.add_log("Switched to Browse mode")
            return
        if self.current_dir != self.current_dir.parent:
            self.current_dir = self.current_dir.parent
            self.update_file_list()
            self.add_log(f"Up: {self.current_dir.name}")
        else:
            self.add_log("Already at root")

    def cycle_mode(self):
        if self.scanning:
            self.add_log("Wait for scan to finish...")
            return
        if self.mode == "BROWSE":
            self.mode = "PC_SCAN"
            self.start_pc_scan()
        else:
            self.mode = "BROWSE"
            self.update_file_list()
            self.add_log("Browse mode")

    def stop(self, reset_seek=True):
        if self.is_playing:
            self.elapsed_at_pause = time.time() - self.start_time
        self.is_playing = False
        try:
            if self.playback and self.playback.active:
                self.playback.stop()
                time.sleep(0.05)
        except:
            pass
        if reset_seek:
            self.elapsed_at_pause = 0
            self.current_filepath = None

    def toggle_pause(self):
        if not self.playback: return
        if self.is_playing:
            self.is_playing = False
            self.elapsed_at_pause = time.time() - self.start_time
            try: self.playback.pause()
            except: pass
        else:
            if not self.display_playlist:
                return
            if (self.current_index < 0 or 
                self.current_index >= len(self.display_playlist) or
                self.display_playlist[self.current_index][0] != 'file'):
                for i, item in enumerate(self.display_playlist):
                    if item[0] == 'file':
                        self.current_index = i
                        break
                else:
                    return
            item = self.display_playlist[self.current_index]
            if self.current_filepath == item[2] and self.playback.active:
                try:
                    self.playback.resume()
                    self.start_time = time.time() - self.elapsed_at_pause
                    self.is_playing = True
                except:
                    self.play_index(self.current_index, resume=True)
            else:
                self.play_index(self.current_index, resume=True)

    def seek(self, seconds):
        if not self.playback: return
        if not self.is_playing and self.elapsed_at_pause == 0: return
        current = (time.time() - self.start_time) if self.is_playing else self.elapsed_at_pause
        new_pos = max(0, min(self.duration, current + seconds))
        try:
            self.playback.seek(new_pos)
            self.elapsed_at_pause = new_pos
            self.start_time = time.time() - new_pos
        except:
            pass

    def draw_box(self, x, y, w, h, title="", color=Screen.COLOUR_WHITE, attr=Screen.A_BOLD, rounded=False, clear=True, bg=Screen.COLOUR_BLACK):
        if w < 2 or h < 2: return
        if clear:
            for i in range(h + 1):
                self.screen.print_at(" " * w, x, y + i, bg=bg)
        tl, tr, bl, br = ("╭", "╮", "╰", "╯") if rounded else ("╔", "╗", "╚", "╝")
        h_line, v_line = ("─", "│") if rounded else ("═", "║")
        self.screen.print_at(tl + h_line * (w - 2) + tr, x, y, color, attr, bg=bg)
        for i in range(1, h):
            self.screen.print_at(v_line, x, y + i, color, attr, bg=bg)
            self.screen.print_at(v_line, x + w - 1, y + i, color, attr, bg=bg)
        self.screen.print_at(bl + h_line * (w - 2) + br, x, y + h, color, attr, bg=bg)
        if title:
            clean_title = self.truncate_text(title, w - 6)
            self.screen.print_at(f" {clean_title} ", x + 2, y, Screen.COLOUR_BLACK, Screen.A_BOLD, bg=color)

    def update_scroll(self, list_h):
        if self.current_index < self.scroll_offset:
            self.scroll_offset = self.current_index
        elif self.current_index >= self.scroll_offset + list_h:
            self.scroll_offset = self.current_index - list_h + 1
        max_offset = max(0, len(self.display_playlist) - list_h)
        self.scroll_offset = max(0, min(self.scroll_offset, max_offset))

    def draw(self):
        w, h = self.screen.width, self.screen.height
        if w < 60 or h < 20:
            self.screen.print_at("Terminal too small!", (w - 18) // 2, h // 2, Screen.COLOUR_RED, Screen.A_BOLD)
            return

        top_y = 1
        main_h = h - 9

        # 1. LIBRARY
        p_w = min(48, max(28, w // 4))
        if self.scanning:
            p_title = f" [PC-SCAN] (Found {self.scan_found}...) "
        else:
            if self.mode == "PC_SCAN":
                mode_icon = "[PC-SCAN]"
                p_title = f" {mode_icon} (All Files) "
            else:
                mode_icon = "[BROWSE]"
                path_str = str(self.current_dir)
                if len(path_str) > 28:
                    parts = self.current_dir.parts
                    if len(parts) >= 3:
                        path_str = ".../" + "/".join(parts[-2:])
                p_title = f" {mode_icon} {path_str} "
            
        self.draw_box(0, top_y, p_w, main_h, p_title, Screen.COLOUR_CYAN)
        
        list_h = main_h - 1 
        self.update_scroll(list_h)

        visible_items = self.display_playlist[self.scroll_offset : self.scroll_offset + list_h]
        for i, item in enumerate(visible_items):
            actual_idx = i + self.scroll_offset
            is_sel = (actual_idx == self.current_index)
            avail_w = p_w - 2
            
            if item[0] == 'folder':
                if item[1] == '..':
                    text = "[..] (up one level)"
                    color = Screen.COLOUR_BLACK if is_sel else Screen.COLOUR_YELLOW
                else:
                    count_str = f"  ({item[3]})" if item[3] > 0 else ""
                    text = f"[+] {item[1]}{count_str}"
                    color = Screen.COLOUR_BLACK if is_sel else Screen.COLOUR_YELLOW
                bg = Screen.COLOUR_CYAN if is_sel else Screen.COLOUR_BLACK
                attr = Screen.A_BOLD
            else:
                is_playing_song = (self.current_filepath == item[2])
                if is_sel:
                    icon = '>>'
                elif is_playing_song:
                    icon = ' >'
                else:
                    icon = ' -'
                clean_name = item[1].rsplit('.', 1)[0]
                text = f"{icon} {clean_name}"
                if is_sel:
                    color = Screen.COLOUR_BLACK
                elif is_playing_song:
                    color = Screen.COLOUR_GREEN
                else:
                    color = Screen.COLOUR_WHITE
                bg = Screen.COLOUR_CYAN if is_sel else Screen.COLOUR_BLACK
                attr = Screen.A_BOLD if (is_sel or is_playing_song) else Screen.A_NORMAL
            
            display_name = self.truncate_text(text, avail_w - 1)
            padded_line = self.pad_text(f" {display_name}", avail_w)
            self.screen.print_at(padded_line, 1, top_y + 1 + i, color, attr, bg=bg)

        # 2. SPECTRUM + LIVE CLOCK
        v_w = w - p_w - 1
        curr_time = datetime.now().strftime("%H:%M:%S")
        self.draw_box(p_w, top_y, v_w, main_h, " CAVA SPECTRUM ", Screen.COLOUR_BLUE)
        self.screen.print_at(f"[ {curr_time} ]", p_w + v_w - 12, top_y, Screen.COLOUR_CYAN, Screen.A_BOLD, bg=Screen.COLOUR_BLUE)
        
        bar_area_h = main_h - 2
        bar_step = max(3, (v_w - 6) // self.fixed_bar_count)
        
        for i in range(self.fixed_bar_count):
            bar_x = p_w + 3 + (i * bar_step)
            if bar_x + 3 >= w - 1: break 
            if self.is_playing: 
                t = time.time()
                self.target_bars[i] = (math.sin(t * 8 + i * 0.3) * 0.3 + math.sin(t * 4 - i * 0.1) * 0.2 + 0.5) * bar_area_h
            else: 
                self.target_bars[i] *= 0.8
            self.last_bars[i] += (self.target_bars[i] - self.last_bars[i]) * self.smoothing
            clamped_bar_val = max(0, min(int(self.last_bars[i]), bar_area_h))
            for bh in range(clamped_bar_val):
                if bh < bar_area_h * 0.3:
                    color = Screen.COLOUR_BLUE
                elif bh < bar_area_h * 0.7:
                    color = Screen.COLOUR_CYAN
                else:
                    color = Screen.COLOUR_WHITE
                self.screen.print_at("███", bar_x, top_y + main_h - 1 - bh, color)

        # 3. BOTTOM PANELS
        self.draw_box(0, h - 8, p_w, 6, " LOGS ", Screen.COLOUR_GREEN)
        for i, log in enumerate(self.logs):
            self.screen.print_at(self.truncate_text(f" > {log}", p_w - 2), 1, h - 7 + i, Screen.COLOUR_WHITE)

        k_w = 30
        m_w = w - p_w - k_w
        self.draw_box(p_w, h - 8, m_w, 6, " SESSION ", Screen.COLOUR_MAGENTA)
        self.screen.print_at(self.truncate_text(f" TITLE : {self.metadata['title']}", m_w - 4), p_w + 2, h - 7, Screen.COLOUR_WHITE, Screen.A_BOLD)
        self.screen.print_at(self.truncate_text(f" ARTIST: {self.metadata['artist']}", m_w - 4), p_w + 2, h - 6, Screen.COLOUR_CYAN)
        
        elapsed = (time.time() - self.start_time) if self.is_playing else self.elapsed_at_pause
        dur = self.duration or 1
        bar_len = max(0, m_w - 18)
        if bar_len > 0:
            filled = int(bar_len * min(1.0, (elapsed / dur)))
            self.screen.print_at(f"{int(elapsed//60):02d}:{int(elapsed%60):02d} ", p_w + 2, h - 5, Screen.COLOUR_YELLOW)
            self.screen.print_at("-" * filled, p_w + 8, h - 5, Screen.COLOUR_YELLOW)
            self.screen.print_at("-" * (bar_len - filled), p_w + 8 + filled, h - 5, Screen.COLOUR_BLACK, Screen.A_BOLD)
            self.screen.print_at(f" {int(dur//60):02d}:{int(dur%60):02d}", p_w + 8 + bar_len, h - 5, Screen.COLOUR_YELLOW)

        self.draw_box(w - k_w, h - 8, k_w, 6, " SWEETVIBE ", Screen.COLOUR_YELLOW)
        if time.time() - self.last_cat_update > 0.3:
            self.cat_idx = (self.cat_idx + 1) % len(self.cat_frames) if self.is_playing else 0
            self.last_cat_update = time.time()
        for i, line in enumerate(self.cat_frames[self.cat_idx].split('\n')):
            self.screen.print_at(line, w - 12, h - 7 + i, Screen.COLOUR_YELLOW)
        self.screen.print_at(f"VOL: {self.volume}%", w - k_w + 2, h - 7, Screen.COLOUR_WHITE)
        self.screen.print_at(f"SR : {self.metadata['samplerate']}", w - k_w + 2, h - 6, Screen.COLOUR_WHITE)
        self.screen.print_at(f"ST : {'PLAY' if self.is_playing else 'IDLE'}", w - k_w + 2, h - 5, Screen.COLOUR_WHITE)

        footer = f" [SHUF:{'ON' if self.shuffle else 'OFF'}] [LOOP:{'ON' if self.repeat else 'OFF'}] [MOUSE:{'ON' if self.mouse_enabled else 'OFF'}] [MODE:{self.mode}] | TAB:Mode Ctrl+B:Back ^F:Search ^O:Cmd Q:Quit "
        self.screen.print_at(footer.center(w)[:w], 0, h - 1, Screen.COLOUR_BLACK, bg=Screen.COLOUR_WHITE)

        # ABOUT DIALOG
        if self.show_about:
            aw, ah = 60, 16
            ax, ay = (w - aw) // 2, (h - ah) // 2
            self.draw_box(ax, ay, aw, ah, " ABOUT SWEETVIBE ", Screen.COLOUR_MAGENTA, rounded=True)
            logo = [
                " ▐▄▄▄▄▄▄▌▐▄▄▌   ▐▄▄▌ ▐▄▄▄▄▄▌ ▐▄▄▄▄▄▌▐▄▄▄▄▄▄▌",
                "▐██▌     ▐██▌   ▐██▌▐██▌    ▐██▌      ▐██▌  ",
                " ▐█████▌ ▐██▌▐█▌▐██▌▐████▌  ▐████▌    ▐██▌  ",
                "     ▐▀▀▌▐▀▀▌▐▀▌▐▀▀ ▐▀▀▌    ▐▀▀▌      ▐▀▀▌  ",
                "▐▄▄▄▄▄▄▌  ▐▄▄▄▀▄▄▄▌  ▐▄▄▄▄▄▌ ▐▄▄▄▄▄▌  ▐▄▄▌  ",
            ]
            for i, line in enumerate(logo):
                self.screen.print_at(line.center(aw-2), ax + 1, ay + 2 + i, Screen.COLOUR_YELLOW, Screen.A_BOLD)
            info = [
                "Built with Asciimatics & just_playback",
                "A lightweight Terminal Music Player",
                "Licensed under the Apache License 2.0",
                "",
                "Developed by: Dihan Ramanayaka",
                "",
                "Press any key to close."
            ]
            for i, line in enumerate(info):
                color = Screen.COLOUR_WHITE
                if "Developed" in line: color = Screen.COLOUR_CYAN
                if "Press" in line: color = Screen.COLOUR_GREEN
                self.screen.print_at(line.center(aw-2), ax + 1, ay + 8 + i, color)

        # COMMAND/PATH PALETTE
        if self.input_mode:
            palette_w = 64
            px, py = (w - palette_w) // 2, 2
            title = "SEARCH" if self.input_mode == 'search' else "PATH / COMMAND BAR (:help, :about, :update)"
            self.draw_box(px, py, palette_w, 4, f" {title} ", Screen.COLOUR_YELLOW, rounded=True, bg=Screen.COLOUR_BLACK)
            prompt = "Filter:" if self.input_mode == 'search' else "Path :"
            self.screen.print_at(prompt, px + 2, py + 2, Screen.COLOUR_CYAN, Screen.A_BOLD)
            display_input = self.input_text if self.get_display_width(self.input_text) < palette_w - 15 else "..." + self.input_text[-(palette_w-18):]
            self.screen.print_at(display_input, px + 10, py + 2, Screen.COLOUR_WHITE, Screen.A_BOLD)
            if int(time.time() * 2) % 2 == 0:
                self.screen.print_at("█", px + 10 + self.get_display_width(display_input), py + 2, Screen.COLOUR_YELLOW)

        # HELP MENU (Dynamic Multi-Page)
        if self.show_help:
            hw, hh = 66, 22
            hx, hy = (w - hw) // 2, max(0, (h - hh) // 2 - 1)
            self.draw_box(hx, hy, hw, hh, f" HELP & SHORTCUTS (Page {self.help_page + 1}/2) ", Screen.COLOUR_YELLOW, rounded=True)
            
            help_descriptions = [
                ("up", "Move selection up"),
                ("down", "Move selection down"),
                ("enter", "Open folder / Play file"),
                ("back", "Go back / Exit Mode"),
                ("mode_switch", "Cycle Mode (Browse / PC-Scan)"),
                ("jump_music", "Jump to Music folder"),
                ("jump_docs", "Jump to Documents folder"),
                ("search", "Search / Filter songs"),
                ("open_path", "Open Path / Cmd Bar"),
                ("play_pause", "Play / Pause"),
                ("seek_forward", "Seek +10s"),
                ("seek_backward", "Seek -10s"),
                ("volume_up", "Volume Up"),
                ("volume_down", "Volume Down"),
                ("mute", "Mute Toggle"),
                ("repeat", "Toggle Repeat"),
                ("shuffle", "Toggle Shuffle"),
                ("toggle_mouse", "Toggle Mouse Support"),
                ("quit", "Quit application")
            ]
            
            pages = [
                [
                    ("--- NAVIGATION ---", "HEADER"),
                    help_descriptions[0],
                    help_descriptions[1],
                    help_descriptions[2],
                    help_descriptions[3],
                    help_descriptions[4],
                    help_descriptions[5],
                    help_descriptions[6],
                    help_descriptions[7],
                    help_descriptions[8],
                    ("", None),
                    ("--- PLAYBACK ---", "HEADER"),
                    help_descriptions[9],
                    help_descriptions[10],
                    help_descriptions[11],
                    help_descriptions[12],
                    help_descriptions[13],
                    help_descriptions[14],
                    help_descriptions[15],
                    help_descriptions[16]
                ],
                [
                    ("--- SYSTEM & MOUSE ---", "HEADER"),
                    help_descriptions[17],
                    help_descriptions[18],
                    ("", None),
                    ("--- COMMANDS (in Cmd Bar) ---", "HEADER"),
                    (":help", "Open this Help Menu"),
                    (":about", "View About SweetVibe"),
                    (":update", "Download latest update"),
                    (":keybinds", "Edit keybindings.json"),
                    ("", None),
                    ("--- CONFIG ---", "HEADER"),
                    ("Config File", "./keybindings.json"),
                    ("", None),
                    ("--- ABOUT ---", "HEADER"),
                    ("Developer", "Dihan Ramanayaka"),
                    ("License", "Apache 2.0")
                ]
            ]
            
            page_items = pages[self.help_page % 2]
            for i, item in enumerate(page_items):
                y_pos = hy + 2 + i
                if y_pos >= hy + hh - 1: break
                
                key, val = item
                if val == "HEADER":
                    self.screen.print_at(key.center(hw - 4), hx + 2, y_pos, Screen.COLOUR_CYAN, Screen.A_BOLD)
                elif key == "":
                    continue
                elif key.startswith(":") or key in ["Config File", "Developer", "License"]:
                    label = self.pad_text(key, 22)
                    self.screen.print_at(label, hx + 4, y_pos, Screen.COLOUR_YELLOW)
                    self.screen.print_at(f": {val}", hx + 28, y_pos, Screen.COLOUR_WHITE)
                else:
                    # Dynamic keybind reading from json!
                    keys_list = self.keybinds.get(key, [])
                    formatted_keys = " / ".join([k.upper() for k in keys_list])
                    label = self.pad_text(formatted_keys, 22)
                    self.screen.print_at(label, hx + 4, y_pos, Screen.COLOUR_YELLOW)
                    self.screen.print_at(f": {val}", hx + 28, y_pos, Screen.COLOUR_WHITE)
            
            self.screen.print_at("< Left / Right >".center(hw - 4), hx + 2, hy + hh - 1, Screen.COLOUR_WHITE, Screen.A_BOLD)


_shared_state = {}

def get_key_str(event):
    if not hasattr(event, 'key_code'): return None
    k = event.key_code
    if k in [Screen.KEY_BACK, -300, 8, 127]: return "backspace"
    if k == Screen.KEY_UP: return "up"
    if k == Screen.KEY_DOWN: return "down"
    if k == Screen.KEY_LEFT: return "left"
    if k == Screen.KEY_RIGHT: return "right"
    if k in [10, 13]: return "enter"
    if k == 32: return "space"
    if k == 27: return "esc"
    if k == 9: return "tab"
    if 1 <= k <= 26:
        return f"ctrl+{chr(k + 96)}"
    if 32 <= k <= 126:
        return chr(k).lower()
    return str(k)

def demo(screen):
    global _shared_state
    player = KityPlayer(screen)
    
    if _shared_state:
        player.current_index = _shared_state.get('index', -1)
        player.volume = _shared_state.get('volume', 65)
        player.is_muted = _shared_state.get('muted', False)
        player.shuffle = _shared_state.get('shuffle', False)
        player.repeat = _shared_state.get('repeat', False)
        player.current_dir = _shared_state.get('dir', player.current_dir)
        player.mode = _shared_state.get('mode', player.mode)
        player.update_file_list()
        if _shared_state.get('playing') and player.current_index != -1:
            if 0 <= player.current_index < len(player.display_playlist):
                item = player.display_playlist[player.current_index]
                if item[0] == 'file':
                    player.current_filepath = item[2]
                    player.play_index(player.current_index, resume=True, seek_to=_shared_state.get('elapsed'))

    while True:
        try:
            if screen.has_resized(): raise ResizeScreenError("Manual Resize")
            event = screen.get_event()
            
            if isinstance(event, MouseEvent):
                if player.mouse_enabled:
                    w, h = screen.width, screen.height
                    top_y = 1
                    main_h = h - 9
                    p_w = min(48, max(28, w // 4))
                    
                    # Left click
                    if event.buttons == 0:
                        if 0 <= event.x <= p_w and top_y + 1 <= event.y <= top_y + main_h - 1:
                            idx = player.scroll_offset + (event.y - (top_y + 1))
                            if 0 <= idx < len(player.display_playlist):
                                player.current_index = idx
                                item = player.display_playlist[idx]
                                if item[0] == 'folder':
                                    player.navigate_into()
                                else:
                                    player.play_index(idx)
                    # Right click
                    elif event.buttons == 1:
                        player.navigate_up()

            elif event:
                key_str = get_key_str(event)
                action = player.get_action(key_str)

                if player.input_mode:
                    if key_str in ["enter"]:
                        if player.input_mode == 'search': 
                            player.search_query = player.input_text
                            player.apply_filter()
                        elif player.input_mode == 'folder':
                            raw_text = player.input_text.strip()
                            # Only switch to command mode if it starts with ':'
                            if raw_text.startswith(":"):
                                cmd = raw_text.lower()
                                if cmd == ":help":
                                    player.show_help = True
                                    player.help_page = 0
                                elif cmd == ":about":
                                    player.show_about = True
                                elif cmd == ":update":
                                    if player.update_available:
                                        player.perform_update()
                                    else:
                                        player.add_log("No updates available.")
                                elif cmd == ":keybinds":
                                    kb_file = Path("keybindings.json")
                                    if not kb_file.exists():
                                        kb_file.write_text(json.dumps(DEFAULT_KEYBINDS, indent=4))
                                    try:
                                        if sys.platform == "win32":
                                            os.startfile(str(kb_file.resolve()))
                                        else:
                                            opener = "open" if sys.platform == "darwin" else "xdg-open"
                                            subprocess.call([opener, str(kb_file.resolve())])
                                        player.add_log("Opened keybindings.json")
                                    except Exception as e:
                                        player.add_log(f"Failed to open: {str(e)[:20]}")
                                else:
                                    player.add_log("Unknown command")
                            else:
                                # Treat as path
                                expanded_path = os.path.expanduser(os.path.expandvars(raw_text))
                                p = Path(expanded_path)
                                if p.exists() and p.is_dir(): 
                                    player.current_dir = p
                                    player.mode = "BROWSE"
                                    player.update_file_list()
                                    player.add_log(f"Path: {p}")
                                else:
                                    player.add_log("Invalid path")
                        
                        player.input_mode = None
                        player.input_text = ""
                        
                    elif key_str in ["esc", "ctrl+b"]:
                        player.input_mode = None
                        player.input_text = ""
                    elif key_str in ["backspace"]:
                        player.input_text = player.input_text[:-1]
                        if player.input_mode == 'search': player.apply_filter()
                    elif key_str and len(key_str) == 1:
                        player.input_text += key_str
                        if player.input_mode == 'search': player.apply_filter()
                
                elif player.show_about:
                    player.show_about = False
                
                elif player.show_help:
                    if key_str == "right": player.help_page = (player.help_page + 1) % 2
                    elif key_str == "left": player.help_page = (player.help_page - 1) % 2
                    elif action in ["back", "esc", "enter", "play_pause", "open_path"]: player.show_help = False
                
                else:
                    if action == "quit":
                        player.stop()
                        raise QuitApplication()
                    elif action == "play_pause": player.toggle_pause()
                    elif action == "mute": player.toggle_mute()
                    elif action == "open_path": 
                        player.input_mode = 'folder'
                        # Auto display current path
                        player.input_text = str(player.current_dir)
                    elif action == "volume_up": player.change_volume(5)
                    elif action == "volume_down": player.change_volume(-5)
                    elif action == "seek_forward": player.seek(10)
                    elif action == "seek_backward": player.seek(-10)
                    elif action == "mode_switch": player.cycle_mode()
                    elif action == "search": 
                        player.input_mode = 'search'
                        player.input_text = player.search_query
                    elif action in ["back", "esc"]: 
                        if player.search_query: 
                            player.search_query = ""
                            player.apply_filter()
                        else:
                            player.navigate_up()
                    elif action == "shuffle": 
                        player.shuffle = not player.shuffle
                        player.apply_filter()
                    elif action == "repeat": 
                        player.repeat = not player.repeat
                    elif action == "jump_music":
                        player.current_dir = Path.home() / "Music"
                        player.mode = "BROWSE"
                        player.update_file_list()
                    elif action == "jump_docs":
                        player.current_dir = Path.home() / "Documents"
                        player.mode = "BROWSE"
                        player.update_file_list()
                    elif action == "toggle_mouse":
                        player.mouse_enabled = not player.mouse_enabled
                        player.add_log(f"Mouse {'enabled' if player.mouse_enabled else 'disabled'}")
                    elif action == "up": 
                        player.current_index = max(0, player.current_index - 1)
                    elif action == "down": 
                        player.current_index = min(len(player.display_playlist)-1, player.current_index + 1)
                    elif action == "enter":
                        if 0 <= player.current_index < len(player.display_playlist):
                            item = player.display_playlist[player.current_index]
                            if item[0] == 'folder':
                                player.navigate_into()
                            else:
                                player.play_index(player.current_index)

            # Check if the track finished or crashed prematurely
            if player.is_playing and player.playback:
                try:
                    elapsed = time.time() - player.start_time
                    if elapsed > 1.0 and not player.playback.active:
                        track_dur = player.duration if player.duration > 0 else 0
                        try:
                            pb_dur = player.playback.duration
                            if pb_dur > 0: track_dur = pb_dur
                        except: pass
                        
                        if track_dur > 0 and elapsed < track_dur - 2.0:
                            player.add_log(f"Crashed at {int(elapsed)}s")
                            player.stop()
                        else:
                            if not player.display_playlist:
                                player.stop()
                            else:
                                next_idx = player.current_index if player.repeat else (player.current_index + 1) % len(player.display_playlist)
                                attempts = 0
                                found = False
                                while attempts < len(player.display_playlist):
                                    if 0 <= next_idx < len(player.display_playlist):
                                        item = player.display_playlist[next_idx]
                                        if item[0] == 'file':
                                            player.play_index(next_idx)
                                            found = True
                                            break
                                    next_idx = (next_idx + 1) % len(player.display_playlist)
                                    attempts += 1
                                if not found:
                                    player.stop()
                except:
                    pass

            screen.clear_buffer(Screen.COLOUR_BLACK, Screen.A_NORMAL, Screen.COLOUR_BLACK)
            player.draw()
            screen.refresh()
            time.sleep(0.01) 
        except ResizeScreenError:
            curr_elapsed = (time.time() - player.start_time) if player.is_playing else player.elapsed_at_pause
            _shared_state = {
                'index': player.current_index, 'elapsed': curr_elapsed, 
                'playing': player.is_playing, 'volume': player.volume, 
                'muted': player.is_muted, 'shuffle': player.shuffle, 
                'repeat': player.repeat, 'dir': player.current_dir,
                'mode': player.mode
            }
            player.stop(reset_seek=False)
            raise 
        except QuitApplication:
            _shared_state = {}
            raise

def sigint_handler(sig, frame):
    raise KeyboardInterrupt

if __name__ == "__main__":
    signal.signal(signal.SIGINT, sigint_handler)
    while True:
        try:
            Screen.wrapper(demo)
            break
        except ResizeScreenError:
            continue
        except (KeyboardInterrupt, QuitApplication):
            print_goodbye()
            break