"""
Automated Tests for Unified Media Pipeline and Audio Sources
Validates:
1. FileAudioSource loading, mono conversion, and 16 kHz normalization.
2. VideoAudioSource extension validation.
3. YouTubeAudioSource URL validation and video ID extraction.
4. UnifiedMediaPipeline full execution on real speech.
"""

from pathlib import Path
import unittest
import numpy as np

from ai.common.media_sources import FileAudioSource, VideoAudioSource, YouTubeAudioSource
from ai.common.common_pipeline import UnifiedMediaPipeline


class TestUnifiedMedia(unittest.TestCase):
    def setUp(self):
        self.pipeline = UnifiedMediaPipeline()
        self.wav_path = Path("real_speech.wav").resolve()

    def test_file_audio_source_wav(self):
        self.assertTrue(self.wav_path.exists(), "real_speech.wav must exist")
        source = FileAudioSource(self.wav_path)
        self.assertEqual(source.get_source_type(), "file")

        metadata = source.get_metadata()
        self.assertEqual(metadata["filename"], "real_speech.wav")
        self.assertEqual(metadata["extension"], ".wav")

        audio, sr = source.load_audio()
        self.assertEqual(sr, 16000)
        self.assertEqual(audio.dtype, np.float32)
        self.assertGreater(len(audio), 64600)
        self.assertTrue(np.all(audio >= -1.0) and np.all(audio <= 1.0))

    def test_video_audio_source_extensions(self):
        # Valid extensions accepted
        self.assertIn(".mp4", VideoAudioSource.SUPPORTED_EXTENSIONS)
        self.assertIn(".mkv", VideoAudioSource.SUPPORTED_EXTENSIONS)
        self.assertIn(".webm", VideoAudioSource.SUPPORTED_EXTENSIONS)

        # Nonexistent file should raise FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            VideoAudioSource("non_existent_video.mp4")

    def test_youtube_url_validation(self):
        # Valid standard URLs
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        ]
        for u in valid_urls:
            yt = YouTubeAudioSource(u)
            self.assertEqual(yt.video_id, "dQw4w9WgXcQ")
            self.assertEqual(yt.get_source_type(), "youtube")

        # Invalid URLs
        invalid_urls = [
            "https://notyoutube.com/video123",
            "https://youtube.com/invalid_path",
            "not_a_url",
        ]
        for u in invalid_urls:
            with self.assertRaises(ValueError):
                YouTubeAudioSource(u)

    def test_pipeline_on_real_speech(self):
        source = FileAudioSource(self.wav_path)
        report = self.pipeline.analyze_source(source)

        # Standard AnalysisResult contract assertions
        self.assertIn("analysis_id", report)
        self.assertEqual(report["source_type"], "file")
        self.assertGreater(report["windows_analyzed"], 0)
        self.assertIn("risk_score", report)
        self.assertIn(report["risk_level"], ["LOW", "SUSPICIOUS", "HIGH"])
        self.assertIn("evidence_hash", report)
        self.assertEqual(len(report["evidence_hash"]), 64)  # SHA-256 hex string
        self.assertIn("fusion", report)
        self.assertIn("temporal", report)


if __name__ == "__main__":
    unittest.main()
