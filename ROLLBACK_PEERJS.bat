@echo off
echo ==========================================
echo  ROLLBACK: Restore Pre-PeerJS Checkpoint
echo ==========================================
echo.
echo This will restore your project to the state BEFORE PeerJS was implemented.
echo.
pause

echo Restoring call.js...
copy /Y "CHECKPOINT_BEFORE_PEERJS\frontend\js\call.js" "frontend\js\call.js"

echo Restoring call.html...
copy /Y "CHECKPOINT_BEFORE_PEERJS\frontend\templates\call.html" "frontend\templates\call.html"

echo Restoring dashboard.js...
copy /Y "CHECKPOINT_BEFORE_PEERJS\frontend\js\dashboard.js" "frontend\js\dashboard.js"

echo Restoring users.js...
copy /Y "CHECKPOINT_BEFORE_PEERJS\frontend\js\users.js" "frontend\js\users.js"

echo Restoring backend main.py...
copy /Y "CHECKPOINT_BEFORE_PEERJS\backend\main.py" "backend\main.py"

echo Restoring backend auth.py...
copy /Y "CHECKPOINT_BEFORE_PEERJS\backend\app\auth.py" "backend\app\auth.py"

echo.
echo ==========================================
echo  ROLLBACK COMPLETE!
echo ==========================================
echo All files restored to pre-PeerJS state.
echo.
pause
