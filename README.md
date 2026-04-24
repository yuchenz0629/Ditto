# Project: Poster Generator

In this project I am building An AI-powered dating app poster generator that automatically selects, edits, and arranges user photos into polished posters, with natural language editing support.


## How It Works

1. Generation: within a specified diectory, Claude analyzes all photos, OpenCV finds the subject's face, selects the ones with best quality, assigns roles (hero, body, lifestyle, group), picks a matching background based on it, and renders a poster.
2. Editing: for an already generated poster, describe a change in natural language (i.e. "swap the main photo", "use a darker background") and Claude interprets the instruction and re-renders by changing the "state" of the poster (what images and background are selected, what are their alignments, etc).

Outputs are saved under `outputs` directory. Within it I have two sub-directories: the `/generations` stores the posters generated for the first time, and the `/edits` stores the edited versions. This project supports multiple consecutive edits. The `/edits` directory is going to store all edits of each user. In each of the posters created, regardless of whether it is first time generated or edited, it will always come with a JSON object indicating its state and outcome.


## Project Structure

```
.
├── assets/
│   ├── backgrounds/        # Existing background images + index.json + selection guide
│   └── users/              # One subdirectory contains images and profile information about a user
├── src/
│   ├── generate.py         # Entry point for generate a poster from scratch
│   ├── edit.py             # Entry point for making edits to a poster via natural language
│   ├── analyzer.py         # Claude vision: photo selection and background matching
│   ├── editor.py           # Claude natural language edit command interpretation
│   ├── renderer.py         # PIL-based poster compositor
│   ├── layouts.py          # Layout definitions (1–4 image, v2 variants to satisfy support for layout toggles during editing)
│   ├── cropper.py          # Smart photo cropping, in general I crop around the face to make the subject more noticeable
│   ├── metadata_parser.py  # Parses user metadata.md files to extract the user's profile information
│   └── models.py           # Pydantic data models: BackgroundMeta, PosterState, etc.
├── tests/
│   ├── test_edit.py        # Test poster generation
│   ├── test_generate.py    # Test poster editing. I am going to assume the user runs this after generating posters
├── requirements.txt
└── .env                    # API key (not committed)
```


## Setup

### 1. Prerequisites

- Python 3.11+
- An Anthropic API Key stored in the `.env` file in the project root directory/

### 2. Create and activate a virtual environment

```zsh
python3 -m venv venv
source venv/bin/activate && set -a && source .env && set +a
```

Run this command each time you open a new terminal session before using the tool to activate the environment and load variables.


### 3. Install dependencies

```zsh
pip install -r requirements.txt
```


## Usage

All commands should be run from the project root directory.

### Example: generate a poster

```zsh
python3 src/generate.py assets/users/user_01/
```

### Examples: edit a poster

Pass the generation output directory and a natural language instruction:

```bash
python src/edit.py outputs/generations/user_01/ "swap the main photo"
python src/edit.py outputs/generations/user_01/ "use a darker background"
python src/edit.py outputs/generations/user_01/ "remove the weakest photo"
python src/edit.py outputs/generations/user_01/ "make the hero photo bigger"
```


## Running Tests and obtaining the results

```bash
pytest tests/test_generate.py
pytest tests/test_edit.py  
```


## Result Analysis

1. Each oster generation typically costs around 6 - 15 seconds, which on average, meets the targeted duration. Overall, the posters generated looks good, the crops are reasonable and arrangement, after many attempts, turns out neat. The only imperfection is that for user_07, the fifth image of her wearing a ski helmet with goggles still has a big chance of being misidentified. But other than that, the results are able to match my expectation.
2. I designed 25 editing tasks across all 10 users and the test is complete within 90 seconds, a pretty decent speed. 


## Rooms for improvement and future insights

1. Currently the image layouts are fixed. There are some limitations because the difference in the aspect ratio of the original photo means that some combinations are going to make better use of the canvas than others. A potential optimization would be add some kind of flexing to it. 
2. Image recognition when it comes to subjects very far away and blurry ones could still be improved. 
3. With the inclusion of some lightweight mobile architectures, I see the potential of shrinking each generation from just over 10 seconds to something drastically faster.