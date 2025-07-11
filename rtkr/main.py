# rtkr/main.py - Your Python application file

import os
import json
import random
import threading
import tempfile # Import tempfile for creating temporary files
import re # Import re for regular expressions (for XML parsing)

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.window import Window # Import Window here
from kivy.core.text import LabelBase
from kivy.properties import BooleanProperty, ListProperty, DictProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.lang import Builder
from kivy.metrics import dp # Ensure dp is imported here for use in MainLayout and KV

# Import SoundLoader for audio playback
from kivy.core.audio import SoundLoader

# Import gTTS for Text-to-Speech
from gtts import gTTS

# Import configurations and utility functions from our local package
from .config import (
    JMDICT_COMMON_FILE, JLPT_LEVELS, REMOTE_JSON_URLS,
    FONT_FILE, BUFFER_SIZE, REVISIONS_FILE, FONT_SIZE_LIST,
    RESIZE_HANDLE_WIDTH_RAW, MIN_PANEL_WIDTH_RAW, MAX_PANEL_WIDTH_RATIO, # Use RAW names
    BLUE_DOT_DISPLAY_DURATION, KV_FILE # Import KV_FILE
)
from .utils import download_file_content, is_primarily_katakana, ensure_font_downloaded

# --- Initial Setup ---

# Ensure the font is downloaded and registered
ensure_font_downloaded()
LabelBase.register(name="HinaMincho", fn_regular=FONT_FILE)

# Ensure the 'data' directory exists for revisions.json
DATA_DIR = os.path.dirname(REVISIONS_FILE)
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    print(f"Created data directory: {DATA_DIR}")

# Load Kivy Language (KV) file
# The KV file should be in the same directory as main.py
Builder.load_file(os.path.join(os.path.dirname(__file__), KV_FILE))

class RevisionList(BoxLayout):
    """
    A custom BoxLayout for displaying the list of marked words for revision.
    It includes a scrollable grid of ToggleButtons and remove buttons.
    """
    revisions = ListProperty() # List of revision entries
    remove_callback = None # Callback function to remove an entry
    in_revision_mode = BooleanProperty(False) # New property to reflect MainLayout's state

    def on_revisions(self, *args):
        """
        Called when the 'revisions' property changes. Populates the list.
        """
        self.populate()

    def populate(self):
        """
        Clears and repopulates the GridLayout with revision entries.
        Each entry gets a ToggleButton (to switch between reading and word)
        and a 'X' button to remove it.
        """
        grid = self.ids.grid
        grid.clear_widgets() # Clear existing widgets
        for entry in self.revisions:
            reading = entry.get('reading','')
            word = entry.get('word','')
            
            # ToggleButton to display reading/word
            btn = ToggleButton(
                text=reading,
                font_name='HinaMincho',
                font_size=FONT_SIZE_LIST,
                size_hint_y=None,
                height=dp(40), # Use dp for consistent sizing across devices
                background_normal='', # No background for normal state
                background_down='', # No background for pressed state
                background_color=(0, 0, 0, 0), # Explicitly set transparent background color
                color=(1, 1, 1, 1), # White text color
                halign='left', # Align text to the left
                valign='middle', # Vertically align text to the middle
                padding=(dp(5), 0), # Add some left padding
                # IMPORTANT: Set text_size to the button's actual size to enable halign
                text_size=self.size # This will be updated by Kivy's layout system
            )
            # Bind button press to toggle text between reading and word
            btn.bind(on_press=lambda inst, rd=reading, w=word: setattr(inst, 'text', w if inst.text==rd else rd))
            
            # Bind to the button's size to update text_size when it changes
            # This is crucial because self.size is not immediately available when the widget is created
            btn.bind(size=lambda instance, value: setattr(instance, 'text_size', value))

            # Button to remove the entry
            remove_btn = Button(
                text='X',
                size_hint=(None,None),
                size=(dp(30),dp(30)), # Use dp for consistent sizing - ensures it's squarish
                background_normal='', # No background for normal state
                background_down='', # No background for pressed state
                background_color=(0, 0, 0, 0), # Explicitly set transparent background color
                color=(0.6, 0.6, 0.6, 1) # Grey text color for 'X'
            )
            # Bind remove button to call the remove callback
            remove_btn.bind(on_release=lambda inst, e=entry: self.remove(e))
            
            # Create a horizontal row for each entry
            row = BoxLayout(size_hint_y=None, height=dp(40)) # Use dp for height
            row.add_widget(btn)
            row.add_widget(remove_btn)
            grid.add_widget(row) # Add the row to the grid

    def remove(self, entry):
        """
        Calls the remove_callback function if it's set, passing the entry to be removed.
        """
        if self.remove_callback:
            self.remove_callback(entry)

