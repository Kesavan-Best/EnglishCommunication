from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

# Request schemas
class UserRegisterRequest(BaseModel):
    email: str
    password: str
    name: str

class UserLoginRequest(BaseModel):
    email: str
    password: str

class CallInviteRequest(BaseModel):
    receiver_id: str

class CallAcceptRequest(BaseModel):
    call_id: str

class CallEndRequest(BaseModel):
    call_id: str
    duration_seconds: int
    audio_file: Optional[str] = None

class RatePartnerRequest(BaseModel):
    call_id: str
    rating: float  # 1-5 stars
    feedback: Optional[str] = None

class UploadAudioRequest(BaseModel):
    call_id: str
    user_id: str

# Response schemas
class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: Optional[str]
    is_online: bool
    ai_score: float
    total_calls: int
    total_call_duration: int
    avg_fluency_score: float
    weaknesses: List[str]
    rank: Optional[int] = None

class CallResponse(BaseModel):
    id: str
    caller_id: str
    receiver_id: str
    status: str
    jitsi_room_id: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    
    # Individual recordings
    caller_audio_url: Optional[str] = None
    receiver_audio_url: Optional[str] = None
    
    # Ratings
    caller_ai_rating: Optional[float] = None
    receiver_ai_rating: Optional[float] = None
    caller_peer_rating: Optional[float] = None
    receiver_peer_rating: Optional[float] = None
    
    # Feedback
    caller_ai_feedback: Optional[str] = None
    receiver_ai_feedback: Optional[str] = None
    
    # Weaknesses
    caller_weaknesses: List[str] = []
    receiver_weaknesses: List[str] = []
    
    created_at: datetime

class AnalysisResponse(BaseModel):
    id: str
    call_id: str
    grammar_errors: int
    filler_words: List[str]
    vocabulary_repetition: float
    fluency_score: float
    words_per_minute: float
    pause_count: int
    english_compliance_score: float
    overall_score: float
    weaknesses: List[str]
    suggestions: List[str]
    created_at: datetime

class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    name: str
    avatar_url: Optional[str]
    ai_score: float
    total_calls: int
    avg_fluency_score: float

class QuizQuestion(BaseModel):
    type: str
    question: str
    options: List[str]
    correct_answer: str
    explanation: str

class QuizResponse(BaseModel):
    id: str
    weaknesses: List[str]
    questions: List[QuizQuestion]
    completed: bool
    score: Optional[float]
    created_at: datetime