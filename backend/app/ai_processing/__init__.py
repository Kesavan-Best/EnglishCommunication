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

# Language Weakness Analyzer (uses LanguageTool, WordNet, Rule-based systems)
try:
    from backend.app.ai_processing.language_weakness_analyzer import (
        language_analyzer,
        grammar_checker,
        vocabulary_analyzer,
        filler_detector,
        analyze_conversation
    )
    LANGUAGE_ANALYZER_AVAILABLE = True
except ImportError:
    LANGUAGE_ANALYZER_AVAILABLE = False
    language_analyzer = None
    grammar_checker = None
    vocabulary_analyzer = None
    filler_detector = None
    analyze_conversation = None

__all__ = [
    'get_ai_processor', 
    'LightweightAIProcessor',
    'language_analyzer',
    'grammar_checker',
    'vocabulary_analyzer',
    'filler_detector',
    'analyze_conversation',
    'LANGUAGE_ANALYZER_AVAILABLE'
]
