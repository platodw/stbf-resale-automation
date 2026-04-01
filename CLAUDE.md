# CLAUDE.md

Python/FastAPI backend for STBF resale listing automation. Upload item photos, AI groups them, generates draft listings with market research, then publishes to eBay and Poshmark. Mobile-first web UI served via Jinja2 templates.

## Context

The original prototype for Katie's resale listing workflow, built before the Lovable/Supabase version (stbf repo). This runs locally as a standalone server. It may still be used for local photo processing or as a fallback, but the primary app has moved to the stbf repo.

## Tech Stack

- Python 3 + FastAPI + Uvicorn
- SQLite (via stdlib sqlite3, no ORM)
- Jinja2 templates + vanilla HTML/CSS/JS (mobile-first)
- Claude Vision API (Anthropic) for photo analysis
- Pillow for image processing (HEIC conversion, thumbnails)
- httpx for async HTTP calls

## Running Locally

```bash
chmod +x start.sh
./start.sh         # Creates venv if needed, installs deps, starts server
```

Or manually:
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000

## Credentials

Stored in `~/.openclaw/credentials/`:
- `ebay/config.json` -- eBay app credentials (client ID, secret, RuName)
- `ebay/oauth_tokens.json` -- eBay OAuth tokens (auto-refreshed)
- `anthropic/api_key` -- Claude API key (falls back to `ANTHROPIC_API_KEY` env var)

## Project Structure

```
main.py              FastAPI app, all routes (pages + API endpoints)
config.py            Paths, credential loading (eBay, Anthropic)
database.py          SQLite schema init and connection helper
ai_service.py        Claude Vision: photo grouping, sequencing, listing generation, stock photo search
ebay_service.py      eBay Inventory API: create/update listings
poshmark_service.py  Poshmark listing via browser automation bridge
monarch_service.py   Financial data from Monarch Money

templates/           Jinja2 HTML templates (upload, groups, review, edit, published, dashboard)
static/              CSS/JS assets
uploads/             Photo storage (per-batch subdirectories with thumbs/)
```

## Key Patterns

- Flat module structure (no packages). All Python files at root.
- SQLite database at `./stbf.db` with tables: batches, photos, item_groups, listings.
- Upload flow: photos -> AI grouping -> AI sequencing -> confirm -> AI draft generation + stock photo fetch -> review/edit -> publish.
- Photo thumbnails generated on upload for fast grid display.
- HEIC/HEIF support via pillow-heif (optional).
- Poshmark publishing is semi-automated: the service starts a draft that Katie finishes manually.
- `/api/financial-data` endpoint pulls STBF sales data from Monarch Money.

## External Services

- Anthropic Claude Vision API
- eBay Inventory/Browse APIs
- Poshmark (browser bridge)
- Monarch Money (financial tracking)
