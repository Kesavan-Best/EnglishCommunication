@echo off
echo ========================================
echo  Deploying Fixes to Render
echo ========================================
echo.

echo [1/5] Checking Git status...
git status
echo.

echo [2/5] Adding all changes...
git add .
echo.

echo [3/5] Committing changes...
git commit -m "Fix: Resolve CSS loading and path issues for Render deployment - Add missing enhanced-theme.css - Change all relative paths to absolute paths (/frontend/) - Fix navigation links across all pages - Update JS redirects to use absolute URLs - Fixes registration and login on Render"
echo.

echo [4/5] Pushing to repository...
git push origin main
echo.

echo [5/5] Done!
echo.
echo ========================================
echo  Deployment Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Wait 2-3 minutes for Render to deploy
echo 2. Visit: https://english-communication-backend.onrender.com/frontend/index.html
echo 3. Clear browser cache (Ctrl+Shift+R)
echo 4. Test registration and login
echo.
pause
