"""
stt.py - Speech-to-Text API endpoints using faster-whisper.

POST /api/stt/transcribe
    Accepts an audio file upload and returns the transcribed text.
    Optional: verify_speaker=true checks audio against the user's stored
    voice fingerprint and returns empty text if the speaker doesn't match.

POST /api/stt/save-whisper-transcript
    Silently saves a Whisper-accurate transcript to the call's
    caller_whisper_transcript / receiver_whisper_transcript field.
    Used by the frontend after a successful transcription so that
    post-call AI analysis can use the more accurate Whisper text.

GET /api/stt/status
    Returns model availability.
"""

import os
import shutil
import logging
import tempfile
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import JSONResponse
from bson import ObjectId
from pydantic import BaseModel

try:
    from backend.app.auth import AuthHandler
    from backend.app.models import UserInDB
    from backend.app.database import Database
    from backend.app.ai_processing.faster_whisper_stt import faster_whisper_stt
except ImportError:
    from app.auth import AuthHandler          # type: ignore
    from app.models import UserInDB           # type: ignore
    from app.database import Database         # type: ignore
    from app.ai_processing.faster_whisper_stt import faster_whisper_stt  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter()


# ----------------------------------------------------------------------- #
# Request / response schemas
# ----------------------------------------------------------------------- #

class SaveWhisperRequest(BaseModel):
    call_id: str
    text: str
    message_id: str | None = None
    persist_to_conversation: bool = False


# ----------------------------------------------------------------------- #
# Endpoints
# ----------------------------------------------------------------------- #

