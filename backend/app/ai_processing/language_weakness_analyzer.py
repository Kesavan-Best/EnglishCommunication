"""
Language Weakness Analyzer
Comprehensive analysis using LanguageTool, WordNet, and Rule-based systems

Components:
1. LanguageTool - Grammar error detection
2. WordNet (NLTK) - Vocabulary richness analysis
3. Rule-based system - Filler word detection

Author: English Communication App
"""
import re
from typing import Dict, List, Tuple, Optional
from collections import Counter
import logging

logger = logging.getLogger(__name__)

# Lazy imports to avoid memory issues on Render
language_tool = None
nltk_wordnet = None
nltk_tokenizer = None


def _init_language_tool():
    """Initialize LanguageTool lazily"""
    global language_tool
    if language_tool is None:
        try:
            import language_tool_python
            language_tool = language_tool_python.LanguageTool('en-US')
            logger.info("LanguageTool initialized successfully")
        except ImportError:
            logger.warning("language_tool_python not installed. Using fallback grammar checker.")
            language_tool = None
        except Exception as e:
            logger.error(f"Error initializing LanguageTool: {e}")
            language_tool = None
    return language_tool


def _init_nltk():
    """Initialize NLTK WordNet lazily"""
    global nltk_wordnet, nltk_tokenizer
    if nltk_wordnet is None:
        try:
            import nltk
            # Download required data (only once)
            try:
                nltk.data.find('corpora/wordnet')
            except LookupError:
                nltk.download('wordnet', quiet=True)
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)
            try:
                nltk.data.find('averaged_perceptron_tagger')
            except LookupError:
                nltk.download('averaged_perceptron_tagger', quiet=True)
            
            from nltk.corpus import wordnet
            from nltk.tokenize import word_tokenize
            
            nltk_wordnet = wordnet
            nltk_tokenizer = word_tokenize
            logger.info("NLTK WordNet initialized successfully")
        except ImportError:
            logger.warning("NLTK not installed. Using fallback vocabulary analyzer.")
            nltk_wordnet = None
        except Exception as e:
            logger.error(f"Error initializing NLTK: {e}")
            nltk_wordnet = None
    return nltk_wordnet, nltk_tokenizer


