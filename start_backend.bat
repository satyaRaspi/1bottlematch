@echo off
echo Starting Bottle Signature Backend v1.6.0
cd /d "%~dp0backend"
if not exist venv (
  python -m venv venv
)
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