class MainLayout(BoxLayout):
    """
    The main application layout, handling word fetching, display,
    revision list management, and the new resizable sidebar functionality.
    """
    buffer = ListProperty([]) # Buffer for upcoming words
    words = ListProperty([]) # All loaded words
    revisions = ListProperty([]) # Words marked for revision
    current = DictProperty({}) # The currently displayed word

    # Properties for resizing the revision panel
    resizing = BooleanProperty(False) # True if the user is currently dragging the resize handle
    resize_start_x = NumericProperty(0) # X-coordinate where resizing started
    resize_start_width = NumericProperty(0) # Width of the panel when resizing started
    # Apply dp() here when assigning to a Kivy property that expects dp units
    resize_handle_width = NumericProperty(dp(RESIZE_HANDLE_WIDTH_RAW)) # Width of the draggable handle
    
    _cursor_on_handle = BooleanProperty(False) # Internal flag to track if cursor is on handle

    # New properties for revision session
    in_revision_mode = BooleanProperty(False) # True if currently in a revision session
    revision_queue = ListProperty([]) # Shuffled list of words for the current revision session
    revision_index = NumericProperty(0) # Current index in the revision_queue

    # Audio related properties for TTS
    _current_sound = None # Holds the currently loaded sound object

    # New property to control word source: 'JMdict', 'JLPT1', 'JLPT2', etc.
    current_source = StringProperty('JMdict')
    # Property to control visibility of the source selection panel
    source_panel_visible = BooleanProperty(False)


    def __init__(self, **kwargs):
        """
        Initializes the MainLayout. Loads revisions, starts word loading,
        and schedules the first word display.
        """
        super().__init__(**kwargs)
        self.load_revisions() # Load previously saved revisions and source preference
        # Initial load based on saved preference or default
        threading.Thread(target=self._load_words_from_source, daemon=True).start()
        
        # Bind keyboard events for shortcuts
        Window.bind(on_key_down=self._on_keyboard_down)
        
    def _on_keyboard_down(self, window, key, scancode, codepoint, modifier):
        """
        Handles keyboard key down events for shortcuts.
        """
        # Check for spacebar (key code 32) or right arrow key (key code 275)
        if key == 32 or key == 275:
            # Ensure play_audio_btn is enabled for keyboard shortcut too
            if not self.ids.show_btn.disabled:
                self.show_word()
            elif not self.ids.next_btn.disabled:
                self.next_word()
            return True # Consume the event so it doesn't propagate further
        # Check for 'A' key (key code 97 for 'a') for audio playback
        if key == 97:
            # Ensure play_audio_btn is enabled for keyboard shortcut too
            if self.ids.play_audio_btn: # Check if the button exists
                self.play_current_audio()
            return True
        return False # Let other widgets handle the event if it's not our shortcut

    def on_touch_down(self, touch):
        """
        Handles touch down events. Checks if the touch is on the resize handle.
        """
        # Only allow resizing if not in revision mode
        if not self.in_revision_mode and self.ids.resize_handle.collide_point(*touch.pos) and self.ids.rev_panel.width > 0:
            self.resizing = True # Set resizing flag to True
            self.resize_start_x = touch.x # Record initial touch X position
            self.resize_start_width = self.ids.rev_panel.width # Record initial panel width
            Window.system_cursor = 'size_we' # Change cursor to resize icon immediately on drag start
            return True # Consume the touch event, preventing others from handling it
        # If not on the resize handle, pass the event to the parent.
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        """
        Handles touch move events. If resizing, adjusts the panel width.
        """
        if self.resizing:
            # Calculate the change in X position since the touch started.
            delta_x = touch.x - self.resize_start_x
            # Calculate the new width of the panel.
            new_width = self.resize_start_width + delta_x

            # Clamp the new width to ensure it stays within defined minimum and maximum bounds.
            new_width = max(dp(MIN_PANEL_WIDTH_RAW), new_width) # Prevent panel from becoming too narrow
            new_width = min(self.width * MAX_PANEL_WIDTH_RATIO, new_width) # Prevent panel from becoming too wide
            
            self.ids.rev_panel.width = new_width # Apply the new width to the revision panel
            return True # Consume the touch event
        
        # Pass the event to the parent.
        return super().on_touch_move(touch) # Corrected: Pass 'touch' to super().on_touch_move

    def on_touch_up(self, touch):
        """
        Handles touch up events. Resets the resizing flag and cursor.
        """
        if self.resizing:
            self.resizing = False # Reset resizing flag
            # After releasing the drag, let on_motion handle the cursor based on current hover state.
            # We explicitly set it to 'arrow' here only if it's no longer hovering over the handle
            # or if the panel is closed, to avoid a lingering 'size_we' cursor.
            if not self.ids.resize_handle.collide_point(*touch.pos) or self.ids.rev_panel.width == 0:
                Window.system_cursor = 'arrow'
                self._cursor_on_handle = False
            return True # Consume the touch event
        # If not resizing, pass the event to the parent.
        return super().on_touch_up(touch)

    def on_motion(self, etype, motion):
        """
        Handles general motion events, used for changing the cursor on hover.
        """
        # Only process 'update' events for continuous hover detection and if it's a mouse motion (not touch)
        if etype == 'update' and motion.is_mouse_motion:
            # Only change cursor if the revision panel is open, not currently resizing, and NOT in revision mode
            if self.ids.rev_panel.width > 0 and not self.resizing and not self.in_revision_mode: 
                if self.ids.resize_handle.collide_point(*motion.pos):
                    if not self._cursor_on_handle:
                        Window.system_cursor = 'size_we' # Set resize cursor
                        self._cursor_on_handle = True
                else:
                    if self._cursor_on_handle:
                        Window.system_cursor = 'arrow' # Revert to default cursor
                        self._cursor_on_handle = False
            else: # If panel is closed, resizing, or in revision mode, ensure cursor is default
                if self._cursor_on_handle:
                    Window.system_cursor = 'arrow'
                    self._cursor_on_handle = False
        
        # Call super to ensure other widgets get motion events
        return super().on_motion(etype, motion)

    @mainthread
    def play_current_audio(self):
        """
        Generates and plays TTS audio for the current word.
        Prioritizes kanji for TTS.
        """
        if self._current_sound:
            self._current_sound.stop() # Stop any currently playing sound

        # Get the inner dictionary from the 'japanese' list
        # This is where the actual 'word' and 'reading' are stored
        jap_entry = self.current.get('japanese', [{}])[0]

        word_to_speak = jap_entry.get('word', '')
        if not word_to_speak: # Fallback to reading if kanji is not available
            word_to_speak = jap_entry.get('reading', '')

        print(f"play_current_audio: Attempting to play TTS for: '{word_to_speak}'")

        if word_to_speak:
            try:
                # Create gTTS object for Japanese language
                tts = gTTS(text=word_to_speak, lang='ja')
                print("play_current_audio: gTTS object created.")
                
                # Create a temporary file to save the audio
                # Use delete=False initially so we can load it, then delete it manually
                fd, path = tempfile.mkstemp(suffix=".mp3")
                os.close(fd) # Close the file descriptor immediately

                tts.save(path) # Save audio to the temporary file
                print(f"play_current_audio: TTS audio saved to temporary file: {path}")

                # Load and play the sound from the temporary file path
                self._current_sound = SoundLoader.load(path)
                if self._current_sound:
                    self._current_sound.play()
                    print(f"play_current_audio: Playing TTS audio for: '{word_to_speak}' from {path}")
                    # Schedule deletion of the temporary file after playback
                    # Use a small delay to ensure the sound has started playing
                    Clock.schedule_once(lambda dt: os.remove(path), self._current_sound.length + 0.5 if self._current_sound.length > 0 else 1.0)
                else:
                    print(f"play_current_audio: Could not load TTS sound from file: {path}. SoundLoader returned None.")
                    os.remove(path) # Clean up temp file if loading fails
            except Exception as e:
                print(f"play_current_audio: Error generating or playing TTS audio for '{word_to_speak}': {e}")
                # Ensure temp file is cleaned up even on error, if it was created
                if 'path' in locals() and os.path.exists(path):
                    os.remove(path)
        else:
            print("play_current_audio: No word text available for TTS (word_to_speak is empty).")

    def load_revisions(self):
        """
        Loads saved revision words and the preferred word source from a JSON file.
        Handles both old (list) and new (dict) formats of revisions.json.
        """
        if os.path.exists(REVISIONS_FILE):
            try:
                with open(REVISIONS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list): # Old format: just a list of revisions
                        self.revisions = data
                        self.current_source = 'JMdict' # Default to JMdict for old format
                        print("Loaded old format revisions.json. Defaulting source to JMdict.")
                    elif isinstance(data, dict): # New format: dictionary with 'revisions' and 'current_source'
                        self.revisions = data.get('revisions', [])
                        self.current_source = data.get('current_source', 'JMdict')
                        print(f"Loaded new format revisions.json. Current source: {self.current_source}")
                    else:
                        print(f"Unexpected format in {REVISIONS_FILE}. Resetting revisions and source.")
                        self.revisions = []
                        self.current_source = 'JMdict'
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {REVISIONS_FILE}: {e}. File might be corrupted. Resetting revisions and source.")
                self.revisions = []
                self.current_source = 'JMdict'
            except Exception as e:
                print(f"Error loading revisions from {REVISIONS_FILE}: {e}. Resetting revisions and source.")
                self.revisions = []
                self.current_source = 'JMdict'
        else:
            print(f"{REVISIONS_FILE} not found. Starting with empty revisions and default source.")
            self.revisions = []
            self.current_source = 'JMdict' # Default to JMdict if file doesn't exist

        # Schedule UI update for the source button text after loading preference
        Clock.schedule_once(lambda dt: self._update_select_source_button_text(), 0.1)


    def save_revisions(self):
        """
        Saves the current list of revision words and the preferred word source to a JSON file.
        """
        try:
            data = {
                'revisions': self.revisions,
                'current_source': self.current_source # Save the current source
            }
            with open(REVISIONS_FILE,'w',encoding='utf-8') as f:
                json.dump(data,f,ensure_ascii=False,indent=2)
        except Exception as e:
            print(f"Error saving revisions: {e}")

    @mainthread
    def _update_select_source_button_text(self):
        """
        Updates the text of the main 'Select Source' button based on the current source.
        """
        if self.current_source == 'JMdict':
            self.ids.select_source_btn.text = 'Source: JMdict'
        elif self.current_source.startswith('JLPT'):
            self.ids.select_source_btn.text = f'Source: {self.current_source}'
        else:
            self.ids.select_source_btn.text = 'Select Source' # Fallback

    def _load_words_from_source(self):
        """
        Loads words based on the current source preference (JMdict or JLPT level).
        """
        self.words = [] # Clear existing words
        self.buffer = [] # Clear buffer
        # Clear current word display and disable buttons during loading
        Clock.schedule_once(lambda dt: setattr(self.ids.word_label, 'text', "Loading words..."), 0.1)
        Clock.schedule_once(lambda dt: setattr(self.ids.show_btn, 'disabled', True), 0.1)
        Clock.schedule_once(lambda dt: setattr(self.ids.next_btn, 'disabled', True), 0.1)
        Clock.schedule_once(lambda dt: setattr(self.ids.mark_btn, 'disabled', True), 0.1)

        if self.current_source == 'JMdict':
            self._load_from_jmdict_e()
        elif self.current_source.startswith('JLPT'):
            try:
                level = int(self.current_source.replace('JLPT', ''))
                self._load_from_jlpt_level(level)
            except ValueError:
                print(f"Invalid JLPT source format: {self.current_source}")
                Clock.schedule_once(lambda dt: self.display_error_message("Invalid JLPT source!"), 0.1)
        else:
            print(f"Unknown source: {self.current_source}. Defaulting to JMdict.")
            self.current_source = 'JMdict'
            self._load_from_jmdict_e()


        if self.words:
            for _ in range(BUFFER_SIZE): threading.Thread(target=self.buffer_task,daemon=True).start()
            Clock.schedule_once(lambda dt: self.try_next(), 0.1)
        else:
            print("Word list is empty after loading. The app may not display words correctly.")
            Clock.schedule_once(lambda dt: self.display_error_message("No words loaded from source!"), 0.1)

    def _load_from_jmdict_e(self):
        """
        Loads JMdict words from the specified XML file using regex parsing.
        Assumes the file is already present.
        """
        print("Loading from JMdict_e...")
        # Check if the JMdict file exists in the resources directory
        jmdict_path = os.path.join(os.path.dirname(__file__), JMDICT_COMMON_FILE)
        if not os.path.exists(jmdict_path):
            print(f"Error: {jmdict_path} not found.")
            Clock.schedule_once(lambda dt: self.display_error_message(f"Error: {JMDICT_COMMON_FILE} not found!"), 0.1)
            return

        try:
            file_size_bytes = os.path.getsize(jmdict_path)
            file_size_mb = file_size_bytes / (1024 * 1024)
            print(f"Loading words from {jmdict_path} (Size: {file_size_mb:.2f} MB)...")
            
            with open(jmdict_path, 'r', encoding='utf-8') as file:
                full_content = file.read()
            
            # Split the content into individual entries
            # The Tkinter script splits by '<entry>', so we'll do the same.
            # We skip the first element as it's usually empty or preamble before the first <entry>
            dictionary_entries_raw = full_content.split('<entry>')[1:] 
            
            loaded_words = []
            kanji_pattern = re.compile(r'<keb>(.*?)</keb>')
            reading_pattern = re.compile(r'<reb>(.*?)</reb>')

            for entry_text in dictionary_entries_raw:
                kanji = ''
                reading = ''

                # Find the first kanji
                kanji_match = kanji_pattern.search(entry_text)
                if kanji_match:
                    kanji = kanji_match.group(1).strip()

                # Find the first reading
                reading_match = reading_pattern.search(entry_text)
                if reading_match:
                    reading = reading_match.group(1).strip()
                
                # New filtering logic: Skip if no kanji and the reading is primarily katakana
                if not kanji and is_primarily_katakana(reading):
                    continue

                # Only add if we have at least a reading or a kanji (after filtering)
                if kanji or reading:
                    loaded_words.append({'japanese': [{'reading': reading, 'word': kanji}]})
            
            self.words = loaded_words
            print(f"Loaded {len(self.words)} words from JMdict XML using regex parsing.")

        except IOError as e:
            print(f"IO Error reading {jmdict_path}: {e}")
            Clock.schedule_once(lambda dt: self.display_error_message(f"IO Error: {e}"), 0.1)
        except Exception as e:
            print(f"An unexpected error occurred while loading JMdict words: {e}")
            Clock.schedule_once(lambda dt: self.display_error_message(f"Unexpected Error: {e}"), 0.1)

    def _load_from_jlpt_level(self, level):
        """
        Loads JLPT words for a specific level from the GitHub CSV API.
        """
        print(f"Loading from JLPT N{level} (GitHub CSV API)...")
        jlpt_words = []
        csv_url = REMOTE_JSON_URLS.get(level) # Get the URL for the specific level

        if not csv_url:
            print(f"No URL found for JLPT N{level}.")
            Clock.schedule_once(lambda dt: self.display_error_message(f"No URL for JLPT N{level}!"), 0.1)
            return

        csv_content = download_file_content(csv_url) # Use the new download function from utils

        if csv_content:
            # Split content into lines and skip the header (first line)
            lines = csv_content.strip().split('\n')[1:] 
            for line in lines:
                parts = line.split(',') # Split by comma
                if len(parts) >= 2: # Ensure we have at least 'expression' and 'reading'
                    expression = parts[0].strip() # First part is 'expression' (kanji)
                    reading = parts[1].strip()    # Second part is 'reading'

                    # Apply the same Katakana filtering logic from utils
                    if not expression and is_primarily_katakana(reading):
                        continue

                    if expression or reading:
                        # Reconstruct into the expected {'japanese': [{'reading': ..., 'word': ...}]} format
                        jlpt_words.append({'japanese': [{'reading': reading, 'word': expression}]})
        else:
            print(f"No content or malformed response from CSV API for JLPT N{level}.")
        
        self.words = jlpt_words
        print(f"Loaded {len(self.words)} words from JLPT N{level}.")

        if len(self.words) == 0:
            Clock.schedule_once(lambda dt: self.display_error_message(f"No words loaded from JLPT N{level}!"), 0.1)

    def set_source(self, source_name):
        """
        Sets the current word source, saves the preference, and reloads words.
        """
        self.current_source = source_name
        print(f"Set word source to: {self.current_source}")
        self._update_select_source_button_text() # Update button text immediately
        self.save_revisions() # Save preference
        self.toggle_source_panel() # Hide the source selection panel after selection
        
        # Clear current word and buffer, then reload from the new source
        self.current = {}
        self.buffer = []
        Clock.schedule_once(lambda dt: setattr(self.ids.word_label, 'text', "Switching source..."), 0.1)
        threading.Thread(target=self._load_words_from_source, daemon=True).start()

    def toggle_source_panel(self):
        """
        Toggles the visibility of the source selection panel.
        """
        self.source_panel_visible = not self.source_panel_visible
        print(f"toggle_source_panel called. source_panel_visible: {self.source_panel_visible}")
        # If the panel is being hidden, ensure the main button text is updated
        if not self.source_panel_visible:
            self._update_select_source_button_text()

    def on_in_revision_mode(self, instance, value):
        """
        Observer for in_revision_mode. Controls visibility of source selection UI.
        """
        if value: # If entering revision mode
            self.source_panel_visible = False # Hide source selection panel
            # The KV file will handle hiding the 'select_source_btn' via opacity/height
        else: # If exiting revision mode
            # The KV file will handle showing the 'select_source_btn' via opacity/height
            # The source panel itself remains hidden until explicitly toggled by user
            pass


    def buffer_task(self):
        """
        Fetches a single word entry and adds it to the buffer.
        Runs in a separate thread to keep the UI responsive.
        """
        print("buffer_task: Attempting to fetch entry...")
        entry = self.fetch_entry()
        if entry:
            self.buffer.append(entry)
            print(f"buffer_task: Appended entry to buffer. Buffer size: {len(self.buffer)}")
        else:
            print("buffer_task: fetch_entry returned None.")

    def fetch_entry(self):
        """
        Fetches a random word entry from the loaded JMdict data.
        This function now expects self.words to already contain pre-processed
        dictionaries in the format {'japanese': [{'reading': ..., 'word': ...}]}.
        """
        if not self.words:
            print("fetch_entry: self.words is empty, cannot fetch.")
            return None
        
        # Select a random entry from the pre-processed list
        item = random.choice(self.words)
        
        # 'item' is already in the expected format, so no need for further parsing here.
        # Just return it directly.
        print(f"fetch_entry: Selected item: {item.get('japanese', [{}])[0].get('reading', '')} (Kanji: {item.get('japanese', [{}])[0].get('word', '')})")
        
        # Basic validation to ensure the item structure is as expected
        if not item or not isinstance(item, dict) or 'japanese' not in item or \
           not isinstance(item['japanese'], list) or not item['japanese'] or \
           not isinstance(item['japanese'][0], dict):
            print(f"fetch_entry: Malformed item structure encountered: {item}")
            return None

        # Extract the inner dictionary
        jap_entry = item['japanese'][0]
        kanji = jap_entry.get('word', '')
        reading = jap_entry.get('reading', '')

        if not kanji and not reading:
            print(f"fetch_entry: Entry has no kanji or reading after extraction: {item}")
            return None

        return item 

    @mainthread
    def try_next(self):
        """
        Attempts to display the next word from the buffer. If the buffer is empty,
        it schedules itself to try again shortly. This is for normal mode.
        """
        if self.in_revision_mode: return # Do not run in revision mode

        if self.buffer:
            self.next_word() # Display next word if available
        else:
            # If self.words is empty, it means the loading failed. Display error.
            if not self.words:
                print("No words available to display. Please check the JMdict file.")
                setattr(self.ids.word_label, 'text', "No words loaded!") # This message is already set by display_error_message
                setattr(self.ids.show_btn, 'disabled', True)
                setattr(self.ids.next_btn, 'disabled', True)
                setattr(self.ids.mark_btn, 'disabled', True)
                return # Stop trying if no words are loaded

            # If self.words is populated but buffer is empty, wait for buffer_task to fill it.
            print(f"Buffer is empty ({len(self.buffer)} words), but words list has {len(self.words)} words. Retrying in 0.1s...")
            Clock.schedule_once(lambda dt: self.try_next(),0.1)

    @mainthread
    def next_word(self):
        """
        Displays the next word. Behavior depends on whether in revision mode or normal mode.
        """
        if self.in_revision_mode:
            self.revision_index += 1
            self.display_revision_word()
        else:
            if not self.buffer: 
                print("next_word: Buffer is empty, cannot display next word.")
                return # Do nothing if buffer is empty
            self.current=self.buffer.pop(0) # Get the next word from the buffer
            # The structure of self.current is now directly from the processed XML.
            # It's already in the {'japanese': [{'reading': reading, 'word': kanji}]} format.
            jap=self.current.get('japanese',[{}])[0] # Extract Japanese word data
            self.ids.word_label.text=jap.get('reading','...') # Display the reading
            
            # Enable/disable buttons based on current state.
            self.ids.show_btn.disabled=False
            self.ids.next_btn.disabled=True
            self.ids.mark_btn.disabled=False
            
            # Show the blue dot when a new word (reading) is displayed
            self.ids.blue_dot.opacity = 1
            # Schedule the blue dot to disappear after BLUE_DOT_DISPLAY_DURATION
            Clock.schedule_once(self._hide_blue_dot, BLUE_DOT_DISPLAY_DURATION)
            
            # Start a new thread to replenish the buffer.
            threading.Thread(target=self.buffer_task,daemon=True).start()

            # Automatically play TTS audio for the new word
            self.play_current_audio()

    @mainthread
    def _hide_blue_dot(self, dt):
        """
        Hides the blue dot. This method is scheduled by Clock.schedule_once.
        Only hides if not in revision mode.
        """
        if not self.in_revision_mode:
            self.ids.blue_dot.opacity = 0

    def show_word(self):
        """
        Reveals the full Japanese word (kanji) and updates button states.
        Behavior depends on whether in revision mode or normal mode.
        """
        if self.in_revision_mode:
            # In revision mode, show the Kanji for the current word
            if self.revision_index < len(self.revision_queue):
                current_rev_word = self.revision_queue[self.revision_index]
                self.ids.word_label.text = current_rev_word.get('word', '')
                self.ids.show_btn.disabled = True
                self.ids.next_btn.disabled = False
        else:
            # In normal mode, reveal the kanji from the current word
            txt=self.current.get('japanese',[{}])[0].get('word','') # Get the full word
            self.ids.word_label.text=txt # Display the full word
            self.ids.show_btn.disabled=True # Disable "Show word" button
            self.ids.next_btn.disabled=False # Enable "Next" button
            
    def mark_current(self):
        """
        Marks the current word for revision and saves the revisions.
        Only callable in normal mode.
        """
        if self.in_revision_mode: return # Cannot mark in revision mode

        j=self.current.get('japanese',[{}])[0]
        entry={'reading':j.get('reading',''),'word':j.get('word','')}
        if entry not in self.revisions: # Avoid duplicate entries
            self.revisions.append(entry) # Add to revisions list
            self.save_revisions() # Save revisions to file
        self.ids.mark_btn.disabled=True # Disable "Mark" button after marking

    def toggle_review(self):
        """
        Toggles the visibility and width of the revision panel.
        Only callable in normal mode.
        """
        if self.in_revision_mode: return # Cannot toggle review panel in revision mode

        panel=self.ids.rev_panel
        if panel.width > 0:
            # If open, close it smoothly
            panel.width = 0
            panel.opacity = 0
            self.ids.resize_handle.opacity = 0 # Hide handle
            Window.system_cursor = 'arrow' # Revert cursor when closing
            self._cursor_on_handle = False
        else:
            # If closed, open it to a default width and make it visible
            panel.width = dp(MIN_PANEL_WIDTH_RAW) # Use the config value here, wrapped with dp()
            panel.opacity = 1
            self.ids.resize_handle.opacity = 1 # Show handle

    def on_remove_revision(self, entry):
        """
        Callback function to remove a specific entry from the revisions list.
        """
        self.revisions=[e for e in self.revisions if e!=entry] # Filter out the removed entry
        self.save_revisions() # Save updated revisions
        self.ids.rev_panel.populate() # Repopulate the revision list UI
        # If the revision queue is affected, update it
        if self.in_revision_mode:
            self.revision_queue = [e for e in self.revision_queue if e!=entry]
            # Adjust revision_index if the removed item was before the current one
            if self.revision_index >= len(self.revision_queue) and len(self.revision_queue) > 0:
                self.revision_index = len(self.revision_queue) - 1
            elif len(self.revision_queue) == 0:
                self.end_revision_session() # End session if no words left
            else:
                self.display_revision_word() # Redisplay current word if it changed

    @mainthread
    def start_revision_session(self):
        """
        Initiates the revision session.
        """
        if not self.revisions:
            print("No words in revision list to start a session.")
            return

        self.in_revision_mode = True
        self.revision_queue = list(self.revisions) # Copy and shuffle revisions
        random.shuffle(self.revision_queue)
        self.revision_index = 0

        # Close the revision panel when starting a session
        self.ids.rev_panel.width = 0
        self.ids.rev_panel.opacity = 0
        self.ids.resize_handle.opacity = 0
        Window.system_cursor = 'arrow'
        self._cursor_on_handle = False
        self.ids.blue_dot.opacity = 0 # Ensure blue dot is hidden

        self.display_revision_word()

    @mainthread
    def display_revision_word(self, *args): # Added *args to allow scheduling
        """
        Displays the current word in the revision session.
        """
        if self.revision_index < len(self.revision_queue):
            # Update self.current with the revision word before playing audio
            self.current = {'japanese': [self.revision_queue[self.revision_index]]}
            current_rev_word = self.revision_queue[self.revision_index]
            self.ids.word_label.text = current_rev_word.get('reading', '...') # Show reading first
            
            setattr(self.ids.show_btn, 'disabled', False)
            setattr(self.ids.next_btn, 'disabled', True)
            # Mark button is hidden/disabled via KV, review_toggle_btn too

            # Automatically play TTS audio for the revision word
            self.play_current_audio()
        else:
            # End of revision session
            setattr(self.ids.word_label, 'text', "Revision Session Complete!")
            setattr(self.ids.show_btn, 'disabled', True)
            setattr(self.ids.next_btn, 'disabled', True)
            Clock.schedule_once(self.end_revision_session, 2) # Auto-end after 2 seconds

    @mainthread
    def end_revision_session(self, *args): # Added *args to allow scheduling
        """
        Ends the revision session and returns to normal word review.
        """
        self.in_revision_mode = False
        self.revision_queue = []
        self.revision_index = 0
        
        # Reset UI to normal mode
        setattr(self.ids.word_label, 'text', "...")
        setattr(self.ids.show_btn, 'disabled', True)
        setattr(self.ids.next_btn, 'disabled', True)
        setattr(self.ids.mark_btn, 'disabled', False)
        
        # Re-enable review list toggle if needed (KV handles opacity)
        # Re-enable resize handle if needed (KV handles opacity)
        
        self.try_next() # Get a new random word for normal mode

    @mainthread
    def display_error_message(self, message):
        """
        Displays an error message on the main word label and disables buttons.
        """
        setattr(self.ids.word_label, 'text', message)
        Clock.schedule_once(lambda dt: setattr(self.ids.show_btn, 'disabled', True), 0.1)
        Clock.schedule_once(lambda dt: setattr(self.ids.next_btn, 'disabled', True), 0.1)
        Clock.schedule_once(lambda dt: setattr(self.ids.mark_btn, 'disabled', True), 0.1)


class RandomJapaneseApp(App):
    """
    The main Kivy application class.
    """
    def build(self):
        """
        Builds the root widget of the application.
        """
        Window.clearcolor=(0.082,0.082,0.098,1) # Set window background color
        return MainLayout() # Return the main layout as the root widget

if __name__=='__main__':
    # Set the window size here, before the app runs
    Window.size = (1280, 720) # Example: 1280 pixels wide, 720 pixels high
    RandomJapaneseApp().run()
