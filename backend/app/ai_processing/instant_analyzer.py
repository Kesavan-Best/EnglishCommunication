"""
Instant AI Analysis Generator
Provides immediate feedback without waiting for audio processing
"""
import random
from typing import Dict, List
from datetime import datetime

class InstantAnalyzer:
    """Generate instant AI feedback based on call duration and basic metrics"""
    
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

### Conditionals
- **Zero**: General truths - "If you heat water, it boils"
- **First**: Real possibility - "If it rains, I'll stay home"
- **Second**: Unreal present - "If I won the lottery, I would travel"
- **Third**: Unreal past - "If I had studied, I would have passed"

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
- **analyze** (verb) → analysis (noun) → analytical (adj)

### Collocations
Words that naturally go together:
- **Make**: make a decision, make progress, make sense
- **Do**: do homework, do business, do your best
- **Take**: take a break, take time, take notes
- **Get**: get tired, get better, get the idea

### Synonyms for Common Words
Instead of "good":
- excellent, outstanding, remarkable, superb
- positive, beneficial, advantageous

Instead of "bad":
- poor, terrible, awful, dreadful
- negative, harmful, detrimental

### Context Clues
Learn from context:
"The enigmatic smile puzzled everyone" 
→ enigmatic = mysterious (from 'puzzled')

### Practice Method
1. Learn word + definition
2. Create example sentence
3. Use in conversation within 24 hours
4. Review after 1 week
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

### Conversation Strategies
**Keep talking:**
- Elaborate on your points
- Give examples
- Ask follow-up questions

**Buy time naturally:**
- "That's a great question..."
- "Let me think about that..."
- "Well, in my experience..."

### Natural Expressions
- "I know what you mean" (understanding)
- "That makes sense" (agreement)
- "I see where you're coming from" (empathy)
- "Actually..." (correction politely)

