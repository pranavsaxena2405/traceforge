@echo off
echo ===================================================
echo   TRACEFORGE 1-Click PyPI Publisher (traceforge-ai)
echo ===================================================
echo.

set /p PYPI_TOKEN="Enter your PyPI API Token (starts with pypi-): "

if "%PYPI_TOKEN%"=="" (
    echo Error: PyPI API Token cannot be empty.
    echo Get your token for free at https://pypi.org/manage/account/token/
    exit /b 1
)

echo.
echo Uploading dist/ packages to PyPI...
.\.venv\Scripts\python.exe -m twine upload dist/* -u __token__ -p %PYPI_TOKEN%

echo.
echo ===================================================
echo   SUCCESS! traceforge-ai is live on PyPI!
echo   URL: https://pypi.org/project/traceforge-ai/
echo   Install: pip install traceforge-ai
echo ===================================================
pause
