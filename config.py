"""
config.py — Central configuration for the RFP Automation pipeline.
Set ANTHROPIC_API_KEY in your environment or in a .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-3-5-haiku-20241022")  # fast & free-tier friendly
LLM_MAX_TOKENS: int = 4096

# ── Project metadata (used in slide cover) ────────────────────────────────────
PROJECT_NAME: str = os.getenv("PROJECT_NAME", "EnABLEHR — HR Digital Transformation")
CLIENT_NAME: str  = os.getenv("CLIENT_NAME",  "CLIENT")
VENDOR_NAME: str  = os.getenv("VENDOR_NAME",  "Accenture")
DECK_VERSION: str = os.getenv("DECK_VERSION", "v0.1 DRAFT")

# ── Paths ─────────────────────────────────────────────────────────────────────
import pathlib
BASE_DIR = pathlib.Path(__file__).parent
OUTPUTS_DIR  = BASE_DIR / "outputs"
SAMPLES_DIR  = BASE_DIR / "samples"
KB_FILE      = BASE_DIR / "knowledge_base" / "solutions.json"

OUTPUTS_DIR.mkdir(exist_ok=True)
