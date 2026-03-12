"""
Lightweight AI Model for Conversation Analysis
Optimized for 6GB RAM laptops - No external APIs required

Uses pre-trained models:
- DistilBERT for text classification (260MB)
- Sentence-BERT for embeddings (80MB)
Total RAM usage: ~1.3GB

Models are downloaded once and cached locally
"""

from transformers import pipeline
from sentence_transformers import SentenceTransformer
import re
import warnings
from typing import Dict, List, Optional
import logging

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LightweightAIProcessor:
    """
    Lightweight NLP processor for English learning analysis
    Runs entirely offline after initial model download
    """
    
    def __init__(self):
        """
        Initialize and load pre-trained models
        First time: Downloads models (3-5 minutes)
        After that: Loads from cache (10-20 seconds)
        """
        logger.info("Loading AI models (this may take a moment on first run)...")
        
        try:
            # Model 1: Sentence embeddings (80MB, ~500MB RAM)
            logger.info("Loading Sentence-BERT...")
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Model 2: Text classifier (260MB, ~800MB RAM)
            logger.info("Loading DistilBERT classifier...")
            self.classifier = pipeline(
                "zero-shot-classification",
                model="typeform/distilbert-base-uncased-mnli",
                device=-1  # CPU only (use 0 for GPU)
            )
            
            # Topics for English learning
            self.learning_topics = [
                "grammar practice",
                "vocabulary building",
                "conversation skills",
                "pronunciation",
                "reading comprehension",
                "writing skills"
            ]
            
            logger.info("✓ All models loaded successfully!")
            logger.info("✓ RAM usage: ~1.3GB")
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise
    
    def analyze_conversation(self, text: str) -> Dict:
        """
        Analyze conversation text and provide comprehensive feedback
        
        Args:
            text: The conversation transcript
            
        Returns:
            Dictionary with analysis results
        """
        if not text or len(text.strip()) < 10:
            return {
                "error": "Text too short for analysis",
                "topics": [],
                "grammar_issues": [],
                "vocabulary_level": "Unknown",
                "suggestions": ["Please provide more text for analysis"]
            }
        
        logger.info(f"Analyzing text ({len(text)} characters)...")
        
        try:
            # Step 1: Topic classification
            topics = self._identify_topics(text)
            
            # Step 2: Grammar analysis
            grammar_issues = self._analyze_grammar(text)
            
            # Step 3: Vocabulary assessment
            vocab_stats = self._assess_vocabulary(text)
            
            # Step 4: Generate suggestions
            suggestions = self._generate_suggestions(topics, grammar_issues, vocab_stats)
            
            # Step 5: Recommend learning topics
            recommended_topics = self._recommend_learning_topics(topics, grammar_issues)
            
            result = {
                "topics": topics,
                "grammar_issues": grammar_issues,
                "vocabulary_level": vocab_stats['level'],
                "vocabulary_stats": vocab_stats,
                "suggestions": suggestions,
                "recommended_topics": recommended_topics,
                "weak_areas": self._identify_weak_areas(grammar_issues, vocab_stats)
            }
            
            logger.info("✓ Analysis complete")
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {
                "error": str(e),
                "topics": [],
                "grammar_issues": [],
                "vocabulary_level": "Unknown",
                "suggestions": ["Analysis temporarily unavailable"]
            }
    
    def _identify_topics(self, text: str) -> List[Dict]:
        """
        Identify main topics using zero-shot classification
        Uses DistilBERT to classify without specific training
        """
        try:
            result = self.classifier(
                text[:500],  # Limit to 500 chars for speed
                self.learning_topics,
                multi_label=True
            )
            
            # Get topics with confidence > 30%
            topics = []
            for label, score in zip(result['labels'], result['scores']):
                if score > 0.3:
                    topics.append({
                        "topic": label,
                        "confidence": round(score * 100, 1)
                    })
            
            return topics[:3]  # Return top 3
            
        except Exception as e:
            logger.error(f"Topic identification failed: {e}")
            return []
    
    def _analyze_grammar(self, text: str) -> List[Dict]:
        """
        Detect common grammar errors using pattern matching
        """
        issues = []
        text_lower = text.lower()
        
        # Common grammar patterns to check
        patterns = {
            "subject_verb_agreement": [
                (r'\b(he|she|it)\s+(are|were|have)\b', 'Subject-verb agreement: Use "is/was/has" with he/she/it'),
                (r'\b(i|you|we|they)\s+(is|was|has)\b', 'Subject-verb agreement: Use "are/were/have" with I/you/we/they'),
                (r'\b(he|she|it)\s+don\'t\b', 'Subject-verb agreement: Use "doesn\'t" instead of "don\'t"'),
            ],
            "double_past_tense": [
                (r'\b(did|didn\'t)\s+\w+(ed)\b', 'Double past tense: Use base form after "did"'),
            ],
            "article_usage": [
                (r'\b(a)\s+[aeiou]\w+\b', 'Article error: Use "an" before vowel sounds'),
            ],
            "preposition_errors": [
                (r'\b(go)\s+(to)\s+(home|here|there)\b', 'Preposition error: No "to" needed before home/here/there'),
            ]
        }
        
        for error_type, pattern_list in patterns.items():
            for pattern, description in pattern_list:
                matches = re.finditer(pattern, text_lower, re.IGNORECASE)
                for match in matches:
                    issues.append({
                        "type": error_type.replace('_', ' ').title(),
                        "error": match.group(),
                        "description": description,
                        "position": match.start()
                    })
        
        return issues
    
    def _assess_vocabulary(self, text: str) -> Dict:
        """
        Assess vocabulary level and richness
        """
        # Extract words
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        if not words:
            return {
                "level": "Unknown",
                "total_words": 0,
                "unique_words": 0,
                "vocabulary_richness": 0,
                "average_word_length": 0
            }
        
        unique_words = set(words)
        total_words = len(words)
        unique_count = len(unique_words)
        avg_length = sum(len(w) for w in words) / total_words
        richness = unique_count / total_words if total_words > 0 else 0
        
        # Determine level based on metrics
        if avg_length < 4.5 and richness < 0.5:
            level = "Beginner"
        elif avg_length < 6 and richness < 0.7:
            level = "Intermediate"
        else:
            level = "Advanced"
        
        return {
            "level": level,
            "total_words": total_words,
            "unique_words": unique_count,
            "vocabulary_richness": round(richness, 2),
            "average_word_length": round(avg_length, 1)
        }
    
    def _generate_suggestions(self, topics: List[Dict], grammar_issues: List[Dict], 
                             vocab_stats: Dict) -> List[str]:
        """
        Generate personalized learning suggestions
        """
        suggestions = []
        
        # Topic-based suggestions
        if topics:
            top_topic = topics[0]['topic']
            suggestions.append(f"Great job discussing {top_topic}! Keep practicing.")
        
        # Grammar suggestions
        if len(grammar_issues) > 3:
            suggestions.append("Focus on grammar fundamentals - consider taking grammar quizzes")
        elif len(grammar_issues) > 0:
            issue_types = set(issue['type'] for issue in grammar_issues)
            suggestions.append(f"Work on: {', '.join(list(issue_types)[:2])}")
        else:
            suggestions.append("Excellent grammar! Keep up the good work.")
        
        # Vocabulary suggestions
        if vocab_stats['level'] == "Beginner":
            suggestions.append("Build your vocabulary with daily word practice")
        elif vocab_stats['vocabulary_richness'] < 0.5:
            suggestions.append("Try using more varied vocabulary in your conversations")
        else:
            suggestions.append("Great vocabulary range! Continue expanding it.")
        
        return suggestions
    
    def _recommend_learning_topics(self, topics: List[Dict], 
                                  grammar_issues: List[Dict]) -> List[str]:
        """
        Recommend specific topics to learn based on analysis
        """
        recommendations = []
        
        # Based on grammar issues
        if grammar_issues:
            issue_types = [issue['type'] for issue in grammar_issues]
            if 'Subject Verb Agreement' in issue_types:
                recommendations.append("Subject-Verb Agreement")
            if 'Double Past Tense' in issue_types:
                recommendations.append("Past Tense Usage")
            if 'Article Usage' in issue_types:
                recommendations.append("Articles (a, an, the)")
        
        # Based on detected topics
        if topics:
            for topic in topics[:2]:
                topic_name = topic['topic'].replace(' practice', '').replace(' building', '')
                if topic_name not in ['grammar', 'vocabulary']:
                    recommendations.append(topic_name.title())
        
        # Add general recommendations
        if not recommendations:
            recommendations = ["General English Practice", "Daily Conversation"]
        
        return recommendations[:3]
    
    def _identify_weak_areas(self, grammar_issues: List[Dict], 
                           vocab_stats: Dict) -> List[str]:
        """
        Identify weak areas that need improvement
        """
        weak_areas = []
        
        # Grammar weakness
        if len(grammar_issues) > 2:
            weak_areas.append("grammar")
        
        # Vocabulary weakness
        if vocab_stats['level'] == "Beginner" or vocab_stats['vocabulary_richness'] < 0.4:
            weak_areas.append("vocabulary")
        
        return weak_areas
    
    def generate_quiz(self, topic: str, difficulty: str = "medium", 
                     num_questions: int = 5) -> List[Dict]:
        """
        Generate quiz questions for a specific topic
        
        Args:
            topic: The topic to generate questions about
            difficulty: beginner, intermediate, or advanced
            num_questions: Number of questions (default: 5)
            
        Returns:
            List of quiz questions with options
        """
        logger.info(f"Generating {num_questions} quiz questions on '{topic}' ({difficulty})")
        
        # Quiz templates based on topics
        quiz_bank = {
            "grammar": self._get_grammar_questions(difficulty),
            "subject-verb agreement": self._get_subject_verb_questions(difficulty),
            "past tense": self._get_past_tense_questions(difficulty),
            "vocabulary": self._get_vocabulary_questions(difficulty),
            "articles": self._get_article_questions(difficulty),
            "conversation": self._get_conversation_questions(difficulty),
        }
        
        # Match topic to quiz bank
        topic_lower = topic.lower()
        questions = []
        
        for key in quiz_bank:
            if key in topic_lower:
                questions = quiz_bank[key]
                break
        
        # Default to grammar if no match
        if not questions:
            questions = quiz_bank["grammar"]
        
        # Return requested number of questions
        return questions[:num_questions]
    
    def _get_grammar_questions(self, difficulty: str) -> List[Dict]:
        """Generate grammar quiz questions"""
        questions = [
            {
                "id": 1,
                "question": "Which sentence is correct?",
                "options": [
                    "She goes to school every day.",
                    "She go to school every day.",
                    "She going to school every day.",
                    "She gone to school every day."
                ],
                "correct_answer": 0,
                "explanation": "With third person singular (she), use 'goes' in present simple.",
                "difficulty": difficulty
            },
            {
                "id": 2,
                "question": "Fill in the blank: They ___ watching TV now.",
                "options": ["are", "is", "am", "be"],
                "correct_answer": 0,
                "explanation": "'They' takes 'are' in present continuous tense.",
                "difficulty": difficulty
            },
            {
                "id": 3,
                "question": "Choose the correct form: I ___ to the store yesterday.",
                "options": ["went", "go", "goes", "going"],
                "correct_answer": 0,
                "explanation": "Use past tense 'went' with 'yesterday'.",
                "difficulty": difficulty
            },
            {
                "id": 4,
                "question": "Which is correct?",
                "options": [
                    "He doesn't like coffee.",
                    "He don't like coffee.",
                    "He not like coffee.",
                    "He doesn't likes coffee."
                ],
                "correct_answer": 0,
                "explanation": "Use 'doesn't' (does not) with third person singular.",
                "difficulty": difficulty
            },
            {
                "id": 5,
                "question": "Complete: We ___ been waiting for an hour.",
                "options": ["have", "has", "are", "is"],
                "correct_answer": 0,
                "explanation": "Present perfect uses 'have' with plural subjects.",
                "difficulty": difficulty
            }
        ]
        return questions
    
    def _get_subject_verb_questions(self, difficulty: str) -> List[Dict]:
        """Generate subject-verb agreement questions"""
        return [
            {
                "id": 1,
                "question": "She ___ a teacher.",
                "options": ["is", "are", "am", "be"],
                "correct_answer": 0,
                "explanation": "Use 'is' with 'she' (third person singular).",
                "difficulty": difficulty
            },
            {
                "id": 2,
                "question": "They ___ playing soccer.",
                "options": ["are", "is", "am", "was"],
                "correct_answer": 0,
                "explanation": "Use 'are' with 'they' (plural).",
                "difficulty": difficulty
            },
            {
                "id": 3,
                "question": "He ___ to work every day.",
                "options": ["goes", "go", "going", "gone"],
                "correct_answer": 0,
                "explanation": "Add 's' to verbs with he/she/it in present simple.",
                "difficulty": difficulty
            }
        ]
    
    def _get_past_tense_questions(self, difficulty: str) -> List[Dict]:
        """Generate past tense questions"""
        return [
            {
                "id": 1,
                "question": "I ___ to Paris last year.",
                "options": ["went", "go", "goed", "going"],
                "correct_answer": 0,
                "explanation": "Past tense of 'go' is 'went'.",
                "difficulty": difficulty
            },
            {
                "id": 2,
                "question": "She ___ the book yesterday.",
                "options": ["read", "reads", "reading", "readed"],
                "correct_answer": 0,
                "explanation": "Past tense of 'read' is also 'read' (pronunciation changes).",
                "difficulty": difficulty
            },
            {
                "id": 3,
                "question": "Did you ___ your homework?",
                "options": ["do", "did", "done", "does"],
                "correct_answer": 0,
                "explanation": "After 'did', use base form of the verb.",
                "difficulty": difficulty
            }
        ]
    
    def _get_vocabulary_questions(self, difficulty: str) -> List[Dict]:
        """Generate vocabulary questions"""
        return [
            {
                "id": 1,
                "question": "What does 'improve' mean?",
                "options": [
                    "To make something better",
                    "To make something worse",
                    "To remove something",
                    "To copy something"
                ],
                "correct_answer": 0,
                "explanation": "Improve means to make something better or enhance it.",
                "difficulty": difficulty
            },
            {
                "id": 2,
                "question": "Choose the synonym for 'happy':",
                "options": ["joyful", "sad", "angry", "tired"],
                "correct_answer": 0,
                "explanation": "Joyful is a synonym (similar meaning) of happy.",
                "difficulty": difficulty
            }
        ]
    
    def _get_article_questions(self, difficulty: str) -> List[Dict]:
        """Generate article usage questions"""
        return [
            {
                "id": 1,
                "question": "I saw ___ elephant at the zoo.",
                "options": ["an", "a", "the", "no article"],
                "correct_answer": 0,
                "explanation": "Use 'an' before words starting with vowel sounds.",
                "difficulty": difficulty
            },
            {
                "id": 2,
                "question": "She is ___ doctor.",
                "options": ["a", "an", "the", "no article"],
                "correct_answer": 0,
                "explanation": "Use 'a' before consonant sounds for professions.",
                "difficulty": difficulty
            }
        ]
    
    def _get_conversation_questions(self, difficulty: str) -> List[Dict]:
        """Generate conversation skills questions"""
        return [
            {
                "id": 1,
                "question": "How do you greet someone formally?",
                "options": [
                    "Good morning, how are you?",
                    "Hey! What's up?",
                    "Yo!",
                    "Hi there!"
                ],
                "correct_answer": 0,
                "explanation": "Formal greetings use complete sentences and polite language.",
                "difficulty": difficulty
            },
            {
                "id": 2,
                "question": "Which response is most polite?",
                "options": [
                    "Thank you very much for your help.",
                    "Thanks.",
                    "OK.",
                    "Yeah."
                ],
                "correct_answer": 0,
                "explanation": "Complete, specific phrases are more polite and formal.",
                "difficulty": difficulty
            }
        ]


# Singleton instance
_ai_processor = None


def get_ai_processor() -> LightweightAIProcessor:
    """
    Get or create the AI processor singleton instance
    Models are loaded only once and reused
    """
    global _ai_processor
    if _ai_processor is None:
        _ai_processor = LightweightAIProcessor()
    return _ai_processor


# Test function
if __name__ == "__main__":
    import json
    print("=" * 60)
    print("Testing Lightweight AI Processor")
    print("=" * 60)
    
    # Initialize processor
    processor = get_ai_processor()
    
    # Test conversation analysis
    print("\n1. Testing Conversation Analysis:")
    print("-" * 60)
    test_text = """
    Hello, I want to improve my English speaking skills.
    Yesterday, I goes to the library and I reading a book.
    The book was very interesting. I wants to practice more.
    """
    
    result = processor.analyze_conversation(test_text)
    print(json.dumps(result, indent=2))
    
    # Test quiz generation
    print("\n2. Testing Quiz Generation:")
    print("-" * 60)
    quiz = processor.generate_quiz("grammar", "medium", 3)
    print(json.dumps(quiz, indent=2))
    
    print("\n" + "=" * 60)
    print("✓ All tests completed!")
    print("=" * 60)
