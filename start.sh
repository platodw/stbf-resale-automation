#!/bin/bash
cd "$(dirname "$0")"

# Try venv first, fall back to system python
if [ -d "venv" ]; then
    source venv/bin/activate
elif command -v python3 &>/dev/null; then
    # Check if deps are installed
    python3 -c "import fastapi" 2>/dev/null || {
        echo "Installing dependencies..."
        python3 -m pip install --user --break-system-packages -r requirements.txt -q 2>/dev/null \
        || python3 -m pip install --user -r requirements.txt -q 2>/dev/null \
        || pip install -r requirements.txt -q
    }
fi

echo "Starting STBF Listing Manager on http://0.0.0.0:8000"
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