@router.get("/status")
async def stt_status():
    """Check whether the faster-whisper model is loaded and ready."""
    available = faster_whisper_stt.is_available()
    return {"available": available, "model": faster_whisper_stt.model_size}


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio chunk to transcribe (WebM, WAV, …)"),
    language: str = "en",
    verify_speaker: bool = Query(False, description="Check audio against stored voice fingerprint"),
    current_user: UserInDB = Depends(AuthHandler.get_current_user),
):
    """
    Transcribe an audio chunk uploaded from the browser's MediaRecorder.

    - **audio**: Binary audio data (WebM/Opus recommended from browser, WAV also works)
    - **language**: BCP-47 language code (default: 'en')
    - **verify_speaker**: When True, compares the audio to the user's stored
      voice fingerprint; returns empty text if it does not match.

    Returns:
        { "text": "...", "confidence": 0.98, "success": true }
    """
    if not faster_whisper_stt.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="faster-whisper model is not available on this server. "
                   "Install it with: pip install faster-whisper",
        )

    # Determine file extension from upload MIME type
    content_type = (audio.content_type or "").lower()
    if "wav" in content_type:
        suffix = ".wav"
    elif "ogg" in content_type:
        suffix = ".ogg"
    elif "mp4" in content_type or "m4a" in content_type:
        suffix = ".mp4"
    else:
        suffix = ".webm"  # default – browsers send WebM/Opus

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            shutil.copyfileobj(audio.file, tmp)
            tmp_path = tmp.name

        # Skip tiny files (< 1 KB = probably silence)
        file_size = os.path.getsize(tmp_path)
        if file_size < 1024:
            return JSONResponse({"text": "", "confidence": 0.0, "success": True})

        # ------------------------------------------------------------------
        # Optional speaker verification
        # ------------------------------------------------------------------
        if verify_speaker:
            stored_fp = getattr(current_user, "voice_fingerprint", None)
            if stored_fp and len(stored_fp) > 0:
                try:
                    from backend.app.ai_processing.voice_fingerprint import is_registered_speaker
                    with open(tmp_path, "rb") as f:
                        audio_bytes = f.read()
                    is_match, similarity = is_registered_speaker(audio_bytes, stored_fp, suffix=suffix)
                    if not is_match:
                        logger.debug(
                            "[STT] Speaker verification failed (sim=%.3f) for user=%s",
                            similarity, current_user.id
                        )
                        return JSONResponse({
                            "text": "",
                            "confidence": 0.0,
                            "success": True,
                            "speaker_verified": False,
                            "similarity": similarity,
                        })
                    logger.debug("[STT] Speaker verified (sim=%.3f) for user=%s", similarity, current_user.id)
                except Exception as vfe:
                    logger.warning("[STT] Voice fingerprint check skipped: %s", vfe)

        text, confidence = faster_whisper_stt.transcribe(tmp_path, language=language)
        logger.debug(f"[STT] user={current_user.id} size={file_size}B text={text!r}")
        return {"text": text, "confidence": confidence, "success": True}

    except Exception as exc:
        logger.error(f"[STT] Transcription failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {exc}",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/save-whisper-transcript")
async def save_whisper_transcript(
    payload: SaveWhisperRequest,
    current_user: UserInDB = Depends(AuthHandler.get_current_user),
):
    """
    Silently persist a Whisper-accurate transcript to the call document.

    The frontend calls this after /api/stt/transcribe returns a non-empty result.
    The text is stored in caller_whisper_transcript / receiver_whisper_transcript
    so the post-call AI analysis can use the more accurate Whisper version.
    This endpoint does NOT broadcast the text to the partner – that is handled
    separately by the Web Speech API path.
    """
    db = Database.get_db()

    try:
        call_id_obj = ObjectId(payload.call_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid call_id")

    call_data = db.calls.find_one({"_id": call_id_obj}, {"caller_id": 1, "receiver_id": 1})
    if not call_data:
        raise HTTPException(status_code=404, detail="Call not found")

    is_caller   = str(call_data.get("caller_id"))   == str(current_user.id)
    is_receiver = str(call_data.get("receiver_id")) == str(current_user.id)

    if not is_caller and not is_receiver:
        raise HTTPException(status_code=403, detail="Not part of this call")

    whisper_field = "caller_whisper_transcript" if is_caller else "receiver_whisper_transcript"
    transcript_field = "caller_transcript" if is_caller else "receiver_transcript"
    speaker_role = "caller" if is_caller else "receiver"
    cleaned = payload.text.strip()
    if not cleaned:
        return {"success": True}

    set_payload = {
        whisper_field: {
            "$concat": [
                {"$ifNull": [f"${whisper_field}", ""]},
                {
                    "$cond": [
                        {"$eq": [{"$ifNull": [f"${whisper_field}", ""]}, ""]},
                        "",
                        " ",
                    ]
                },
                cleaned,
            ]
        }
    }

    if payload.persist_to_conversation:
        conversation_item = {
            "message_id": payload.message_id or f"whisper-{uuid.uuid4().hex}",
            "speaker": speaker_role,
            "speaker_id": str(current_user.id),
            "text": cleaned,
            "timestamp": datetime.utcnow().isoformat(),
        }

        set_payload[transcript_field] = {
            "$trim": {
                "input": {
                    "$concat": [
                        {"$ifNull": [f"${transcript_field}", ""]},
                        {
                            "$cond": [
                                {"$eq": [{"$ifNull": [f"${transcript_field}", ""]}, ""]},
                                "",
                                " ",
                            ]
                        },
                        cleaned,
                    ]
                }
            }
        }

        # Only append when the last entry is not exactly the same speaker+text.
        set_payload["conversation"] = {
            "$let": {
                "vars": {
                    "existing": {"$ifNull": ["$conversation", []]}
                },
                "in": {
                    "$cond": [
                        {
                            "$and": [
                                {"$gt": [{"$size": "$$existing"}, 0]},
                                {"$eq": [{"$arrayElemAt": ["$$existing.speaker", -1]}, speaker_role]},
                                {"$eq": [{"$arrayElemAt": ["$$existing.text", -1]}, cleaned]},
                            ]
                        },
                        "$$existing",
                        {"$concatArrays": ["$$existing", [conversation_item]]},
                    ]
                },
            }
        }

    db.calls.update_one(
        {"_id": call_id_obj},
        [{"$set": set_payload}],
    )

    return {
        "success": True,
        "field": whisper_field,
        "persisted_to_conversation": payload.persist_to_conversation,
    }
