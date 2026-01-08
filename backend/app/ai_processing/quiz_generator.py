import random
from typing import List, Dict
import json

class QuizGenerator:
    def __init__(self):
        # Grammar questions database
        self.grammar_questions = [
            {
                "type": "grammar",
                "question": "Choose the correct sentence:",
                "options": [
                    "She don't like coffee.",
                    "She doesn't like coffee.",
                    "She doesn't likes coffee.",
                    "She not like coffee."
                ],
                "correct_answer": "She doesn't like coffee.",
                "explanation": "Use 'doesn't' with third person singular (he, she, it)."
            },
            {
                "type": "grammar",
                "question": "Which sentence is grammatically correct?",
                "options": [
                    "I have went to the store yesterday.",
                    "I have gone to the store yesterday.",
                    "I went to the store yesterday.",
                    "I going to the store yesterday."
                ],
                "correct_answer": "I went to the store yesterday.",
                "explanation": "Use simple past for completed actions at specific times."
            },
            {
                "type": "grammar",
                "question": "Choose the correct verb form:",
                "options": [
                    "If I was you, I would study more.",
                    "If I were you, I would study more.",
                    "If I am you, I would study more.",
                    "If I be you, I would study more."
                ],
                "correct_answer": "If I were you, I would study more.",
                "explanation": "Use 'were' for all subjects in hypothetical situations."
            }
        ]
        
        # Vocabulary questions
        self.vocabulary_questions = [
            {
                "type": "vocabulary",
                "question": "Choose the word that means 'extremely happy':",
                "options": ["Ecstatic", "Miserable", "Content", "Neutral"],
                "correct_answer": "Ecstatic",
                "explanation": "Ecstatic means extremely happy or joyful."
            },
            {
                "type": "vocabulary",
                "question": "What is a synonym for 'difficult'?",
                "options": ["Easy", "Challenging", "Simple", "Basic"],
                "correct_answer": "Challenging",
                "explanation": "Challenging means testing one's abilities; difficult."
            }
        ]
        
        # Sentence correction questions
        self.correction_questions = [
            {
                "type": "sentence_correction",
                "question": "Correct this sentence: 'He goed to school everyday.'",
                "options": [
                    "He goes to school everyday.",
                    "He go to school everyday.",
                    "He going to school everyday.",
                    "He went to school everyday."
                ],
                "correct_answer": "He goes to school everyday.",
                "explanation": "'Goed' is incorrect. Use 'goes' for present tense."
            },
            {
                "type": "sentence_correction",
                "question": "Correct this sentence: 'They was happy to see us.'",
                "options": [
                    "They were happy to see us.",
                    "They is happy to see us.",
                    "They am happy to see us.",
                    "They be happy to see us."
                ],
                "correct_answer": "They were happy to see us.",
                "explanation": "Use 'were' with plural subject 'they'."
            }
        ]
        
        # Weakness-specific questions
        self.weakness_questions = {
            "grammar": self.grammar_questions,
            "vocabulary": self.vocabulary_questions,
            "vocabulary_repetition": self.vocabulary_questions,
            "fluency": [
                {
                    "type": "fluency",
                    "question": "Which phrase helps with smooth transitions?",
                    "options": [
                        "Um... you know...",
                        "Anyway... so...",
                        "In addition to that...",
                        "Like, I mean..."
                    ],
                    "correct_answer": "In addition to that...",
                    "explanation": "Transition phrases improve fluency and connection between ideas."
                }
            ],
            "filler_words": [
                {
                    "type": "filler_words",
                    "question": "What's a better alternative to 'um' when thinking?",
                    "options": [
                        "Just pause briefly",
                        "Say 'like' repeatedly",
                        "Use 'you know'",
                        "Say nothing and continue"
                    ],
                    "correct_answer": "Just pause briefly",
                    "explanation": "A brief pause is more professional than filler words."
                }
            ]
        }
    
    def generate_quiz(self, weaknesses: List[str], num_questions: int = 5) -> List[Dict]:
        """Generate quiz based on weaknesses"""
        quiz = []
        used_questions = set()
        
        # Ensure we have questions
        if not weaknesses:
            weaknesses = ["grammar", "vocabulary"]
        
        # Calculate questions per weakness
        questions_per_weakness = max(1, num_questions // len(weaknesses))
        
        for weakness in weaknesses:
            if weakness in self.weakness_questions:
                questions = self.weakness_questions[weakness]
                
                # Add unique questions for this weakness
                added = 0
                for question in random.sample(questions, min(len(questions), questions_per_weakness)):
                    question_id = f"{weakness}_{question['question']}"
                    if question_id not in used_questions:
                        quiz.append(question)
                        used_questions.add(question_id)
                        added += 1
                
                # If not enough questions from this weakness, add from others
                if added < questions_per_weakness:
                    remaining = questions_per_weakness - added
                    all_questions = self._get_all_questions()
                    for question in random.sample(all_questions, min(len(all_questions), remaining)):
                        question_id = f"general_{question['question']}"
                        if question_id not in used_questions:
                            quiz.append(question)
                            used_questions.add(question_id)
        
        # Ensure we have exactly num_questions
        if len(quiz) < num_questions:
            all_questions = self._get_all_questions()
            needed = num_questions - len(quiz)
            for question in random.sample(all_questions, min(len(all_questions), needed)):
                question_id = f"general_{question['question']}"
                if question_id not in used_questions:
                    quiz.append(question)
                    used_questions.add(question_id)
        
        # Shuffle questions
        random.shuffle(quiz)
        return quiz[:num_questions]
    
    def _get_all_questions(self) -> List[Dict]:
        """Get all available questions"""
        all_questions = []
        for questions in self.weakness_questions.values():
            all_questions.extend(questions)
        return all_questions