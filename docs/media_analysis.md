# Unified Media Analysis Guide

Dhwani provides a standardized ingestion and analysis pipeline for all static and streamed media.

---

## 1. Supported Media Formats

### Audio Files:
- `.wav`: PCM standard WAV (any sample rate, 16/24/32-bit).
- `.mp3`: MPEG-1 Audio Layer III.
- `.m4a`: Advanced Audio Coding (AAC/ALAC).
- `.flac`: Free Lossless Audio Codec.
- `.ogg`: Ogg Vorbis/Opus.

### Video Containers:
- `.mp4`: MPEG-4 Part 14.
- `.mov`: Apple QuickTime Movie.
- `.mkv`: Matroska Multimedia Container.
- `.webm`: WebM open media format.

---

## 2. Ingestion & Conversion Pipeline

For video containers:
1. Dhwani invokes FFmpeg directly to extract the audio stream:
   ```bash
   ffmpeg -v error -i input.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 -f s16le pipe:1
   ```
2. Video frames are **never stored or processed by the voice model**, minimizing memory overhead and processing time.
3. The extracted audio is converted into a normalized float32 array in `[-1.0, 1.0]`.

---

## 3. Privacy & Ephemeral Buffer Policy

- Uploaded files are written to ephemeral storage (`tempfile.gettempdir()`).
- Immediately upon completion of the neural ensemble evaluation, the uploaded file is purged from disk.
- If persistent audio retention is required for legal compliance, set:
  ```env
  DHWANI_RETAIN_AUDIO=true
  ```
- By default, Dhwani retains only the forensic JSON metadata and the SHA-256 evidence hash of the audio.
