"""
voice_fingerprint.py – Lightweight voice fingerprint extraction and comparison.

Audio decoding strategy:
1) Try direct WAV decoding (no external binary required).
2) For WebM/MP4/OGG, normalize via ffmpeg to 16k mono WAV.
     ffmpeg binary resolution order:
     - FFMPEG_PATH env var
     - ffmpeg on PATH
     - imageio-ffmpeg bundled binary

Called from:
    - POST /api/users/enroll-voice   (enrollment, one-time per user)
    - POST /api/stt/transcribe       (optional speaker verification during calls)
"""

import io
import os
import math
import wave
import shutil
import tempfile
import subprocess
import logging
from typing import Optional, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Audio parameters
# --------------------------------------------------------------------------- #
SAMPLE_RATE   = 16_000
FRAME_SIZE    = 0.025      # 25 ms
FRAME_STRIDE  = 0.010      # 10 ms
N_MELS        = 40
N_MFCC        = 20
NFFT          = 512

# Speaker-match threshold (cosine similarity)
SIMILARITY_THRESHOLD = 0.78

# Embedding backend: "mfcc" (default) or "resemblyzer" (optional).
# Keep default as MFCC for reliability across environments.
VOICE_FP_MODEL = os.getenv("VOICE_FP_MODEL", "mfcc").strip().lower()

_RESEMBLYZER_ENCODER = None


# --------------------------------------------------------------------------- #
# Audio loading (ffmpeg → 16 kHz mono PCM)
# --------------------------------------------------------------------------- #

