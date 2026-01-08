# import nltk
# from textblob import TextBlob
from langdetect import detect
from typing import List, Dict, Tuple
import re
from collections import Counter
import math

# Download required NLTK data
# try:
#     nltk.data.find('tokenizers/punkt')
#     nltk.data.find('taggers/averaged_perceptron_tagger')
# except LookupError:
#     nltk.download('punkt')
#     nltk.download('averaged_perceptron_tagger')

class TextAnalyzer:
    def __init__(self):
        """Initialize NLP models"""
        # Using TextBlob instead of spaCy for Python 3.13 compatibility
        self.use_textblob = True
        
        # Common filler words
        self.filler_words = {
            'um', 'uh', 'ah', 'er', 'like', 'you know', 'i mean',
            'actually', 'basically', 'seriously', 'literally',
            'so', 'well', 'okay', 'right', 'anyway'
        }
        
        # Pause detection regex patterns
        self.pause_patterns = [
            r'\.{2,}',  # Multiple dots
            r'\-{2,}',  # Multiple dashes
            r'\s+',     # Excessive whitespace
        ]
    
    def analyze_text(self, text: str, audio_duration: float = None) -> Dict:
        """
        Analyze text for various metrics
        
        Args:
            text: The transcribed text
            audio_duration: Duration of audio in seconds
        
        Returns:
            Dictionary with analysis results
        """
        if not text.strip():
            return self._empty_analysis()
        
        # Basic metrics
        words = text.split()
        word_count = len(words)
        sentences = self._split_sentences(text)
        sentence_count = len(sentences)
        
        # Language detection
        language_score = self._detect_english_score(text)
        
        # Grammar analysis (simplified)
        grammar_errors = self._estimate_grammar_errors(text)
        
        # Filler words detection
        filler_words = self._detect_filler_words(text)
        
        # Vocabulary analysis
        vocabulary_repetition = self._calculate_vocabulary_repetition(words)
        
        # Fluency metrics
        fluency_score = self._calculate_fluency_score(text, audio_duration)
        words_per_minute = self._calculate_wpm(word_count, audio_duration)
        pause_count = self._detect_pauses(text)
        
        # Overall score calculation
        overall_score = self._calculate_overall_score(
            grammar_errors=grammar_errors,
            filler_count=len(filler_words),
            vocabulary_repetition=vocabulary_repetition,
            fluency_score=fluency_score,
            language_score=language_score
        )
        
        # Weaknesses detection
        weaknesses = self._identify_weaknesses(
            grammar_errors=grammar_errors,
            filler_words=filler_words,
            vocabulary_repetition=vocabulary_repetition,
            fluency_score=fluency_score,
            language_score=language_score
        )
        
        # Suggestions
        suggestions = self._generate_suggestions(weaknesses)
        
        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "grammar_errors": grammar_errors,
            "filler_words": filler_words,
            "vocabulary_repetition": vocabulary_repetition,
            "fluency_score": fluency_score,
            "words_per_minute": words_per_minute,
            "pause_count": pause_count,
            "english_compliance_score": language_score,
            "overall_score": overall_score,
            "weaknesses": weaknesses,
            "suggestions": suggestions
        }
    
    def _detect_english_score(self, text: str) -> float:
        """Detect if text is English and return confidence score"""
        try:
            lang = detect(text)
            if lang == 'en':
                # Simple scoring without TextBlob
                words = text.split()
                total_words = len(words)
                
                if total_words > 0:
                    return min(1.0, 1.0)
            return 0.5
        except:
            return 0.5  # Default if detection fails
    
    def _estimate_grammar_errors(self, text: str) -> int:
        """Estimate grammar errors (simplified)"""
        # This is a simplified version. In production, use LanguageTool
        errors = 0
        
        # Check for common errors
        patterns = [
            (r'\bi\s+am\s+', 0),  # Lowercase I
            (r'\byour\s+you\b', 1),  # Your/you're confusion
            (r'\btheir\s+there\b', 1),
            (r'\bits\s+it\'s\b', 1),
            (r'\bdouble\s+is\b', 1),  # Double verbs
        ]
        
        for pattern, error_count in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            errors += len(matches) * error_count
        
        # Count based on sentence structure (simplified)
        sentences = self._split_sentences(text)
        for sentence in sentences:
            words = sentence.split()
            if len(words) < 3:  # Very short sentences might be fragments
                errors += 1
        
        return min(errors, 20)  # Cap errors
    
    def _detect_filler_words(self, text: str) -> List[str]:
        """Detect filler words in text"""
        found_fillers = []
        text_lower = text.lower()
        
        for filler in self.filler_words:
            # Use regex to find whole words
            pattern = r'\b' + re.escape(filler) + r'\b'
            if re.search(pattern, text_lower):
                found_fillers.append(filler)
        
        return found_fillers
    
    def _calculate_vocabulary_repetition(self, words: List[str]) -> float:
        """Calculate vocabulary repetition ratio"""
        if len(words) < 10:
            return 0.0
        
        # Get unique words (case insensitive)
        unique_words = set(word.lower() for word in words if word.isalpha())
        repetition_ratio = 1 - (len(unique_words) / len(words))
        
        return max(0.0, min(1.0, repetition_ratio))
    
    def _calculate_fluency_score(self, text: str, audio_duration: float = None) -> float:
        """Calculate fluency score (0-100)"""
        if not text.strip():
            return 0.0
        
        # Base score components
        score = 50.0  # Start with average
        
        # Sentence length variation
        sentences = self._split_sentences(text)
        if len(sentences) > 1:
            sentence_lengths = [len(s.split()) for s in sentences]
            length_variance = sum((l - sum(sentence_lengths)/len(sentence_lengths))**2 for l in sentence_lengths)
            if length_variance > 0:
                score += min(20, length_variance / 10)
        
        # Word variety
        words = [w.lower() for w in text.split() if w.isalpha()]
        if len(words) > 20:
            unique_ratio = len(set(words)) / len(words)
            score += unique_ratio * 20
        
        # Adjust based on audio duration if available
        if audio_duration and audio_duration > 0:
            wpm = len(words) / (audio_duration / 60)
            if 100 <= wpm <= 150:  # Optimal speaking rate
                score += 10
            elif wpm < 50 or wpm > 200:  # Too slow or too fast
                score -= 10
        
        return max(0.0, min(100.0, score))
    
    def _calculate_wpm(self, word_count: int, audio_duration: float = None) -> float:
        """Calculate words per minute"""
        if not audio_duration or audio_duration == 0:
            return 0.0
        return (word_count / audio_duration) * 60
    
    def _detect_pauses(self, text: str) -> int:
        """Detect pauses in transcribed text"""
        pause_count = 0
        
        for pattern in self.pause_patterns:
            matches = re.findall(pattern, text)
            pause_count += len(matches)
        
        # Also count filler words as potential pauses
        filler_matches = sum(1 for filler in self.filler_words 
                           if re.search(r'\b' + re.escape(filler) + r'\b', text.lower()))
        
        return pause_count + filler_matches
    
    def _calculate_overall_score(self, **metrics) -> float:
        """Calculate overall communication score (0-100)"""
        weights = {
            'grammar_errors': -2.0,  # Each error reduces score
            'filler_count': -1.5,    # Each filler reduces score
            'vocabulary_repetition': -20.0,  # Repetition penalty
            'fluency_score': 0.8,    # Direct contribution
            'language_score': 30.0,  # English compliance importance
        }
        
        score = 50.0  # Base score
        
        # Apply weights
        if 'grammar_errors' in metrics:
            score += metrics['grammar_errors'] * weights['grammar_errors']
        
        if 'filler_count' in metrics:
            score += metrics['filler_count'] * weights['filler_count']
        
        if 'vocabulary_repetition' in metrics:
            score -= metrics['vocabulary_repetition'] * weights['vocabulary_repetition']
        
        if 'fluency_score' in metrics:
            score += metrics['fluency_score'] * weights['fluency_score']
        
        if 'language_score' in metrics:
            score += metrics['language_score'] * weights['language_score']
        
        return max(0.0, min(100.0, score))
    
    def _identify_weaknesses(self, **metrics) -> List[str]:
        """Identify communication weaknesses"""
        weaknesses = []
        
        if metrics.get('grammar_errors', 0) > 5:
            weaknesses.append("grammar")
        
        if metrics.get('filler_count', 0) > 3:
            weaknesses.append("filler_words")
        
        if metrics.get('vocabulary_repetition', 0) > 0.3:
            weaknesses.append("vocabulary_repetition")
        
        if metrics.get('fluency_score', 0) < 60:
            weaknesses.append("fluency")
        
        if metrics.get('language_score', 0) < 0.7:
            weaknesses.append("english_compliance")
        
        if metrics.get('pause_count', 0) > 5:
            weaknesses.append("pauses")
        
        return weaknesses
    
    def _generate_suggestions(self, weaknesses: List[str]) -> List[str]:
        """Generate improvement suggestions based on weaknesses"""
        suggestions_map = {
            "grammar": [
                "Practice basic grammar rules",
                "Use LanguageTool to check your sentences",
                "Read English articles aloud"
            ],
            "filler_words": [
                "Practice speaking with pauses instead of filler words",
                "Record yourself and identify filler word patterns",
                "Use the '2-second rule' - pause for 2 seconds before speaking"
            ],
            "vocabulary_repetition": [
                "Learn synonyms for commonly used words",
                "Read diverse English materials",
                "Keep a vocabulary journal"
            ],
            "fluency": [
                "Practice speaking at a consistent pace",
                "Use tongue twisters for articulation",
                "Shadow native speakers' speech patterns"
            ],
            "english_compliance": [
                "Focus on speaking only in English during calls",
                "Practice thinking in English",
                "Use English in daily activities"
            ],
            "pauses": [
                "Plan your thoughts before speaking",
                "Practice speaking in complete sentences",
                "Use transitional phrases instead of long pauses"
            ]
        }
        
        suggestions = []
        for weakness in weaknesses:
            if weakness in suggestions_map:
                suggestions.extend(suggestions_map[weakness][:2])  # Take top 2 suggestions
        
        # Add default suggestions if none
        if not suggestions:
            suggestions = [
                "Practice regularly with different partners",
                "Record and review your conversations",
                "Set specific goals for each practice session"
            ]
        
        return list(set(suggestions))[:5]  # Return up to 5 unique suggestions
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure"""
        return {
            "word_count": 0,
            "sentence_count": 0,
            "grammar_errors": 0,
            "filler_words": [],
            "vocabulary_repetition": 0.0,
            "fluency_score": 0.0,
            "words_per_minute": 0.0,
            "pause_count": 0,
            "english_compliance_score": 0.0,
            "overall_score": 0.0,
            "weaknesses": ["no_speech"],
            "suggestions": ["Try to speak more during calls"]
        }

# Singleton instance
text_analyzer = TextAnalyzer()