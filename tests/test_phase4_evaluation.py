"""
Phase 4: Real-World Voice Deepfake Evaluation Unit Tests
========================================================
Validates:
- Audio content hash computation (SHA-256) and content duplicate detection
- Split leakage verification (disjoint speaker ID, path, and content hash checking)
- Latency percentile calculation (median p50, p95)
- Per-attack breakdown metrics computation
- UNCALIBRATED fallback threshold logic when real labeled validation data is insufficient (< 100 samples)
- Robustness perturbation generators (resampling, SNR additive noise, duration truncation, companding)
- ASVspoof protocol converter edge cases
"""

import json
from pathlib import Path
import tempfile
import numpy as np
import pytest
import soundfile as sf

from scripts.evaluation.dataset import (
    AudioValidator,
    DatasetManifestLoader,
    ManifestRecord,
    verify_split_leakage,
)
from scripts.evaluation.metrics import (
    compute_latency_statistics,
    compute_per_attack_breakdown,
)
from scripts.evaluation.calibrate_thresholds import calibrate_thresholds
from scripts.evaluation.asvspoof_to_manifest import convert_asvspoof_protocol
from scripts.evaluation.robustness import (
    apply_additive_noise,
    apply_duration_truncation,
    apply_resampling,
    apply_telephony_companding,
)


class TestAudioContentHashAndDuplicateDetection:
    """Tests for content-hash duplicate detection and audio validation."""

    def test_compute_content_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "audio1.wav"
            f2 = Path(tmpdir) / "audio2_copy.wav"
            f3 = Path(tmpdir) / "audio3_diff.wav"

            samples1 = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)).astype(np.float32)
            samples2 = samples1.copy()
            samples3 = np.cos(2 * np.pi * 880 * np.linspace(0, 1, 16000)).astype(np.float32)

            sf.write(str(f1), samples1, 16000)
            sf.write(str(f2), samples2, 16000)
            sf.write(str(f3), samples3, 16000)

            hash1 = AudioValidator.compute_content_hash(f1)
            hash2 = AudioValidator.compute_content_hash(f2)
            hash3 = AudioValidator.compute_content_hash(f3)

            assert hash1 == hash2, "Identical audio files must have identical SHA-256 hashes"
            assert hash1 != hash3, "Different audio files must have distinct hashes"

    def test_duplicate_content_hash_manifest_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f1 = Path(tmpdir) / "file1.wav"
            f2 = Path(tmpdir) / "file2_renamed.wav"

            data = np.zeros(16000, dtype=np.float32)
            sf.write(str(f1), data, 16000)
            sf.write(str(f2), data, 16000)

            m = Path(tmpdir) / "manifest.csv"
            m.write_text(
                f"audio_path,label\n"
                f"{f1.name},bonafide\n"
                f"{f2.name},bonafide\n",
                encoding="utf-8",
            )

            loader = DatasetManifestLoader(dataset_root=tmpdir, validate_audio=True)
            records, report = loader.load_manifest(m)

            assert len(records) == 2
            assert report["duplicate_content_hashes_detected"] == 1
            assert records[0].content_hash == records[1].content_hash


