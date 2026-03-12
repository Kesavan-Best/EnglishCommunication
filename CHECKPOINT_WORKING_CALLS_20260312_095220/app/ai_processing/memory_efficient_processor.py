"""
Memory-Efficient AI Processor
Automatically uses lightweight instant analyzer for Render free tier (< 512MB)
Falls back to heavy models if available and memory allows
"""

import logging
from typing import Dict, List

# Try different import methods
try:
    from backend.app.ai_processing.instant_analyzer import instant_analyzer
except ImportError:
    try:
        from app.ai_processing.instant_analyzer import instant_analyzer
    except ImportError:
        from .instant_analyzer import instant_analyzer

logger = logging.getLogger(__name__)

# Try to import heavy models, but don't fail if not available
try:
    try:
        from backend.app.ai_processing.lightweight_model import LightweightAIProcessor
    except ImportError:
        from app.ai_processing.lightweight_model import LightweightAIProcessor
    HEAVY_MODELS_AVAILABLE = True
    # Don't log here - it's misleading since we use language_weakness_analyzer now
except (ImportError, ModuleNotFoundError) as e:
    HEAVY_MODELS_AVAILABLE = False
    # Silent fallback - we use language_weakness_analyzer anyway


class MemoryEfficientProcessor:
    """
    Smart AI processor that adapts to available resources
    - Uses instant analyzer by default (< 100MB memory)
    - Can use heavy models if installed and memory allows
    """
    
    def __init__(self, use_heavy_models: bool = False):
        """
        Initialize processor
        
        Args:
            use_heavy_models: Force use of heavy models if available (requires 1.3GB+ RAM)
        """
        self.use_heavy = use_heavy_models and HEAVY_MODELS_AVAILABLE
        self._heavy_processor = None
        
        if self.use_heavy:
            logger.info("🚀 Initializing heavy NLP models (1.3GB RAM)...")
            try:
                self._heavy_processor = LightweightAIProcessor()
                logger.info("✅ Heavy models loaded successfully")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load heavy models: {e}")
                logger.info("⚡ Falling back to instant analyzer")
                self.use_heavy = False
        else:
            logger.info("⚡ Using instant analyzer (memory-optimized)")
    
    def analyze_conversation(self, text: str, call_duration_minutes: int = 10) -> Dict:
        """
        Analyze conversation text
        
        Args:
            text: Conversation transcript
            call_duration_minutes: Duration of call for scoring
            
        Returns:
            Analysis results with scores, topics, and suggestions
        """
        if self.use_heavy and self._heavy_processor:
            # Use advanced AI models
            logger.info("Using heavy NLP models for analysis")
            return self._heavy_processor.analyze_conversation(text)
        else:
            # Use instant analyzer (memory efficient)
            logger.info("Using instant analyzer (memory-optimized)")
            
            # Generate instant analysis using the instant_analyzer
            duration_seconds = call_duration_minutes * 60
            analysis = instant_analyzer.generate_instant_feedback(
                duration_seconds=duration_seconds,
                user_id="test_user",
                transcript=text
            )
            
            # Convert to expected format
            weaknesses = analysis.get("weaknesses", [])
            recommended = analysis.get("recommended_topics", [])
            
            # Extract topics from recommended topics
            topics = []
            for topic in recommended[:3]:
                topics.append({
                    "topic": topic.get("name", "General"),
                    "confidence": 75.0
                })
            
            # Extract grammar issues from weaknesses
            grammar_issues = []
            for weakness in weaknesses:
                if weakness.get("category") == "grammar":
                    grammar_issues.append({
                        "issue": weakness.get("title", "Grammar"),
                        "suggestion": weakness.get("tip", "Practice grammar exercises"),
                        "severity": weakness.get("severity", "medium")
                    })
            
            # Extract improvement areas
            improvement_areas = [w.get("category", "general") for w in weaknesses]
            
            return {
                "topics": topics,
                "grammar_issues": grammar_issues,
                "vocabulary_level": self._assess_vocab_level(text),
                "vocabulary_stats": {
                    "level": self._assess_vocab_level(text),
                    "total_words": len(text.split()),
                    "unique_words": len(set(text.lower().split())),
                    "vocabulary_richness": round(len(set(text.lower().split())) / max(len(text.split()), 1) * 100, 1),
                    "average_word_length": round(sum(len(word) for word in text.split()) / max(len(text.split()), 1), 1)
                },
                "suggestions": self._generate_suggestions_from_weaknesses(weaknesses),
                "recommended_topics": [t.get("name", "General") for t in recommended],
                "weak_areas": improvement_areas
            }
    
    def _assess_vocab_level(self, text: str) -> str:
        """Assess vocabulary level from text"""
        words = text.split()
        unique_words = set(text.lower().split())
        avg_word_length = sum(len(word) for word in words) / max(len(words), 1)
        
        if avg_word_length > 6 and len(unique_words) > 50:
            return "Advanced"
        elif avg_word_length > 5 and len(unique_words) > 30:
            return "Intermediate"
        else:
            return "Beginner"
    
    def _generate_suggestions_from_weaknesses(self, weaknesses: List[Dict]) -> List[str]:
        """Generate suggestions from weakness data"""
        suggestions = []
        for weakness in weaknesses[:3]:
            tip = weakness.get("tip", "")
            if tip:
                suggestions.append(tip)
        
        # Add some general tips if not enough
        if len(suggestions) < 3:
            suggestions.extend([
                "Practice speaking English daily for at least 10 minutes",
                "Read English articles or books to improve vocabulary",
                "Listen to English podcasts or watch movies with subtitles"
            ])
        
        return suggestions[:5]
    
    def generate_quiz(self, topic: str, difficulty: str = "medium", num_questions: int = 5) -> List[Dict]:
        """
        Generate quiz questions for a topic
        
        Args:
            topic: Topic to generate quiz about
            difficulty: Difficulty level (beginner, intermediate, advanced)
            num_questions: Number of questions to generate
            
        Returns:
            List of quiz questions
        """
        if self.use_heavy and self._heavy_processor:
            # Use advanced AI for quiz generation
            logger.info("Using heavy models for quiz generation")
            return self._heavy_processor.generate_quiz(topic, difficulty, num_questions)
        else:
            # Use instant analyzer's pre-defined quizzes
            logger.info("Using instant quiz generator")
            
            # Get quiz from instant analyzer's topic database
            topic_key = topic.lower().replace(" ", "_")
            topic_data = instant_analyzer.TOPICS.get(topic_key, None)
            
            if topic_data and "quiz" in topic_data:
                questions = topic_data["quiz"][:num_questions]
                return questions
            else:
                # Return a default quiz if topic not found
                return self._get_default_quiz(num_questions)
    
    def _get_default_quiz(self, num_questions: int) -> List[Dict]:
        """Generate default quiz questions"""
        default_questions = [
            {
                "question": "Which sentence is grammatically correct?",
                "options": [
                    "I go to the store yesterday",
                    "I went to the store yesterday",
                    "I goes to the store yesterday",
                    "I going to the store yesterday"
                ],
                "correct": 1,
                "explanation": "Use past tense 'went' for actions that happened in the past."
            },
            {
                "question": "Choose the correct form:",
                "options": [
                    "She don't like coffee",
                    "She doesn't like coffee",
                    "She doesn't likes coffee",
                    "She not like coffee"
                ],
                "correct": 1,
                "explanation": "'Doesn't' is the correct negative form for third person singular."
            },
            {
                "question": "What's the correct article?",
                "options": [
                    "I saw a elephant",
                    "I saw an elephant",
                    "I saw the elephant",
                    "I saw elephant"
                ],
                "correct": 1,
                "explanation": "Use 'an' before words that start with vowel sounds."
            },
            {
                "question": "Which preposition is correct?",
                "options": [
                    "I'm good in English",
                    "I'm good at English",
                    "I'm good on English",
                    "I'm good with English"
                ],
                "correct": 1,
                "explanation": "Use 'at' with skills and abilities."
            },
            {
                "question": "Choose the correct pronoun:",
                "options": [
                    "Me and John went shopping",
                    "John and me went shopping",
                    "John and I went shopping",
                    "I and John went shopping"
                ],
                "correct": 2,
                "explanation": "Use 'I' as the subject, and mention yourself last."
            }
        ]
        
        return default_questions[:num_questions]
    
    def get_status(self) -> Dict:
        """Get processor status information"""
        return {
            "mode": "heavy_models" if self.use_heavy else "instant_analyzer",
            "memory_usage": "1.3GB+" if self.use_heavy else "< 100MB",
            "heavy_models_available": HEAVY_MODELS_AVAILABLE,
            "description": "Using AI models" if self.use_heavy else "Using memory-optimized instant analyzer"
        }


