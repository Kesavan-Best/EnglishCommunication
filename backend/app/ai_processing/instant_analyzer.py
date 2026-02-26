"""
Instant AI Analysis Generator
Provides feedback based on ACTUAL conversation transcript - NO FAKE DATA
"""
import re
from typing import Dict, List
from datetime import datetime

class InstantAnalyzer:
    """Generate AI feedback based on actual transcript analysis only"""
    
    # Topic categories with reading content
    TOPICS = {
        "daily_conversation": {
            "name": "Daily Conversation",
            "description": "Improve your everyday English communication skills",
            "reading_content": """
## Daily Conversation Tips

### Greetings and Small Talk
- "How's it going?" - Casual greeting
- "What have you been up to?" - Ask about recent activities
- "Nice weather we're having!" - Weather small talk

### Expressing Opinions
- "I think that..." / "In my opinion..."
- "I agree/disagree because..."
- "That's an interesting point."

### Active Listening
- "That's interesting, tell me more."
- "I see what you mean."
- "Could you explain that further?"

### Practice Exercise
Try having a 5-minute conversation about:
- Your weekend plans
- A recent movie or TV show
- Your hobbies or interests
            """,
            "quiz": [
                {
                    "question": "Which phrase is best for casual greetings?",
                    "options": ["How's it going?", "To whom it may concern", "Greetings sir", "Hello formal"],
                    "correct": 0,
                    "explanation": "'How's it going?' is a friendly, casual greeting perfect for daily conversations."
                },
                {
                    "question": "What's a good way to show you're listening actively?",
                    "options": ["Stay silent", "Change the topic", "Say 'That's interesting, tell me more'", "Look at your phone"],
                    "correct": 2,
                    "explanation": "Active listening phrases encourage the speaker and show engagement."
                },
                {
                    "question": "How do you politely express disagreement?",
                    "options": ["You're wrong", "I disagree because...", "That's stupid", "Never"],
                    "correct": 1,
                    "explanation": "'I disagree because...' is polite and provides reasoning for your viewpoint."
                }
            ]
        },
        "business_english": {
            "name": "Business English",
            "description": "Professional communication for workplace success",
            "reading_content": """
## Business English Essentials

### Professional Emails
- Subject line: Clear and specific
- Greeting: "Dear [Name]" or "Hello [Name]"
- Body: Concise and professional
- Closing: "Best regards," / "Sincerely,"

### Meeting Phrases
- "Let's schedule a meeting to discuss..."
- "Could we arrange a call next week?"
- "I'd like to follow up on..."
- "Thank you for your time."

### Presentations
- Opening: "Today, I'll be discussing..."
- Transitions: "Moving on to..." / "Let's look at..."
- Conclusion: "To summarize..." / "In conclusion..."

### Networking
- "What do you do?" / "What's your role?"
- "I work in [industry/field]"
- "Let's stay in touch."
            """,
            "quiz": [
                {
                    "question": "What's the best way to start a professional email?",
                    "options": ["Hey!", "Dear [Name],", "Yo", "What's up"],
                    "correct": 1,
                    "explanation": "'Dear [Name],' is professional and appropriate for business emails."
                },
                {
                    "question": "In a meeting, how do you politely transition topics?",
                    "options": ["Next!", "Moving on to...", "Forget that", "Whatever"],
                    "correct": 1,
                    "explanation": "'Moving on to...' is a professional way to transition between topics."
                },
                {
                    "question": "What's appropriate networking small talk?",
                    "options": ["What's your salary?", "What do you do?", "Are you married?", "How old are you?"],
                    "correct": 1,
                    "explanation": "Asking about someone's profession is standard and appropriate networking conversation."
                }
            ]
        },
        "pronunciation": {
            "name": "Pronunciation Practice",
            "description": "Improve clarity and reduce accent challenges",
            "reading_content": """
## Pronunciation Improvement Guide

### Common Problem Sounds
- **TH sounds**: "think" (θ) vs "this" (ð)
  - Practice: "I think this thing is thick"
  
- **R vs L**: Many learners confuse these
  - Practice: "really, rally, rarely"
  
- **V vs W**: Important distinction
  - Practice: "very well, we will"

### Word Stress Patterns
English uses stress for meaning:
- REcord (noun) vs reCORD (verb)
- PREsent (noun) vs preSENT (verb)

### Sentence Rhythm
English has a rhythm pattern:
- STRONG words: nouns, verbs, adjectives
- weak words: articles, prepositions

### Practice Exercises
Record yourself saying:
1. "The thoughtful therapist thinks thoroughly"
2. "Really rare red roses"
3. "Very well viewed videos"
4. "She SELLS seaSHELLS by the SEAshore"
            """,
            "quiz": [
                {
                    "question": "What's the difference between 'sink' and 'think'?",
                    "options": ["No difference", "The 'th' sound", "The vowel", "The stress"],
                    "correct": 1,
                    "explanation": "The 'th' sound (θ) in 'think' vs 's' sound in 'sink' is crucial."
                },
                {
                    "question": "Where is the stress in 'REcord' (noun)?",
                    "options": ["Second syllable", "First syllable", "Both equal", "No stress"],
                    "correct": 1,
                    "explanation": "REcord (noun) has stress on the first syllable, unlike reCORD (verb)."
                },
                {
                    "question": "Which words get strong stress in English sentences?",
                    "options": ["Articles", "Prepositions", "Nouns and verbs", "All words equally"],
                    "correct": 2,
                    "explanation": "Content words (nouns, verbs, adjectives) receive strong stress in English."
                }
            ]
        },
        "grammar": {
            "name": "Grammar Fundamentals",
            "description": "Master essential English grammar rules",
            "reading_content": """
## Essential Grammar Rules

### Present Perfect vs Simple Past
- **Simple Past**: Finished action with specific time
  - "I went to Paris last year"
  
- **Present Perfect**: Connection to present, no specific time
  - "I have been to Paris" (experience)
  - "I have lived here for 5 years" (continuing)

### Articles (a, an, the)
- **a/an**: First mention, one of many
  - "I saw a dog" (any dog)
  
- **the**: Specific, already mentioned
  - "The dog was friendly" (that specific dog)

### Common Mistakes
❌ "I am living here since 2020"
✅ "I have lived here since 2020"

❌ "I have went yesterday"
✅ "I went yesterday"
            """,
            "quiz": [
                {
                    "question": "Which is correct?",
                    "options": ["I live here since 2020", "I have lived here since 2020", "I am living here since 2020", "I lived here since 2020"],
                    "correct": 1,
                    "explanation": "Present perfect (have lived) is used with 'since' for continuing actions."
                },
                {
                    "question": "When do we use 'the'?",
                    "options": ["Always with nouns", "For specific things", "Never", "Only for plural"],
                    "correct": 1,
                    "explanation": "'The' is used for specific nouns that are already known to the listener."
                },
                {
                    "question": "Complete: 'If I ___ a million dollars, I would buy a house'",
                    "options": ["have", "had", "will have", "having"],
                    "correct": 1,
                    "explanation": "Second conditional uses 'if + past simple' for unreal present situations."
                }
            ]
        },
        "vocabulary": {
            "name": "Vocabulary Building",
            "description": "Expand your English word bank effectively",
            "reading_content": """
## Vocabulary Expansion Strategies

### Word Families
Learn related words together:
- **decide** (verb) → decision (noun) → decisive (adj)
- **success** (noun) → succeed (verb) → successful (adj)

### Collocations
Words that naturally go together:
- **Make**: make a decision, make progress, make sense
- **Do**: do homework, do business, do your best
- **Take**: take a break, take time, take notes

### Synonyms for Common Words
Instead of "good":
- excellent, outstanding, remarkable, superb

Instead of "bad":
- poor, terrible, awful, dreadful
            """,
            "quiz": [
                {
                    "question": "What's the adjective form of 'analyze'?",
                    "options": ["analyzation", "analytical", "analyzable", "analyzer"],
                    "correct": 1,
                    "explanation": "'Analytical' is the adjective form, meaning 'using careful analysis'."
                },
                {
                    "question": "Which collocation is correct?",
                    "options": ["make homework", "do homework", "take homework", "get homework"],
                    "correct": 1,
                    "explanation": "'Do homework' is the correct collocation in English."
                },
                {
                    "question": "What's a synonym for 'good' in formal writing?",
                    "options": ["nice", "cool", "excellent", "okay"],
                    "correct": 2,
                    "explanation": "'Excellent' is a formal, sophisticated alternative to 'good'."
                }
            ]
        },
        "fluency": {
            "name": "Speaking Fluency",
            "description": "Speak more naturally and confidently",
            "reading_content": """
## Fluency Enhancement Tips

### Reduce Filler Words
Common fillers to avoid:
- "um", "uh", "like", "you know", "I mean"

**Strategies:**
1. Pause instead of filling
2. Slow down your speech
3. Think before speaking

### Linking Words
Connect ideas smoothly:
- **Addition**: furthermore, moreover, in addition
- **Contrast**: however, on the other hand, nevertheless
- **Example**: for instance, such as, for example
- **Result**: therefore, consequently, as a result

### Natural Expressions
- "I know what you mean" (understanding)
- "That makes sense" (agreement)
- "I see where you're coming from" (empathy)
            """,
            "quiz": [
                {
                    "question": "What's the best strategy when you need time to think?",
                    "options": ["Say 'um' repeatedly", "Stay silent for 30 seconds", "Say 'That's a great question...'", "Change the topic"],
                    "correct": 2,
                    "explanation": "Natural time-buying phrases are better than silence or filler words."
                },
                {
                    "question": "Which linking word shows contrast?",
                    "options": ["furthermore", "however", "for example", "therefore"],
                    "correct": 1,
                    "explanation": "'However' indicates a contrast or opposing idea."
                },
                {
                    "question": "How can you naturally keep a conversation going?",
                    "options": ["Repeat yourself", "Give examples and elaborate", "Talk faster", "Use more filler words"],
                    "correct": 1,
                    "explanation": "Providing examples and elaborating keeps conversations flowing naturally."
                }
            ]
        }
    }
    
    # Common filler words to detect
    FILLER_WORDS = ['um', 'uh', 'uhm', 'like', 'you know', 'i mean', 'so like', 'basically', 'actually', 'literally']
    
    # Grammar patterns to check
    GRAMMAR_ISSUES = {
        r'\bi am\b.+\bsince\b': 'Consider using present perfect with "since" (e.g., "I have been" instead of "I am")',
        r'\bhave went\b': 'Use "have gone" instead of "have went"',
        r'\bmore better\b': 'Use either "more" or "better", not both',
        r'\bdon\'t has\b|\bdoesn\'t has\b': 'Use "have" after "don\'t", "has" after "doesn\'t"',
        r'\bI goed\b': 'Use "I went" instead of "I goed"',
        r'\bmore bigger\b|\bmore smaller\b': 'Remove "more" before comparative adjectives ending in -er',
    }
    
    def analyze_transcript(self, transcript: str) -> Dict:
        """
        Analyze actual transcript text for language issues
        Returns specific issues found, not random ones
        """
        if not transcript or len(transcript.strip()) < 10:
            return {
                "word_count": 0,
                "filler_words": [],
                "filler_count": 0,
                "grammar_issues": [],
                "vocabulary_stats": {},
                "strengths": [],
                "weaknesses": []
            }
        
        transcript_lower = transcript.lower()
        words = transcript.split()
        word_count = len(words)
        
        # Count filler words
        filler_words_found = []
        for filler in self.FILLER_WORDS:
            count = transcript_lower.count(filler)
            if count > 0:
                filler_words_found.append({"word": filler, "count": count})
        
        filler_count = sum(f["count"] for f in filler_words_found)
        
        # Check for grammar issues
        grammar_issues_found = []
        for pattern, suggestion in self.GRAMMAR_ISSUES.items():
            if re.search(pattern, transcript_lower):
                grammar_issues_found.append(suggestion)
        
        # Vocabulary analysis
        unique_words = set(w.lower().strip('.,!?;:') for w in words if len(w) > 2)
        vocabulary_ratio = len(unique_words) / word_count if word_count > 0 else 0
        
        # Sentence structure
        sentences = re.split(r'[.!?]+', transcript)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)
        avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
        
        # Determine strengths based on actual analysis
        strengths = []
        if word_count >= 50:
            strengths.append("Good speaking participation - you contributed substantially to the conversation")
        if vocabulary_ratio >= 0.5:
            strengths.append("Good vocabulary variety - you used diverse words")
        if filler_count < 3:
            strengths.append("Fluent speech - minimal filler words used")
        if sentence_count >= 3 and 5 <= avg_sentence_length <= 20:
            strengths.append("Well-structured sentences - good sentence length and variety")
        
        # Determine weaknesses based on actual findings
        weaknesses = []
        
        # Filler word weakness
        if filler_count >= 3:
            filler_list = ", ".join(f['word'] for f in filler_words_found[:3])
            weaknesses.append({
                "category": "fluency",
                "title": "Filler Words Detected",
                "description": f"Found {filler_count} filler words in your speech ({filler_list})",
                "tip": "Try pausing briefly instead of using filler words. This sounds more confident and professional."
            })
        
        # Grammar weakness
        if grammar_issues_found:
            weaknesses.append({
                "category": "grammar",
                "title": "Grammar Patterns to Review",
                "description": grammar_issues_found[0],
                "tip": "Review the grammar rule and practice using it correctly in sentences."
            })
        
        # Vocabulary weakness
        if vocabulary_ratio < 0.4 and word_count >= 30:
            weaknesses.append({
                "category": "vocabulary",
                "title": "Vocabulary Variety",
                "description": "Consider using more varied vocabulary - some words were repeated frequently",
                "tip": "Try learning synonyms for common words you use often."
            })
        
        # Short responses weakness
        if word_count < 30 and sentence_count < 3:
            weaknesses.append({
                "category": "confidence",
                "title": "Brief Responses",
                "description": "Your responses were quite short",
                "tip": "Try elaborating more on your thoughts - give examples, share opinions, ask follow-up questions."
            })
        
        return {
            "word_count": word_count,
            "filler_words": filler_words_found,
            "filler_count": filler_count,
            "grammar_issues": grammar_issues_found,
            "vocabulary_stats": {
                "unique_words": len(unique_words),
                "vocabulary_ratio": round(vocabulary_ratio, 2),
                "sentence_count": sentence_count,
                "avg_sentence_length": round(avg_sentence_length, 1)
            },
            "strengths": strengths,
            "weaknesses": weaknesses
        }
    
    def generate_instant_feedback(self, duration_seconds: int, user_id: str, transcript: str = None, conversation: list = None) -> Dict:
        """
        Generate AI feedback based ONLY on actual transcript data
        NO random/fake feedback - only real analysis
        
        Args:
            duration_seconds: Call duration in seconds
            user_id: User ID
            transcript: User's actual transcript text
            conversation: Full conversation array
            
        Returns:
            Real AI feedback based on actual speech, or clear message if no data
        """
        
        # Check if we have actual transcript data
        has_transcript = transcript and len(transcript.strip()) > 10
        
        if not has_transcript:
            # No transcript = no fake feedback, just a clear message
            return {
                "ai_rating": None,  # No rating without data
                "overall_message": "No speech data was captured for analysis. To get AI feedback, make sure you're speaking clearly during the call and your microphone is working.",
                "strengths": [],
                "weaknesses": [],
                "recommended_topics": [self._get_topic_data("daily_conversation")],
                "generated_at": datetime.utcnow().isoformat(),
                "analysis_version": "instant_v3_real_only",
                "transcript_analyzed": False,
                "no_data_reason": "No transcript captured during the call"
            }
        
        # Analyze the actual transcript
        analysis = self.analyze_transcript(transcript)
        
        # Calculate rating based on REAL metrics
        rating = self._calculate_real_rating(analysis, duration_seconds)
        
        # Generate message based on actual analysis
        overall_message = self._generate_real_message(analysis, rating, duration_seconds)
        
        # Get recommended topics based on actual weaknesses found
        recommended_topics = self._get_relevant_topics(analysis["weaknesses"])
        
        return {
            "ai_rating": rating,
            "overall_message": overall_message,
            "strengths": analysis["strengths"] if analysis["strengths"] else ["Participated in the conversation"],
            "weaknesses": analysis["weaknesses"],
            "recommended_topics": recommended_topics,
            "generated_at": datetime.utcnow().isoformat(),
            "analysis_version": "instant_v3_real_only",
            "transcript_analyzed": True,
            "transcript_stats": {
                "word_count": analysis["word_count"],
                "filler_count": analysis["filler_count"],
                "vocabulary_ratio": analysis["vocabulary_stats"].get("vocabulary_ratio", 0)
            }
        }
    
    def _calculate_real_rating(self, analysis: Dict, duration_seconds: int) -> float:
        """Calculate rating based on actual metrics, not random"""
        
        word_count = analysis["word_count"]
        filler_count = analysis["filler_count"]
        vocab_ratio = analysis["vocabulary_stats"].get("vocabulary_ratio", 0)
        grammar_issues = len(analysis["grammar_issues"])
        
        # Start with base rating
        rating = 5.0
        
        # Word count contribution (more words = more engagement)
        if word_count >= 100:
            rating += 1.5
        elif word_count >= 50:
            rating += 1.0
        elif word_count >= 20:
            rating += 0.5
        elif word_count < 10:
            rating -= 1.0
        
        # Vocabulary variety bonus
        if vocab_ratio >= 0.6:
            rating += 1.0
        elif vocab_ratio >= 0.5:
            rating += 0.5
        elif vocab_ratio < 0.3:
            rating -= 0.5
        
        # Filler word penalty
        filler_ratio = filler_count / word_count if word_count > 0 else 0
        if filler_ratio > 0.1:  # More than 10% fillers
            rating -= 1.0
        elif filler_ratio > 0.05:  # More than 5% fillers
            rating -= 0.5
        elif filler_count == 0:
            rating += 0.5
        
        # Grammar issues penalty
        if grammar_issues > 2:
            rating -= 1.0
        elif grammar_issues > 0:
            rating -= 0.5
        
        # Duration bonus (longer calls = more practice)
        if duration_seconds >= 180:  # 3+ minutes
            rating += 0.5
        elif duration_seconds < 60:  # Less than 1 minute
            rating -= 0.5
        
        # Clamp to valid range
        return round(max(1.0, min(10.0, rating)), 1)
    
    def _generate_real_message(self, analysis: Dict, rating: float, duration_seconds: int) -> str:
        """Generate feedback message based on actual analysis"""
        
        word_count = analysis["word_count"]
        weakness_count = len(analysis["weaknesses"])
        strength_count = len(analysis["strengths"])
        
        if rating >= 8.0:
            base = "Excellent conversation! Your English communication was strong."
        elif rating >= 6.5:
            base = "Good job! You communicated effectively."
        elif rating >= 5.0:
            base = "Nice effort! You're making progress."
        else:
            base = "Keep practicing! Regular conversations will help you improve."
        
        # Add specific observations
        details = []
        
        if word_count >= 50:
            details.append(f"You contributed {word_count} words to the conversation.")
        elif word_count > 0:
            details.append(f"Try to speak more - you only said about {word_count} words.")
        
        if weakness_count > 0:
            details.append(f"We found {weakness_count} area(s) to work on.")
        
        if strength_count > 0:
            details.append(f"You showed {strength_count} strength(s) in your speech.")
        
        return base + " " + " ".join(details)
    
    def _get_relevant_topics(self, weaknesses: List[Dict]) -> List[Dict]:
        """Get topics relevant to actual weaknesses found"""
        
        topic_mapping = {
            "grammar": "grammar",
            "fluency": "fluency",
            "vocabulary": "vocabulary",
            "confidence": "daily_conversation",
            "pronunciation": "pronunciation"
        }
        
        recommended = []
        added_keys = set()
        
        # Add topics based on actual weaknesses
        for weakness in weaknesses:
            category = weakness.get("category", "")
            topic_key = topic_mapping.get(category, "daily_conversation")
            
            if topic_key not in added_keys:
                recommended.append(self._get_topic_data(topic_key))
                added_keys.add(topic_key)
        
        # If no weaknesses found, recommend general practice
        if not recommended:
            recommended.append(self._get_topic_data("daily_conversation"))
        
        # Limit to 3 topics
        return recommended[:3]
    
    def _get_topic_data(self, topic_key: str) -> Dict:
        """Get full topic data by key"""
        
        if topic_key not in self.TOPICS:
            topic_key = "daily_conversation"
        
        topic_data = self.TOPICS[topic_key]
        return {
            "key": topic_key,
            "name": topic_data["name"],
            "description": topic_data["description"],
            "reading_content": topic_data["reading_content"],
            "quiz": topic_data["quiz"]
        }
    
    def get_all_topics(self) -> List[Dict]:
        """Get all available topics for browsing"""
        topics = []
        for key, data in self.TOPICS.items():
            topics.append({
                "key": key,
                "name": data["name"],
                "description": data["description"],
                "has_reading": True,
                "has_quiz": True,
                "quiz_questions": len(data["quiz"])
            })
        return topics
    
    def get_topic_details(self, topic_key: str) -> Dict:
        """Get full details for a specific topic"""
        if topic_key not in self.TOPICS:
            return None
        
        topic_data = self.TOPICS[topic_key]
        return {
            "key": topic_key,
            "name": topic_data["name"],
            "description": topic_data["description"],
            "reading_content": topic_data["reading_content"],
            "quiz": topic_data["quiz"]
        }


# Global instance
instant_analyzer = InstantAnalyzer()
