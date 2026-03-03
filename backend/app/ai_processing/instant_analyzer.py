"""
Instant AI Analysis Generator
Provides feedback based on ACTUAL conversation transcript - NO FAKE DATA
Uses LanguageTool-style grammar checking, WordNet-style vocabulary analysis, and filler detection
"""
import re
from typing import Dict, List
from datetime import datetime
from collections import Counter

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
    
    # Common filler words to detect (comprehensive list)
    FILLER_WORDS = [
        'um', 'uh', 'uhm', 'umm', 'uhh', 'hmm',
        'like', 'you know', 'i mean', 'so like', 'basically', 'actually', 'literally',
        'kind of', 'sort of', 'right', 'okay so', 'well like', 'i guess',
        'you see', 'to be honest', 'at the end of the day', 'in a way'
    ]
    
    # Grammar patterns to check (LanguageTool-style)
    GRAMMAR_ISSUES = {
        r'\bi am\b.+\bsince\b': 'Use present perfect with "since" (e.g., "I have been" instead of "I am")',
        r'\bhave went\b': 'Use "have gone" instead of "have went"',
        r'\bmore better\b': 'Use either "more" or "better", not both (double comparative)',
        r'\bdon\'t has\b|\bdoesn\'t has\b': 'Use "have" after "don\'t"; "has" only with "doesn\'t"',
        r'\bI goed\b': 'Use "I went" instead of "I goed" (irregular past tense)',
        r'\bmore bigger\b|\bmore smaller\b|\bmore faster\b|\bmore slower\b': 'Remove "more" before comparative adjectives ending in -er',
        r'\bhe don\'t\b|\bshe don\'t\b|\bit don\'t\b': 'Use "doesn\'t" with he/she/it (third person singular)',
        r'\bthey was\b|\bwe was\b': 'Use "were" with they/we (subject-verb agreement)',
        r'\bi has\b': 'Use "I have" instead of "I has"',
        r'\bcould of\b|\bshould of\b|\bwould of\b': 'Use "could have" / "should have" / "would have" (not "of")',
        r'\bmuch\s+\w+s\b': 'Use "many" instead of "much" with countable nouns',
        r'\bless\s+\w+s\b': 'Use "fewer" instead of "less" with countable nouns',
        r'\bme and\b.+\b(went|go|are|is|was|were)\b': 'Put yourself last: "X and I" (not "me and X") as subject',
        r'\bdid\s+\w+ed\b': 'Don\'t use past tense after "did" (e.g., "did go" not "did went")',
        r'\btheir\s+is\b|\btheir\s+was\b': 'Did you mean "there is" / "there was"?',
        r'\byour\s+welcome\b': 'Use "you\'re welcome" (you are welcome)',
        r'\bits\s+a\s+\w+\s+then\b': 'Did you mean "than" (comparison) instead of "then"?',
        r'\bi\s+seen\b': 'Use "I saw" (simple past) or "I have seen" (present perfect)',
        r'\bwent\s+to\s+went\b': 'Repeated word: "went to went"',
    }
    
    # Word synonyms for vocabulary richness (WordNet-style)
    COMMON_WORDS_WITH_ALTERNATIVES = {
        'good': ['excellent', 'outstanding', 'remarkable', 'superb', 'wonderful'],
        'bad': ['poor', 'terrible', 'awful', 'dreadful', 'unsatisfactory'],
        'big': ['large', 'enormous', 'substantial', 'immense', 'massive'],
        'small': ['tiny', 'compact', 'miniature', 'modest', 'petite'],
        'happy': ['delighted', 'thrilled', 'content', 'pleased', 'joyful'],
        'sad': ['unhappy', 'melancholy', 'disheartened', 'gloomy', 'sorrowful'],
        'nice': ['pleasant', 'delightful', 'agreeable', 'lovely', 'charming'],
        'said': ['stated', 'mentioned', 'expressed', 'remarked', 'commented'],
        'think': ['believe', 'consider', 'suppose', 'reckon', 'assume'],
        'very': ['extremely', 'incredibly', 'remarkably', 'exceptionally', 'significantly'],
        'thing': ['item', 'object', 'element', 'aspect', 'matter'],
        'get': ['obtain', 'acquire', 'receive', 'gain', 'retrieve'],
        'make': ['create', 'produce', 'construct', 'generate', 'develop'],
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
        
        # Vocabulary richness: check for overuse of common words
        word_freq = Counter(w.lower().strip('.,!?;:') for w in words if len(w) > 2)
        overused_words = []
        vocabulary_suggestions = []
        for word, count in word_freq.most_common(10):
            if count >= 3 and word in self.COMMON_WORDS_WITH_ALTERNATIVES:
                overused_words.append({"word": word, "count": count})
                alts = self.COMMON_WORDS_WITH_ALTERNATIVES[word][:3]
                vocabulary_suggestions.append({
                    "overused": word,
                    "count": count,
                    "alternatives": alts,
                    "suggestion": f"Instead of '{word}' (used {count} times), try: {', '.join(alts)}"
                })
        
        # Sentence complexity: check for variety
        short_sentences = sum(1 for s in sentences if len(s.split()) <= 5)
        long_sentences = sum(1 for s in sentences if len(s.split()) >= 15)
        
        # Determine strengths based on actual analysis
        strengths = []
        if word_count >= 100:
            strengths.append("Excellent speaking participation - you contributed substantially to the conversation")
        elif word_count >= 50:
            strengths.append("Good speaking participation - you were actively engaged")
        if vocabulary_ratio >= 0.6:
            strengths.append("Rich vocabulary variety - you used diverse and expressive words")
        elif vocabulary_ratio >= 0.5:
            strengths.append("Good vocabulary variety - you used reasonably diverse words")
        if filler_count == 0:
            strengths.append("Very fluent speech - no filler words detected!")
        elif filler_count <= 2:
            strengths.append("Fluent speech - minimal filler words used")
        if sentence_count >= 5 and 5 <= avg_sentence_length <= 20:
            strengths.append("Well-structured sentences with good length and variety")
        if len(grammar_issues_found) == 0 and word_count >= 30:
            strengths.append("Clean grammar - no common grammatical errors detected")
        if long_sentences >= 2:
            strengths.append("Good use of complex sentences - shows advanced speaking ability")
        
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
        
        # Vocabulary suggestions weakness
        if vocabulary_suggestions:
            top_suggestion = vocabulary_suggestions[0]
            weaknesses.append({
                "category": "vocabulary",
                "title": f"Overuse of '{top_suggestion['overused']}'",
                "description": top_suggestion["suggestion"],
                "tip": f"Expand your word choice. Instead of '{top_suggestion['overused']}', try using words like {', '.join(top_suggestion['alternatives'])}."
            })
        
        # Short responses weakness
        if word_count < 30 and sentence_count < 3:
            weaknesses.append({
                "category": "confidence",
                "title": "Brief Responses",
                "description": "Your responses were quite short",
                "tip": "Try elaborating more on your thoughts - give examples, share opinions, ask follow-up questions."
            })
        
        # Sentence complexity weakness
        if sentence_count >= 3 and short_sentences / sentence_count > 0.7:
            weaknesses.append({
                "category": "grammar",
                "title": "Sentence Complexity",
                "description": "Most of your sentences were short and simple",
                "tip": "Try using linking words (however, therefore, although) to combine ideas into longer, more complex sentences."
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
                "avg_sentence_length": round(avg_sentence_length, 1),
                "overused_words": overused_words,
                "vocabulary_suggestions": vocabulary_suggestions
            },
            "strengths": strengths,
            "weaknesses": weaknesses
        }
    
    def _analyze_conversation_context(self, user_id: str, conversation: list) -> Dict:
        """
        Analyze the user's role within the full conversation context.
        Extracts individual interaction patterns, turn-taking, responsiveness, etc.
        """
        if not conversation:
            return {
                "user_messages": 0,
                "partner_messages": 0,
                "initiated_topics": 0,
                "asked_questions": 0,
                "avg_response_length": 0,
                "conversation_balance": 0.5,
                "context_strengths": [],
                "context_weaknesses": []
            }
        
        user_msgs = []
        partner_msgs = []
        user_questions = 0
        user_word_counts = []
        
        for msg in conversation:
            speaker_id = str(msg.get("speaker_id", msg.get("user_id", "")))
            text = msg.get("text", msg.get("message", "")).strip()
            if not text:
                continue
            
            if speaker_id == str(user_id):
                user_msgs.append(text)
                user_word_counts.append(len(text.split()))
                if '?' in text:
                    user_questions += 1
            else:
                partner_msgs.append(text)
        
        total_msgs = len(user_msgs) + len(partner_msgs)
        user_msg_count = len(user_msgs)
        partner_msg_count = len(partner_msgs)
        conversation_balance = user_msg_count / total_msgs if total_msgs > 0 else 0
        avg_response_len = sum(user_word_counts) / len(user_word_counts) if user_word_counts else 0
        
        # Check for one-word / very short responses
        short_responses = sum(1 for wc in user_word_counts if wc <= 3)
        short_ratio = short_responses / user_msg_count if user_msg_count > 0 else 0
        
        # Detect if user initiated topics (spoke first or after long gap)
        initiated = 0
        for i, msg in enumerate(conversation):
            speaker_id = str(msg.get("speaker_id", msg.get("user_id", "")))
            if speaker_id == str(user_id):
                if i == 0:
                    initiated += 1
                elif i >= 2:
                    # Check if previous 2 messages were from partner (user broke silence)
                    prev1 = str(conversation[i-1].get("speaker_id", conversation[i-1].get("user_id", "")))
                    if prev1 != str(user_id):
                        initiated += 1
        
        context_strengths = []
        context_weaknesses = []
        
        # Conversation balance analysis
        if 0.35 <= conversation_balance <= 0.65:
            context_strengths.append("Balanced conversation — you contributed equally with your partner")
        elif conversation_balance > 0.65:
            context_weaknesses.append({
                "category": "confidence",
                "title": "Dominated the conversation",
                "description": f"You spoke {user_msg_count} times vs partner's {partner_msg_count} — try giving your partner more space to share",
                "tip": "Practice active listening: after making a point, ask a follow-up question to invite your partner's perspective."
            })
        elif conversation_balance < 0.35 and total_msgs >= 4:
            context_weaknesses.append({
                "category": "confidence",
                "title": "Could contribute more",
                "description": f"You spoke {user_msg_count} times vs partner's {partner_msg_count} — try sharing more of your thoughts",
                "tip": "Don't wait for the perfect thing to say. Share opinions, ask questions, and build on what your partner says."
            })
        
        # Question-asking analysis
        if user_questions >= 2:
            context_strengths.append(f"Great engagement — you asked {user_questions} questions, showing genuine interest in the conversation")
        elif user_questions == 0 and user_msg_count >= 3:
            context_weaknesses.append({
                "category": "fluency",
                "title": "No questions asked",
                "description": "You didn't ask any questions during the conversation",
                "tip": "Asking questions keeps conversations flowing naturally. Try 'What do you think about...?' or 'Can you tell me more about...?'"
            })
        
        # Response length analysis
        if avg_response_len >= 12:
            context_strengths.append(f"Detailed responses — averaging {avg_response_len:.0f} words per message shows strong elaboration skills")
        elif short_ratio > 0.6 and user_msg_count >= 3:
            context_weaknesses.append({
                "category": "confidence",
                "title": "Responses are too brief",
                "description": f"{short_responses} of your {user_msg_count} messages were very short (1-3 words)",
                "tip": "Expand your responses: explain why, give examples, or share related experiences."
            })
        
        # Topic initiation
        if initiated >= 2:
            context_strengths.append("Good initiative — you proactively introduced new topics into the conversation")
        
        return {
            "user_messages": user_msg_count,
            "partner_messages": partner_msg_count,
            "initiated_topics": initiated,
            "asked_questions": user_questions,
            "avg_response_length": round(avg_response_len, 1),
            "conversation_balance": round(conversation_balance, 2),
            "context_strengths": context_strengths,
            "context_weaknesses": context_weaknesses
        }
    
    def generate_instant_feedback(self, duration_seconds: int, user_id: str, transcript: str = None, conversation: list = None) -> Dict:
        """
        Generate AI feedback based ONLY on actual transcript data.
        Uses INDIVIDUAL transcript for language analysis + CONVERSATION for context analysis.
        
        Args:
            duration_seconds: Call duration in seconds
            user_id: User ID (to identify their messages in conversation)
            transcript: User's individual transcript text
            conversation: Full conversation array (for context analysis)
            
        Returns:
            Personalized AI feedback based on actual speech
        """
        
        # Check if we have actual transcript data
        has_transcript = transcript and len(transcript.strip()) > 10
        
        if not has_transcript:
            return {
                "ai_rating": None,
                "overall_message": "No speech data was captured for analysis. To get AI feedback, make sure you're speaking clearly during the call and your microphone is working.",
                "strengths": [],
                "weaknesses": [],
                "recommended_topics": [self._get_topic_data("daily_conversation")],
                "generated_at": datetime.utcnow().isoformat(),
                "analysis_version": "instant_v4_individual",
                "transcript_analyzed": False,
                "no_data_reason": "No transcript captured during the call"
            }
        
        # 1. Analyze the individual transcript (grammar, fillers, vocabulary)
        analysis = self.analyze_transcript(transcript)
        
        # 2. Analyze conversation context (turn-taking, balance, questions, responsiveness)
        conv_context = self._analyze_conversation_context(user_id, conversation)
        
        # Merge conversation-level strengths and weaknesses into the analysis
        all_strengths = analysis["strengths"] + conv_context["context_strengths"]
        all_weaknesses = analysis["weaknesses"] + conv_context["context_weaknesses"]
        
        # Calculate rating based on REAL metrics + conversation context
        rating = self._calculate_real_rating(analysis, duration_seconds)
        
        # Adjust rating based on conversation context
        if conv_context["asked_questions"] >= 2:
            rating = min(10.0, rating + 0.3)
        if 0.35 <= conv_context["conversation_balance"] <= 0.65:
            rating = min(10.0, rating + 0.3)
        if conv_context["avg_response_length"] >= 12:
            rating = min(10.0, rating + 0.2)
        if conv_context["conversation_balance"] < 0.25:
            rating = max(1.0, rating - 0.5)
        
        rating = round(rating, 1)
        
        # Generate personalized message
        overall_message = self._generate_real_message(analysis, rating, duration_seconds, conv_context)
        
        # Get recommended topics based on actual weaknesses found
        recommended_topics = self._get_relevant_topics(all_weaknesses)
        
        return {
            "ai_rating": rating,
            "overall_message": overall_message,
            "strengths": all_strengths if all_strengths else ["Participated in the conversation"],
            "weaknesses": all_weaknesses,
            "recommended_topics": recommended_topics,
            "generated_at": datetime.utcnow().isoformat(),
            "analysis_version": "instant_v4_individual",
            "transcript_analyzed": True,
            "transcript_stats": {
                "word_count": analysis["word_count"],
                "filler_count": analysis["filler_count"],
                "vocabulary_ratio": analysis["vocabulary_stats"].get("vocabulary_ratio", 0),
                "messages_sent": conv_context["user_messages"],
                "questions_asked": conv_context["asked_questions"],
                "conversation_balance": conv_context["conversation_balance"]
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
    
    def _generate_real_message(self, analysis: Dict, rating: float, duration_seconds: int, conv_context: Dict = None) -> str:
        """Generate personalized feedback message based on actual analysis + conversation context"""
        
        word_count = analysis["word_count"]
        weakness_count = len(analysis["weaknesses"])
        strength_count = len(analysis["strengths"])
        filler_count = analysis["filler_count"]
        vocab_stats = analysis["vocabulary_stats"]
        
        if rating >= 8.0:
            base = "Excellent conversation! Your English communication was strong and confident."
        elif rating >= 6.5:
            base = "Good job! You communicated effectively with clear speech."
        elif rating >= 5.0:
            base = "Nice effort! You're making steady progress in your English skills."
        elif rating >= 3.5:
            base = "Keep practicing! Regular conversations will help you build confidence."
        else:
            base = "Don't give up! Every conversation is a step toward improvement."
        
        # Add specific observations
        details = []
        
        if word_count >= 100:
            details.append(f"You spoke {word_count} words — great engagement!")
        elif word_count >= 50:
            details.append(f"You contributed {word_count} words to the conversation.")
        elif word_count > 0:
            details.append(f"Try to speak more — you only said about {word_count} words.")
        
        if filler_count > 5:
            details.append(f"Watch your filler words ({filler_count} detected) — try pausing instead.")
        elif filler_count > 0:
            details.append(f"Only {filler_count} filler word(s) — that's good control!")
        
        if vocab_stats.get("vocabulary_suggestions"):
            details.append("We found some vocabulary you can diversify — see suggestions below.")
        
        # Add conversation-context specific feedback
        if conv_context:
            user_msgs = conv_context.get("user_messages", 0)
            partner_msgs = conv_context.get("partner_messages", 0)
            questions = conv_context.get("asked_questions", 0)
            balance = conv_context.get("conversation_balance", 0.5)
            
            if user_msgs > 0 and partner_msgs > 0:
                if 0.35 <= balance <= 0.65:
                    details.append(f"Your conversation was well-balanced ({user_msgs} messages from you, {partner_msgs} from your partner).")
                elif balance > 0.65:
                    details.append(f"You spoke significantly more ({user_msgs} vs {partner_msgs} messages) — try to listen and let your partner share more.")
                elif balance < 0.35:
                    details.append(f"Your partner spoke more ({partner_msgs} vs your {user_msgs} messages) — don't hesitate to share your thoughts!")
            
            if questions >= 2:
                details.append(f"Great conversational skill — you asked {questions} questions to keep the dialogue going!")
            elif questions == 0 and user_msgs >= 3:
                details.append("Try asking more questions next time — it shows interest and keeps conversations engaging.")
        
        total_weaknesses = weakness_count + len(conv_context.get("context_weaknesses", [])) if conv_context else weakness_count
        total_strengths = strength_count + len(conv_context.get("context_strengths", [])) if conv_context else strength_count
        
        if total_weaknesses > 0:
            details.append(f"We identified {total_weaknesses} area(s) to work on — check below for personalized tips.")
        
        if total_strengths >= 3:
            details.append(f"You showed {total_strengths} strengths — well done!")
        
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
