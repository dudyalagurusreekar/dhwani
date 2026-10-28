"""
Threshold Calibration Engine for Dhwani Voice Anti-Spoofing Pipeline
====================================================================
Evaluates validation predictions, computes Equal Error Rate (EER) and
cost-sensitive operating points, and exports versioned calibration artifacts
without silently mutating production application defaults.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


def get_git_info() -> Dict[str, str]:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
        return {"commit_sha": sha, "branch": branch}
    except Exception:
        return {"commit_sha": "unknown", "branch": "unknown"}


def load_predictions(predictions_file: Path) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]]]:
    """Load binary ground truths and predicted probabilities from predictions.jsonl."""
    pfile = Path(predictions_file).resolve()
    if not pfile.is_file():
        raise FileNotFoundError(f"Predictions file not found: {pfile}")

    y_true: List[int] = []
    y_score: List[float] = []
    raw_records: List[Dict[str, Any]] = []

    with open(pfile, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            raw_records.append(rec)
            # Ensure sample was successfully predicted
            gt = rec.get("binary_ground_truth")
            score = rec.get("fused_spoof_probability")
            if gt is not None and score is not None:
                y_true.append(int(gt))
                y_score.append(float(score))

    if len(y_true) == 0:
        raise ValueError(f"No usable prediction records found in {pfile}.")

    return np.array(y_true, dtype=int), np.array(y_score, dtype=float), raw_records


def calibrate_thresholds(
    predictions_file: Path,
    output_config: Optional[Path] = None,
    objective: str = "eer",
    target_far: float = 0.01,
    cost_miss: float = 10.0,
    cost_fa: float = 1.0,
    prior_spoof: float = 0.10,
    min_samples_for_calibration: int = 100,
) -> Dict[str, Any]:
    """
    Evaluate candidate thresholds across validation predictions and select optimal operating point.
    If sample count is below min_samples_for_calibration, production threshold remains 0.50
    and status is marked UNCALIBRATED.
    """
    yt, ys, raw_recs = load_predictions(predictions_file)
    n_total = len(yt)
    n_pos = int(np.sum(yt == 1))
    n_neg = int(np.sum(yt == 0))

    print("=" * 70)
    print(" DHWANI THRESHOLD CALIBRATION ENGINE")
    print("=" * 70)
    print(f" Source Predictions: {predictions_file}")
    print(f" Samples Evaluated:  {n_total} (Bona fide: {n_neg}, Spoof: {n_pos})")
    print(f" Calibration Goal:   {objective.upper()}")
    print("=" * 70)

    # Uncertainty check
    uncertainty_warnings = []
    is_sufficient = n_total >= min_samples_for_calibration
    if not is_sufficient:
        warning_msg = (
            f"Small sample size ({n_total} samples < {min_samples_for_calibration}). "
            f"Insufficient real labeled data for production threshold calibration."
        )
        print(f" WARNING: {warning_msg}")
        uncertainty_warnings.append(warning_msg)

    if n_pos == 0 or n_neg == 0:
        raise ValueError(
            f"Calibration failed: missing class in validation data. Found {n_pos} positive, {n_neg} negative samples."
        )

    # Candidate thresholds
    candidates = np.linspace(0.01, 0.99, 990)
    sweep_results = []

    best_thresh = 0.50
    best_eer_diff = float("inf")
    best_eer_thresh = 0.50
    best_eer_val = 0.50

    min_cost = float("inf")
    best_cost_thresh = 0.50

    target_far_thresh = None

    for tau in candidates:
        yp = (ys >= tau).astype(int)
        tp = int(np.sum((yt == 1) & (yp == 1)))
        fp = int(np.sum((yt == 0) & (yp == 1)))
        tn = int(np.sum((yt == 0) & (yp == 0)))
        fn = int(np.sum((yt == 1) & (yp == 0)))

        far = fp / n_neg
        frr = fn / n_pos

        # Check EER crossing / minimum diff
        diff = abs(far - frr)
        if diff < best_eer_diff:
            best_eer_diff = diff
            best_eer_thresh = tau
            best_eer_val = (far + frr) / 2.0

        # Cost-sensitive: Cost = C_miss * P_spoof * FRR + C_fa * (1 - P_spoof) * FAR
        cost = cost_miss * prior_spoof * frr + cost_fa * (1.0 - prior_spoof) * far
        if cost < min_cost:
            min_cost = cost
            best_cost_thresh = tau

        # Target FAR: find threshold where FAR <= target_far
        if far <= target_far and target_far_thresh is None:
            target_far_thresh = tau

        sweep_results.append({
            "threshold": round(float(tau), 4),
            "far": round(float(far), 4),
            "frr": round(float(frr), 4),
            "cost": round(float(cost), 4),
        })

    # Select recommended threshold based on requested objective
    if objective == "eer":
        selected_threshold = best_eer_thresh
        objective_explanation = (
            f"Equal Error Rate (EER) threshold where FAR ({best_eer_val:.2%}) ≈ FRR ({best_eer_val:.2%})."
        )
    elif objective == "target_far":
        selected_threshold = target_far_thresh if target_far_thresh is not None else best_cost_thresh
        objective_explanation = f"Threshold enforcing False Alarm Rate (FAR) <= {target_far:.1%}."
    elif objective == "cost_sensitive":
        selected_threshold = best_cost_thresh
        objective_explanation = (
            f"Cost-sensitive threshold minimizing decision loss (C_miss={cost_miss}, C_fa={cost_fa})."
        )
    else:
        selected_threshold = 0.50
        objective_explanation = "Default balanced 0.50 threshold."

    # Enforce UNCALIBRATED status and keep production default if insufficient data
    if not is_sufficient:
        calibration_status = "UNCALIBRATED"
        final_recommended_threshold = 0.5000
        status_note = (
            f"Insufficient labeled data ({n_total} samples < {min_samples_for_calibration}). "
            f"Production threshold kept unchanged at default 0.5000."
        )
    else:
        calibration_status = "CALIBRATED"
        final_recommended_threshold = selected_threshold
        status_note = "Calibrated on validation split with sufficient statistical sample size."

    # Compute confusion matrix at final recommended threshold
    yp_sel = (ys >= final_recommended_threshold).astype(int)
    tp_s = int(np.sum((yt == 1) & (yp_sel == 1)))
    fp_s = int(np.sum((yt == 0) & (yp_sel == 1)))
    tn_s = int(np.sum((yt == 0) & (yp_sel == 0)))
    fn_s = int(np.sum((yt == 1) & (yp_sel == 0)))

    sel_far = fp_s / n_neg
    sel_frr = fn_s / n_pos

    git_info = get_git_info()
    calibration_artifact = {
        "calibration_timestamp": datetime.now(timezone.utc).isoformat(),
        "git": git_info,
        "calibration_status": calibration_status,
        "source_predictions_file": str(predictions_file),
        "dataset_partition_used": "validation",
        "sample_statistics": {
            "total_samples": n_total,
            "bonafide_count": n_neg,
            "spoof_count": n_pos,
            "imbalance_ratio_spoof_to_bonafide": round(n_pos / n_neg, 3) if n_neg > 0 else None,
        },
        "optimization_objective": objective,
        "recommended_threshold": round(float(final_recommended_threshold), 4),
        "empirical_validation_threshold": round(float(selected_threshold), 4),
        "status_note": status_note,
        "objective_explanation": objective_explanation,
        "operating_points": {
            "eer_threshold": round(float(best_eer_thresh), 4),
            "eer_error_rate": round(float(best_eer_val), 4),
            "min_cost_threshold": round(float(best_cost_thresh), 4),
            "target_far_threshold": round(float(target_far_thresh), 4) if target_far_thresh else None,
        },
        "performance_at_recommended_threshold": {
            "threshold": round(float(final_recommended_threshold), 4),
            "false_alarm_rate_far": round(float(sel_far), 4),
            "miss_rate_frr": round(float(sel_frr), 4),
            "confusion_matrix": {
                "tp": tp_s,
                "fp": fp_s,
                "tn": tn_s,
                "fn": fn_s,
            },
        },
        "uncertainty_warnings": uncertainty_warnings,
    }

    out_cfg_path = Path(output_config or "config/evaluation/calibrated_thresholds.json").resolve()
    out_cfg_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_cfg_path, "w", encoding="utf-8") as f:
        json.dump(calibration_artifact, f, indent=2)

    print(f" Optimal Threshold Selected: {selected_threshold:.4f}")
    print(f" Performance at Threshold:   FAR = {sel_far:.2%}, FRR = {sel_frr:.2%}")
    print(f" Calibration artifact saved: {out_cfg_path}")
    print("=" * 70)

    return calibration_artifact


def main():
    parser = argparse.ArgumentParser(description="Calibrate operating thresholds on validation predictions")
    parser.add_argument("--predictions", required=True, type=Path, help="Path to validation predictions.jsonl")
    parser.add_argument(
        "--output-config",
        default=Path("config/evaluation/calibrated_thresholds.json"),
        type=Path,
        help="Target JSON artifact path for calibrated thresholds",
    )
    parser.add_argument(
        "--objective",
        default="eer",
        choices=["eer", "target_far", "cost_sensitive"],
        help="Calibration objective",
    )
    parser.add_argument("--target-far", default=0.01, type=float, help="Target FAR for target_far objective")
    parser.add_argument("--cost-miss", default=10.0, type=float, help="Penalty for missed spoof in cost mode")
    parser.add_argument("--cost-fa", default=1.0, type=float, help="Penalty for false alarm in cost mode")
    args = parser.parse_args()

    calibrate_thresholds(
        predictions_file=args.predictions,
        output_config=args.output_config,
        objective=args.objective,
        target_far=args.target_far,
        cost_miss=args.cost_miss,
        cost_fa=args.cost_fa,
    )


if __name__ == "__main__":
    main()