class TestSplitLeakageVerification:
    """Tests for leak-safe separation across train/val/test splits."""

    def test_leakage_free_splits(self):
        train = [
            ManifestRecord(
                audio_path=Path("/data/train/spk1_01.wav"),
                label="bonafide",
                binary_label=0,
                speaker_id="SPK_001",
                content_hash="hash_001",
            ),
            ManifestRecord(
                audio_path=Path("/data/train/spk2_01.wav"),
                label="spoof",
                binary_label=1,
                speaker_id="SPK_002",
                content_hash="hash_002",
            ),
        ]
        val = [
            ManifestRecord(
                audio_path=Path("/data/val/spk3_01.wav"),
                label="bonafide",
                binary_label=0,
                speaker_id="SPK_003",
                content_hash="hash_003",
            ),
        ]
        test = [
            ManifestRecord(
                audio_path=Path("/data/test/spk4_01.wav"),
                label="spoof",
                binary_label=1,
                speaker_id="SPK_004",
                content_hash="hash_004",
            ),
        ]

        report = verify_split_leakage(train, val, test)
        assert report["leakage_detected"] is False
        assert report["status"] == "LEAKAGE_FREE"
        assert len(report["speaker_overlaps"]) == 0
        assert len(report["path_overlaps"]) == 0
        assert len(report["hash_overlaps"]) == 0

    def test_detects_speaker_leakage(self):
        train = [
            ManifestRecord(
                audio_path=Path("/data/train/spk1_01.wav"),
                label="bonafide",
                binary_label=0,
                speaker_id="SPK_001",
                content_hash="hash_001",
            ),
        ]
        val = [
            ManifestRecord(
                audio_path=Path("/data/val/spk1_02.wav"),
                label="spoof",
                binary_label=1,
                speaker_id="SPK_001",  # Same speaker in val!
                content_hash="hash_002",
            ),
        ]

        report = verify_split_leakage(train, val)
        assert report["leakage_detected"] is True
        assert report["status"] == "LEAKAGE_DETECTED"
        assert len(report["speaker_overlaps"]) == 1
        assert "SPK_001" in report["speaker_overlaps"][0]["overlapping_speakers"]

    def test_detects_content_hash_leakage(self):
        train = [
            ManifestRecord(
                audio_path=Path("/data/train/utterance_a.wav"),
                label="bonafide",
                binary_label=0,
                speaker_id="SPK_A",
                content_hash="identical_hash_123",
            ),
        ]
        test = [
            ManifestRecord(
                audio_path=Path("/data/test/utterance_renamed.wav"),
                label="bonafide",
                binary_label=0,
                speaker_id="SPK_B",
                content_hash="identical_hash_123",  # Identical content!
            ),
        ]

        report = verify_split_leakage(train, val_records=[], test_records=test)
        assert report["leakage_detected"] is True
        assert len(report["hash_overlaps"]) == 1


class TestLatencyAndPerAttackMetrics:
    """Tests for latency statistics and attack category metrics."""

    def test_latency_statistics_calculation(self):
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        stats = compute_latency_statistics(latencies)

        assert stats["count"] == 10
        assert stats["mean_ms"] == 55.0
        assert stats["median_p50_ms"] == 55.0
        assert stats["p95_ms"] == 95.5
        assert stats["min_ms"] == 10.0
        assert stats["max_ms"] == 100.0

    def test_latency_statistics_empty_list(self):
        stats = compute_latency_statistics([])
        assert stats["count"] == 0
        assert stats["mean_ms"] is None
        assert stats["median_p50_ms"] is None

    def test_per_attack_breakdown_metrics(self):
        records = [
            # Bona fide
            {"binary_ground_truth": 0, "fused_spoof_probability": 0.10, "attack_type": None},
            {"binary_ground_truth": 0, "fused_spoof_probability": 0.30, "attack_type": None},
            {"binary_ground_truth": 0, "fused_spoof_probability": 0.80, "attack_type": None},  # FP at 0.50
            # Attack A01
            {"binary_ground_truth": 1, "fused_spoof_probability": 0.90, "attack_type": "A01"},  # TP
            {"binary_ground_truth": 1, "fused_spoof_probability": 0.85, "attack_type": "A01"},  # TP
            # Attack A02
            {"binary_ground_truth": 1, "fused_spoof_probability": 0.20, "attack_type": "A02"},  # FN at 0.50
            {"binary_ground_truth": 1, "fused_spoof_probability": 0.95, "attack_type": "A02"},  # TP
        ]

        breakdown = compute_per_attack_breakdown(records, decision_threshold=0.50)

        # Check bona fide
        bf = breakdown["bona_fide_baseline"]
        assert bf["total_samples"] == 3
        assert bf["correct_genuine_tn"] == 2
        assert bf["false_alarm_fp"] == 1
        assert bf["false_alarm_rate_far"] == pytest.approx(1 / 3, abs=0.001)

        # Check Attack A01
        a01 = breakdown["attack_breakdown"]["A01"]
        assert a01["total_samples"] == 2
        assert a01["detected_spoofs_tp"] == 2
        assert a01["missed_spoofs_fn"] == 0
        assert a01["detection_rate_recall"] == 1.0

        # Check Attack A02
        a02 = breakdown["attack_breakdown"]["A02"]
        assert a02["total_samples"] == 2
        assert a02["detected_spoofs_tp"] == 1
        assert a02["missed_spoofs_fn"] == 1
        assert a02["detection_rate_recall"] == 0.5