class GrammarChecker:
    """
    Grammar error detection using LanguageTool
    
    Features:
    - Detects grammar, spelling, and style errors
    - Categorizes errors by type
    - Provides correction suggestions
    """
    
    def __init__(self):
        self.tool = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization"""
        if not self._initialized:
            self.tool = _init_language_tool()
            self._initialized = True
    
    def check(self, text: str) -> Dict:
        """
        Analyze text for grammar errors
        
        Returns:
            {
                'total_errors': int,
                'errors_by_category': {category: count},
                'error_details': [
                    {
                        'message': str,
                        'context': str,
                        'suggestions': [str],
                        'category': str,
                        'rule_id': str
                    }
                ],
                'grammar_score': float (0-100)
            }
        """
        self._ensure_initialized()
        
        if not text.strip():
            return self._empty_result()
        
        if self.tool is None:
            return self._fallback_check(text)
        
        try:
            matches = self.tool.check(text)
            return self._process_matches(text, matches)
        except Exception as e:
            logger.error(f"LanguageTool error: {e}")
            return self._fallback_check(text)
    
    def _process_matches(self, text: str, matches) -> Dict:
        """Process LanguageTool matches into structured result"""
        errors_by_category = Counter()
        error_details = []
        
        for match in matches:
            category = self._categorize_error(match.ruleId)
            errors_by_category[category] += 1
            
            error_details.append({
                'message': match.message,
                'context': match.context,
                'suggestions': match.replacements[:3] if match.replacements else [],
                'category': category,
                'rule_id': match.ruleId,
                'offset': match.offset,
                'length': match.errorLength
            })
        
        # Calculate grammar score (fewer errors = higher score)
        word_count = len(text.split())
        error_rate = len(matches) / max(word_count, 1)
        grammar_score = max(0, 100 - (error_rate * 100 * 5))  # 5x penalty per error ratio
        
        return {
            'total_errors': len(matches),
            'errors_by_category': dict(errors_by_category),
            'error_details': error_details,
            'grammar_score': round(grammar_score, 2)
        }
    
    def _categorize_error(self, rule_id: str) -> str:
        """Categorize error by rule ID"""
        rule_id = rule_id.upper()
        
        if any(x in rule_id for x in ['SPELL', 'TYPO', 'MORFOLOGIK']):
            return 'spelling'
        elif any(x in rule_id for x in ['COMMA', 'PUNCTUATION', 'APOSTROPHE', 'QUOTES']):
            return 'punctuation'
        elif any(x in rule_id for x in ['AGREEMENT', 'VERB', 'TENSE']):
            return 'verb_agreement'
        elif any(x in rule_id for x in ['ARTICLE', 'DT_']):
            return 'articles'
        elif any(x in rule_id for x in ['WORD_ORDER', 'SENTENCE']):
            return 'sentence_structure'
        elif any(x in rule_id for x in ['STYLE', 'REDUNDANCY', 'WORDINESS']):
            return 'style'
        elif any(x in rule_id for x in ['CONFUSION', 'YOUR', 'THEIR', 'ITS']):
            return 'word_confusion'
        else:
            return 'grammar'
    
    def _fallback_check(self, text: str) -> Dict:
        """Fallback grammar checking without LanguageTool"""
        errors = []
        
        # Common error patterns
        patterns = [
            (r'\bi\b(?!\s+(am|was|will|have|had|would|could|should|do|did|can|cannot|don\'t|didn\'t|won\'t))', 
             'Lowercase "i" should be capitalized to "I"', 'capitalization'),
            (r'\byour\s+(?:going|welcome|right|wrong)\b', 
             'Possible confusion: "your" vs "you\'re"', 'word_confusion'),
            (r'\btheir\s+(?:is|are|was|were)\b', 
             'Possible confusion: "their" vs "there"', 'word_confusion'),
            (r'\bits\s+(?:a|an|the)\b', 
             'Possible confusion: "its" vs "it\'s"', 'word_confusion'),
            (r'\ba\s+[aeiou]', 
             'Use "an" before vowel sounds', 'articles'),
            (r'\bdoesn\'t\s+(?:has|have)\b', 
             'Verb agreement error after "doesn\'t"', 'verb_agreement'),
            (r'\bdon\'t\s+(?:has)\b', 
             'Verb agreement error after "don\'t"', 'verb_agreement'),
            (r'[.!?]\s*[a-z]', 
             'Sentence should start with capital letter', 'capitalization'),
            (r'\s+[,.!?]', 
             'Remove space before punctuation', 'punctuation'),
            (r'[,.!?]{2,}', 
             'Multiple punctuation marks', 'punctuation'),
        ]
        
        for pattern, message, category in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE if 'your' in pattern else 0)
            for match in matches:
                errors.append({
                    'message': message,
                    'context': text[max(0, match.start()-20):min(len(text), match.end()+20)],
                    'suggestions': [],
                    'category': category,
                    'rule_id': 'FALLBACK',
                    'offset': match.start(),
                    'length': match.end() - match.start()
                })
        
        errors_by_category = Counter(e['category'] for e in errors)
        word_count = len(text.split())
        error_rate = len(errors) / max(word_count, 1)
        grammar_score = max(0, 100 - (error_rate * 100 * 5))
        
        return {
            'total_errors': len(errors),
            'errors_by_category': dict(errors_by_category),
            'error_details': errors,
            'grammar_score': round(grammar_score, 2)
        }
    
    def _empty_result(self) -> Dict:
        return {
            'total_errors': 0,
            'errors_by_category': {},
            'error_details': [],
            'grammar_score': 100.0
        }


class VocabularyAnalyzer:
    """
    Vocabulary richness analysis using WordNet
    
    Features:
    - Type-Token Ratio (TTR) - unique words / total words
    - Lexical Sophistication - using advanced vocabulary
    - Word Diversity Score - synonym coverage
    - Vocabulary Level Assessment
    """
    
    # Common/basic words (1000 most common English words approximation)
    BASIC_WORDS = {
        'a', 'about', 'after', 'all', 'also', 'am', 'an', 'and', 'another', 'any',
        'are', 'as', 'at', 'back', 'be', 'because', 'been', 'before', 'being',
        'between', 'both', 'but', 'by', 'call', 'came', 'can', 'come', 'could',
        'day', 'did', 'do', 'does', 'done', 'down', 'each', 'even', 'find', 'first',
        'for', 'from', 'get', 'give', 'go', 'good', 'great', 'had', 'has', 'have',
        'he', 'her', 'here', 'him', 'his', 'how', 'i', 'if', 'in', 'into', 'is',
        'it', 'its', 'just', 'know', 'last', 'left', 'let', 'life', 'like', 'little',
        'long', 'look', 'made', 'make', 'man', 'many', 'may', 'me', 'men', 'might',
        'more', 'most', 'much', 'must', 'my', 'name', 'never', 'new', 'no', 'not',
        'now', 'of', 'off', 'old', 'on', 'one', 'only', 'or', 'other', 'our', 'out',
        'over', 'own', 'part', 'people', 'place', 'put', 'right', 'said', 'same',
        'say', 'see', 'she', 'should', 'show', 'side', 'since', 'so', 'some', 'still',
        'such', 'take', 'tell', 'than', 'that', 'the', 'their', 'them', 'then',
        'there', 'these', 'they', 'thing', 'think', 'this', 'those', 'through',
        'time', 'to', 'too', 'two', 'under', 'up', 'upon', 'us', 'use', 'very',
        'want', 'was', 'way', 'we', 'well', 'went', 'were', 'what', 'when', 'where',
        'which', 'while', 'who', 'why', 'will', 'with', 'without', 'work', 'would',
        'year', 'yes', 'yet', 'you', 'your'
    }
    
    def __init__(self):
        self.wordnet = None
        self.tokenizer = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization"""
        if not self._initialized:
            self.wordnet, self.tokenizer = _init_nltk()
            self._initialized = True
    
    def analyze(self, text: str) -> Dict:
        """
        Analyze vocabulary richness
        
        Returns:
            {
                'word_count': int,
                'unique_words': int,
                'type_token_ratio': float (0-1),
                'lexical_sophistication': float (0-100),
                'vocabulary_diversity_score': float (0-100),
                'vocabulary_level': str (basic/intermediate/advanced),
                'advanced_words_used': [str],
                'word_frequency': {word: count},
                'repeated_words': [str],
                'suggestions': [str]
            }
        """
        self._ensure_initialized()
        
        if not text.strip():
            return self._empty_result()
        
        # Tokenize text
        words = self._tokenize(text)
        content_words = [w for w in words if w.isalpha() and len(w) > 2]
        
        if not content_words:
            return self._empty_result()
        
        # Basic metrics
        word_count = len(content_words)
        unique_words = set(w.lower() for w in content_words)
        unique_count = len(unique_words)
        
        # Type-Token Ratio (TTR)
        ttr = unique_count / word_count if word_count > 0 else 0
        
        # Word frequency analysis
        word_freq = Counter(w.lower() for w in content_words)
        repeated_words = [word for word, count in word_freq.most_common() if count >= 3]
        
        # Lexical sophistication (advanced words percentage)
        advanced_words = [w for w in unique_words if w.lower() not in self.BASIC_WORDS]
        lexical_sophistication = (len(advanced_words) / unique_count * 100) if unique_count > 0 else 0
        
        # Vocabulary diversity using WordNet
        diversity_score = self._calculate_diversity_score(list(unique_words))
        
        # Vocabulary level assessment
        vocab_level = self._assess_vocabulary_level(ttr, lexical_sophistication, diversity_score)
        
        # Overall vocabulary score
        vocab_score = self._calculate_vocab_score(ttr, lexical_sophistication, diversity_score)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(
            ttr, lexical_sophistication, repeated_words, vocab_level
        )
        
        return {
            'word_count': word_count,
            'unique_words': unique_count,
            'type_token_ratio': round(ttr, 3),
            'lexical_sophistication': round(lexical_sophistication, 2),
            'vocabulary_diversity_score': round(diversity_score, 2),
            'vocabulary_score': round(vocab_score, 2),
            'vocabulary_level': vocab_level,
            'advanced_words_used': advanced_words[:20],  # Top 20
            'word_frequency': dict(word_freq.most_common(10)),
            'repeated_words': repeated_words[:10],
            'suggestions': suggestions
        }
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text using NLTK or fallback"""
        if self.tokenizer:
            try:
                return self.tokenizer(text)
            except:
                pass
        # Fallback tokenization
        return re.findall(r'\b\w+\b', text)
    
    def _calculate_diversity_score(self, words: List[str]) -> float:
        """Calculate vocabulary diversity using WordNet synonym coverage"""
        if not words:
            return 0.0
        
        if self.wordnet is None:
            # Fallback without WordNet
            unique_count = len(set(words))
            return min(100, (unique_count / max(len(words), 1)) * 100 * 1.5)
        
        try:
            synonym_coverage = 0
            words_with_synonyms = 0
            
            for word in words[:50]:  # Limit for performance
                synsets = self.wordnet.synsets(word.lower())
                if synsets:
                    words_with_synonyms += 1
                    # Count unique synonyms
                    synonyms = set()
                    for synset in synsets[:3]:  # Top 3 synsets
                        for lemma in synset.lemmas():
                            synonyms.add(lemma.name())
                    synonym_coverage += min(len(synonyms), 10) / 10  # Normalize
            
            if words_with_synonyms > 0:
                avg_synonym_richness = synonym_coverage / words_with_synonyms
                # Check if user uses varied words from synonym sets
                return min(100, avg_synonym_richness * 100)
            return 50.0
        except Exception as e:
            logger.error(f"WordNet error: {e}")
            return 50.0
    
    def _assess_vocabulary_level(self, ttr: float, sophistication: float, diversity: float) -> str:
        """Assess overall vocabulary level"""
        avg_score = (ttr * 100 + sophistication + diversity) / 3
        
        if avg_score >= 70:
            return 'advanced'
        elif avg_score >= 40:
            return 'intermediate'
        else:
            return 'basic'
    
    def _calculate_vocab_score(self, ttr: float, sophistication: float, diversity: float) -> float:
        """Calculate overall vocabulary score 0-100"""
        # Weighted average
        score = (ttr * 100 * 0.4) + (sophistication * 0.3) + (diversity * 0.3)
        return min(100, max(0, score))
    
    def _generate_suggestions(self, ttr: float, sophistication: float, 
                              repeated_words: List[str], level: str) -> List[str]:
        """Generate vocabulary improvement suggestions"""
        suggestions = []
        
        if ttr < 0.5:
            suggestions.append("Try to use more varied vocabulary instead of repeating words")
        
        if sophistication < 30:
            suggestions.append("Practice using more advanced vocabulary beyond basic words")
        
        if repeated_words:
            words_str = ', '.join(repeated_words[:3])
            suggestions.append(f"You repeated these words often: {words_str}. Try using synonyms.")
        
        if level == 'basic':
            suggestions.append("Read more English content to expand your vocabulary naturally")
            suggestions.append("Learn 5 new words daily and use them in sentences")
        elif level == 'intermediate':
            suggestions.append("Challenge yourself with academic or professional vocabulary")
        
        return suggestions[:4]
    
    def _empty_result(self) -> Dict:
        return {
            'word_count': 0,
            'unique_words': 0,
            'type_token_ratio': 0.0,
            'lexical_sophistication': 0.0,
            'vocabulary_diversity_score': 0.0,
            'vocabulary_score': 0.0,
            'vocabulary_level': 'unknown',
            'advanced_words_used': [],
            'word_frequency': {},
            'repeated_words': [],
            'suggestions': ["Speak more to analyze your vocabulary"]
        }


class FillerWordDetector:
    """
    Rule-based filler word detection
    
    Features:
    - Detects common filler words (um, uh, like, you know, etc.)
    - Categorizes fillers by type
    - Calculates filler frequency
    - Provides context for each filler
    """
    
    # Filler word categories with patterns
    FILLER_PATTERNS = {
        'hesitation_sounds': {
            'words': ['um', 'uh', 'ah', 'er', 'eh', 'uhm', 'umm', 'uhh', 'hmm', 'mm'],
            'severity': 'high',
            'description': 'Vocal pauses showing hesitation'
        },
        'discourse_markers': {
            'words': ['like', 'so', 'well', 'anyway', 'basically', 'actually', 'honestly', 'literally'],
            'severity': 'medium',
            'description': 'Overused discourse markers'
        },
        'hedge_words': {
            'words': ['kind of', 'sort of', 'you know', 'i mean', 'i guess', 'i think', 'maybe', 'probably'],
            'severity': 'low',
            'description': 'Words that weaken statements'
        },
        'verbal_crutches': {
            'words': ['right', 'okay', 'obviously', 'clearly', 'seriously', 'totally', 'definitely'],
            'severity': 'medium',
            'description': 'Unnecessary intensifiers/confirmations'
        },
        'repetition_starters': {
            'words': ['i mean like', 'you know what', 'the thing is', 'at the end of the day'],
            'severity': 'low',
            'description': 'Repetitive phrase starters'
        }
    }
    
    def __init__(self):
        # Compile regex patterns for efficiency
        self.compiled_patterns = {}
        for category, data in self.FILLER_PATTERNS.items():
            patterns = []
            for word in data['words']:
                # Create pattern that matches whole words/phrases
                pattern = r'\b' + re.escape(word) + r'\b'
                patterns.append(pattern)
            self.compiled_patterns[category] = re.compile('|'.join(patterns), re.IGNORECASE)
    
    def detect(self, text: str) -> Dict:
        """
        Detect filler words in text
        
        Returns:
            {
                'total_fillers': int,
                'filler_rate': float (fillers per 100 words),
                'fillers_by_category': {category: [fillers]},
                'filler_details': [
                    {
                        'word': str,
                        'category': str,
                        'severity': str,
                        'count': int,
                        'positions': [int]
                    }
                ],
                'filler_score': float (0-100, higher = less fillers),
                'most_common_fillers': [(word, count)],
                'suggestions': [str]
            }
        """
        if not text.strip():
            return self._empty_result()
        
        word_count = len(text.split())
        all_fillers = Counter()
        fillers_by_category = {}
        filler_positions = {}
        
        for category, pattern in self.compiled_patterns.items():
            matches = list(pattern.finditer(text.lower()))
            if matches:
                fillers_by_category[category] = []
                for match in matches:
                    filler = match.group().lower()
                    all_fillers[filler] += 1
                    fillers_by_category[category].append(filler)
                    
                    if filler not in filler_positions:
                        filler_positions[filler] = []
                    filler_positions[filler].append(match.start())
        
        total_fillers = sum(all_fillers.values())
        filler_rate = (total_fillers / word_count * 100) if word_count > 0 else 0
        
        # Create detailed filler analysis
        filler_details = []
        for filler, count in all_fillers.items():
            category = self._get_filler_category(filler)
            filler_details.append({
                'word': filler,
                'category': category,
                'severity': self.FILLER_PATTERNS.get(category, {}).get('severity', 'medium'),
                'count': count,
                'positions': filler_positions.get(filler, [])
            })
        
        # Calculate filler score (fewer fillers = higher score)
        filler_score = max(0, 100 - (filler_rate * 10))  # -10 points per 1% filler rate
        
        # Generate suggestions
        suggestions = self._generate_suggestions(filler_details, filler_rate)
        
        return {
            'total_fillers': total_fillers,
            'filler_rate': round(filler_rate, 2),
            'fillers_by_category': fillers_by_category,
            'filler_details': sorted(filler_details, key=lambda x: x['count'], reverse=True),
            'filler_score': round(filler_score, 2),
            'most_common_fillers': all_fillers.most_common(5),
            'suggestions': suggestions
        }
    
    def _get_filler_category(self, filler: str) -> str:
        """Get category for a filler word"""
        for category, data in self.FILLER_PATTERNS.items():
            if filler.lower() in [w.lower() for w in data['words']]:
                return category
        return 'other'
    
    def _generate_suggestions(self, filler_details: List[Dict], filler_rate: float) -> List[str]:
        """Generate suggestions based on filler analysis"""
        suggestions = []
        
        if filler_rate > 10:
            suggestions.append("Your filler word usage is high. Practice pausing silently instead of using 'um' or 'uh'")
        
        # Category-specific suggestions
        categories_present = set(f['category'] for f in filler_details)
        
        if 'hesitation_sounds' in categories_present:
            suggestions.append("Replace 'um' and 'uh' with brief pauses - silence is more powerful")
        
        if 'discourse_markers' in categories_present:
            suggestions.append("Notice when you overuse 'like' or 'basically' - practice speaking without them")
        
        if 'hedge_words' in categories_present:
            suggestions.append("Be more direct - instead of 'I think' or 'kind of', make confident statements")
        
        # Most common filler specific suggestion
        if filler_details:
            top_filler = filler_details[0]
            if top_filler['count'] >= 3:
                suggestions.append(f"You said '{top_filler['word']}' {top_filler['count']} times. Focus on reducing this specific filler.")
        
        if not suggestions:
            suggestions.append("Great job! You use minimal filler words. Keep practicing!")
        
        return suggestions[:4]
    
    def _empty_result(self) -> Dict:
        return {
            'total_fillers': 0,
            'filler_rate': 0.0,
            'fillers_by_category': {},
            'filler_details': [],
            'filler_score': 100.0,
            'most_common_fillers': [],
            'suggestions': ["Speak more to analyze filler word usage"]
        }


class LanguageWeaknessAnalyzer:
    """
    Comprehensive language weakness analyzer combining all three components
    """
    
    def __init__(self):
        self.grammar_checker = GrammarChecker()
        self.vocabulary_analyzer = VocabularyAnalyzer()
        self.filler_detector = FillerWordDetector()
    
    def analyze(self, text: str, audio_duration: float = None) -> Dict:
        """
        Perform comprehensive language analysis
        
        Args:
            text: Transcribed conversation text
            audio_duration: Optional audio duration in seconds
        
        Returns:
            Comprehensive analysis with scores, weaknesses, and suggestions
        """
        if not text.strip():
            return self._empty_analysis()
        
        # Run all analyzers
        grammar_result = self.grammar_checker.check(text)
        vocabulary_result = self.vocabulary_analyzer.analyze(text)
        filler_result = self.filler_detector.detect(text)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(
            grammar_result['grammar_score'],
            vocabulary_result['vocabulary_score'],
            filler_result['filler_score']
        )
        
        # Identify weaknesses
        weaknesses = self._identify_weaknesses(grammar_result, vocabulary_result, filler_result)
        
        # Compile all suggestions
        all_suggestions = self._compile_suggestions(
            grammar_result.get('error_details', []),
            vocabulary_result.get('suggestions', []),
            filler_result.get('suggestions', [])
        )
        
        # Speaking metrics
        word_count = vocabulary_result['word_count']
        wpm = (word_count / audio_duration * 60) if audio_duration and audio_duration > 0 else 0
        
        return {
            'overall_score': round(overall_score, 2),
            'scores': {
                'grammar': grammar_result['grammar_score'],
                'vocabulary': vocabulary_result['vocabulary_score'],
                'filler': filler_result['filler_score'],
                'overall': round(overall_score, 2)
            },
            'grammar_analysis': grammar_result,
            'vocabulary_analysis': vocabulary_result,
            'filler_analysis': filler_result,
            'weaknesses': weaknesses,
            'suggestions': all_suggestions,
            'speaking_metrics': {
                'word_count': word_count,
                'words_per_minute': round(wpm, 2),
                'unique_words': vocabulary_result['unique_words'],
                'vocabulary_level': vocabulary_result['vocabulary_level'],
                'total_grammar_errors': grammar_result['total_errors'],
                'total_fillers': filler_result['total_fillers']
            },
            'strength_areas': self._identify_strengths(grammar_result, vocabulary_result, filler_result)
        }
    
    def _calculate_overall_score(self, grammar_score: float, vocab_score: float, 
                                  filler_score: float) -> float:
        """Calculate weighted overall score"""
        weights = {
            'grammar': 0.40,    # Grammar is most important
            'vocabulary': 0.35, # Vocabulary richness
            'filler': 0.25     # Filler words
        }
        
        return (
            grammar_score * weights['grammar'] +
            vocab_score * weights['vocabulary'] +
            filler_score * weights['filler']
        )
    
    def _identify_weaknesses(self, grammar: Dict, vocabulary: Dict, filler: Dict) -> List[Dict]:
        """Identify key weaknesses based on analysis"""
        weaknesses = []
        
        # Grammar weaknesses
        if grammar['grammar_score'] < 70:
            weakness = {
                'area': 'grammar',
                'severity': 'high' if grammar['grammar_score'] < 50 else 'medium',
                'description': f"Grammar needs improvement ({grammar['total_errors']} errors found)",
                'details': grammar.get('errors_by_category', {})
            }
            weaknesses.append(weakness)
        
        # Vocabulary weaknesses
        if vocabulary['vocabulary_score'] < 60:
            weakness = {
                'area': 'vocabulary',
                'severity': 'high' if vocabulary['vocabulary_score'] < 40 else 'medium',
                'description': f"Limited vocabulary diversity (Level: {vocabulary['vocabulary_level']})",
                'details': {
                    'ttr': vocabulary['type_token_ratio'],
                    'repeated_words': vocabulary['repeated_words']
                }
            }
            weaknesses.append(weakness)
        
        # Filler word weaknesses
        if filler['filler_score'] < 70:
            weakness = {
                'area': 'fluency',
                'severity': 'high' if filler['filler_score'] < 50 else 'medium',
                'description': f"High filler word usage ({filler['total_fillers']} fillers, {filler['filler_rate']}% rate)",
                'details': {
                    'top_fillers': filler['most_common_fillers'],
                    'categories': list(filler['fillers_by_category'].keys())
                }
            }
            weaknesses.append(weakness)
        
        return weaknesses
    
    def _identify_strengths(self, grammar: Dict, vocabulary: Dict, filler: Dict) -> List[str]:
        """Identify areas of strength"""
        strengths = []
        
        if grammar['grammar_score'] >= 85:
            strengths.append("Excellent grammar accuracy")
        elif grammar['grammar_score'] >= 70:
            strengths.append("Good grammatical foundation")
        
        if vocabulary['vocabulary_score'] >= 70:
            strengths.append(f"Rich vocabulary ({vocabulary['vocabulary_level']} level)")
        
        if filler['filler_score'] >= 85:
            strengths.append("Minimal filler word usage - fluent delivery")
        
        if vocabulary['lexical_sophistication'] >= 50:
            strengths.append("Uses advanced vocabulary naturally")
        
        if not strengths:
            strengths.append("Good effort! Keep practicing to build strengths")
        
        return strengths
    
    def _compile_suggestions(self, grammar_errors: List, vocab_suggestions: List, 
                             filler_suggestions: List) -> List[str]:
        """Compile top suggestions from all analyzers"""
        suggestions = []
        
        # Top grammar suggestion
        if grammar_errors:
            categories = Counter(e['category'] for e in grammar_errors)
            top_category = categories.most_common(1)[0][0]
            suggestions.append(f"Focus on improving {top_category.replace('_', ' ')} errors")
        
        # Add vocabulary and filler suggestions
        suggestions.extend(vocab_suggestions[:2])
        suggestions.extend(filler_suggestions[:2])
        
        # Remove duplicates and limit
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s.lower() not in seen:
                seen.add(s.lower())
                unique_suggestions.append(s)
        
        return unique_suggestions[:6]
    
    def _empty_analysis(self) -> Dict:
        return {
            'overall_score': 0,
            'scores': {'grammar': 0, 'vocabulary': 0, 'filler': 100, 'overall': 0},
            'grammar_analysis': self.grammar_checker._empty_result(),
            'vocabulary_analysis': self.vocabulary_analyzer._empty_result(),
            'filler_analysis': self.filler_detector._empty_result(),
            'weaknesses': [{'area': 'speech', 'severity': 'high', 'description': 'No speech detected'}],
            'suggestions': ['Try speaking more during the conversation'],
            'speaking_metrics': {
                'word_count': 0, 'words_per_minute': 0, 'unique_words': 0,
                'vocabulary_level': 'unknown', 'total_grammar_errors': 0, 'total_fillers': 0
            },
            'strength_areas': []
        }


# Singleton instances for easy import
grammar_checker = GrammarChecker()
vocabulary_analyzer = VocabularyAnalyzer()
filler_detector = FillerWordDetector()
language_analyzer = LanguageWeaknessAnalyzer()


# Convenience function
def analyze_conversation(text: str, audio_duration: float = None) -> Dict:
    """
    Analyze a conversation for language weaknesses
    
    Args:
        text: Transcribed text from the conversation
        audio_duration: Optional duration in seconds
    
    Returns:
        Comprehensive analysis dictionary
    """
    return language_analyzer.analyze(text, audio_duration)
