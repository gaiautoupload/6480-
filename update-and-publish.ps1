$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
& "D:\codex\stock1\.venv\Scripts\python.exe" "$Project\export_tracker.py"
git -C $Project add data/pair_tracker.json
if (-not (git -C $Project diff --cached --quiet)) { git -C $Project commit -m "data: update pair tracker" }
git -C $Project push origin main