class TestThresholdCalibrationFallback:
    """Verifies that insufficient sample sizes trigger UNCALIBRATED fallback status."""

    def test_uncalibrated_status_on_small_validation_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pred_file = Path(tmpdir) / "small_preds.jsonl"
            # Write 5 samples (< 100)
            rows = [
                {"binary_ground_truth": 0, "fused_spoof_probability": 0.15},
                {"binary_ground_truth": 0, "fused_spoof_probability": 0.25},
                {"binary_ground_truth": 0, "fused_spoof_probability": 0.35},
                {"binary_ground_truth": 1, "fused_spoof_probability": 0.85},
                {"binary_ground_truth": 1, "fused_spoof_probability": 0.95},
            ]
            with open(pred_file, "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r) + "\n")

            out_config = Path(tmpdir) / "calibrated.json"
            res = calibrate_thresholds(
                predictions_file=pred_file,
                output_config=out_config,
                objective="eer",
                min_samples_for_calibration=100,
            )

            assert res["calibration_status"] == "UNCALIBRATED"
            assert res["recommended_threshold"] == 0.5000, "Must fall back to 0.5000 default"
            assert "Insufficient labeled data" in res["status_note"]


class TestRobustnessPerturbations:
    """Tests for audio perturbation operators."""

    def test_resampling_8khz(self):
        orig_sr = 16000
        target_sr = 8000
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, orig_sr)).astype(np.float32)

        resampled, sr = apply_resampling(audio, orig_sr, target_sr)
        assert sr == 8000
        assert len(resampled) == 8000

    def test_additive_noise_snr(self):
        audio = np.ones(16000, dtype=np.float32) * 0.5  # Power = 0.25
        noisy_20 = apply_additive_noise(audio, snr_db=20.0, rng_seed=42)
        noisy_0 = apply_additive_noise(audio, snr_db=0.0, rng_seed=42)

        # 0 dB noise must have significantly higher variance than 20 dB noise
        diff_20 = np.var(noisy_20 - audio)
        diff_0 = np.var(noisy_0 - audio)
        assert diff_0 > diff_20

    def test_duration_truncation(self):
        audio = np.ones(16000, dtype=np.float32)  # 1.0 second at 16 kHz
        truncated_half_sec = apply_duration_truncation(audio, sample_rate=16000, duration_sec=0.5)
        assert len(truncated_half_sec) == 8000

        # Truncating longer than audio returns original
        untouched = apply_duration_truncation(audio, sample_rate=16000, duration_sec=2.0)
        assert len(untouched) == 16000

    def test_telephony_companding_preserves_bounds(self):
        audio = np.linspace(-1.0, 1.0, 1000, dtype=np.float32)
        companded = apply_telephony_companding(audio)
        assert np.all(companded >= -1.0)
        assert np.all(companded <= 1.0)


class TestASVspoofProtocolConverter:
    """Tests for ASVspoof protocol parsing to CSV manifest."""

    def test_protocol_conversion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            td = Path(tmpdir)
            audio_dir = td / "flac"
            audio_dir.mkdir()

            # Create mock audio files
            f1 = audio_dir / "LA_0001.flac"
            f2 = audio_dir / "LA_0002.flac"
            data = np.zeros(1600, dtype=np.float32)
            sf.write(str(f1), data, 16000)
            sf.write(str(f2), data, 16000)

            proto_file = td / "protocol.txt"
            proto_file.write_text(
                "LA_0039 LA_0001 - - bonafide\n"
                "LA_0039 LA_0002 - A01 spoof\n",
                encoding="utf-8",
            )

            out_csv = td / "manifest.csv"
            count = convert_asvspoof_protocol(
                protocol_file=proto_file,
                audio_dir=audio_dir,
                output_manifest=out_csv,
                subset_name="eval",
            )

            assert count == 2
            assert out_csv.is_file()

            # Load generated manifest
            loader = DatasetManifestLoader(dataset_root=audio_dir, validate_audio=True)
            recs, report = loader.load_manifest(out_csv)
            assert len(recs) == 2
            assert recs[0].label == "bonafide"
            assert recs[0].speaker_id == "LA_0039"
            assert recs[1].label == "spoof"
            assert recs[1].attack_type == "A01"
            assert recs[1].subset == "eval"
