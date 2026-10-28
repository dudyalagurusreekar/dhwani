"""
Phase 2: Comprehensive Test Suite for Labeled-Data Evaluation & Threshold Calibration
=====================================================================================
Covers:
- Dataset manifest parsing, relative/absolute path resolution, and duplicate detection
- Label canonicalization and strict rejection of ambiguous labels
- Audio validation: missing files, empty files, corrupt headers, non-finite samples
- Score direction and decision rule verification (higher is more spoof)
- Metric calculations against analytical ground truth (confusion matrix, FAR, FRR, F1)
- ROC-AUC and EER calculation including edge cases (single class, score ties)
- Threshold calibration runner and versioned artifact generation
- End-to-end smoke evaluation runner execution and output schema compliance
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
    LabelCanonicalizer,
    ManifestRecord,
)
from scripts.evaluation.metrics import (
    compute_confusion_matrix,
    compute_eer,
    compute_full_evaluation_metrics,
    compute_hard_decision_metrics,
    compute_roc_and_auc,
)
from scripts.evaluation.calibrate_thresholds import calibrate_thresholds
from scripts.evaluation.evaluate import run_evaluation


class TestManifestAndDatasetLoader:
    """Tests for dataset manifest ingestion, path resolution, and audio validation."""

    def test_label_canonicalization(self):
        # Genuine / bonafide variants
        for raw in ["bonafide", "bona-fide", "BONA_FIDE", "genuine", "real", "0", 0]:
            assert LabelCanonicalizer.canonicalize(raw) == "bonafide"
            assert LabelCanonicalizer.label_to_binary(raw) == 0

        # Spoof / fake variants
        for raw in ["spoof", "fake", "SYNTHETIC", "clone", "attack", "1", 1]:
            assert LabelCanonicalizer.canonicalize(raw) == "spoof"
            assert LabelCanonicalizer.label_to_binary(raw) == 1

        # Ambiguous / unsupported labels must raise ValueError
        for bad in ["unknown", "maybe", "human_or_ai", "2", None, ""]:
            with pytest.raises(ValueError):
                LabelCanonicalizer.canonicalize(bad)

    def test_valid_manifest_loading(self):
        manifest_path = Path("tests/fixtures/sample_manifest.csv")
        dataset_root = Path("tests/fixtures/audio_smoke")

        loader = DatasetManifestLoader(dataset_root=dataset_root, validate_audio=True)
        records, report = loader.load_manifest(manifest_path)

        assert len(records) == 5
        assert report["valid_records_count"] == 5
        assert report["invalid_records_count"] == 0
        assert report["bonafide_count"] == 3
        assert report["spoof_count"] == 2

        # Check record attributes
        rec0 = records[0]
        assert rec0.audio_path.is_file()
        assert rec0.label == "bonafide"
        assert rec0.binary_label == 0
        assert rec0.speaker_id == "SPK_001"
        assert rec0.sample_rate == 16000

    def test_subset_filtering(self):
        manifest_path = Path("tests/fixtures/sample_manifest.csv")
        dataset_root = Path("tests/fixtures/audio_smoke")

        loader = DatasetManifestLoader(dataset_root=dataset_root, validate_audio=True)
        dev_records, _ = loader.load_manifest(manifest_path, subset_filter="dev")
        eval_records, _ = loader.load_manifest(manifest_path, subset_filter="eval")

        assert len(dev_records) == 3
        assert len(eval_records) == 2
        assert all(r.subset == "dev" for r in dev_records)
        assert all(r.subset == "eval" for r in eval_records)

    def test_missing_audio_files_reported_in_invalid_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_m = Path(tmpdir) / "broken_manifest.csv"
            tmp_m.write_text(
                "audio_path,label\n"
                "nonexistent_audio.wav,bonafide\n"
                "tests/fixtures/audio_smoke/sample_bonafide.wav,spoof\n",
                encoding="utf-8",
            )
            loader = DatasetManifestLoader(validate_audio=True)
            records, report = loader.load_manifest(tmp_m)

            assert len(records) == 1
            assert report["valid_records_count"] == 1
            assert report["invalid_records_count"] == 1
            assert "does not exist" in report["invalid_records"][0]["error"]

    def test_corrupt_or_empty_audio_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_wav = Path(tmpdir) / "empty.wav"
            empty_wav.write_bytes(b"")  # 0 bytes

            corrupt_wav = Path(tmpdir) / "corrupt.wav"
            corrupt_wav.write_bytes(b"RIFF1234WAVEfmt " + b"\x00" * 20)  # truncated header

            tmp_m = Path(tmpdir) / "corrupt_manifest.csv"
            tmp_m.write_text(
                f"audio_path,label\n"
                f"{empty_wav.name},bonafide\n"
                f"{corrupt_wav.name},spoof\n",
                encoding="utf-8",
            )
            loader = DatasetManifestLoader(dataset_root=tmpdir, validate_audio=True)
            records, report = loader.load_manifest(tmp_m)

            assert len(records) == 0
            assert report["invalid_records_count"] == 2

    def test_non_finite_audio_samples_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_wav = Path(tmpdir) / "bad_samples.wav"
            samples = np.concatenate([[np.nan, np.inf], np.zeros(1000, dtype=np.float32)])
            sf.write(str(bad_wav), samples, 16000, subtype="FLOAT")

            is_valid, err, _ = AudioValidator.validate_audio(bad_wav)
            assert is_valid is False
            assert "non-finite" in err.lower()

    def test_duplicate_paths_detection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dup_m = Path(tmpdir) / "duplicate_manifest.csv"
            dup_m.write_text(
                "audio_path,label\n"
                "tests/fixtures/audio_smoke/sample_bonafide.wav,bonafide\n"
                "tests/fixtures/audio_smoke/sample_bonafide.wav,bonafide\n",
                encoding="utf-8",
            )
            loader = DatasetManifestLoader(validate_audio=False)
            records, report = loader.load_manifest(dup_m)

            assert len(records) == 2
            assert report["duplicate_paths_detected"] == 1


class TestMetricCalculations:
    """Analytical verification of confusion matrix, biometric error rates, EER, and ROC-AUC."""

    def test_confusion_matrix_and_hard_metrics_known_case(self):
        # 4 samples: positive class is spoof (1)
        y_true = np.array([1, 1, 0, 0])
        y_pred = np.array([1, 0, 0, 1])

        cm = compute_confusion_matrix(y_true, y_pred)
        assert cm["true_positives"] == 1
        assert cm["false_negatives"] == 1
        assert cm["true_negatives"] == 1
        assert cm["false_positives"] == 1

        metrics = compute_hard_decision_metrics(
            tp=cm["true_positives"],
            fp=cm["false_positives"],
            tn=cm["true_negatives"],
            fn=cm["false_negatives"],
        )

        assert metrics["accuracy"] == 0.50
        assert metrics["precision"] == 0.50
        assert metrics["recall_tpr"] == 0.50
        assert metrics["specificity_tnr"] == 0.50
        assert metrics["f1_score"] == 0.50
        # FAR = FP / (TN + FP) = 1 / 2 = 0.50
        assert metrics["false_alarm_rate_far"] == 0.50
        # FRR = FN / (TP + FN) = 1 / 2 = 0.50
        assert metrics["miss_rate_frr"] == 0.50

    def test_metric_division_by_zero_safety(self):
        # No predicted positives (TP=0, FP=0)
        metrics = compute_hard_decision_metrics(tp=0, fp=0, tn=10, fn=5)
        assert metrics["precision"] == 0.0
        assert metrics["recall_tpr"] == 0.0
        assert metrics["f1_score"] == 0.0
        assert metrics["false_alarm_rate_far"] == 0.0

    def test_roc_and_auc_analytical(self):
        # Perfectly separable case
        y_true = np.array([0, 0, 1, 1])
        y_score = np.array([0.1, 0.2, 0.8, 0.9])

        fpr, tpr, threshs, auc, err = compute_roc_and_auc(y_true, y_score)
        assert err is None
        assert auc == 1.0
        assert len(fpr) > 0

        # Inverted / completely wrong classifier
        y_score_inv = np.array([0.9, 0.8, 0.2, 0.1])
        _, _, _, auc_inv, _ = compute_roc_and_auc(y_true, y_score_inv)
        assert auc_inv == 0.0

    def test_eer_linear_interpolation(self):
        # Symmetric threshold crossing at 0.50
        y_true = np.array([0, 0, 1, 1])
        y_score = np.array([0.1, 0.3, 0.7, 0.9])

        eer_res = compute_eer(y_true, y_score)
        assert eer_res["eer"] == 0.0
        assert 0.3 <= eer_res["eer_threshold"] <= 0.7

    def test_eer_edge_cases(self):
        # Single class only (missing spoof or missing bonafide)
        single_class_res = compute_eer(np.array([1, 1, 1]), np.array([0.8, 0.9, 0.95]))
        assert single_class_res["eer"] is None
        assert "missing class" in single_class_res["explanation"].lower()

        # All identical scores
        identical_scores_res = compute_eer(np.array([0, 1, 0, 1]), np.array([0.5, 0.5, 0.5, 0.5]))
        assert identical_scores_res["eer"] is None
        assert "identical scores" in identical_scores_res["explanation"].lower()

    def test_compute_full_evaluation_metrics_package(self):
        y_true = [0, 0, 1, 1]
        y_score = [0.1, 0.3, 0.6, 0.8]

        full_res = compute_full_evaluation_metrics(y_true, y_score, decision_threshold=0.50)
        assert full_res["sample_counts"]["total_evaluated"] == 4
        assert full_res["sample_counts"]["bonafide_count"] == 2
        assert full_res["sample_counts"]["spoof_count"] == 2
        assert full_res["hard_decision_metrics"]["accuracy"] == 1.0
        assert full_res["continuous_metrics"]["roc_auc"] == 1.0
        assert full_res["continuous_metrics"]["eer"] == 0.0


class TestThresholdCalibration:
    """Tests for threshold calibration on validation predictions."""

    def test_calibrate_thresholds_from_predictions_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pred_file = Path(tmpdir) / "val_predictions.jsonl"
            out_config = Path(tmpdir) / "calibrated_thresh.json"

            # Create synthetic validation predictions
            # 10 bona fide (low score), 10 spoof (high score)
            records = []
            for i in range(10):
                records.append({
                    "sample_index": i + 1,
                    "binary_ground_truth": 0,
                    "fused_spoof_probability": 0.10 + i * 0.02,
                })
            for i in range(10):
                records.append({
                    "sample_index": i + 11,
                    "binary_ground_truth": 1,
                    "fused_spoof_probability": 0.70 + i * 0.02,
                })

            with open(pred_file, "w", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r) + "\n")

            # Run calibration for EER objective
            calib = calibrate_thresholds(
                predictions_file=pred_file,
                output_config=out_config,
                objective="eer",
            )

            assert out_config.is_file()
            assert 0.28 <= calib["recommended_threshold"] <= 0.70
            assert calib["operating_points"]["eer_error_rate"] == 0.0
            assert len(calib["uncertainty_warnings"]) > 0  # 20 samples < 100 triggers warning


class TestEvaluationRunner:
    """Smoke testing the command-line evaluation runner."""

    def test_end_to_end_smoke_evaluation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "eval_out"

            manifest = Path("tests/fixtures/sample_manifest.csv")
            dataset_root = Path("tests/fixtures/audio_smoke")

            report = run_evaluation(
                manifest_path=manifest,
                dataset_root=dataset_root,
                output_dir=out_dir,
                decision_threshold=0.50,
            )

            assert report["execution_summary"]["total_utterances"] == 5
            assert (out_dir / "predictions.jsonl").is_file()
            assert (out_dir / "metrics.json").is_file()

            # Verify predictions content
            with open(out_dir / "predictions.jsonl", "r", encoding="utf-8") as f:
                lines = [json.loads(l) for l in f]
                assert len(lines) == 5
                # Verify schema includes active models and detector details
                assert "AASIST" in lines[0]["detector_details"]
                assert "AASIST-L" in lines[0]["detector_details"]
                assert "ACOUSTIC" in lines[0]["detector_details"]
                # Skipped detector must be recorded as SKIPPED, never 0.0
                assert lines[0]["detector_details"]["W2V2-AASIST"]["status"] == "SKIPPED"
                assert lines[0]["detector_details"]["W2V2-AASIST"]["raw_score"] is None

            # Verify metrics summary schema
            with open(out_dir / "metrics.json", "r", encoding="utf-8") as f:
                meta = json.load(f)
                assert meta["target_detector"] == "ensemble"
                assert meta["decision_threshold"] == 0.50
                assert "fused_pipeline_metrics" in meta
                assert "individual_detector_metrics" in meta
                assert "git" in meta
                assert "runtime_environment" in meta

    def test_evaluation_runner_aborts_on_empty_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_m = Path(tmpdir) / "empty_manifest.csv"
            empty_m.write_text("audio_path,label\n", encoding="utf-8")

            with pytest.raises(ValueError) as exc:
                run_evaluation(
                    manifest_path=empty_m,
                    dataset_root=Path(tmpdir),
                    output_dir=Path(tmpdir) / "out",
                )
            assert "No valid audio records" in str(exc.value)
