@echo off
cd /d "%~dp0"
python -m aptgraph %*
exit /b %errorlevel%
