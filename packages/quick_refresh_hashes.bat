@echo off
REM Change dir to the script's directory
cd /d %~dp0

git pull
python hasher.py
git add .
git commit -m "Regenerate hashes"
git push