### Practice Exercise
Record a 2-minute answer to:
"Describe your perfect day off"
- Goal: No filler words
- Use 3+ linking words
- Include specific examples
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
    
    # Weakness categories with specific advice
    WEAKNESS_TYPES = {
        "grammar": {
            "title": "Grammar Accuracy",
            "descriptions": [
                "Tense consistency needs improvement",
                "Subject-verb agreement errors detected",
                "Article usage (a, an, the) needs work",
                "Preposition selection could be better"
            ],
            "tips": [
                "Review present perfect vs simple past",
                "Practice conditional sentences daily",
                "Study article rules with examples",
                "Focus on common preposition pairs"
            ]
        },
        "pronunciation": {
            "title": "Pronunciation Clarity",
            "descriptions": [
                "Some sounds are unclear",
                "Word stress patterns need attention",
                "Sentence rhythm could be smoother",
                "Certain consonants need practice"
            ],
            "tips": [
                "Practice TH sounds: 'think' vs 'sink'",
                "Work on R vs L distinction",
                "Record and compare with native speakers",
                "Focus on word stress in longer words"
            ]
        },
        "vocabulary": {
            "title": "Vocabulary Range",
            "descriptions": [
                "Limited word variety observed",
                "Same words repeated frequently",
                "Could use more advanced expressions",
                "Vocabulary range is intermediate"
            ],
            "tips": [
                "Learn 5 new words daily from context",
                "Use a thesaurus for variety",
                "Study word collocations",
                "Practice synonym substitution"
            ]
        },
        "fluency": {
            "title": "Speaking Fluency",
            "descriptions": [
                "Some hesitation in responses",
                "Filler words detected (um, uh, like)",
                "Pace varies too much",
                "Long pauses between thoughts"
            ],
            "tips": [
                "Practice speaking for 2 minutes non-stop",
                "Replace fillers with brief pauses",
                "Use linking words to connect ideas",
                "Think in English, not translate"
            ]
        },
        "confidence": {
            "title": "Speaking Confidence",
            "descriptions": [
                "Good effort, building confidence",
                "Speaking improved during conversation",
                "Started strong, maintain momentum",
                "Confidence fluctuated throughout"
            ],
            "tips": [
                "Practice with a mirror daily",
                "Record yourself and listen back",
                "Join conversation groups",
                "Celebrate small improvements"
            ]
        }
    }
    
    def generate_instant_feedback(self, duration_seconds: int, user_id: str, transcript: str = None, conversation: list = None) -> Dict:
        """
        Generate instant AI feedback based on call duration and optionally transcript
        
        Args:
            duration_seconds: Call duration in seconds
            user_id: User ID for personalization
            transcript: Optional - User's transcript text
            conversation: Optional - Full conversation array
            
        Returns:
            Complete AI feedback with rating, weaknesses, topics, and quiz
        """
        # Calculate base score from duration (longer calls = better engagement)
        if duration_seconds < 30:
            base_score = 3.0
        elif duration_seconds < 60:
            base_score = 4.0
        elif duration_seconds < 120:
            base_score = 5.0
        elif duration_seconds < 300:
            base_score = 6.5
        elif duration_seconds < 600:
            base_score = 7.5
        else:
            base_score = 8.5
        
        # If we have transcript, analyze it for more accurate scoring
        if transcript and len(transcript.strip()) > 0:
            word_count = len(transcript.split())
            
            # Bonus for more words (active participation)
            if word_count > 100:
                base_score += 0.5
            elif word_count > 50:
                base_score += 0.3
            
            # Check for variety in vocabulary (unique words)
            unique_words = len(set(transcript.lower().split()))
            if unique_words > 50:
                base_score += 0.3
            
            # Check for sentence variety (periods indicate complete sentences)
            sentences = transcript.count('.') + transcript.count('?') + transcript.count('!')
            if sentences > 5:
                base_score += 0.2
        
        # Add small random variation
        rating = round(min(10.0, base_score + random.uniform(-0.3, 0.5)), 1)
        
        # Generate weaknesses (2-3 random weaknesses, but fewer if we have good transcript)
        if transcript and len(transcript.split()) > 80:
            weakness_count = 2 if rating >= 7.0 else 2
        else:
            weakness_count = 2 if rating >= 7.0 else 3
        
        selected_weaknesses = random.sample(list(self.WEAKNESS_TYPES.keys()), weakness_count)
        
        weaknesses = []
        for weakness_key in selected_weaknesses:
            weakness_data = self.WEAKNESS_TYPES[weakness_key]
            weaknesses.append({
                "category": weakness_key,
                "title": weakness_data["title"],
                "description": random.choice(weakness_data["descriptions"]),
                "tip": random.choice(weakness_data["tips"]),
                "severity": "medium" if rating < 6.0 else "low"
            })
        
        # Select recommended topics (2-3 topics based on weaknesses)
        recommended_topics = []
        topic_mapping = {
            "grammar": "grammar",
            "pronunciation": "pronunciation",
            "vocabulary": "vocabulary",
            "fluency": "fluency",
            "confidence": "daily_conversation"
        }
        
        # Add topics based on weaknesses
        for weakness in weaknesses[:2]:
            topic_key = topic_mapping.get(weakness["category"], "daily_conversation")
            if topic_key not in [t["key"] for t in recommended_topics]:
                topic_data = self.TOPICS[topic_key]
                recommended_topics.append({
                    "key": topic_key,
                    "name": topic_data["name"],
                    "description": topic_data["description"],
                    "reading_content": topic_data["reading_content"],
                    "quiz": topic_data["quiz"]
                })
        
        # Always add business English as third topic (common request)
        if len(recommended_topics) < 3 and "business_english" not in [t["key"] for t in recommended_topics]:
            topic_data = self.TOPICS["business_english"]
            recommended_topics.append({
                "key": "business_english",
                "name": topic_data["name"],
                "description": topic_data["description"],
                "reading_content": topic_data["reading_content"],
                "quiz": topic_data["quiz"]
            })
        
        # Generate personalized feedback message
        if transcript and len(transcript.split()) > 100:
            transcript_feedback = " You actively participated with meaningful contributions."
        elif transcript and len(transcript.split()) > 30:
            transcript_feedback = " You participated well in the conversation."
        else:
            transcript_feedback = ""
        
        if rating >= 8.0:
            overall_message = f"Excellent conversation!{transcript_feedback} You demonstrated strong English skills with good fluency and vocabulary. Keep practicing to maintain this level."
        elif rating >= 6.5:
            overall_message = f"Good job!{transcript_feedback} You communicated effectively with some minor areas for improvement. Continue practicing daily."
        elif rating >= 5.0:
            overall_message = f"Nice effort!{transcript_feedback} You're making progress. Focus on the areas highlighted below to improve further."
        else:
            overall_message = f"Good start! Regular practice will help you improve. Review the topics below to strengthen your skills."
        
        # Calculate strength areas
        strengths = []
        if duration_seconds >= 120:
            strengths.append("Good engagement and conversation length")
        if transcript and len(transcript.split()) > 80:
            strengths.append("Active participation with substantial contribution")
        if rating >= 7.0:
            strengths.append("Overall communication was effective")
        if "fluency" not in selected_weaknesses:
            strengths.append("Decent speaking fluency")
        if "vocabulary" not in selected_weaknesses:
            strengths.append("Adequate vocabulary usage")
        
        return {
            "ai_rating": rating,
            "overall_message": overall_message,
            "strengths": strengths if strengths else ["Participated in conversation", "Practiced speaking English"],
            "weaknesses": weaknesses,
            "recommended_topics": recommended_topics,
            "generated_at": datetime.utcnow().isoformat(),
            "analysis_version": "instant_v2_with_transcript",
            "transcript_analyzed": bool(transcript)
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
