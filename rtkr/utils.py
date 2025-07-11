# rtkr/utils.py

import urllib.request
import re
import os
import json

# Import configuration settings
from .config import FONT_URL, FONT_FILE, REVISIONS_FILE

def download_file_content(url):
    """
    Helper function to download file content from a given URL and return it as a string.
    """
    try:
        print(f"Fetching data from {url}...")
        # Set a timeout for the request to prevent indefinite hanging
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.getcode() == 200:
                content = response.read().decode('utf-8')
                print(f"Successfully fetched data from {url}.")
                return content
            else:
                print(f"Error fetching data from {url}: HTTP Error {response.getcode()}: {response.reason}")
                return None
    except urllib.error.HTTPError as e:
        print(f"Error downloading from {url}: HTTP Error {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"URL Error for {url}: {e.reason}. Check internet connection or URL validity.")
        return None
    except Exception as e:
        print(f"Error fetching or parsing content from {url}: {e}")
        return None

def is_primarily_katakana(text):
    """
    Checks if a string is primarily Katakana (contains Katakana and no Hiragana/Kanji).
    This is used to filter out words that are only written in Katakana.
    """
    if not text:
        return False

    has_katakana = False
    for char in text:
        # Check for full-width and half-width Katakana ranges
        if ('\u30A0' <= char <= '\u30FF' or # Katakana
            '\uFF66' <= char <= '\uFF9F'): # Half-width Katakana
            has_katakana = True
        elif '\u3040' <= char <= '\u309F': # Hiragana
            return False # Contains Hiragana, so not "primarily Katakana"
        elif ('\u4E00' <= char <= '\u9FAF' or # CJK Unified Ideographs (Kanji)
              '\u3400' <= char <= '\u4DBF'): # CJK Unified Ideographs Extension A (Kanji)
            return False # Contains Kanji, so not "primarily Katakana"
        # Allow other characters like spaces, numbers, common punctuation if needed,
        # but for strict "primarily katakana" we only care about the above.

    return has_katakana # Returns true only if it has katakana and no hiragana/kanji

def ensure_font_downloaded():
    """
    Ensures the custom Japanese font is downloaded and available.
    Creates the necessary directory if it doesn't exist.
    """
    font_dir = os.path.dirname(FONT_FILE)
    if not os.path.exists(font_dir):
        os.makedirs(font_dir)
        print(f"Created font directory: {font_dir}")

    if not os.path.exists(FONT_FILE):
        try:
            print(f"Downloading font from {FONT_URL} to {FONT_FILE}...")
            urllib.request.urlretrieve(FONT_URL, FONT_FILE)
            print("Font downloaded successfully.")
        except Exception as e:
            print(f"Error downloading font: {e}")
