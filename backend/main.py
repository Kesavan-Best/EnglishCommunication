from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import uvicorn
import os
import sys
from pathlib import Path

# Add parent directory to path for both local and Render deployment
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from backend.app.api import users, calls, analysis, leaderboard, websocket, oauth
from backend.app.database import init_db
from backend.app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initializing database...")
    await init_db()
    print("Database initialized")
    yield
    # Shutdown
    print("Shutting down...")

app = FastAPI(
    title="English Communication Platform",
    description="AI-powered English speaking improvement platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - Allow all origins for development and ngrok
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for ngrok and development)
    allow_credentials=False,  # Must be False when allow_origins is "*"
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose all headers
)

# Mount static files for audio storage
static_path = os.path.join(os.path.dirname(__file__), "..", "static")
os.makedirs(os.path.join(static_path, "audio"), exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Mount frontend files
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_path):
    print(f"Mounting frontend from: {frontend_path}")
    app.mount("/frontend", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    print(f"WARNING: Frontend path not found: {frontend_path}")

# Include routers
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(calls.router, prefix="/api/calls", tags=["calls"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(leaderboard.router, prefix="/api/leaderboard", tags=["leaderboard"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])  # FIXED: Added prefix
app.include_router(oauth.router, tags=["oauth"])  # OAuth routes

@app.get("/")
async def root():
    """Redirect to frontend"""
    return RedirectResponse(url="/frontend/index.html")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Add WebSocket endpoint directly
@app.websocket("/api/ws/{user_id}")
async def websocket_route(websocket: WebSocket, user_id: str):
    """Direct WebSocket endpoint for compatibility"""
    from backend.app.api.websocket import manager
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": "now"
                }, user_id)
            elif message_type == "webrtc-signal":
                signal_data = data.get("signal", {})
                await manager.handle_webrtc_signal(user_id, signal_data)
                
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(user_id)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )