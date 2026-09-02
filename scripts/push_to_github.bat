@echo off
echo ===================================================
echo   TRACEFORGE 1-Click Push to pranavsaxena2405/traceforge
echo ===================================================
echo.

set GITHUB_REPO=https://github.com/pranavsaxena2405/traceforge.git

echo Target Repository: %GITHUB_REPO%
echo.

echo 1. Initializing Git repository...
git init

echo 2. Staging all files...
git add .

echo 3. Creating release commit...
git commit -m "feat: TRACEFORGE v0.1 Release - Open-Source AI Behavioral Intelligence Platform"

echo 4. Setting main branch...
git branch -M main

echo 5. Linking remote origin...
git remote add origin %GITHUB_REPO% 2>nul || git remote set-url origin %GITHUB_REPO%

echo 6. Pushing code live to GitHub!
git push -u origin main

echo.
echo ===================================================
echo   SUCCESS! TRACEFORGE is live on GitHub!
echo   Repo: https://github.com/pranavsaxena2405/traceforge
echo ===================================================
pause
