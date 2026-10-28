"""
Scientific Metrics Engine for Dhwani Voice Anti-Spoofing Pipeline
=================================================================
Implements binary classification metrics, biometric error rates (FAR, FRR),
Equal Error Rate (EER) with linear interpolation, and ROC-AUC computation.
Positive class is strictly defined as 'spoof' (1).
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


def compute_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, int]:
    """
    Compute binary confusion matrix with positive class = spoof (1), negative class = bonafide (0).
    """
    yt = np.asarray(y_true, dtype=int)
    yp = np.asarray(y_pred, dtype=int)

    tp = int(np.sum((yt == 1) & (yp == 1)))
    fp = int(np.sum((yt == 0) & (yp == 1)))
    tn = int(np.sum((yt == 0) & (yp == 0)))
    fn = int(np.sum((yt == 1) & (yp == 0)))

    return {
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "total_samples": len(yt),
    }


def compute_hard_decision_metrics(
    tp: int,
    fp: int,
    tn: int,
    fn: int,
) -> Dict[str, Any]:
    """
    Compute standard accuracy, precision, recall, specificity, F1, FAR, and FRR.
    Handles division-by-zero safely by returning None with explanation.
    """
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total > 0 else None

    # Precision: TP / (TP + FP)
    denom_prec = tp + fp
    precision = tp / denom_prec if denom_prec > 0 else (0.0 if denom_prec == 0 and tp == 0 else None)

    # Recall / TPR: TP / (TP + FN)
    denom_rec = tp + fn
    recall = tp / denom_rec if denom_rec > 0 else None

    # Specificity / TNR: TN / (TN + FP)
    denom_spec = tn + fp
    specificity = tn / denom_spec if denom_spec > 0 else None

    # F1 score
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = (2.0 * precision * recall) / (precision + recall)
    else:
        f1 = 0.0 if (precision == 0.0 or recall == 0.0) else None

    # Biometric False Alarm Rate (genuine falsely rejected as spoof) = FP / (TN + FP)
    far = fp / denom_spec if denom_spec > 0 else None

    # Biometric False Acceptance Rate (spoof falsely passed as genuine) = FN / (TP + FN)
    frr = fn / denom_rec if denom_rec > 0 else None

    return {
        "accuracy": round(accuracy, 4) if accuracy is not None else None,
        "precision": round(precision, 4) if precision is not None else None,
        "recall_tpr": round(recall, 4) if recall is not None else None,
        "specificity_tnr": round(specificity, 4) if specificity is not None else None,
        "f1_score": round(f1, 4) if f1 is not None else None,
        "false_alarm_rate_far": round(far, 4) if far is not None else None,
        "miss_rate_frr": round(frr, 4) if frr is not None else None,
    }


def compute_roc_and_auc(
    y_true: np.ndarray,
    y_score: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Optional[float], Optional[str]]:
    """
    Compute ROC curve (FPR, TPR, thresholds) and ROC-AUC using trapezoidal integration.

    Returns:
        (fpr: np.ndarray, tpr: np.ndarray, thresholds: np.ndarray, auc: Optional[float], explanation: Optional[str])
    """
    yt = np.asarray(y_true, dtype=int)
    ys = np.asarray(y_score, dtype=float)

    n_pos = int(np.sum(yt == 1))
    n_neg = int(np.sum(yt == 0))

    if n_pos == 0 or n_neg == 0:
        msg = f"ROC curve undefined: requires both classes, but found {n_pos} positive and {n_neg} negative samples."
        return np.array([]), np.array([]), np.array([]), None, msg

    # Sort descending by score
    desc_idx = np.argsort(ys, kind="mergesort")[::-1]
    yt_sorted = yt[desc_idx]
    ys_sorted = ys[desc_idx]

    # Find distinct thresholds
    distinct_indices = np.where(np.diff(ys_sorted))[0]
    threshold_idxs = np.concatenate([distinct_indices, [len(ys_sorted) - 1]])

    # Cumulative sums
    tps = np.cumsum(yt_sorted == 1)[threshold_idxs]
    fps = np.cumsum(yt_sorted == 0)[threshold_idxs]

    tpr = tps / n_pos
    fpr = fps / n_neg

    # Prepend (0, 0) point with threshold infinity
    tpr = np.concatenate([[0.0], tpr])
    fpr = np.concatenate([[0.0], fpr])
    thresholds = np.concatenate([[ys_sorted[0] + 1.0], ys_sorted[threshold_idxs]])

    # Trapezoidal AUC (compatibility for NumPy 2.0+ and legacy NumPy)
    if hasattr(np, "trapezoid"):
        auc = float(np.trapezoid(tpr, fpr))
    elif hasattr(np, "trapz"):
        auc = float(np.trapz(tpr, fpr))
    else:
        from scipy.integrate import trapezoid
        auc = float(trapezoid(tpr, fpr))
    return fpr, tpr, thresholds, round(auc, 4), None


def compute_eer(
    y_true: np.ndarray,
    y_score: np.ndarray,
) -> Dict[str, Any]:
    """
    Compute Equal Error Rate (EER) and operating threshold using linear interpolation.

    EER is the operating point where False Alarm Rate (FAR) == False Rejection Rate (FRR).
    FAR = FP / (TN + FP)  (Bona fide classified as spoof)
    FRR = FN / (TP + FN)  (Spoof classified as bona fide)
    """
    yt = np.asarray(y_true, dtype=int)
    ys = np.asarray(y_score, dtype=float)

    n_pos = int(np.sum(yt == 1))
    n_neg = int(np.sum(yt == 0))

    if n_pos == 0 or n_neg == 0:
        return {
            "eer": None,
            "eer_threshold": None,
            "explanation": f"EER undefined: missing class (positives={n_pos}, negatives={n_neg}).",
        }

    # Evaluate across fine grid of thresholds + unique sample scores
    unique_scores = np.unique(ys)
    if len(unique_scores) == 1:
        return {
            "eer": None,
            "eer_threshold": float(unique_scores[0]),
            "explanation": "All predictions have identical scores; EER cannot be estimated.",
        }

    # Generate candidate thresholds spanning slightly beyond [min(scores), max(scores)]
    min_s = float(unique_scores[0])
    max_s = float(unique_scores[-1])
    grid = np.linspace(min_s - 1e-4, max_s + 1e-4, 1000)
    all_thresholds = np.sort(np.unique(np.concatenate([unique_scores, grid])))

    fars = []
    frrs = []

    for tau in all_thresholds:
        # Prediction: score >= tau is spoof (1), else bona fide (0)
        yp = (ys >= tau).astype(int)
        fp = np.sum((yt == 0) & (yp == 1))
        fn = np.sum((yt == 1) & (yp == 0))
        fars.append(fp / n_neg)
        frrs.append(fn / n_pos)

    fars = np.array(fars)
    frrs = np.array(frrs)

    # Find where (FAR - FRR) crosses zero
    diff = fars - frrs
    crossings = np.where(np.diff(np.sign(diff)))[0]

    if len(crossings) > 0:
        idx = crossings[0]
        # Linear interpolation between idx and idx+1
        x1, x2 = all_thresholds[idx], all_thresholds[idx + 1]
        far1, far2 = fars[idx], fars[idx + 1]
        frr1, frr2 = frrs[idx], frrs[idx + 1]

        denom = (far2 - far1) - (frr2 - frr1)
        if abs(denom) > 1e-9:
            alpha = (frr1 - far1) / denom
            alpha = np.clip(alpha, 0.0, 1.0)
            eer_thresh = x1 + alpha * (x2 - x1)
            eer_val = far1 + alpha * (far2 - far1)
        else:
            eer_thresh = (x1 + x2) / 2.0
            eer_val = (far1 + frr1) / 2.0
    else:
        # Fallback to minimum absolute difference
        min_idx = int(np.argmin(np.abs(diff)))
        eer_thresh = float(all_thresholds[min_idx])
        eer_val = float((fars[min_idx] + frrs[min_idx]) / 2.0)

    return {
        "eer": round(float(eer_val), 4),
        "eer_threshold": round(float(eer_thresh), 4),
        "method": "linear_interpolation",
        "explanation": "Calculated via continuous false-alarm and miss-rate interpolation.",
    }


def compute_full_evaluation_metrics(
    y_true: Union[List[int], np.ndarray],
    y_score: Union[List[float], np.ndarray],
    decision_threshold: float = 0.50,
) -> Dict[str, Any]:
    """
    Compute comprehensive metrics package combining hard-threshold decisions
    and continuous threshold-independent measures (EER, ROC-AUC).
    """
    yt = np.asarray(y_true, dtype=int)
    ys = np.asarray(y_score, dtype=float)

    if len(yt) != len(ys):
        raise ValueError(f"Length mismatch: {len(yt)} ground-truth labels vs {len(ys)} scores.")

    if len(yt) == 0:
        return {
            "error": "Cannot compute metrics on empty dataset.",
            "total_samples": 0,
        }

    # Hard decisions at specified threshold
    ypred = (ys >= decision_threshold).astype(int)
    cm = compute_confusion_matrix(yt, ypred)
    hard_metrics = compute_hard_decision_metrics(
        tp=cm["true_positives"],
        fp=cm["false_positives"],
        tn=cm["true_negatives"],
        fn=cm["false_negatives"],
    )

    # Continuous metrics (ROC, AUC, EER)
    fpr, tpr, roc_threshs, auc_score, roc_err = compute_roc_and_auc(yt, ys)
    eer_res = compute_eer(yt, ys)

    return {
        "sample_counts": {
            "total_evaluated": len(yt),
            "bonafide_count": int(np.sum(yt == 0)),
            "spoof_count": int(np.sum(yt == 1)),
        },
        "decision_threshold_evaluated": float(decision_threshold),
        "confusion_matrix": cm,
        "hard_decision_metrics": hard_metrics,
        "continuous_metrics": {
            "roc_auc": auc_score,
            "roc_status": "OK" if auc_score is not None else roc_err,
            "eer": eer_res.get("eer"),
            "eer_threshold": eer_res.get("eer_threshold"),
            "eer_status": eer_res.get("explanation"),
        },
    }


def compute_latency_statistics(latencies_ms: List[float]) -> Dict[str, Optional[float]]:
    """
    Compute inference latency summary statistics including mean, median (p50), and p95.
    """
    if not latencies_ms:
        return {
            "count": 0,
            "mean_ms": None,
            "median_p50_ms": None,
            "p90_ms": None,
            "p95_ms": None,
            "min_ms": None,
            "max_ms": None,
        }
    arr = np.asarray(latencies_ms, dtype=float)
    return {
        "count": len(arr),
        "mean_ms": round(float(np.mean(arr)), 2),
        "median_p50_ms": round(float(np.median(arr)), 2),
        "p90_ms": round(float(np.percentile(arr, 90)), 2),
        "p95_ms": round(float(np.percentile(arr, 95)), 2),
        "min_ms": round(float(np.min(arr)), 2),
        "max_ms": round(float(np.max(arr)), 2),
    }


def compute_per_attack_breakdown(
    prediction_records: List[Dict[str, Any]],
    decision_threshold: float = 0.50,
) -> Dict[str, Any]:
    """
    Compute granular detection metrics stratified by attack_type.
    Positive class is strictly defined as spoof (1).
    """
    attack_groups: Dict[str, List[Dict[str, Any]]] = {}
    bonafide_records: List[Dict[str, Any]] = []

    for rec in prediction_records:
        gt = rec.get("binary_ground_truth")
        score = rec.get("fused_spoof_probability")
        if gt is None or score is None:
            continue

        if gt == 0:
            bonafide_records.append(rec)
        else:
            att = rec.get("attack_type") or "unspecified_spoof"
            attack_groups.setdefault(att, []).append(rec)

    # Metrics for bona fide
    bf_scores = [r["fused_spoof_probability"] for r in bonafide_records]
    bf_preds = [1 if s >= decision_threshold else 0 for s in bf_scores]
    bf_fp = sum(1 for p in bf_preds if p == 1)
    bf_tn = sum(1 for p in bf_preds if p == 0)
    bf_total = len(bonafide_records)

    bonafide_summary = {
        "total_samples": bf_total,
        "correct_genuine_tn": bf_tn,
        "false_alarm_fp": bf_fp,
        "false_alarm_rate_far": round(bf_fp / bf_total, 4) if bf_total > 0 else None,
        "specificity_tnr": round(bf_tn / bf_total, 4) if bf_total > 0 else None,
        "mean_score": round(float(np.mean(bf_scores)), 4) if bf_scores else None,
    }

    # Metrics per attack category
    attacks_summary: Dict[str, Any] = {}
    for att_name, att_recs in sorted(attack_groups.items()):
        scores = [r["fused_spoof_probability"] for r in att_recs]
        preds = [1 if s >= decision_threshold else 0 for s in scores]
        tp = sum(1 for p in preds if p == 1)
        fn = sum(1 for p in preds if p == 0)
        n_att = len(att_recs)

        attacks_summary[att_name] = {
            "total_samples": n_att,
            "detected_spoofs_tp": tp,
            "missed_spoofs_fn": fn,
            "detection_rate_recall": round(tp / n_att, 4) if n_att > 0 else None,
            "miss_rate_frr": round(fn / n_att, 4) if n_att > 0 else None,
            "mean_score": round(float(np.mean(scores)), 4) if scores else None,
        }

    return {
        "decision_threshold": decision_threshold,
        "bona_fide_baseline": bonafide_summary,
        "attack_breakdown": attacks_summary,
    }
