from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import os

from backend.app.api import users, calls, analysis, leaderboard, websocket
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
os.makedirs("static/audio", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount frontend files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path, html=True), name="frontend")

# Include routers
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(calls.router, prefix="/api/calls", tags=["calls"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(leaderboard.router, prefix="/api/leaderboard", tags=["leaderboard"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])

@app.get("/")
async def root():
    return {"message": "English Communication Platform API", "frontend": "Access frontend at /frontend/index.html"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )