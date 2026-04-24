from pathlib import Path

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
TEMPERATURE = 0.05

BACKGROUNDS_DIR = Path("assets/backgrounds")
BACKGROUNDS_INDEX = Path("assets/backgrounds/index.json")
BACKGROUND_GUIDE_PATH = Path("assets/backgrounds/Background_Guide.md")
LOGO_PATH = Path("assets/logo.png")

GENERATIONS_ROOT = Path("outputs/generations")
EDITS_ROOT = Path("outputs/edits")
