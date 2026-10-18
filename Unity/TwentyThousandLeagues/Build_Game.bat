@echo off
setlocal
rem Twenty Thousand Leagues: builds TwentyThousandLeagues.exe without opening the Unity editor window.
rem 1) CLOSE the Unity editor first (it locks the project).  2) Double-click this file.  3) Wait 10-30 minutes.
set "PROJ=%~dp0"
if "%PROJ:~-1%"=="\" set "PROJ=%PROJ:~0,-1%"
set "UNITY="
for /d %%V in ("C:\Program Files\Unity\Hub\Editor\6000.*") do if exist "%%V\Editor\Unity.exe" set "UNITY=%%V\Editor\Unity.exe"
if not defined UNITY (
  echo Could not find Unity 6 under C:\Program Files\Unity\Hub\Editor. Install it from Unity Hub.
  pause & exit /b 1
)
echo Using %UNITY%
echo Building... this window stays quiet while Unity works. Log: %PROJ%\Logs\build_windows.log
set VERNE_NO_AUTORUN=1
"%UNITY%" -batchmode -quit -projectPath "%PROJ%" -executeMethod Verne.EditorTools.BuildWindows.Run -logFile "%PROJ%\Logs\build_windows.log"
if errorlevel 1 (
  echo.
  echo The build failed. Send Claude the file Logs\build_windows.log
  pause & exit /b 1
)
echo.
echo Done. Your game is in: %PROJ%\Build\TwentyThousandLeagues.exe
start "" "%PROJ%\Build"
pause
