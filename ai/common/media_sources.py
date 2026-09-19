"""
Unified AudioSource Abstractions for Dhwani / EchoShield AI
Enforces a single common audio contract across Phone, Microphone, File, Video, and YouTube streams.
All sources converge into normalized 16 kHz mono float32 audio arrays [-1.0, 1.0].
"""

from abc import ABC, abstractmethod
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Dict, Optional, Tuple
import numpy as np
import soundfile as sf
import librosa


class AudioSource(ABC):
    """Abstract base class for all Dhwani audio ingestion sources."""

    @abstractmethod
    def get_source_type(self) -> str:
        """Return source identifier: 'file', 'video', 'youtube', 'microphone', 'phone'."""
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Return source metadata (filename, duration, format, etc.)."""
        pass

    @abstractmethod
    def load_audio(self) -> Tuple[np.ndarray, int]:
        """
        Load, extract, resample, and normalize audio to (float32_array, sample_rate).
        Guaranteed to return 16000 Hz mono float32 in [-1.0, 1.0].
        """
        pass


class FileAudioSource(AudioSource):
    """Handles audio file formats: .wav, .mp3, .m4a, .flac, .ogg."""

    SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".wma"}

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path).resolve()
        if not self.file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {self.file_path}")

        ext = self.file_path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported audio format '{ext}'. Supported: {self.SUPPORTED_EXTENSIONS}")

    def get_source_type(self) -> str:
        return "file"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "filename": self.file_path.name,
            "extension": self.file_path.suffix.lower(),
            "file_size_bytes": self.file_path.stat().st_size,
        }

    def load_audio(self) -> Tuple[np.ndarray, int]:
        ext = self.file_path.suffix.lower()
        try:
            # First try soundfile (fastest for WAV/FLAC/OGG)
            audio, sr = sf.read(str(self.file_path), dtype="float32")
        except Exception:
            # Fall back to librosa/ffmpeg (robust for MP3/M4A/AAC)
            audio, sr = librosa.load(str(self.file_path), sr=16000, mono=True)
            return audio.astype(np.float32), 16000

        # Convert stereo to mono
        if audio.ndim > 1:
            audio = np.mean(audio, axis=-1)

        # Resample to 16000 Hz if needed
        if sr != 16000:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
            sr = 16000

        audio = np.clip(audio, -1.0, 1.0).astype(np.float32)
        return audio, 16000


class VideoAudioSource(AudioSource):
    """
    Extracts purely the audio track from video files (.mp4, .mov, .mkv, .webm, .avi)
    using FFmpeg without saving or retaining raw video frames in memory.
    """

    SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".flv"}

    def __init__(self, video_path: str | Path):
        self.video_path = Path(video_path).resolve()
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        ext = self.video_path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported video format '{ext}'. Supported: {self.SUPPORTED_EXTENSIONS}")

    def get_source_type(self) -> str:
        return "video"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "filename": self.video_path.name,
            "extension": self.video_path.suffix.lower(),
            "file_size_bytes": self.video_path.stat().st_size,
        }

    def load_audio(self) -> Tuple[np.ndarray, int]:
        """
        Stream audio directly out of the video container using FFmpeg to 16 kHz mono 16-bit PCM.
        """
        cmd = [
            "ffmpeg",
            "-v", "error",
            "-i", str(self.video_path),
            "-vn",  # No video stream
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-f", "s16le",
            "pipe:1",
        ]

        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            raw_pcm = result.stdout
            if not raw_pcm:
                raise ValueError(f"No audio stream found in video container: {self.video_path.name}")

            audio_int16 = np.frombuffer(raw_pcm, dtype=np.int16)
            audio_f32 = audio_int16.astype(np.float32) / 32768.0
            return np.clip(audio_f32, -1.0, 1.0), 16000
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"FFmpeg audio extraction failed: {err_msg}")


class YouTubeAudioSource(AudioSource):
    """
    Validates and extracts audio track from authorized YouTube URLs.
    Adheres strictly to platform terms: retrieves audio stream, avoids storing video,
    and cleans up temporary files immediately after processing.
    """

    YOUTUBE_REGEX = re.compile(
        r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})"
    )

    def __init__(self, url: str):
        self.url = url.strip()
        match = self.YOUTUBE_REGEX.match(self.url)
        if not match:
            raise ValueError(
                "Invalid YouTube URL. Please provide a valid URL (e.g., https://www.youtube.com/watch?v=... or https://youtu.be/...)"
            )
        self.video_id = match.group(4)
        self.temp_audio_path: Optional[Path] = None

    def get_source_type(self) -> str:
        return "youtube"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "source_url": self.url,
            "video_id": self.video_id,
        }

    def load_audio(self) -> Tuple[np.ndarray, int]:
        """
        Download only the audio stream into a temporary WAV file, load it,
        and remove the temporary file immediately.
        """
        try:
            import yt_dlp
        except ImportError:
            raise RuntimeError(
                "yt-dlp is required for YouTube audio extraction. Please install with: pip install yt-dlp"
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            self.temp_audio_path = Path(tmp.name)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(self.temp_audio_path.with_suffix("")),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "192",
                }
            ],
            "postprocessor_args": ["-ar", "16000", "-ac", "1"],
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])

            actual_wav = self.temp_audio_path.with_suffix(".wav")
            if not actual_wav.exists():
                raise FileNotFoundError(f"Failed to extract audio from YouTube URL: {self.url}")

            audio, sr = sf.read(str(actual_wav), dtype="float32")
            if audio.ndim > 1:
                audio = np.mean(audio, axis=-1)
            if sr != 16000:
                audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

            return np.clip(audio, -1.0, 1.0).astype(np.float32), 16000

        finally:
            # Guaranteed cleanup: delete temporary audio file
            for p in [self.temp_audio_path, self.temp_audio_path.with_suffix(".wav")]:
                if p and p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass


class MicrophoneAudioSource(AudioSource):
    """Captures live speech from the system microphone at 16 kHz mono."""

    def __init__(self, duration_sec: float = 4.0375):
        self.duration_sec = duration_sec

    def get_source_type(self) -> str:
        return "microphone"

    def get_metadata(self) -> Dict[str, Any]:
        return {"duration_sec": self.duration_sec, "sample_rate": 16000}

    def load_audio(self) -> Tuple[np.ndarray, int]:
        import sounddevice as sd
        num_samples = int(self.duration_sec * 16000)
        audio = sd.rec(num_samples, samplerate=16000, channels=1, dtype="float32")
        sd.wait()
        return np.clip(audio.reshape(-1), -1.0, 1.0), 16000
