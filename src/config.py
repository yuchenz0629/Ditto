from pathlib import Path

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
TEMPERATURE = 0.05

EDITOR_MAX_TOKENS = 512
EDITOR_TEMPERATURE = 0

GENDER_FALLBACK_BACKGROUND: dict[str, str] = {
    "female": "Forest_Green",
    "male": "Serene_Blue",
    "default": "Sunset_Glow",
}

BACKGROUNDS_DIR = Path("assets/backgrounds")
BACKGROUNDS_INDEX = Path("assets/backgrounds/index.json")
BACKGROUND_GUIDE_PATH = Path("assets/backgrounds/Background_Guide.md")
LOGO_PATH = Path("assets/logo.png")

GENERATIONS_ROOT = Path("outputs/generations")
EDITS_ROOT = Path("outputs/edits")