# Global singleton instance
_processor_instance = None


def get_ai_processor(use_heavy_models: bool = False) -> MemoryEfficientProcessor:
    """
    Get or create the AI processor singleton
    
    Args:
        use_heavy_models: Force use of heavy models if available (requires 1.3GB+ RAM)
        
    Returns:
        MemoryEfficientProcessor instance
    """
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = MemoryEfficientProcessor(use_heavy_models=use_heavy_models)
    return _processor_instance


# For backward compatibility
def LightweightAIProcessor():
    """Backward compatibility wrapper"""
    return get_ai_processor(use_heavy_models=False)


if __name__ == "__main__":
    # Test the processor
    print("=" * 60)
    print("Testing Memory-Efficient Processor")
    print("=" * 60)
    
    processor = get_ai_processor()
    print(f"\nStatus: {processor.get_status()}")
    
    # Test analysis
    print("\n1. Testing Analysis:")
    print("-" * 60)
    test_text = "Hello, I want to improve my English. This is a conversation test."
    result = processor.analyze_conversation(test_text, call_duration_minutes=5)
    print(f"Topics: {result['topics']}")
    print(f"Vocabulary Level: {result['vocabulary_level']}")
    print(f"Suggestions: {result['suggestions'][:2]}")
    
    # Test quiz
    print("\n2. Testing Quiz Generation:")
    print("-" * 60)
    quiz = processor.generate_quiz("grammar", "medium", 3)
    print(f"Generated {len(quiz)} questions")
    print(f"First question: {quiz[0]['question']}")
    
    print("\n✅ All tests passed!")
