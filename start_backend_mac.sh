#!/bin/bash
set -e
echo "Starting Bottle Signature Backend v1.5.7"
cd "$(dirname "$0")/backend"
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
