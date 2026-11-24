@echo off
cd /d "%~dp0"
echo MSL ONE CVRM local workspace
echo Open http://127.0.0.1:8000/cvrm in your browser.
echo Keep this window open while searching. Press Ctrl+C to stop.
"%~dp0.venv\Scripts\python.exe" -m uvicorn api:app --host 127.0.0.1 --port 8000
pause
