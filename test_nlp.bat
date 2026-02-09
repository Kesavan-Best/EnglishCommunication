@echo off
REM Quick Test Script for NLP System
REM Run this to test the NLP implementation

echo ========================================
echo NLP System Quick Test
echo ========================================
echo.

echo Step 1: Testing NLP Model Directly...
echo ----------------------------------------
python backend\app\ai_processing\lightweight_model.py
if %errorlevel% neq 0 (
    echo ERROR: Model test failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS! NLP Models are working!
echo ========================================
echo.
echo Next steps:
echo 1. Start backend: python backend\main.py
echo 2. Test API: curl http://localhost:8000/api/nlp/health
echo 3. Check the full guide: NLP_INSTALLATION_GUIDE.md
echo.
pause
