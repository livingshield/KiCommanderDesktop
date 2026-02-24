---
description: Build KiCommander exe and deploy to bin/
---

// turbo-all

1. Kill any running instance of KiCommander.exe:

```powershell
taskkill /F /IM KiCommander.exe 2>$null ; Start-Sleep 1
```

1. Remove old build artefacts (keep bin/ for now):

```powershell
Remove-Item -Recurse -Force dist 2>$null ; Remove-Item -Recurse -Force build_tmp 2>$null
```

1. Run PyInstaller (outputs to dist/KiCommander/):

```powershell
& .\.venv\Scripts\pyinstaller.exe KiCommander.spec --noconfirm --workpath build_tmp
```

1. Replace bin/ contents with fresh build:

```powershell
Remove-Item -Recurse -Force bin 2>$null ; Move-Item dist/KiCommander bin ; Remove-Item -Recurse -Force dist 2>$null ; Remove-Item -Recurse -Force build_tmp 2>$null
```

1. Commit and push:

```powershell
git add bin/ ; git commit -m "deploy: update compiled bin/" ; git push
```
