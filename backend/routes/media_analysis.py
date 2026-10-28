"""
Media Analysis Endpoints for Dhwani / EchoShield AI
Supports file uploads (audio/video) and YouTube URLs via UnifiedMediaPipeline.
Adheres strictly to zero-storage privacy policies: raw uploads are immediately purged
unless DHWANI_RETAIN_AUDIO=true is explicitly set.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, Optional
import uuid

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from ai.common.media_sources import FileAudioSource, VideoAudioSource, YouTubeAudioSource
from ai.common.common_pipeline import UnifiedMediaPipeline
from backend.websocket.dashboard import broadcast_event
from security.ssrf import validate_url_security

router = APIRouter(prefix="/analyze", tags=["Media Analysis"])

# Persistent in-memory cache for past analyses
ANALYSIS_STORE: Dict[str, Dict[str, Any]] = {}
_PIPELINE = UnifiedMediaPipeline()
MAX_MEDIA_UPLOAD_SIZE = int(os.getenv("MAX_MEDIA_UPLOAD_SIZE", str(50 * 1024 * 1024)))  # 50 MB
CHUNK_SIZE = 1024 * 1024


class YouTubeRequest(BaseModel):
    url: str


@router.post("/upload")
async def analyze_uploaded_file(request: Request, file: UploadFile = File(...)):
    """
    Ingest audio (.wav, .mp3, .m4a, .flac, .ogg) or video (.mp4, .mov, .mkv, .webm).
    Extracts 16 kHz mono audio and runs through the complete 5-model neural ensemble.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    filename = file.filename
    ext = Path(filename).suffix.lower()

    is_audio = ext in FileAudioSource.SUPPORTED_EXTENSIONS
    is_video = ext in VideoAudioSource.SUPPORTED_EXTENSIONS

    if not (is_audio or is_video):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Supported audio: {list(FileAudioSource.SUPPORTED_EXTENSIONS)}, video: {list(VideoAudioSource.SUPPORTED_EXTENSIONS)}",
        )

    # Pre-check Content-Length header
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_MEDIA_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"Uploaded file exceeds maximum permitted size of {MAX_MEDIA_UPLOAD_SIZE // (1024 * 1024)}MB.",
                )
        except ValueError:
            pass

    # Save to ephemeral temporary file with bounded streaming
    temp_dir = Path(tempfile.gettempdir()) / "dhwani_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4()}{ext}"

    total_size = 0
    with open(temp_path, "wb") as f_out:
        while chunk := await file.read(CHUNK_SIZE):
            total_size += len(chunk)
            if total_size > MAX_MEDIA_UPLOAD_SIZE:
                if temp_path.exists():
                    temp_path.unlink()
                raise HTTPException(
                    status_code=413,
                    detail=f"Uploaded file exceeds maximum permitted size of {MAX_MEDIA_UPLOAD_SIZE // (1024 * 1024)}MB.",
                )
            f_out.write(chunk)

    retain_audio = os.getenv("DHWANI_RETAIN_AUDIO", "false").lower() in ("true", "1", "yes")

    try:
        if is_audio:
            source = FileAudioSource(temp_path)
        else:
            source = VideoAudioSource(temp_path)

        analysis_id = str(uuid.uuid4())
        await broadcast_event("analysis_started", {"analysis_id": analysis_id, "filename": filename, "type": "upload"})

        result = _PIPELINE.analyze_source(source, analysis_id=analysis_id)
        result["source_metadata"]["original_filename"] = filename

        ANALYSIS_STORE[analysis_id] = result
        await broadcast_event("analysis_completed", result)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    finally:
        # Guarantee privacy: delete temporary upload file unless explicitly retained
        if not retain_audio and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


@router.post("/youtube")
async def analyze_youtube_url(req: YouTubeRequest):
    """
    Analyze speech in an authorized YouTube video URL.
    Extracts only the audio track, runs through UnifiedMediaPipeline, and purges all media.
    """
    if not req.url:
        raise HTTPException(status_code=400, detail="URL is required")

    # SSRF Protection: validate destination host and IP ranges
    is_safe, reason = validate_url_security(
        req.url,
        allowed_domains=["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"],
    )
    if not is_safe:
        raise HTTPException(status_code=400, detail=f"SSRF Protection: {reason}")

    try:
        source = YouTubeAudioSource(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    analysis_id = str(uuid.uuid4())
    await broadcast_event("analysis_started", {"analysis_id": analysis_id, "url": req.url, "type": "youtube"})

    try:
        result = _PIPELINE.analyze_source(source, analysis_id=analysis_id)
        ANALYSIS_STORE[analysis_id] = result
        await broadcast_event("analysis_completed", result)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube extraction failed: {str(e)}")


@router.get("/{analysis_id}")
async def get_analysis_result(analysis_id: str):
    """
    Retrieve stored analysis report by unique ID.
    """
    if analysis_id not in ANALYSIS_STORE:
        raise HTTPException(status_code=404, detail="Analysis report not found")
    return ANALYSIS_STORE[analysis_id]
