@echo off
echo ===================================================
echo   TRACEFORGE 1-Click Push to GitHub
echo   Target: https://github.com/pranavsaxena2405/traceforge.git
echo ===================================================
echo.

set GIT_CMD="C:\Users\Pranav Saxena\.gemini\tools\git\cmd\git.exe"

if not exist %GIT_CMD% (
    set GIT_CMD=git
)

echo 1. Configuring Git author email...
%GIT_CMD% config user.email "saxena.pranav798@gmail.com"
%GIT_CMD% config user.name "Pranav Saxena"

echo 2. Checking repository status...
%GIT_CMD% status

echo.
echo 3. Pushing main branch to https://github.com/pranavsaxena2405/traceforge.git...
%GIT_CMD% push -u origin main

echo.
echo ===================================================
echo   If browser authentication opened, please approve!
echo   Repo URL: https://github.com/pranavsaxena2405/traceforge
echo ===================================================
pause
