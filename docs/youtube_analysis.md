# YouTube Speech Forensics Guide

Dhwani supports inspecting public authorized YouTube videos for AI voice synthesis and deepfake cloning.

---

## 1. Compliance & Legal Constraints

- Adheres strictly to YouTube Terms of Service.
- Does not bypass DRM, access controls, or private/restricted content.
- Extracts purely the audio stream; video streams are never retained.
- Deletes all temporary audio files immediately after analysis.

---

## 2. Extraction Prerequisites

YouTube analysis requires `yt-dlp` and `ffmpeg`:

```powershell
pip install yt-dlp
```

---

## 3. Supported URL Schemas

- Standard Watch URLs: `https://www.youtube.com/watch?v=VIDEO_ID`
- Shortened URLs: `https://youtu.be/VIDEO_ID`
- YouTube Shorts: `https://www.youtube.com/shorts/VIDEO_ID`

---

## 4. API Usage

Send a POST request to `/api/analyze/youtube`:

```bash
curl -X POST http://localhost:8000/api/analyze/youtube \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

The response returns the canonical Dhwani `AnalysisResult` JSON schema including model breakdown, speech duration, and SHA-256 evidence hash.
