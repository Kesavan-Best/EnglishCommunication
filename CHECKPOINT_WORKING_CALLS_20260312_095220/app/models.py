from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId
import pydantic

# Check Pydantic version
PYDANTIC_V2 = int(pydantic.VERSION.split('.')[0]) >= 2

if PYDANTIC_V2:
    from pydantic import GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue
    from pydantic_core import core_schema

class PyObjectId(ObjectId):
    if PYDANTIC_V2:
        @classmethod
        def __get_pydantic_core_schema__(
            cls, source_type: Any, handler: Any
        ) -> core_schema.CoreSchema:
            return core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ],
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ))
        
        @classmethod
        def __get_pydantic_json_schema__(
            cls, schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
        ) -> JsonSchemaValue:
            return {"type": "string"}
    else:
        @classmethod
        def __get_validators__(cls):
            yield cls.validate

        @classmethod
        def __modify_schema__(cls, field_schema):
            field_schema.update(type="string")
    
    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str) and ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError("Invalid ObjectId")

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
    
    if PYDANTIC_V2:
        model_config = {
            "from_attributes": True,
            "populate_by_name": True,
            "arbitrary_types_allowed": True,
            "json_encoders": {ObjectId: str}
        }
    else:
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
    
    # Track who actually joined
    caller_joined: bool = False
    receiver_joined: bool = False
    both_users_connected: bool = False
    
    # Individual user recordings
    caller_audio_url: Optional[str] = None
    receiver_audio_url: Optional[str] = None
    
    # Transcripts
    transcript_id: Optional[PyObjectId] = None
    caller_transcript_id: Optional[PyObjectId] = None
    receiver_transcript_id: Optional[PyObjectId] = None
    
    # Real-time conversation data
    caller_transcript: Optional[str] = None  # Full text of what caller said
    receiver_transcript: Optional[str] = None  # Full text of what receiver said
    conversation: List[dict] = []  # [{speaker: "caller/receiver", text: "...", timestamp: "..."}]
    
    # Analysis IDs
    analysis_id: Optional[PyObjectId] = None
    caller_analysis_id: Optional[PyObjectId] = None
    receiver_analysis_id: Optional[PyObjectId] = None
    
    # Ratings - each user gets two ratings
    caller_ai_rating: Optional[float] = None  # AI rating for caller
    receiver_ai_rating: Optional[float] = None  # AI rating for receiver
    caller_peer_rating: Optional[float] = None  # Receiver rates caller
    receiver_peer_rating: Optional[float] = None  # Caller rates receiver
    
    # Feedback
    caller_ai_feedback: Optional[str] = None
    receiver_ai_feedback: Optional[str] = None
    caller_peer_feedback: Optional[str] = None
    receiver_peer_feedback: Optional[str] = None
    
    # Weaknesses and quiz status
    caller_weaknesses: List[Any] = []  # Changed from List[str] to List[Any] to accept dicts
    receiver_weaknesses: List[Any] = []  # Changed from List[str] to List[Any] to accept dicts
    caller_quiz_generated: bool = False
    receiver_quiz_generated: bool = False
    
    # Additional fields for instant AI feedback
    caller_strengths: Optional[List[str]] = None
    receiver_strengths: Optional[List[str]] = None
    caller_recommended_topics: Optional[List[Any]] = None
    receiver_recommended_topics: Optional[List[Any]] = None
    analysis_completed_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    if PYDANTIC_V2:
        model_config = {
            "from_attributes": True,
            "populate_by_name": True,
            "arbitrary_types_allowed": True,
            "json_encoders": {ObjectId: str}
        }
    else:
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