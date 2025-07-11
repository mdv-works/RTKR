# rtkr/config.py

import os
# Removed: from kivy.metrics import dp # dp should not be used here

# --- File Paths ---
# JMdict_e XML file (should be placed in rtkr/resources/)
JMDICT_COMMON_FILE = os.path.join('resources', 'JMdict_e')

# JLPT specific configurations
JLPT_LEVELS = [1, 2, 3, 4, 5]
# Updated to use the new GitHub CSV source
# Using .format() instead of f-string as a workaround for URL parsing issue
REMOTE_JSON_URLS = {lvl: "https://raw.githubusercontent.com/elzup/jlpt-word-list/refs/heads/master/src/n{}.csv".format(lvl) for lvl in JLPT_LEVELS}

# Local JLPT CSV files (fallback if online download fails)
# These files should be placed in rtkr/resources/
LOCAL_JLPT_FILES = {
    1: os.path.join('resources', 'n1.csv'),
    2: os.path.join('resources', 'n2.csv'),
    3: os.path.join('resources', 'n3.csv'),
    4: os.path.join('resources', 'n4.csv'),
    5: os.path.join('resources', 'n5.csv'),
}

# Font file (should be placed in rtkr/resources/fonts/)
FONT_URL = "https://github.com/google/fonts/raw/master/ofl/hinamincho/HinaMincho-Regular.ttf"
FONT_FILE = os.path.join(os.path.dirname(__file__), 'resources', 'fonts', 'HinaMincho-Regular.ttf') # Updated path

# Revisions file (will be stored in the 'data' directory outside the package)
# This path is relative to the directory where the app is run from (e.g., rtkr/)
REVISIONS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'revisions.json') # Updated path

# Kivy Language (KV) file
KV_FILE = 'rtkr.kv' # Name of the KV file, assumed to be in the same directory as main.py

# --- Application Settings ---
BUFFER_SIZE = 5  # Number of words to pre-fetch
FONT_SIZE_LIST = 24 # Font size for items in the revision list
# These should be raw numbers, not dp() calls. dp() will be applied in main.py.
RESIZE_HANDLE_WIDTH_RAW = 5 # Width of the draggable handle in density-independent pixels
MIN_PANEL_WIDTH_RAW = 250 # Minimum width for the revision panel
MAX_PANEL_WIDTH_RATIO = 0.8 # Maximum width as a ratio of window width
BLUE_DOT_DISPLAY_DURATION = 0.35 # Duration in seconds the blue dot is visible
