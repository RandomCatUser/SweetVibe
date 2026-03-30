import os
import sys
import time
import random
import math
import subprocess
import unicodedata
from pathlib import Path
from datetime import datetime

# Dependencies: pip install asciimatics tinytag
try:
    from asciimatics.screen import Screen
    from asciimatics.exceptions import ResizeScreenError
    from tinytag import TinyTag
except ImportError:
    print("Missing dependencies. Please run: pip install asciimatics tinytag")
    sys.exit(1)

class KityPlayer:
    def __init__(self, screen):
        self.screen = screen
        self.base_dir = Path.cwd() / "songs"
        self.current_dir = self.base_dir if self.base_dir.exists() else Path.cwd()
        
        self.all_songs = []
        self.display_playlist = []
        self.current_index = -1
        self.scroll_offset = 0  
        
        self.is_playing = False
        self.repeat = False
        self.shuffle = False
        self.search_query = ""
        self.volume = 65
        self.is_muted = False
        
        self.audio_proc = None
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
        self.show_about = False
        self.logs = ["System Booted Successfully", "Welcome to SweetVibe"]

        self.update_file_list()

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

    def update_file_list(self):
        extensions = {'.mp3', '.wav', '.flac', '.m4a', '.ogg'}
        try:
            if not self.current_dir.exists():
                self.current_dir = Path.cwd()
            files = [f.name for f in self.current_dir.iterdir() if f.suffix.lower() in extensions]
            self.all_songs = sorted(files)
            self.apply_filter()
        except Exception as e:
            self.add_log(f"Dir Error: {str(e)}")

    def apply_filter(self):
        filtered = self.all_songs[:]
        query = self.input_text if (self.input_mode == 'search') else self.search_query
        if query:
            filtered = [f for f in filtered if query.lower() in f.lower()]
        
        if self.shuffle:
            random.shuffle(filtered)
            
        self.display_playlist = filtered
        if not self.display_playlist:
            self.current_index = -1
        elif self.current_index >= len(self.display_playlist):
            self.current_index = 0

    def add_log(self, msg):
        now = datetime.now().strftime('%H:%M')
        self.logs.append(f"[{now}] {msg}")
        if len(self.logs) > 4: self.logs.pop(0)

    def change_volume(self, delta):
        self.volume = max(0, min(100, self.volume + delta))
        if self.is_playing:
            curr_pos = time.time() - self.start_time
            self.play_index(self.current_index, resume=True, seek_to=curr_pos)
        self.add_log(f"Volume: {self.volume}%")

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        curr_pos = (time.time() - self.start_time) if self.is_playing else self.elapsed_at_pause
        self.play_index(self.current_index, resume=True, seek_to=curr_pos)
        self.add_log("Muted" if self.is_muted else "Unmuted")

    def play_index(self, index, resume=False, seek_to=None):
        if not self.display_playlist or index < 0 or index >= len(self.display_playlist): return
        self.stop(reset_seek=(not resume and seek_to is None))
        self.current_index = index
        filename = self.display_playlist[index]
        filepath = self.current_dir / filename
        try:
            tag = TinyTag.get(str(filepath))
            self.duration = tag.duration or 0
            self.metadata["title"] = tag.title or filename
            self.metadata["artist"] = tag.artist or "Unknown Artist"
            self.metadata["samplerate"] = f"{int(tag.samplerate/1000)}kHz" if tag.samplerate else "44.1kHz"
        except:
            self.metadata["title"] = filename
            self.metadata["artist"] = "Unknown"

        if seek_to is not None: self.elapsed_at_pause = max(0, min(self.duration, seek_to))
        elif not resume: self.elapsed_at_pause = 0
        
        self.start_time = time.time() - self.elapsed_at_pause
        self.is_playing = True
        
        vol_val = 0 if self.is_muted else self.volume
        cmd = ["ffplay", "-nodisp", "-autoexit", "-volume", str(vol_val)]
        if self.elapsed_at_pause > 0: cmd.extend(["-ss", str(self.elapsed_at_pause)])
        cmd.append(str(filepath))
        self.audio_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self, reset_seek=True):
        if self.is_playing: self.elapsed_at_pause = time.time() - self.start_time
        self.is_playing = False
        if self.audio_proc:
            self.audio_proc.terminate()
            self.audio_proc.wait() 
            self.audio_proc = None
        if reset_seek: self.elapsed_at_pause = 0

    def toggle_pause(self):
        if self.is_playing: self.stop(reset_seek=False)
        else:
            if self.current_index == -1 and self.display_playlist: self.play_index(0)
            else: self.play_index(self.current_index, resume=True)

    def seek(self, seconds):
        if not self.is_playing and self.elapsed_at_pause == 0: return
        current = (time.time() - self.start_time) if self.is_playing else self.elapsed_at_pause
        new_pos = max(0, min(self.duration, current + seconds))
        self.play_index(self.current_index, resume=True, seek_to=new_pos)

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
        p_w = min(40, max(25, w // 4))
        p_title = " LIBRARY " if not self.search_query else f" SEARCH: {self.search_query} "
        self.draw_box(0, top_y, p_w, main_h, p_title, Screen.COLOUR_CYAN)
        
        list_h = main_h - 1 
        self.update_scroll(list_h)

        visible_songs = self.display_playlist[self.scroll_offset : self.scroll_offset + list_h]
        for i, song in enumerate(visible_songs):
            actual_idx = i + self.scroll_offset
            is_sel = (actual_idx == self.current_index)
            color = Screen.COLOUR_BLACK if is_sel else Screen.COLOUR_WHITE
            bg = Screen.COLOUR_CYAN if is_sel else Screen.COLOUR_BLACK
            icon = '♪ ' if is_sel else '  '
            clean_name = song.rsplit('.', 1)[0]
            
            avail_w = p_w - 2
            display_name = self.truncate_text(f"{icon}{clean_name}", avail_w - 1)
            padded_line = self.pad_text(f" {display_name}", avail_w)
            
            self.screen.print_at(padded_line, 1, top_y + 1 + i, color, Screen.A_BOLD if is_sel else Screen.A_NORMAL, bg=bg)

        # 2. SPECTRUM (CAVA STYLE GRADIENT)
        v_w = w - p_w - 1
        self.draw_box(p_w, top_y, v_w, main_h, " CAVA SPECTRUM ", Screen.COLOUR_BLUE)
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

        footer = f" [SHUF:{'ON' if self.shuffle else 'OFF'}] [LOOP:{'ON' if self.repeat else 'OFF'}] | ^H:Help ^A:About ^F:Search ^B:Back Q:Quit "
        self.screen.print_at(footer.center(w)[:w], 0, h - 1, Screen.COLOUR_BLACK, bg=Screen.COLOUR_WHITE)

        # ABOUT DIALOG
        if self.show_about:
            aw, ah = 54, 13
            ax, ay = (w - aw) // 2, (h - ah) // 2
            self.draw_box(ax, ay, aw, ah, " ABOUT SWEETVIBE ", Screen.COLOUR_MAGENTA, rounded=True)
            about_lines = [
                "SweetVibe TUI Player v1.1",
                "Built with Asciimatics & FFmpeg",
                "",
                "A lightweight Terminal Music Player",
                "featuring real-time CAVA-style visualizers.",
                "",
                "--- CREDITS ---",
                "Developed by: Dihan Ramanayaka",
                "",
                "Press any key to close."
            ]
            for i, line in enumerate(about_lines):
                # Highlight credits line
                if "Dihan" in line:
                    color = Screen.COLOUR_YELLOW
                elif line.startswith("---"):
                    color = Screen.COLOUR_CYAN
                elif "Press" in line:
                    color = Screen.COLOUR_GREEN
                else:
                    color = Screen.COLOUR_WHITE
                self.screen.print_at(line.center(aw-2), ax + 1, ay + 2 + i, color)

        # SEARCH/PATH PALETTE
        if self.input_mode:
            palette_w = 64
            px, py = (w - palette_w) // 2, 2
            title = "SEARCH" if self.input_mode == 'search' else "CHANGE DIRECTORY"
            self.draw_box(px, py, palette_w, 4, f" COMMAND: {title} ", Screen.COLOUR_YELLOW, rounded=True, bg=Screen.COLOUR_BLACK)
            prompt = "Filter:" if self.input_mode == 'search' else "Path:"
            self.screen.print_at(prompt, px + 2, py + 2, Screen.COLOUR_CYAN, Screen.A_BOLD)
            display_input = self.input_text if self.get_display_width(self.input_text) < palette_w - 15 else "..." + self.input_text[-(palette_w-18):]
            self.screen.print_at(display_input, px + 10, py + 2, Screen.COLOUR_WHITE, Screen.A_BOLD)
            if int(time.time() * 2) % 2 == 0:
                self.screen.print_at("█", px + 10 + self.get_display_width(display_input), py + 2, Screen.COLOUR_YELLOW)

        # HELP MENU
        if self.show_help:
            hw, hh = 62, 19
            hx, hy = (w - hw) // 2, (h - hh) // 2 - 1
            self.draw_box(hx, hy, hw, hh, " HELP & COMMANDS ", Screen.COLOUR_YELLOW, rounded=True)
            help_items = [
                ("CATEGORY: NAVIGATION", Screen.COLOUR_CYAN),
                ("UP / DOWN", "Navigate Song List"),
                ("ENTER", "Play Selected Song"),
                ("CTRL + F", "Search songs"),
                ("CTRL + O", "Open Path"),
                ("", None),
                ("CATEGORY: PLAYBACK", Screen.COLOUR_CYAN),
                ("SPACE", "Play / Pause"),
                ("LEFT / RIGHT", "Seek -/+ 10s"),
                ("+ / -", "Volume Up / Down"),
                ("M", "Mute Toggle"),
                ("", None),
                ("CATEGORY: SYSTEM", Screen.COLOUR_CYAN),
                ("CTRL + A", "About This Player"),
                ("CTRL + E", "Toggle Shuffle"),
                ("R", "Toggle Repeat"),
                ("Q", "Quit")
            ]
            for i, item in enumerate(help_items):
                if item[1] is None: continue
                color = item[1] if isinstance(item[1], int) else Screen.COLOUR_WHITE
                label = self.pad_text(item[0], 16)
                self.screen.print_at(label, hx + 4, hy + 2 + i, Screen.COLOUR_YELLOW if isinstance(item[1], str) else color)
                if isinstance(item[1], str):
                    self.screen.print_at(f": {item[1]}", hx + 20, hy + 2 + i, Screen.COLOUR_WHITE)

_shared_state = {}

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
        player.update_file_list()
        if _shared_state.get('playing') and player.current_index != -1:
            player.play_index(player.current_index, resume=True, seek_to=_shared_state.get('elapsed'))

    while True:
        try:
            if screen.has_resized(): raise ResizeScreenError("Manual Resize")
            event = screen.get_event()
            if event and hasattr(event, 'key_code'):
                k = event.key_code
                ctrl_a, ctrl_b, ctrl_e, ctrl_f, ctrl_h, ctrl_o, esc = (k == 1), (k == 2), (k == 5), (k == 6), (k == 8), (k == 15), (k == 27)

                if player.input_mode:
                    if k in [10, 13]: 
                        if player.input_mode == 'search': 
                            player.search_query = player.input_text
                        elif player.input_mode == 'folder':
                            p = Path(player.input_text)
                            if p.exists() and p.is_dir(): 
                                player.current_dir = p
                                player.update_file_list()
                        player.input_mode = None
                        player.input_text = ""
                        player.apply_filter()
                    elif ctrl_b or esc: 
                        player.input_mode = None
                        player.input_text = ""
                    elif k in [Screen.KEY_BACK, -300, 8, 127]: 
                        player.input_text = player.input_text[:-1]
                        if player.input_mode == 'search': player.apply_filter()
                    elif 32 <= k <= 126: 
                        player.input_text += chr(k)
                        if player.input_mode == 'search': player.apply_filter()
                
                elif player.show_about:
                    # Closing about with any key
                    player.show_about = False
                
                elif player.show_help:
                    if ctrl_b or ctrl_h or esc: player.show_help = False
                
                else:
                    if k in [ord('q'), ord('Q')]: player.stop(); sys.exit(0)
                    elif k == ord(' '): player.toggle_pause()
                    elif k in [ord('m'), ord('M')]: player.toggle_mute()
                    elif ctrl_h: player.show_help = True
                    elif ctrl_a: player.show_about = True
                    elif k == ord('+') or k == ord('='): player.change_volume(5)
                    elif k == ord('-') or k == ord('_'): player.change_volume(-5)
                    elif k == Screen.KEY_RIGHT: player.seek(10)
                    elif k == Screen.KEY_LEFT: player.seek(-10)
                    elif ctrl_f: 
                        player.input_mode = 'search'
                        player.input_text = player.search_query
                    elif ctrl_o: 
                        player.input_mode = 'folder'
                        player.input_text = str(player.current_dir)
                    elif ctrl_b or esc: 
                        if player.search_query: 
                            player.search_query = ""
                            player.apply_filter()
                    elif ctrl_e: 
                        player.shuffle = not player.shuffle
                        player.apply_filter()
                    elif k in [ord('r'), ord('R')]: 
                        player.repeat = not player.repeat
                    elif k == Screen.KEY_UP: player.current_index = max(0, player.current_index - 1)
                    elif k == Screen.KEY_DOWN: player.current_index = min(len(player.display_playlist)-1, player.current_index + 1)
                    elif k in [10, 13]: player.play_index(player.current_index)

            if player.is_playing and player.audio_proc and player.audio_proc.poll() is not None:
                next_idx = player.current_index if player.repeat else (player.current_index + 1) % len(player.display_playlist)
                player.play_index(next_idx)

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
                'repeat': player.repeat, 'dir': player.current_dir
            }
            player.stop(reset_seek=False)
            raise 

if __name__ == "__main__":
    while True:
        try:
            Screen.wrapper(demo)
            break
        except ResizeScreenError:
            continue