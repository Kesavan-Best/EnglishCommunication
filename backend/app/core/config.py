from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend/ directory explicitly
_env_path = Path(__file__).parent.parent.parent / '.env'
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path, override=True)
else:
    load_dotenv(override=True)

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
    
    # Email Configuration (Gmail SMTP)
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    from_email: str = os.getenv("FROM_EMAIL", "")
    from_name: str = os.getenv("FROM_NAME", "ImproveCommunication")
    
    # Brevo API (for Render - SMTP is blocked on free tier)
    brevo_api_key: str = os.getenv("BREVO_API_KEY", "")
    brevo_from: str = os.getenv("BREVO_FROM", "")
    
    class Config:
        env_file = str(Path(__file__).parent.parent.parent / '.env')
        extra = "allow"

settings = Settings()