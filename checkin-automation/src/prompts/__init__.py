"""Load prompt files from this directory."""

from pathlib import Path

_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt by name (without extension). Returns the text stripped."""
    return (_DIR / f"{name}.txt").read_text().strip()
