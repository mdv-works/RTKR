# ReadingToKanjiRep (RTKR)

This is a Kivy application designed to help users learn the Kanji spelling of words, with the main goal of improving handwriting skills in the Japanese language. It allows fetching of words from JMdict, as well as from word lists for the various JLPT Levels.

The words are displayed in Hiragana in a random sequence, and the user is supposed to recall and manually write down the corresponding Kanji for the displayed Hiragana. The correct Kanji spelling is then revealed for checking.

Additionally, you can add any word from your sessions to a revision list for later reviewing.

A text-to-speech functionality was also implemented, with the goal of providing additional pitch accent information to help write down the Kanji for the intended word, and assist with the identification of homophones. Keep in mind that this type of TTS capability can be unreliable at times, so treat it with discretion.

# Use Cases

This app is mainly intended to help advanced students of the Japanese language in the development of raw writing skills. It is not intended to teach grammar, pronunciation, vocabulary or actual kanji.

The system forces the recall of Kanji without any hints, and the user is expected to remember the complete spelling of the words and write them down. This may help in the cultivation of a native-like writing and word-parsing skills.

It may also help improve listening skills, especially in distinguishing homophones. Since the user must interpret the Hiragana and audio without context, they are challenged to recall the correct Kanji and meaning based on sound alone. The added TTS pitch accent can assist in narrowing down possibilities, making this a valuable way to practice sound-to-meaning recognition.

For instance, if the word とうしょ appears, the user may think of the word 当所, and write it down. When he checks the answer, 投書 was instead the intended word. When replaying the audio, he may notice the pitch accent and then check with external tools if both options have the same one. He will then see that 投書 (Heiban) has a different pitch accent than 当所 and 当初 (both Atamadaka). He may then consider it worth adding to the revision list for later, because he struggled with some part of this parsing and writing process. This is the expected experience and flow of the app, where even advanced learners will not be familiar with all options and should struggle with the out-of-context recall.

# Current limitations

The TTS pitch accent and machine parsing of the word itself may not always be accurate (because it is using the Kanji for the generation of the audio). Additionally, any words with multiple readings will default to the first one available.

It is also understood that all words with identical Hiragana spelling and pitch accent will not be discernible from one another, so many options might be possible for some words.

Future releases may be able to overcome these issues.

## Features

- **Random Word Display:** Get a new random Japanese word in its Hiragana form.

- **Kanji Reveal:** Show the Kanji for the current word.

- **TTS Audio:** Hear the pronunciation of the current word.

- **Word Sources:**

  - **Full JMdict:** Access to JMdict dictionary, which contains virtually every possible word and expression in the Japanese language.

  - **JLPT Levels:** Toggle between word lists from any JLPT level (1-5), which contain a much smaller pool of high-frequency words used in the Japanese language.

- **Revision List:** Mark and save words for later review, and remove them manually when desired. The words are saved locally and persist after closing the app.

- **Revision Session:** Study your personal word list in an appropriate study session format, as many times as you want.

- **Resizable Panel:** Adjust the width of the revision list panel to accommodate longer words (common in JMdict).

- **Keyboard Shortcuts:** Navigate and interact using the spacebar/right arrow (show/next) and the 'A' key (audio) for a more seamless experience.

## Installation

1. **Clone the repository:**

   ```bash
   git clone <repository_url>
   cd RTKR # Assuming your main project folder is 'RTKR'
   ```

2. **Create a virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```
   
## Usage

To run the application, navigate to the `RTKR` directory (the parent directory of your `rtkr` package) and execute the `main.py` file within the `rtkr` package:

```bash
python -m rtkr.main
```
