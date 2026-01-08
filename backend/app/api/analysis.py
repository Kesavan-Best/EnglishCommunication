from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from bson import ObjectId
from datetime import datetime

from app.auth import AuthHandler
from app.database import Database
from app.models import UserInDB
from app.schemas import AnalysisResponse, QuizResponse
from app.ai_processing.whisper_transcriber import whisper_transcriber
from app.ai_processing.text_analyzer import text_analyzer
from app.ai_processing.quiz_generator import QuizGenerator

router = APIRouter()
quiz_generator = QuizGenerator()

@router.get("/call/{call_id}", response_model=AnalysisResponse)
async def get_call_analysis(
    call_id: str,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Get AI analysis for a specific call"""
    db = Database.get_db()
    
    try:
        # Get call
        call_data = db.calls.find_one({"_id": ObjectId(call_id)})
        if not call_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Call not found"
            )
        
        # Check if user was part of the call
        if (str(call_data["caller_id"]) != str(current_user.id) and 
            str(call_data["receiver_id"]) != str(current_user.id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this analysis"
            )
        
        # Get analysis
        analysis_data = db.ai_analysis.find_one({"call_id": ObjectId(call_id)})
        if not analysis_data:
            # Trigger analysis if not exists
            if call_data.get("audio_url"):
                await process_call_analysis_background(call_id)
                raise HTTPException(
                    status_code=status.HTTP_202_ACCEPTED,
                    detail="Analysis in progress, please check back later"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No audio available for analysis"
                )
        
        return AnalysisResponse(
            id=str(analysis_data["_id"]),
            call_id=str(analysis_data["call_id"]),
            grammar_errors=analysis_data["grammar_errors"],
            filler_words=analysis_data["filler_words"],
            vocabulary_repetition=analysis_data["vocabulary_repetition"],
            fluency_score=analysis_data["fluency_score"],
            words_per_minute=analysis_data["words_per_minute"],
            pause_count=analysis_data["pause_count"],
            english_compliance_score=analysis_data["english_compliance_score"],
            overall_score=analysis_data["overall_score"],
            weaknesses=analysis_data["weaknesses"],
            suggestions=analysis_data["suggestions"],
            created_at=analysis_data["created_at"]
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching analysis: {str(e)}"
        )

@router.get("/my-analyses", response_model=list[AnalysisResponse])
async def get_my_analyses(
    current_user: UserInDB = Depends(AuthHandler.get_current_user),
    limit: int = 20,
    skip: int = 0
):
    """Get user's recent AI analyses"""
    db = Database.get_db()
    
    analyses = []
    cursor = db.ai_analysis.find({"user_id": current_user.id}) \
        .sort("created_at", -1) \
        .skip(skip) \
        .limit(limit)
    
    for analysis_data in cursor:
        analyses.append(AnalysisResponse(
            id=str(analysis_data["_id"]),
            call_id=str(analysis_data["call_id"]),
            grammar_errors=analysis_data["grammar_errors"],
            filler_words=analysis_data["filler_words"],
            vocabulary_repetition=analysis_data["vocabulary_repetition"],
            fluency_score=analysis_data["fluency_score"],
            words_per_minute=analysis_data["words_per_minute"],
            pause_count=analysis_data["pause_count"],
            english_compliance_score=analysis_data["english_compliance_score"],
            overall_score=analysis_data["overall_score"],
            weaknesses=analysis_data["weaknesses"],
            suggestions=analysis_data["suggestions"],
            created_at=analysis_data["created_at"]
        ))
    
    return analyses

@router.get("/quiz/generate", response_model=QuizResponse)
async def generate_quiz(
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Generate personalized quiz based on user weaknesses"""
    db = Database.get_db()
    
    # Get user's recent weaknesses
    user_data = db.users.find_one({"_id": current_user.id})
    weaknesses = user_data.get("weaknesses", [])
    
    if not weaknesses:
        # Default weaknesses if none found
        weaknesses = ["grammar", "fluency"]
    
    # Generate quiz
    quiz = quiz_generator.generate_quiz(weaknesses)
    
    # Save to database
    quiz_data = {
        "user_id": current_user.id,
        "weaknesses": weaknesses,
        "questions": [
            {
                "type": q["type"],
                "question": q["question"],
                "options": q["options"],
                "correct_answer": q["correct_answer"],
                "explanation": q["explanation"]
            }
            for q in quiz
        ],
        "completed": False,
        "created_at": datetime.utcnow()
    }
    
    result = db.quizzes.insert_one(quiz_data)
    
    return QuizResponse(
        id=str(result.inserted_id),
        weaknesses=weaknesses,
        questions=[
            {
                "type": q["type"],
                "question": q["question"],
                "options": q["options"],
                "correct_answer": q["correct_answer"],
                "explanation": q["explanation"]
            }
            for q in quiz
        ],
        completed=False,
        score=None,
        created_at=quiz_data["created_at"]
    )

@router.post("/quiz/{quiz_id}/submit")
async def submit_quiz(
    quiz_id: str,
    answers: dict,
    current_user: UserInDB = Depends(AuthHandler.get_current_user)
):
    """Submit quiz answers and get score"""
    db = Database.get_db()
    
    try:
        # Get quiz
        quiz_data = db.quizzes.find_one({
            "_id": ObjectId(quiz_id),
            "user_id": current_user.id
        })
        
        if not quiz_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        if quiz_data.get("completed", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quiz already completed"
            )
        
        # Calculate score
        questions = quiz_data["questions"]
        correct_count = 0
        
        for idx, question in enumerate(questions):
            user_answer = answers.get(str(idx))
            if user_answer == question["correct_answer"]:
                correct_count += 1
        
        score = (correct_count / len(questions)) * 100 if questions else 0
        
        # Update quiz
        db.quizzes.update_one(
            {"_id": ObjectId(quiz_id)},
            {
                "$set": {
                    "completed": True,
                    "score": score,
                    "submitted_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "quiz_id": quiz_id,
            "score": score,
            "correct_answers": correct_count,
            "total_questions": len(questions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting quiz: {str(e)}"
        )

async def process_call_analysis_background(call_id: str):
    """Background task to process call analysis"""
    # This would be triggered by a background worker
    # For now, we'll implement a simplified version
    
    db = Database.get_db()
    call_data = db.calls.find_one({"_id": ObjectId(call_id)})
    
    if not call_data or not call_data.get("audio_url"):
        return
    
    # Here you would:
    # 1. Download/access audio file
    # 2. Transcribe with Whisper
    # 3. Analyze with TextAnalyzer
    # 4. Save results to database
    # 5. Update user's AI score
    
    print(f"Processing analysis for call: {call_id}")
    # Implementation would go here...