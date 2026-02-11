import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = BASE_DIR / "stbf.db"

UPLOAD_DIR.mkdir(exist_ok=True)

# eBay
EBAY_CRED_DIR = Path.home() / ".openclaw" / "credentials" / "ebay"
EBAY_CONFIG_PATH = EBAY_CRED_DIR / "config.json"
EBAY_TOKENS_PATH = EBAY_CRED_DIR / "oauth_tokens.json"
EBAY_STORE_NAME = "somethingtobefound28"
EBAY_API_BASE = "https://api.ebay.com"
EBAY_TOKEN_URL = f"{EBAY_API_BASE}/identity/v1/oauth2/token"

# Anthropic (Claude vision)
ANTHROPIC_KEY_PATH = Path.home() / ".openclaw" / "credentials" / "anthropic" / "api_key"

def get_anthropic_key():
    if ANTHROPIC_KEY_PATH.exists():
        return ANTHROPIC_KEY_PATH.read_text().strip()
    return os.environ.get("ANTHROPIC_API_KEY")

def get_ebay_config():
    import json
    if EBAY_CONFIG_PATH.exists():
        return json.loads(EBAY_CONFIG_PATH.read_text())
    return {}

def get_ebay_tokens():
    import json
    if EBAY_TOKENS_PATH.exists():
        return json.loads(EBAY_TOKENS_PATH.read_text())
    return {}

def save_ebay_tokens(tokens):
    import json
    EBAY_CRED_DIR.mkdir(parents=True, exist_ok=True)
    EBAY_TOKENS_PATH.write_text(json.dumps(tokens, indent=2))
