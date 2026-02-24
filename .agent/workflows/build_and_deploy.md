---
description: Build KiCommander exe and deploy to bin/
---

// turbo-all

1. Kill any running instance of KiCommander.exe so DLLs are not locked:

```powershell
taskkill /F /IM KiCommander.exe 2>$null ; Start-Sleep 1
```

// turbo
2. Run PyInstaller with workpath in build_tmp, output goes directly into project root (--distpath .):

```powershell
& .\.venv\Scripts\pyinstaller.exe KiCommander.spec --noconfirm --workpath build_tmp --distpath .
```

// turbo
3. Remove temporary build artefacts:

```powershell
Remove-Item -Recurse -Force build_tmp 2>$null
```

// turbo
4. Commit and push the updated bin/ to GitHub:

```powershell
git add bin/ ; git commit -m "deploy: update compiled bin/" ; git push
```
