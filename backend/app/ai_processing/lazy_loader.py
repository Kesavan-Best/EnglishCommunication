"""
Lazy NLP Model Loader
Loads models in background after app starts, so they're ready when calls end
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class NLPLazyLoader:
    """Manages lazy loading of NLP models in background"""
    
    def __init__(self):
        self.is_loading = False
        self.is_loaded = False
        self.load_started_at: Optional[datetime] = None
        self.load_completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
    
    async def start_background_loading(self, delay_seconds: int = 600):
        """
        Start loading models in background after delay
        
        Args:
            delay_seconds: Wait time before loading (default: 600s = 10 minutes)
        """
        logger.info(f"NLP models will start loading after {delay_seconds}s (when calls might end)")
        await asyncio.sleep(delay_seconds)
        await self.load_models()
    
    async def load_models(self):
        """Load NLP models in background"""
        if self.is_loaded or self.is_loading:
            return
        
        self.is_loading = True
        self.load_started_at = datetime.utcnow()
        logger.info("🤖 Starting NLP model loading in background...")
        
        try:
            # Import and initialize models
            from backend.app.ai_processing.lightweight_model import get_ai_processor
            
            # This will trigger model download and initialization
            processor = get_ai_processor()
            
            self.is_loaded = True
            self.load_completed_at = datetime.utcnow()
            load_time = (self.load_completed_at - self.load_started_at).total_seconds()
            logger.info(f"✅ NLP models loaded successfully in {load_time:.1f}s")
            
        except Exception as e:
            self.error = str(e)
            logger.error(f"❌ Failed to load NLP models: {e}")
        finally:
            self.is_loading = False
    
    def get_status(self) -> dict:
        """Get current loading status"""
        if self.is_loaded:
            return {
                "status": "ready",
                "message": "NLP models are loaded and ready",
                "loaded_at": self.load_completed_at.isoformat() if self.load_completed_at else None
            }
        elif self.is_loading:
            elapsed = (datetime.utcnow() - self.load_started_at).total_seconds() if self.load_started_at else 0
            return {
                "status": "loading",
                "message": f"NLP models are loading... ({elapsed:.0f}s elapsed)",
                "estimated_time_remaining": "10-30 seconds"
            }
        elif self.error:
            return {
                "status": "error",
                "message": "Failed to load NLP models",
                "error": self.error
            }
        else:
            return {
                "status": "not_started",
                "message": "NLP models will load when first analysis is requested"
            }

# Global instance
nlp_loader = NLPLazyLoader()
