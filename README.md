# STBF Listing Manager

Mobile-first web app for managing resale listings. Upload photos → AI groups them by item → review/edit drafts → publish to eBay.

## Quick Start

```bash
chmod +x start.sh
./start.sh
```

Open http://localhost:8000

## Setup

1. **eBay credentials:** Place `config.json` and `oauth_tokens.json` in `~/.openclaw/credentials/ebay/`
2. **Anthropic API key** (optional): Place key in `~/.openclaw/credentials/anthropic/api_key`
3. Run `start.sh` — it creates a venv and installs dependencies automatically.

## Flow

1. **Upload** — batch upload photos (drag/drop or camera)
2. **Group** — AI groups photos by item; adjust if needed
3. **Review** — edit AI-generated drafts (title, description, price, condition)
4. **Publish** — push to eBay via Inventory API

## Tech Stack

- **Backend:** FastAPI + SQLite
- **Frontend:** Vanilla HTML/CSS/JS (mobile-first)
- **AI:** Claude Vision (stubbed until API key configured)
- **Marketplace:** eBay Inventory API
