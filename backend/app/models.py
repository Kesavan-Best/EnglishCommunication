from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError("Invalid ObjectId")

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class UserBase(BaseModel):
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserInDB(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    password_hash: str
    is_online: bool = False
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    ai_score: float = 0.0
    total_calls: int = 0
    total_call_duration: int = 0
    avg_fluency_score: float = 0.0
    weaknesses: List[str] = []
    friends: List[PyObjectId] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class UserPublic(UserBase):
    id: str
    is_online: bool
    ai_score: float
    total_calls: int
    rank: Optional[int] = None

class CallBase(BaseModel):
    caller_id: PyObjectId
    receiver_id: PyObjectId

class CallCreate(CallBase):
    pass

class CallInDB(CallBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    status: str = "pending"
    jitsi_room_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    audio_url: Optional[str] = None
    transcript_id: Optional[PyObjectId] = None
    analysis_id: Optional[PyObjectId] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class TranscriptBase(BaseModel):
    call_id: PyObjectId
    user_id: PyObjectId
    text: str
    language: str = "en"
    confidence: float
    word_count: int
    audio_duration: float

class AnalysisBase(BaseModel):
    call_id: PyObjectId
    user_id: PyObjectId
    grammar_errors: int = 0
    filler_words: List[str] = []
    vocabulary_repetition: float = 0.0
    fluency_score: float = 0.0
    words_per_minute: float = 0.0
    pause_count: int = 0
    english_compliance_score: float = 0.0
    overall_score: float = 0.0
    weaknesses: List[str] = []
    suggestions: List[str] = []

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic

class CallInvite(BaseModel):
    caller_id: str
    caller_name: str
    call_id: str