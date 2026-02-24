@echo off
echo Building KiCommander EXE...
python -m PyInstaller --noconsole --onefile --distpath bin --name KiCommander --add-data "src/style.qss;." --paths src src/main.py
echo Build finished. The executable is in the bin folder.
pause
