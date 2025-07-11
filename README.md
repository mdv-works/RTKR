# Random Japanese Word App

This is a Kivy application designed to help users learn Japanese vocabulary. It fetches words from either the JMdict_e dictionary (an XML file) or JLPT word lists (from a GitHub CSV API), displays them, allows users to reveal the full word, mark words for revision, and review marked words. The app also includes text-to-speech functionality for audio pronunciation.

## Features

- **Random Word Display:** Get a new random Japanese word (reading first).
- **Kanji Reveal:** Show the Kanji for the displayed word.
- **Text-to-Speech (TTS):** Hear the pronunciation of the current word.
- **Word Sources:** Toggle between JMdict_e (comprehensive dictionary) and JLPT (Japanese Language Proficiency Test) word lists.
- **Revision List:** Mark words for later review.
- **Revision Session:** Practice only the words you've marked.
- **Resizable Panel:** Adjust the width of the revision list panel.
- **Keyboard Shortcuts:** Navigate and interact using the spacebar/right arrow (show/next) and 'A' key (audio).

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd rtkr
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Download JMdict_e:**
    The application expects a file named `JMdict_e` (without any extension) in the `rtkr/rtkr/resources/` directory. You can typically find this file as part of the JMdict XML distribution. You might need to download the full JMdict XML file and extract or rename the main dictionary file to `JMdict_e`.
    - A common source for JMdict XML is the [JMdict website](https://www.edrdg.org/jmdict/jmdict_e.html). Look for the "JMdict_e.gz" or similar XML file. Download it, extract it, and place the `JMdict_e` file (which is the XML content without `.xml` extension) into `rtkr/rtkr/resources/`.

## Usage

To run the application, navigate to the `rtkr` directory and execute the `main.py` file within the `rtkr` package:

```bash
python -m rtkr.main
Project Structurertkr/
├── rtkr/                     # Python package
│   ├── __init__.py             # Makes 'rtkr' a Python package
│   ├── main.py                 # Main application logic and Kivy UI definition
│   ├── utils.py                # Helper functions
│   ├── config.py               # Application configuration
│   └── resources/              # Static assets
│       ├── JMdict_e            # JMdict XML data file
│       └── fonts/
│           └── HinaMincho-Regular.ttf # Custom Japanese font
├── data/                       # Writable runtime data
│   └── revisions.json          # Stores marked words for revision
├── requirements.txt            # Python dependencies
└── README.md                   # Project information
```
