from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Application
    app_name: str = "English Communication Platform"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    
    # Database
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name: str = os.getenv("DB_NAME", "english_comm")
    
    # Jitsi
    jitsi_domain: str = os.getenv("JITSI_DOMAIN", "meet.jit.si")
    
    # File storage
    audio_storage_path: str = "static/audio"
    
    # AI Processing
    whisper_model: str = "base"  # base, small, medium, large
    language_tool_url: str = "http://localhost:8081"  # Local LanguageTool server
    
    class Config:
        env_file = ".env"

settings = Settings()