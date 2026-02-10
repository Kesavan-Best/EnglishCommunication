"""
AI Processing Module
Contains NLP models and processing logic
"""

# Use memory-efficient processor by default (< 512MB RAM for Render free tier)
try:
    # Try absolute import first (for production)
    from backend.app.ai_processing.memory_efficient_processor import (
        get_ai_processor, 
        MemoryEfficientProcessor as LightweightAIProcessor
    )
except ImportError:
    # Fall back to relative import (for development)
    from .memory_efficient_processor import (
        get_ai_processor,
        MemoryEfficientProcessor as LightweightAIProcessor
    )

__all__ = ['get_ai_processor', 'LightweightAIProcessor']
