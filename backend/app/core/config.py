from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Application
    app_name: str = "English Communication Platform"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    
    # CORS
    cors_origins: str = "*"
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins from environment or default list"""
        env_origins = os.getenv("CORS_ORIGINS", "*")
        if env_origins == "*":
            return ["*"]
        # Parse comma-separated origins from environment
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]
    
    # Database
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name: str = os.getenv("DB_NAME", "english_comm")
    
    # Jitsi
    jitsi_domain: str = os.getenv("JITSI_DOMAIN", "meet.jit.si")
    
    # File storage
    audio_storage_path: str = "static/audio"
    
    # AI Processing
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    whisper_model: str = "base"  # base, small, medium, large
    language_tool_url: str = "http://localhost:8081"  # Local LanguageTool server
    
    class Config:
        env_file = ".env"

settings = Settings()