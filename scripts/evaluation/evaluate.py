"""
Reproducible Evaluation Runner for Dhwani Anti-Spoofing & Deepfake Platform
===========================================================================
Executes multi-model or per-detector inference over manifest-driven datasets,
preserves raw detector statuses, evaluates hard and continuous metrics, and
outputs machine-readable per-utterance logs and summary reports.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional
import numpy as np
import soundfile as sf
import torch

from scripts.evaluation.dataset import DatasetManifestLoader, ManifestRecord
from scripts.evaluation.metrics import (
    compute_full_evaluation_metrics,
    compute_latency_statistics,
    compute_per_attack_breakdown,
)
from backend.services import detector


def get_git_info() -> Dict[str, str]:
    """Capture current git commit SHA and branch name."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return {"commit_sha": sha, "branch": branch}
    except Exception:
        return {"commit_sha": "unknown", "branch": "unknown"}


def run_evaluation(
    manifest_path: Path,
    dataset_root: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    decision_threshold: float = 0.50,
    subset_filter: Optional[str] = None,
    max_samples: Optional[int] = None,
    target_detector: str = "ensemble",
) -> Dict[str, Any]:
    """
    Run evaluation across specified manifest and generate predictions & metrics.
    """
    t_start = time.perf_counter()
    mpath = Path(manifest_path).resolve()
    out_dir = Path(output_dir or "evaluation_results").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(" DHWANI REPRODUCIBLE EVALUATION RUNNER")
    print("=" * 70)
    print(f" Manifest:           {mpath}")
    print(f" Dataset Root:       {dataset_root or mpath.parent}")
    print(f" Target Detector:    {target_detector.upper()}")
    print(f" Decision Threshold: {decision_threshold:.4f}")
    if subset_filter:
        print(f" Subset Filter:      {subset_filter}")
    print("=" * 70)

    # 1. Load and validate dataset
    loader = DatasetManifestLoader(dataset_root=dataset_root, validate_audio=True)
    records, load_report = loader.load_manifest(mpath, subset_filter=subset_filter)

    print(f" Loaded {load_report['total_rows_evaluated']} records from manifest:")
    print(f"   * Valid:   {load_report['valid_records_count']} (Bona fide: {load_report['bonafide_count']}, Spoof: {load_report['spoof_count']})")
    print(f"   * Invalid: {load_report['invalid_records_count']}")
    if load_report['duplicate_paths_detected'] > 0:
        print(f"   * Duplicate audio paths detected: {load_report['duplicate_paths_detected']}")

    if len(records) == 0:
        raise ValueError("Evaluation aborted: No valid audio records available to evaluate.")

    if max_samples and max_samples < len(records):
        print(f" Limiting evaluation to first {max_samples} samples.")
        records = records[:max_samples]

    # 2. Inspect active detectors
    active_detectors = detector.get_active_detectors()
    ready_models = [d["model"] for d in active_detectors if d["is_available"]]
    skipped_models = [d["model"] for d in active_detectors if not d["is_available"]]
    print(f" Operational Detectors: {ready_models}")
    print(f" Skipped/Unavailable:   {skipped_models}")

    # 3. Execute inference loop
    predictions_file = out_dir / "predictions.jsonl"
    results: List[Dict[str, Any]] = []

    y_true_fused: List[int] = []
    y_score_fused: List[float] = []
    latencies_ms: List[float] = []

    per_detector_scores: Dict[str, Dict[str, List]] = {
        m: {"y_true": [], "y_score": []} for m in ready_models
    }

    print("\n Running inference across utterances...")
    with open(predictions_file, "w", encoding="utf-8") as pred_f:
        for idx, rec in enumerate(records, start=1):
            try:
                audio, sr = sf.read(str(rec.audio_path), dtype="float32")
                # Downmix stereo to mono if needed
                if audio.ndim > 1:
                    audio = np.mean(audio, axis=-1)

                t_sample_start = time.perf_counter()
                det_resp = detector.detect_voice_sync(audio, sample_rate=sr)
                sample_latency_ms = (time.perf_counter() - t_sample_start) * 1000.0
                latencies_ms.append(sample_latency_ms)

                fused_prob = det_resp.get("fake_probability")
                active_in_run = det_resp.get("active_models", [])

                # Determine hard prediction
                if fused_prob is not None:
                    pred_binary = 1 if fused_prob >= decision_threshold else 0
                    pred_label = "spoof" if pred_binary == 1 else "bonafide"
                    y_true_fused.append(rec.binary_label)
                    y_score_fused.append(float(fused_prob))
                else:
                    pred_binary = None
                    pred_label = "INDETERMINATE"

                # Record per-detector score
                det_scores_map = {}
                for d in det_resp.get("detectors", []):
                    m_name = d["model"]
                    s = d.get("raw_score")
                    status = d.get("status")
                    det_scores_map[m_name] = {
                        "raw_score": s,
                        "status": status,
                        "device": d.get("device"),
                        "latency_ms": d.get("latency_ms"),
                        "error": d.get("error"),
                    }
                    if s is not None and m_name in per_detector_scores:
                        per_detector_scores[m_name]["y_true"].append(rec.binary_label)
                        per_detector_scores[m_name]["y_score"].append(float(s))

                pred_record = {
                    "sample_index": idx,
                    "audio_path": str(rec.audio_path),
                    "ground_truth": rec.label,
                    "binary_ground_truth": rec.binary_label,
                    "predicted_label": pred_label,
                    "predicted_binary": pred_binary,
                    "fused_spoof_probability": fused_prob,
                    "decision_threshold": decision_threshold,
                    "latency_ms": round(sample_latency_ms, 2),
                    "active_models": active_in_run,
                    "detector_details": det_scores_map,
                    "speaker_id": rec.speaker_id,
                    "attack_type": rec.attack_type,
                    "subset": rec.subset,
                }

                pred_f.write(json.dumps(pred_record) + "\n")
                results.append(pred_record)

                if idx % 25 == 0 or idx == len(records):
                    sys.stdout.write(f"\r Progress: {idx}/{len(records)} utterances processed")
                    sys.stdout.flush()

            except Exception as exc:
                print(f"\n Error processing {rec.audio_path}: {exc}")
                pred_record = {
                    "sample_index": idx,
                    "audio_path": str(rec.audio_path),
                    "ground_truth": rec.label,
                    "binary_ground_truth": rec.binary_label,
                    "predicted_label": "FAILED",
                    "predicted_binary": None,
                    "fused_spoof_probability": None,
                    "error": str(exc),
                }
                pred_f.write(json.dumps(pred_record) + "\n")
                results.append(pred_record)

    print()
    total_eval_time = time.perf_counter() - t_start

    # 4. Compute metrics
    fused_metrics = compute_full_evaluation_metrics(
        y_true=y_true_fused,
        y_score=y_score_fused,
        decision_threshold=decision_threshold,
    )

    per_detector_metrics = {}
    for m_name, data in per_detector_scores.items():
        if len(data["y_true"]) > 0:
            per_detector_metrics[m_name] = compute_full_evaluation_metrics(
                y_true=data["y_true"],
                y_score=data["y_score"],
                decision_threshold=decision_threshold,
            )

    latency_stats = compute_latency_statistics(latencies_ms)
    attack_breakdown = compute_per_attack_breakdown(results, decision_threshold=decision_threshold)

    # 5. Compile metadata and summary artifact
    git_info = get_git_info()
    summary_report = {
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "git": git_info,
        "runtime_environment": {
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "device_used": "cuda" if torch.cuda.is_available() else "cpu",
        },
        "dataset_summary": load_report,
        "execution_summary": {
            "total_utterances": len(records),
            "successfully_predicted": len(y_score_fused),
            "indeterminate_or_failed": len(records) - len(y_score_fused),
            "total_elapsed_seconds": round(total_eval_time, 2),
            "avg_latency_ms_per_sample": round((total_eval_time / len(records)) * 1000.0, 2),
            "latency_statistics_ms": latency_stats,
        },
        "target_detector": target_detector,
        "decision_threshold": decision_threshold,
        "fused_pipeline_metrics": fused_metrics,
        "individual_detector_metrics": per_detector_metrics,
        "per_attack_breakdown": attack_breakdown,
        "active_models_in_ensemble": ready_models,
        "skipped_models": skipped_models,
    }

    metrics_file = out_dir / "metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    # 6. Console Report
    print("\n" + "=" * 70)
    print(" EVALUATION RESULTS SUMMARY")
    print("=" * 70)
    print(f" Utterances Evaluated: {len(y_score_fused)} / {len(records)}")
    if fused_metrics.get("hard_decision_metrics"):
        hm = fused_metrics["hard_decision_metrics"]
        print(f" Accuracy:             {hm.get('accuracy')}")
        print(f" Precision:            {hm.get('precision')}")
        print(f" Recall (TPR):         {hm.get('recall_tpr')}")
        print(f" Specificity (TNR):    {hm.get('specificity_tnr')}")
        print(f" F1 Score:             {hm.get('f1_score')}")
        print(f" False Alarm Rate:     {hm.get('false_alarm_rate_far')}")
        print(f" Miss Rate:            {hm.get('miss_rate_frr')}")
    if fused_metrics.get("continuous_metrics"):
        cm = fused_metrics["continuous_metrics"]
        print(f" ROC-AUC:              {cm.get('roc_auc')}")
        print(f" EER:                  {cm.get('eer')} (at threshold: {cm.get('eer_threshold')})")
    print("=" * 70)
    print(f" Per-utterance predictions written to: {predictions_file}")
    print(f" Machine-readable metrics written to:   {metrics_file}")
    print("=" * 70)

    return summary_report


def main():
    parser = argparse.ArgumentParser(description="Run reproducible evaluation on audio dataset manifest")
    parser.add_argument("--manifest", required=True, type=Path, help="Path to evaluation manifest CSV")
    parser.add_argument("--dataset-root", default=None, type=Path, help="Root folder for relative audio paths")
    parser.add_argument("--output-dir", default=Path("evaluation_results"), type=Path, help="Output directory")
    parser.add_argument("--threshold", default=0.50, type=float, help="Decision threshold (default: 0.50)")
    parser.add_argument("--subset", default=None, help="Subset filter (e.g., dev, eval)")
    parser.add_argument("--max-samples", default=None, type=int, help="Maximum samples to evaluate")
    parser.add_argument("--detector", default="ensemble", choices=["ensemble", "AASIST", "AASIST-L", "ACOUSTIC"])
    args = parser.parse_args()

    run_evaluation(
        manifest_path=args.manifest,
        dataset_root=args.dataset_root,
        output_dir=args.output_dir,
        decision_threshold=args.threshold,
        subset_filter=args.subset,
        max_samples=args.max_samples,
        target_detector=args.detector,
    )


if __name__ == "__main__":
    main()
