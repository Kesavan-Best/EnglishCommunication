"""
NLP Analysis API Endpoints
Provides REST API for conversation analysis and quiz generation
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from bson import ObjectId

from backend.app.ai_processing.lightweight_model import get_ai_processor
from backend.app.database import Database
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nlp", tags=["NLP Analysis"])


# Request/Response Models
class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Conversation text to analyze")
    user_id: Optional[str] = Field(None, description="User ID for storing results")


class AnalyzeResponse(BaseModel):
    topics: List[Dict]
    grammar_issues: List[Dict]
    vocabulary_level: str
    vocabulary_stats: Dict
    suggestions: List[str]
    recommended_topics: List[str]
    weak_areas: List[str]


class QuizRequest(BaseModel):
    topic: str = Field(..., description="Topic for quiz generation")
    difficulty: str = Field("medium", description="Difficulty level: beginner, intermediate, advanced")
    num_questions: int = Field(5, ge=1, le=10, description="Number of questions")


class QuizResponse(BaseModel):
    questions: List[Dict]
    topic: str
    difficulty: str


class SaveWeaknessRequest(BaseModel):
    user_id: str
    weak_areas: List[str]
    grammar_issues: List[Dict]
    suggestions: List[str]
    recommended_topics: List[str]


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_conversation(request: AnalyzeRequest):
    """
    Analyze conversation text using NLP models
    
    Returns:
    - Topics discussed
    - Grammar issues detected
    - Vocabulary level assessment
    - Personalized suggestions
    - Recommended learning topics
    """
    try:
        logger.info(f"Analyzing conversation ({len(request.text)} chars)")
        
        # Get AI processor (lazy loading - models load on first use)
        try:
            processor = get_ai_processor()
        except Exception as model_error:
            logger.warning(f"NLP models not available: {model_error}")
            # Return basic analysis without models
            return {
                "topics": [],
                "grammar_issues": [],
                "vocabulary_level": "Unknown",
                "vocabulary_stats": {"level": "Unknown", "total_words": 0, "unique_words": 0, "vocabulary_richness": 0, "average_word_length": 0},
                "suggestions": ["NLP models are downloading. Please try again in a few minutes."],
                "recommended_topics": ["General English Practice"],
                "weak_areas": []
            }
        
        # Analyze the text
        result = processor.analyze_conversation(request.text)
        
        # If user_id provided, save the weaknesses
        if request.user_id:
            try:
                db = Database.get_db()
                await save_user_weaknesses(
                    db=db,
                    user_id=request.user_id,
                    weak_areas=result.get('weak_areas', []),
                    grammar_issues=result.get('grammar_issues', []),
                    suggestions=result.get('suggestions', []),
                    recommended_topics=result.get('recommended_topics', [])
                )
            except Exception as e:
                logger.error(f"Failed to save weaknesses: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/generate-quiz", response_model=QuizResponse)
async def generate_quiz(request: QuizRequest):
    """
    Generate quiz questions for a specific topic
    
    Parameters:
    - topic: The topic to generate questions about
    - difficulty: beginner, intermediate, or advanced
    - num_questions: Number of questions (1-10)
    
    Returns:
    - List of quiz questions with options and explanations
    """
    try:
        logger.info(f"Generating quiz: {request.topic} ({request.difficulty})")
        
        # Get AI processor (lazy loading)
        try:
            processor = get_ai_processor()
        except Exception as model_error:
            logger.warning(f"NLP models not available: {model_error}")
            raise HTTPException(
                status_code=503, 
                detail="NLP models are initializing. Please try again in 1-2 minutes."
            )
        
        # Generate quiz
        questions = processor.generate_quiz(
            topic=request.topic,
            difficulty=request.difficulty,
            num_questions=request.num_questions
        )
        
        return {
            "questions": questions,
            "topic": request.topic,
            "difficulty": request.difficulty
        }
        
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {str(e)}")


@router.get("/weaknesses/{user_id}")
async def get_user_weaknesses(user_id: str):
    """
    Get user's weak areas and personalized recommendations
    
    Returns:
    - Weak areas (grammar, vocabulary, etc.)
    - Recent grammar issues
    - Personalized suggestions
    - Recommended learning topics
    """
    try:
        db = Database.get_db()
        
        # Get user weaknesses
        weakness = await db.user_weaknesses.find_one(
            {"user_id": user_id},
            sort=[("last_updated", -1)]
        )
        
        if not weakness:
            return {
                "user_id": user_id,
                "weak_areas": [],
                "suggestions": ["Complete a conversation to get personalized feedback"],
                "recommended_topics": ["General English Practice"],
                "last_updated": None
            }
        
        # Convert ObjectId to string
        weakness['_id'] = str(weakness['_id'])
        
        return weakness
        
    except Exception as e:
        logger.error(f"Failed to get weaknesses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quiz-history/{user_id}")
async def get_quiz_history(user_id: str, limit: int = 10):
    """
    Get user's quiz history and scores
    
    Parameters:
    - limit: Number of recent quizzes to return (default: 10)
    
    Returns:
    - List of completed quizzes with scores
    """
    try:
        db = Database.get_db()
        
        # Get quiz history
        quizzes = await db.quiz_history.find(
            {"user_id": user_id}
        ).sort("completed_at", -1).limit(limit).to_list(length=limit)
        
        # Convert ObjectIds to strings
        for quiz in quizzes:
            quiz['_id'] = str(quiz['_id'])
        
        return {
            "user_id": user_id,
            "quizzes": quizzes,
            "total_quizzes": len(quizzes)
        }
        
    except Exception as e:
        logger.error(f"Failed to get quiz history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-quiz-result")
async def save_quiz_result(
    user_id: str,
    topic: str,
    difficulty: str,
    score: int,
    total_questions: int,
    questions: List[Dict],
    user_answers: List[int]
):
    """
    Save quiz result to database
    
    Parameters:
    - user_id: User ID
    - topic: Quiz topic
    - difficulty: Quiz difficulty
    - score: Number of correct answers
    - total_questions: Total number of questions
    - questions: List of questions
    - user_answers: List of user's answer indices
    """
    try:
        db = Database.get_db()
        
        quiz_result = {
            "user_id": user_id,
            "topic": topic,
            "difficulty": difficulty,
            "score": score,
            "total_questions": total_questions,
            "percentage": round((score / total_questions) * 100, 1),
            "questions": questions,
            "user_answers": user_answers,
            "completed_at": datetime.utcnow()
        }
        
        result = await db.quiz_history.insert_one(quiz_result)
        
        return {
            "success": True,
            "quiz_id": str(result.inserted_id),
            "message": "Quiz result saved successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to save quiz result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{user_id}")
async def get_learning_progress(user_id: str):
    """
    Get comprehensive learning progress for a user
    
    Returns:
    - Weak areas with scores
    - Quiz statistics
    - Improvement trends
    - Recommended next steps
    """
    try:
        db = Database.get_db()
        
        # Get recent weaknesses
        weakness = await db.user_weaknesses.find_one(
            {"user_id": user_id},
            sort=[("last_updated", -1)]
        )
        
        # Get quiz statistics
        quiz_stats = await db.quiz_history.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": "$topic",
                "avg_score": {"$avg": "$percentage"},
                "total_quizzes": {"$sum": 1},
                "last_quiz": {"$max": "$completed_at"}
            }}
        ]).to_list(length=100)
        
        # Calculate overall progress
        weak_areas = weakness.get('weak_areas', []) if weakness else []
        
        progress = {
            "user_id": user_id,
            "weak_areas": weak_areas,
            "quiz_statistics": quiz_stats,
            "total_quizzes_taken": sum(stat['total_quizzes'] for stat in quiz_stats),
            "average_score": round(
                sum(stat['avg_score'] for stat in quiz_stats) / len(quiz_stats)
                if quiz_stats else 0,
                1
            ),
            "recommended_topics": weakness.get('recommended_topics', []) if weakness else [],
            "last_updated": weakness.get('last_updated') if weakness else None
        }
        
        return progress
        
    except Exception as e:
        logger.error(f"Failed to get progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper function
async def save_user_weaknesses(db, user_id: str, weak_areas: List[str],
                              grammar_issues: List[Dict], suggestions: List[str],
                              recommended_topics: List[str]):
    """
    Save or update user weaknesses in database
    """
    weakness_data = {
        "user_id": user_id,
        "weak_areas": weak_areas,
        "grammar_issues": grammar_issues[:5],  # Keep last 5 issues
        "suggestions": suggestions,
        "recommended_topics": recommended_topics,
        "last_updated": datetime.utcnow()
    }
    
    # Update or insert
    await db.user_weaknesses.update_one(
        {"user_id": user_id},
        {"$set": weakness_data},
        upsert=True
    )
    
    logger.info(f"Saved weaknesses for user {user_id}")


@router.get("/health")
async def nlp_health_check():
    """
    Check if NLP models are loaded and working
    """
    try:
        processor = get_ai_processor()
        return {
            "status": "healthy",
            "models_loaded": True,
            "message": "NLP service is operational"
        }
    except Exception as e:
        logger.warning(f"NLP models not yet loaded: {e}")
        return {
            "status": "initializing",
            "models_loaded": False,
            "message": "Models will load on first use",
            "error": str(e)
        }
