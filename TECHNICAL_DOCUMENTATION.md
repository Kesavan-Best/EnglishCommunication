# English Communication Platform - Technical Documentation

**Complete Technical Stack & Project Workflow Guide**

---

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Complete Tech Stack](#complete-tech-stack)
3. [System Architecture](#system-architecture)
4. [Technical Workflow](#technical-workflow)
5. [Key Features Implementation](#key-features-implementation)
6. [Database Schema](#database-schema)
7. [API Architecture](#api-architecture)
8. [Real-Time Communication](#real-time-communication)
9. [AI/ML Integration](#aiml-integration)
10. [Deployment & Hosting](#deployment--hosting)
11. [Security Implementation](#security-implementation)
12. [Testing Strategy](#testing-strategy)

---

## 🎯 Project Overview

**Project Name:** English Communication Platform  
**Purpose:** AI-powered platform to help users improve English speaking skills through real-time conversations, instant feedback, and personalized recommendations  
**Type:** Full-Stack Web Application with Real-Time Audio Communication

### Core Objectives
- ✅ Enable 1-on-1 real-time audio calls between users
- ✅ Provide instant AI-powered grammar and pronunciation feedback
- ✅ Generate personalized quizzes based on conversation weaknesses
- ✅ Track user progress with analytics and leaderboards
- ✅ Offer detailed post-call analysis with recommendations

---

## 🛠 Complete Tech Stack

### **Frontend Technologies**

| Technology | Version | Purpose |
|------------|---------|---------|
| **HTML5** | - | Structure & semantic markup |
| **CSS3** | - | Styling, animations, responsive design |
| **JavaScript (ES6+)** | - | Client-side logic & interactivity |
| **WebRTC** | Native | Peer-to-peer audio/video communication |
| **WebSocket** | Native | Real-time bidirectional communication |
| **MediaStream API** | Native | Microphone access & audio capture |
| **Fetch API** | Native | HTTP requests to backend |

**Key Frontend Files:**
- `call.js` - WebRTC call management
- `dashboard.js` - User dashboard logic
- `auth.js` - Authentication handling
- `leaderboard.js` - Leaderboard functionality
- `profile.js` - User profile management

---

### **Backend Technologies**

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.11.9 | Programming language |
| **FastAPI** | 0.104.1 | Modern async web framework |
| **Uvicorn** | 0.24.0 | ASGI server for FastAPI |
| **Pydantic** | 2.5.3 | Data validation & settings |
| **PyMongo** | 4.5.0 | MongoDB driver |
| **WebSockets** | 12.0 | Real-time communication |
| **python-jose** | 3.3.0 | JWT token handling |
| **passlib** | 1.7.4 | Password hashing (bcrypt) |

**Backend Architecture Pattern:** MVC (Model-View-Controller) variant
- `models.py` - Data models
- `api/` - API endpoints (controllers)
- `core/` - Configuration & security
- `app/` - Application logic

---

### **Database**

| Technology | Purpose | Details |
|------------|---------|---------|
| **MongoDB** | NoSQL Database | Document-based storage |
| **MongoDB Atlas** | Cloud Hosting | 512MB free tier |

**Why MongoDB?**
- Flexible schema for evolving features
- Excellent for storing conversation transcripts
- Easy JSON data storage
- Scalable for analytics data

---

### **AI/ML Technologies**

| Technology | Version | Purpose |
|------------|---------|---------|
| **OpenAI Whisper** | Latest | Speech-to-text transcription |
| **NLTK** | 3.8.1 | Natural language processing |
| **LanguageTool** | 2.7.1 | Grammar checking |
| **TextBlob** | 0.17.1 | Sentiment & text analysis |
| **langdetect** | 1.0.9 | Language detection |

---

### **Real-Time Communication**

| Technology | Purpose |
|------------|---------|
| **WebRTC** | Peer-to-peer audio communication |
| **STUN Servers** | NAT traversal (Google STUN) |
| **WebSocket** | Signaling for WebRTC |

**STUN Servers Used:**
```javascript
stun:stun.l.google.com:19302
stun:stun1.l.google.com:19302
stun:stun2.l.google.com:19302
```

---

### **Deployment & Hosting**

| Service | Purpose | Plan |
|---------|---------|------|
| **Render.com** | Backend hosting | Free tier |
| **MongoDB Atlas** | Database hosting | Free 512MB |
| **GitHub** | Version control | Free |
| **Render Static** | Frontend hosting | Free |

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT SIDE                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Login   │  │Dashboard │  │  Call    │  │ Profile  │   │
│  │ (HTML/JS)│  │ (HTML/JS)│  │(WebRTC)  │  │(HTML/JS) │   │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘   │
│        │             │             │             │         │
└────────┼─────────────┼─────────────┼─────────────┼─────────┘
         │             │             │             │
         │    ┌────────▼─────────────▼─────────────▼────┐
         │    │         HTTP/HTTPS REST API              │
         │    │         WebSocket Connection             │
         │    └──────────────────┬───────────────────────┘
         │                       │
┌────────▼───────────────────────▼─────────────────────────────┐
│                    BACKEND SERVER (FastAPI)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │     API      │  │  WebSocket   │  │     Auth     │       │
│  │  Endpoints   │  │   Manager    │  │   Handler    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │                │
│  ┌──────▼─────────────────▼─────────────────▼───────┐       │
│  │            Business Logic Layer                   │       │
│  │  • User Management  • Call Management             │       │
│  │  • AI Processing    • Analytics                   │       │
│  └──────┬────────────────────────────────────────────┘       │
└─────────┼────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────┐
│                    DATA LAYER                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   MongoDB    │  │  AI Services │  │  File System │       │
│  │  (Atlas)     │  │ (OpenAI API) │  │ (Audio Files)│       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└───────────────────────────────────────────────────────────────┘
```

---

## 🔄 Technical Workflow

### **1. User Registration & Authentication Flow**

```
User → Frontend Form → POST /api/users/register
                    ↓
              Validate Input (Pydantic)
                    ↓
              Hash Password (bcrypt)
                    ↓
              Save to MongoDB
                    ↓
              Generate JWT Token
                    ↓
              Return Token + User Data
                    ↓
              Store Token in localStorage
```

**Technologies Involved:**
- Pydantic for data validation
- Passlib for password hashing
- python-jose for JWT tokens
- MongoDB for user storage

---

### **2. Audio Call Workflow (WebRTC)**

```
User A              WebSocket Server           User B
  │                        │                      │
  │─────Connect WS─────────▶│                      │
  │                        │◀────Connect WS────────│
  │                        │                      │
  │──Request Call──────────▶│                      │
  │                        │───Call Notification──▶│
  │                        │                      │
  │                        │◀────Accept Call───────│
  │                        │                      │
  │◀───Call Accepted───────│                      │
  │                        │                      │
┌─▼─ WebRTC Setup ─────────┴───────────────────▼─┐
│                                                  │
│  User A                               User B    │
│    │                                    │        │
│    │──────SDP Offer (via WS)───────────▶│        │
│    │                                    │        │
│    │◀─────SDP Answer (via WS)───────────│        │
│    │                                    │        │
│    │──────ICE Candidates──────────────▶│        │
│    │◀─────ICE Candidates───────────────│        │
│    │                                    │        │
│    │═══════ Direct P2P Audio ══════════│        │
│    │        (RTCPeerConnection)         │        │
│                                                  │
└──────────────────────────────────────────────────┘
  │                        │                      │
  │──End Call──────────────▶│                      │
  │                        │───Call Ended─────────▶│
  │                        │                      │
  │──Upload Transcript─────▶│                      │
  │                        │                      │
  │                   AI Processing               │
  │                        │                      │
  │◀──Analysis Results─────│                      │
```

**Key Technologies:**
1. **WebSocket** - Signaling (offer/answer/ICE)
2. **WebRTC** - Peer-to-peer audio connection
3. **STUN** - NAT traversal
4. **MediaStream API** - Microphone access

---

### **3. AI Analysis Workflow**

```
Call Ends
    │
    ▼
Upload Audio + Transcript
    │
    ▼
┌───────────────────────────┐
│   Backend Processing      │
│                           │
│  1. Whisper Transcription │──▶ Convert audio to text
│        ↓                  │
│  2. Grammar Analysis      │──▶ LanguageTool + NLTK
│        ↓                  │
│  3. Vocabulary Analysis   │──▶ TextBlob + Custom logic
│        ↓                  │
│  4. Fluency Scoring       │──▶ Word rate, pauses
│        ↓                  │
│  5. Topic Extraction      │──▶ NLTK + frequency analysis
│        ↓                  │
│  6. Quiz Generation       │──▶ Based on mistakes
│        ↓                  │
│  7. Recommendations       │──▶ Personalized tips
│                           │
└───────────────────────────┘
    │
    ▼
Save to MongoDB
    │
    ▼
Return to User
```

**AI Services Used:**
- **OpenAI Whisper** - Speech-to-text
- **LanguageTool** - Grammar checking
- **NLTK** - Text processing
- **TextBlob** - Sentiment analysis
- **Custom Algorithms** - Scoring & recommendations

---

## 🎨 Key Features Implementation

### **Feature 1: Real-Time Audio Calls**

**How It Works:**
1. User initiates call → WebSocket notifies partner
2. Both users establish WebRTC connection
3. Audio streams directly peer-to-peer (P2P)
4. No audio goes through server (privacy + low latency)

**Code Location:**
- Frontend: `frontend/js/call.js` (lines 214-350)
- Backend: `backend/app/api/websocket.py` (lines 250-283)

**Technologies:**
```javascript
// Frontend
const peerConnection = new RTCPeerConnection({
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' }
    ]
});
```

```python
# Backend
@manager.handle_webrtc_signal()
async def handle_signal(from_user, signal_data):
    # Forward WebRTC signals between peers
    await manager.send_to_user(to_user, signal)
```

---

### **Feature 2: Instant AI Feedback**

**How It Works:**
1. Microphone captures speech → Audio chunks
2. Real-time transcription (Whisper)
3. Grammar check on each sentence (LanguageTool)
4. Instant feedback displayed during call

**Code Location:**
- `backend/app/ai_processing/instant_analyzer.py`

**Process Flow:**
```python
Audio Chunk → Whisper → Text
              ↓
        Grammar Check → Mistakes
              ↓
        Send via WebSocket → User sees feedback
```

---

### **Feature 3: Quiz Generation**

**How It Works:**
1. Analyze conversation mistakes
2. Extract grammar errors, vocabulary gaps
3. Generate multiple-choice questions
4. Target user's specific weaknesses

**Code Location:**
- `backend/app/ai_processing/quiz_generator.py`

**Algorithm:**
```python
def generate_quiz(mistakes, vocabulary):
    questions = []
    for mistake in mistakes:
        question = create_multiple_choice(
            mistake.sentence,
            mistake.correction,
            mistake.type
        )
        questions.append(question)
    return questions
```

---

### **Feature 4: Leaderboard & Analytics**

**How It Works:**
1. Track user metrics: calls, scores, streaks
2. Calculate global rankings
3. Real-time updates via WebSocket

**Metrics Tracked:**
- Total call duration
- Average grammar score
- Fluency rating
- Vocabulary richness
- Call frequency

**Code Location:**
- `backend/app/api/leaderboard.py`
- `frontend/js/leaderboard.js`

---

## 💾 Database Schema

### **Users Collection**
```json
{
  "_id": "ObjectId",
  "username": "string",
  "email": "string",
  "password_hash": "string",
  "full_name": "string",
  "created_at": "datetime",
  "profile_picture": "string",
  "bio": "string",
  "level": "beginner|intermediate|advanced",
  "stats": {
    "total_calls": 0,
    "total_duration": 0,
    "average_score": 0,
    "current_streak": 0
  }
}
```

### **Calls Collection**
```json
{
  "_id": "ObjectId",
  "caller_id": "string",
  "receiver_id": "string",
  "status": "pending|active|completed|cancelled",
  "room_id": "string",
  "started_at": "datetime",
  "ended_at": "datetime",
  "duration": 0,
  "transcript": "string",
  "analysis": {
    "grammar_score": 0-100,
    "vocabulary_score": 0-100,
    "fluency_score": 0-100,
    "mistakes": [],
    "recommendations": []
  }
}
```

### **Analysis Collection**
```json
{
  "_id": "ObjectId",
  "call_id": "string",
  "user_id": "string",
  "transcript": "string",
  "grammar_mistakes": [],
  "vocabulary_analysis": {},
  "fluency_metrics": {},
  "topics_discussed": [],
  "quiz_questions": [],
  "recommendations": [],
  "created_at": "datetime"
}
```

---

## 🔌 API Architecture

### **Authentication Endpoints**

| Method | Endpoint | Purpose | Auth Required |
|--------|----------|---------|---------------|
| POST | `/api/users/register` | Create new user | ❌ |
| POST | `/api/users/login` | User login | ❌ |
| GET | `/api/users/me` | Get current user | ✅ |
| PUT | `/api/users/me` | Update profile | ✅ |

### **Call Endpoints**

| Method | Endpoint | Purpose | Auth Required |
|--------|----------|---------|---------------|
| POST | `/api/calls/initiate` | Start new call | ✅ |
| GET | `/api/calls/{call_id}` | Get call details | ✅ |
| POST | `/api/calls/{call_id}/end` | End active call | ✅ |
| GET | `/api/calls/history` | User call history | ✅ |

### **Analysis Endpoints**

| Method | Endpoint | Purpose | Auth Required |
|--------|----------|---------|---------------|
| POST | `/api/analysis/analyze` | Analyze conversation | ✅ |
| GET | `/api/analysis/{call_id}` | Get call analysis | ✅ |
| POST | `/api/analysis/quiz` | Generate quiz | ✅ |

### **WebSocket Endpoints**

| Endpoint | Purpose |
|----------|---------|
| `ws://backend/ws/{user_id}` | Real-time communication |

**WebSocket Message Types:**
- `call_request` - Incoming call notification
- `call_accepted` - Call accepted by receiver
- `call_rejected` - Call rejected
- `webrtc_signal` - WebRTC signaling data
- `instant_feedback` - Real-time grammar feedback
- `call_ended` - Call terminated

---

## 🔐 Security Implementation

### **1. Authentication (JWT)**

**How It Works:**
```python
# Generate Token
token = jwt.encode({
    "sub": user_id,
    "exp": datetime.utcnow() + timedelta(days=1)
}, SECRET_KEY, algorithm="HS256")
```

**Token Flow:**
```
Login → Generate JWT → Store in localStorage
             ↓
    Every API Request:
    Headers: { "Authorization": "Bearer <token>" }
             ↓
    Verify Token → Extract user_id → Allow access
```

---

### **2. Password Security**

**Hashing Algorithm:** bcrypt (via passlib)

```python
# Hash password during registration
hashed = get_password_hash(plain_password)

# Verify during login
verify_password(plain_password, hashed_password)
```

---

### **3. CORS Configuration**

```python
# Allow specific origins
CORS_ORIGINS = ["*"]  # For development
# Production: specific domains only
```

---

### **4. Input Validation**

**Using Pydantic Models:**
```python
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)
```

---

## 🚀 Deployment & Hosting

### **Backend Deployment (Render)**

**Configuration:**
```yaml
# render.yaml
services:
  - type: web
    name: english-communication-backend
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Environment Variables:**
- `SECRET_KEY` - JWT secret
- `MONGODB_URL` - Database connection
- `OPENAI_API_KEY` - AI services
- `CORS_ORIGINS` - Allowed origins

---

### **Frontend Deployment**

**Options:**
1. **Render Static Site** - Free
2. **Vercel** - Free
3. **Netlify** - Free

**Build:** None needed (pure HTML/CSS/JS)

---

### **Database (MongoDB Atlas)**

**Configuration:**
- Cluster: M0 (512MB free)
- Region: Closest to backend
- Connection: Via connection string

---

## 🧪 Testing Strategy

### **Manual Testing Checklist**

#### **Authentication:**
- ✅ User registration with valid data
- ✅ User login with correct credentials
- ✅ JWT token generation and validation
- ✅ Protected routes require authentication

#### **Audio Calls:**
- ✅ Initiate call between two users
- ✅ WebRTC connection establishment
- ✅ Audio transmission both ways
- ✅ Call end and cleanup

#### **AI Features:**
- ✅ Transcription accuracy
- ✅ Grammar error detection
- ✅ Quiz generation from mistakes
- ✅ Recommendations relevance

---

## 📊 Performance Considerations

### **Optimization Techniques Used:**

1. **WebRTC Direct P2P**
   - Audio doesn't go through server
   - Reduces latency and bandwidth

2. **Async Python (FastAPI)**
   - Non-blocking I/O
   - Handles multiple connections efficiently

3. **MongoDB Indexing**
   - Indexes on user_id, call_id
   - Fast query performance

4. **Lazy Loading**
   - Load call history on demand
   - Pagination for large datasets

---

## 🎓 Presentation Talking Points

### **Opening Statement:**
> "This is an AI-powered English communication platform that helps users improve their speaking skills through real-time audio conversations with instant feedback, personalized quizzes, and detailed analytics."

### **Technical Highlights:**
1. **Real-Time Communication:** "We use WebRTC for peer-to-peer audio, ensuring low latency and privacy"
2. **AI Integration:** "OpenAI Whisper for transcription, LanguageTool for grammar checking"
3. **Scalable Architecture:** "FastAPI backend with MongoDB, deployed on Render"
4. **Security:** "JWT authentication, bcrypt password hashing"

### **Key Differentiators:**
- ✅ Real-time instant feedback during calls
- ✅ Personalized quiz generation
- ✅ Comprehensive analytics dashboard
- ✅ Free and open-source

---

## 📈 Future Enhancements

1. **Group Calls** - Support 3+ users
2. **AI Tutor Mode** - Practice with AI bot
3. **Mobile App** - React Native version
4. **Pronunciation Scoring** - Speech analysis
5. **Gamification** - Badges, achievements

---

## 🔧 Development Setup

### **Local Development:**

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
# Open index.html in browser or use Live Server
```

### **Environment Variables (.env):**
```
SECRET_KEY=your-secret-key
MONGODB_URL=mongodb://localhost:27017
OPENAI_API_KEY=sk-...
CORS_ORIGINS=*
```

---

## 📚 Resources & References

### **Documentation:**
- FastAPI: https://fastapi.tiangolo.com
- WebRTC: https://webrtc.org
- MongoDB: https://docs.mongodb.com
- OpenAI Whisper: https://github.com/openai/whisper

### **Libraries:**
- Pydantic: https://docs.pydantic.dev
- NLTK: https://www.nltk.org
- LanguageTool: https://languagetool.org

---

## 📞 Contact & Support

**Developer:** [Your Name]  
**GitHub:** https://github.com/Kesavan-Best/EnglishCommunication  
**Email:** [Your Email]

---

**Last Updated:** January 29, 2026  
**Version:** 1.0.0
