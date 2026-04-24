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
│   ├── config.py           # Centralized constants: model name, all asset and output paths
│   ├── llm_utils.py        # Shared LLM helpers: JSON extraction, response parsing, layout map
│   ├── generate.py         # Entry point for generating a poster from scratch
│   ├── edit.py             # Entry point for making edits to a poster via natural language
│   ├── analyzer.py         # Claude vision: photo selection and background matching
│   ├── editor.py           # Claude natural language edit command interpretation
│   ├── renderer.py         # PIL-based poster compositor
│   ├── layouts.py          # Layout definitions (1–4 image, v2 variants for layout toggle support)
│   ├── cropper.py          # Face-aware smart photo cropping
│   ├── metadata_parser.py  # Parses user metadata.md to extract profile information
│   └── models.py           # Pydantic data models: BackgroundMeta, PosterState, etc.
├── tests/
│   ├── test_generate.py    # Integration test: poster generation for all 10 users
│   ├── test_edit.py        # Integration test: poster editing (requires generation output)
│   └── test_unit.py        # Unit tests: editor commands, JSON parsing, metadata extraction
├── pyproject.toml          # Ruff and mypy configuration
├── pytest.ini              # Pytest config: live logging, verbose output per test
├── requirements.txt
└── .env                    # API key (not committed)
```


## Setup

### 1. Prerequisites

- Python 3.11+
- An Anthropic API Key stored in the `.env` file in the project root directory/
- UTF-8 locale required. All JSON and Markdown files are read and written with explicit `encoding="utf-8"`. On Windows, ensure your system locale or Python environment is set to UTF-8 to avoid encoding errors.

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

### Performance
Each poster generation takes 6–15 seconds end-to-end. This includes everything from metadata parsing to Claude API call and render, meeting the target throughput. The 10-user test suite completes in roughly 2 or 2.5 minutes. The 25-edit suite across all users finishes in under 90 seconds, averaging around 3–4 seconds per edit.

### Robustness
I enforced in test suite a 30-second hard timeout per subprocess call. On timeout, it retries once before failing to handle transient API latency spikes without masking real failures, separating it with errors that fail immediately. Each test case gives structured live logs per user using pytest's `log_cli`. This way the tester sees timing,  selection details, and the LLM-interpreted action for every edit more clearly.

### Consistency
The analyzer runs at `temperature=0.05`, which minimises but does not eliminate LLM variance. The same set of images may yield different number of images or potentially background, and in this case, I believe it is acceptable, because this project is not a deterministic algorithm. The parse-failure retry fires only when Claude returns malformed JSON, not for selection variance. During testing, this path has never been observed, but it is a good-to-have precaution mechanism.



## Rooms for improvement and future insights

### Fixed image layouts
The current layouts use fixed slot dimensions, so very wide or very tall photos waste canvas space or crop heavily. Adding flexible slot sizing that adapts to the selected images' aspect ratios would make better use of the canvas across diverse photo sets.

### Subject detection for distant and occluded subjects
The face cropper uses OpenCV's Haar cascade, which is trained on frontal faces and performs not as well with accessories (an example that caused the most headache for me: ski helmets, goggles from the user_07 set), awkward angles, and small or distant subjects. Replacing it with a modern deep learning detector (MTCNN, RetinaFace, or MediaPipe Face Landmarker) would handle these edge cases significantly better.

### Generation latency
Currently, the Claude API call dominates generation time. To address it, I can use Anthropic's prompt caching — the system prompt, background guide, and background JSON are static across calls and qualify for caching, which could cut input token processing cost and latency by a lot. Or, make use of a lightweight on-device pre-filter like MobileNet to score and discard blatantly low-quality images before sending the full payload to Claude, reducing image count and payload size.