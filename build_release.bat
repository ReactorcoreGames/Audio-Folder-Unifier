@echo off
setlocal
:: Builds the exe and assembles the portable release: dist\<name>\ (the folder) and dist\<name>.zip.
:: PyInstaller's own output goes to build\ (gitignored), so dist\ only ever holds the release.
:: Don't run the program from inside dist\ for real use: its config.json would be wiped by the next build.
cd /d "%~dp0"

:: ---- set per project ------------------------------------------------------
:: Exe and release folder name (spaces are fine).
set "PROJECT_NAME=Audio Folder Unifier"
:: ---------------------------------------------------------------------------

set "RELEASE_DIR=dist\%PROJECT_NAME%"

if not exist "assets\icon.ico" (
    echo ERROR: assets\icon.ico not found.
    goto :failed
)

if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
if exist "dist\%PROJECT_NAME%.zip" del "dist\%PROJECT_NAME%.zip"
if exist "build\pyinstaller" rmdir /s /q "build\pyinstaller"

:: Paths are absolute because --specpath makes relative ones resolve from build\.
:: Bundle only the assets the program reads at run time (not icon_og.png or other source art).
:: Add one --add-data line per extra file or folder, e.g. --add-data "%CD%\assets\sounds;assets\sounds"
:: The excludes are optional imports of numpy (yaml, psutil) and cffi (setuptools), never used at run time.
pyinstaller --noconfirm --onedir --windowed ^
  --name "%PROJECT_NAME%" ^
  --exclude-module yaml --exclude-module psutil --exclude-module setuptools ^
  --exclude-module charset_normalizer --exclude-module win32pdh ^
  --icon "%CD%\assets\icon.ico" ^
  --add-data "%CD%\assets\icon.ico;assets" ^
  --distpath "build\pyinstaller" --workpath "build\work" --specpath "build" ^
  main.py || goto :failed

xcopy /E /I /Y /Q "build\pyinstaller\%PROJECT_NAME%" "%RELEASE_DIR%" >nul || goto :failed

:: user-facing docs and the homepage link (promo.md is internal and stays out)
for %%F in ("readme.md" "guide.md" "stats-for-nerds.md" "LICENSE" "Reactorcore's Homepage.url") do (
    if exist %%F copy /Y %%F "%RELEASE_DIR%\" >nul
)
if exist promo xcopy /E /I /Y /Q promo "%RELEASE_DIR%\promo" >nul

:: Antivirus often still has the freshly copied files open, which fails Compress-Archive with
:: "being used by another process" while powershell still exits 0. Stop on errors, retry a few times.
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; for ($i = 1; $i -le 5; $i++) { try { Compress-Archive -Path '%RELEASE_DIR%' -DestinationPath 'dist\%PROJECT_NAME%.zip' -Force; exit 0 } catch { Write-Host \"zip attempt $i failed: $_\"; Start-Sleep -Seconds 3 } }; exit 1" || goto :failed

echo.
echo Release folder: %RELEASE_DIR%
echo Zip: dist\%PROJECT_NAME%.zip
pause
exit /b 0

:failed
echo.
echo BUILD FAILED - see the messages above.
pause
exit /b 1