def _resample_linear(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Resample using linear interpolation (dependency-free fallback)."""
    if src_rate <= 0 or dst_rate <= 0 or len(samples) == 0:
        return np.asarray([], dtype=np.float32)
    if src_rate == dst_rate:
        return samples.astype(np.float32, copy=False)

    dst_len = int(round(len(samples) * float(dst_rate) / float(src_rate)))
    if dst_len <= 0:
        return np.asarray([], dtype=np.float32)

    src_x = np.arange(len(samples), dtype=np.float32)
    dst_x = np.linspace(0, len(samples) - 1, dst_len, dtype=np.float32)
    return np.interp(dst_x, src_x, samples).astype(np.float32)


def _decode_wav_bytes(audio_bytes: bytes) -> Optional[np.ndarray]:
    """Decode WAV bytes to mono float32 at SAMPLE_RATE without ffmpeg."""
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            src_rate = wf.getframerate()
            frame_count = wf.getnframes()
            raw = wf.readframes(frame_count)

        if frame_count <= 0:
            return None

        if sample_width == 1:
            data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            data = (data - 128.0) / 128.0
        elif sample_width == 2:
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32_768.0
        elif sample_width == 4:
            data = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2_147_483_648.0
        else:
            logger.warning("[VoiceFP] Unsupported WAV sample width: %s", sample_width)
            return None

        if channels > 1:
            data = data.reshape(-1, channels).mean(axis=1)

        if src_rate != SAMPLE_RATE:
            data = _resample_linear(data, src_rate, SAMPLE_RATE)

        return data.astype(np.float32, copy=False)

    except wave.Error:
        return None
    except Exception as exc:
        logger.warning("[VoiceFP] WAV decode failed: %s", exc)
        return None


def _resolve_ffmpeg_binary() -> Optional[str]:
    """Resolve an ffmpeg executable path from env/PATH/imageio-ffmpeg."""
    env_path = os.getenv("FFMPEG_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    from_path = shutil.which("ffmpeg")
    if from_path:
        return from_path

    try:
        import imageio_ffmpeg  # type: ignore

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled and os.path.exists(bundled):
            return bundled
    except Exception:
        pass

    return None

def _load_audio(audio_bytes: bytes, suffix: str = ".webm") -> Optional[np.ndarray]:
    """Convert audio bytes to 16 kHz mono float32."""
    if not audio_bytes:
        return None

    # Fast path: decode WAV directly with stdlib, no ffmpeg dependency.
    wav_samples = _decode_wav_bytes(audio_bytes)
    if wav_samples is not None and len(wav_samples) > 0:
        return wav_samples

    tmp_in = tmp_out = None
    try:
        ffmpeg_bin = _resolve_ffmpeg_binary()
        if not ffmpeg_bin:
            logger.warning(
                "[VoiceFP] ffmpeg not found (PATH/FFMPEG_PATH/imageio-ffmpeg). "
                "Cannot decode non-WAV audio formats."
            )
            return None

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp_in = f.name

        tmp_out = tmp_in + "_vfp.wav"

        result = subprocess.run(
            [
                ffmpeg_bin, "-y", "-loglevel", "error",
                "-i", tmp_in,
                "-ar", str(SAMPLE_RATE),
                "-ac", "1",
                "-f", "wav",
                tmp_out,
            ],
            capture_output=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.warning("[VoiceFP] ffmpeg error: %s",
                           result.stderr.decode(errors="replace")[:300])
            return None

        with open(tmp_out, "rb") as f:
            wav_bytes = f.read()

        return _decode_wav_bytes(wav_bytes)

    except Exception as exc:
        logger.error("[VoiceFP] load_audio failed: %s", exc)
        return None
    finally:
        for p in (tmp_in, tmp_out):
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except OSError:
                    pass


# --------------------------------------------------------------------------- #
# MFCC extraction (pure NumPy)
# --------------------------------------------------------------------------- #

def _mel_filterbank(n_mels: int, sr: int, nfft: int) -> np.ndarray:
    low_mel  = 0.0
    high_mel = 2_595 * math.log10(1.0 + (sr / 2) / 700)
    mel_pts  = np.linspace(low_mel, high_mel, n_mels + 2)
    hz_pts   = 700.0 * (10.0 ** (mel_pts / 2_595) - 1.0)
    bins     = np.floor((nfft + 1) * hz_pts / sr).astype(int)

    fbank = np.zeros((n_mels, nfft // 2 + 1))
    for m in range(1, n_mels + 1):
        lo, mid, hi = bins[m - 1], bins[m], bins[m + 1]
        if mid > lo:
            fbank[m - 1, lo:mid] = (np.arange(lo, mid) - lo) / (mid - lo)
        if hi > mid:
            fbank[m - 1, mid:hi] = (hi - np.arange(mid, hi)) / (hi - mid)
    return fbank


_FBANK: Optional[np.ndarray] = None   # cached after first call


def _compute_mfcc(samples: np.ndarray) -> np.ndarray:
    """Return MFCC matrix (n_frames × N_MFCC)."""
    global _FBANK

    frame_len  = int(round(FRAME_SIZE   * SAMPLE_RATE))
    frame_step = int(round(FRAME_STRIDE * SAMPLE_RATE))

    # Pre-emphasis
    emph = np.append(samples[0], samples[1:] - 0.97 * samples[:-1])

    # Framing
    n_frames = max(1, 1 + (len(emph) - frame_len) // frame_step)
    idx = (
        np.tile(np.arange(frame_len), (n_frames, 1))
        + np.tile(np.arange(0, n_frames * frame_step, frame_step),
                  (frame_len, 1)).T
    )
    idx = np.clip(idx, 0, len(emph) - 1)
    frames = emph[idx] * np.hamming(frame_len)

    # Power spectrum
    mag   = np.abs(np.fft.rfft(frames, n=NFFT))
    power = (1.0 / NFFT) * mag ** 2

    # Mel filterbank
    if _FBANK is None:
        _FBANK = _mel_filterbank(N_MELS, SAMPLE_RATE, NFFT)

    energies = np.dot(power, _FBANK.T)
    energies  = np.where(energies == 0, np.finfo(float).eps, energies)
    log_e     = 20.0 * np.log10(energies)

    # DCT
    n_filt = log_e.shape[1]
    dct    = np.array([
        [math.cos(math.pi * k * (2 * n + 1) / (2 * n_filt)) for n in range(n_filt)]
        for k in range(N_MFCC)
    ])
    mfcc = np.dot(log_e, dct.T)

    # Cepstral mean normalisation
    mfcc -= np.mean(mfcc, axis=0)
    return mfcc


def _delta(feat: np.ndarray, N: int = 2) -> np.ndarray:
    padded = np.pad(feat, ((N, N), (0, 0)), mode="edge")
    d      = np.zeros_like(feat)
    denom  = 2.0 * sum(i * i for i in range(1, N + 1))
    for i in range(1, N + 1):
        d += i * (padded[N + i : N + i + len(feat)] - padded[N - i : N - i + len(feat)])
    return d / denom


def _extract_resemblyzer_embedding(samples: np.ndarray) -> Optional[List[float]]:
    """Extract encoder-style speaker embedding using free resemblyzer package."""
    global _RESEMBLYZER_ENCODER

    try:
        from resemblyzer import VoiceEncoder  # type: ignore
    except Exception:
        logger.warning(
            "[VoiceFP] VOICE_FP_MODEL=%s but resemblyzer is not installed; using MFCC fallback.",
            VOICE_FP_MODEL,
        )
        return None

    try:
        if _RESEMBLYZER_ENCODER is None:
            _RESEMBLYZER_ENCODER = VoiceEncoder()

        # samples are already mono float32 at 16kHz from _load_audio.
        emb = np.asarray(_RESEMBLYZER_ENCODER.embed_utterance(samples), dtype=np.float32).reshape(-1)
        if emb.size == 0:
            return None

        norm = np.linalg.norm(emb)
        if norm > 1e-9:
            emb /= norm

        return emb.tolist()

    except Exception as exc:
        logger.warning("[VoiceFP] Resemblyzer extraction failed, using MFCC fallback: %s", exc)
        return None


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def extract_voice_fingerprint(
    audio_bytes: bytes, suffix: str = ".webm"
) -> Optional[List[float]]:
    """
    Extract a normalised voice-fingerprint vector from *audio_bytes*.

    Returns a list of floats (length 4 × N_MFCC = 80) on success, or None.
    The vector is L2-normalised so cosine similarity == dot product.
    """
    samples = _load_audio(audio_bytes, suffix=suffix)
    if samples is None or len(samples) < SAMPLE_RATE:
        logger.warning("[VoiceFP] Audio too short (< 1 s) or load failed")
        return None

    # Optional encoder-style embedding backend (Resemblyzer), free library.
    if VOICE_FP_MODEL in {"resemblyzer", "encoder", "speech_encoder"}:
        emb = _extract_resemblyzer_embedding(samples)
        if emb is not None:
            return emb

    try:
        mfcc    = _compute_mfcc(samples)
        delta1  = _delta(mfcc)
        delta2  = _delta(delta1)
        full    = np.concatenate([mfcc, delta1, delta2], axis=1)   # (T, 60)

        # Statistical pooling (mean + std) → 120-dim
        mean_v = np.mean(full, axis=0)
        std_v  = np.std(full,  axis=0)
        embed  = np.concatenate([mean_v, std_v])

        # L2 normalise
        norm = np.linalg.norm(embed)
        if norm > 1e-9:
            embed /= norm

        return embed.tolist()

    except Exception as exc:
        logger.error("[VoiceFP] Feature extraction failed: %s", exc)
        return None


def estimate_audio_duration_seconds(
    audio_bytes: bytes, suffix: str = ".webm"
) -> Optional[float]:
    """Return decoded audio duration in seconds after normalization."""
    samples = _load_audio(audio_bytes, suffix=suffix)
    if samples is None:
        return None
    return float(len(samples) / SAMPLE_RATE)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Cosine similarity between two fingerprint vectors."""
    a = np.asarray(v1, dtype=np.float32).reshape(-1)
    b = np.asarray(v2, dtype=np.float32).reshape(-1)
    if a.size == 0 or b.size == 0 or a.shape != b.shape:
        return 0.0
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 1e-9 else 0.0


def is_registered_speaker(
    audio_bytes: bytes,
    stored_fingerprint: List[float],
    suffix: str = ".webm",
    threshold: float = SIMILARITY_THRESHOLD,
) -> Tuple[bool, float]:
    """
    Check whether *audio_bytes* was spoken by the registered speaker.

    Returns (is_match: bool, similarity: float).
    Returns (False, 0.0) if fingerprint extraction fails.
    """
    fp = extract_voice_fingerprint(audio_bytes, suffix=suffix)
    if fp is None:
        return False, 0.0
    sim = cosine_similarity(fp, stored_fingerprint)
    return sim >= threshold, round(sim, 4)
