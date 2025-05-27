@echo off
cd /d "C:\Users\Joan\Desktop\Projecte NBA\web_nba"
start http://localhost:8000
python -m http.server 8000
pause
