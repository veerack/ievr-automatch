@echo off
setlocal

cd /d "%~dp0"

if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

cd /d "%~dp0source"
pyinstaller main.spec --distpath ..\dist --workpath ..\build --noconfirm

endlocal
pause
