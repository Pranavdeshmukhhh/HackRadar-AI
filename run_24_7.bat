@echo off
title Nagpur AI & Software Hackathon Monitor (24/7 Daemon)
echo ======================================================================
echo  🚀 Starting Nagpur AI & Software Hackathon Monitor 24/7 Daemon
echo ======================================================================
echo.

cd /d "%~dp0"
python -u -m src.main --loop --interval 60

pause
