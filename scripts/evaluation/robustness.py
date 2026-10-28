"""
Synthetic Audio Robustness Perturbation Engine for Dhwani Platform
===================================================================
Applies controlled acoustic distortions (resampling, SNR noise, short durations,
and mu-law telephony compression) to test pipeline stability.

DISCLAIMER:
All tests generated here are explicitly labeled as SYNTHETIC PERTURBATION EXPERIMENTS
and are NOT a substitute for an independent, real-world labeled benchmark.
"""

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from scipy import signal
import soundfile as sf

from backend.services import detector
from scripts.evaluation.dataset import DatasetManifestLoader, ManifestRecord
from scripts.evaluation.metrics import compute_latency_statistics


def apply_resampling(
    audio: np.ndarray,
    orig_sr: int,
    target_sr: int,
) -> Tuple[np.ndarray, int]:
    """
    Resample audio waveform to target_sr using polyphase rational filtering.
    """
    if orig_sr == target_sr:
        return audio.copy(), target_sr

    # Find rational approximation for sample rates
    gcd = math.gcd(orig_sr, target_sr)
    up = target_sr // gcd
    down = orig_sr // gcd

    resampled = signal.resample_poly(audio, up, down).astype(np.float32)
    return resampled, target_sr


def apply_additive_noise(
    audio: np.ndarray,
    snr_db: float,
    rng_seed: Optional[int] = 42,
) -> np.ndarray:
    """
    Add zero-mean Gaussian white noise at specified Signal-to-Noise Ratio (SNR) in dB.
    """
    if rng_seed is not None:
        rng = np.random.default_rng(rng_seed)
    else:
        rng = np.random.default_rng()

    signal_power = float(np.mean(audio ** 2))
    if signal_power <= 1e-12:
        return audio.copy()

    # SNR = 10 * log10(P_signal / P_noise)  =>  P_noise = P_signal / 10^(SNR/10)
    noise_power = signal_power / (10.0 ** (snr_db / 10.0))
    noise_std = math.sqrt(noise_power)

    noise = rng.normal(loc=0.0, scale=noise_std, size=audio.shape).astype(np.float32)
    perturbed = audio + noise

    # Clip to avoid numerical overflow beyond [-1.0, 1.0]
    return np.clip(perturbed, -1.0, 1.0)


def apply_duration_truncation(
    audio: np.ndarray,
    sample_rate: int,
    duration_sec: float,
) -> np.ndarray:
    """
    Truncate audio waveform to target duration in seconds.
    If original is shorter than target, returns original untouched.
    """
    max_samples = int(duration_sec * sample_rate)
    if len(audio) > max_samples:
        return audio[:max_samples].copy()
    return audio.copy()


def apply_telephony_companding(
    audio: np.ndarray,
    mu: float = 255.0,
) -> np.ndarray:
    """
    Simulate ITU-T G.711 mu-law telephony companding (8-bit quantization).
    Compresses dynamic range: F(x) = sign(x) * ln(1 + mu*|x|) / ln(1 + mu)
    Quantizes to 8-bit (-128 to 127) and expands back.
    """
    x = np.clip(audio, -1.0, 1.0)
    sign = np.sign(x)
    # Mu-law compression
    compressed = sign * np.log1p(mu * np.abs(x)) / np.log1p(mu)
    # Quantize to 8-bit discrete bins (-128 to 127)
    quantized = np.round(compressed * 128.0) / 128.0
    # Mu-law expansion
    expanded = np.sign(quantized) * (1.0 / mu) * ((1.0 + mu) ** np.abs(quantized) - 1.0)
    return expanded.astype(np.float32)


def run_robustness_experiments(
    manifest_path: Path,
    dataset_root: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    decision_threshold: float = 0.50,
) -> Dict[str, Any]:
    """
    Execute controlled perturbation experiments on audio records and quantify performance shifts.
    """
    out_dir = Path(output_dir or "evaluation_results/robustness").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    loader = DatasetManifestLoader(dataset_root=dataset_root, validate_audio=True)
    records, _ = loader.load_manifest(manifest_path)

    if not records:
        raise ValueError(f"No valid records loaded from {manifest_path}")

    # Define perturbation suites
    conditions: Dict[str, Any] = {
        "baseline_clean": {"type": "baseline"},
        "snr_noise_20db": {"type": "noise", "snr_db": 20.0},
        "snr_noise_10db": {"type": "noise", "snr_db": 10.0},
        "snr_noise_0db": {"type": "noise", "snr_db": 0.0},
        "telephony_companding_g711": {"type": "companding"},
        "resample_8khz": {"type": "resample", "target_sr": 8000},
        "duration_short_1s": {"type": "duration", "duration_sec": 1.0},
        "duration_ultra_short_0.5s": {"type": "duration", "duration_sec": 0.5},
    }

    condition_results: Dict[str, Any] = {}

    for cond_name, cond_cfg in conditions.items():
        scores: List[float] = []
        latencies: List[float] = []
        correct_predictions = 0
        total_eval = 0

        for rec in records:
            try:
                audio, sr = sf.read(str(rec.audio_path), dtype="float32")
                if audio.ndim > 1:
                    audio = np.mean(audio, axis=-1)

                # Apply perturbation
                p_audio = audio
                p_sr = sr
                c_type = cond_cfg["type"]

                if c_type == "noise":
                    p_audio = apply_additive_noise(audio, snr_db=cond_cfg["snr_db"])
                elif c_type == "companding":
                    p_audio = apply_telephony_companding(audio)
                elif c_type == "resample":
                    p_audio, p_sr = apply_resampling(audio, sr, cond_cfg["target_sr"])
                elif c_type == "duration":
                    p_audio = apply_duration_truncation(audio, sr, cond_cfg["duration_sec"])

                t0 = time.perf_counter()
                resp = detector.detect_voice_sync(p_audio, sample_rate=p_sr)
                lat_ms = (time.perf_counter() - t0) * 1000.0

                prob = resp.get("fake_probability")
                if prob is not None:
                    scores.append(float(prob))
                    latencies.append(lat_ms)
                    pred_bin = 1 if prob >= decision_threshold else 0
                    if pred_bin == rec.binary_label:
                        correct_predictions += 1
                    total_eval += 1

            except Exception as e:
                pass

        acc = (correct_predictions / total_eval) if total_eval > 0 else None
        mean_score = float(np.mean(scores)) if scores else None
        lat_stats = compute_latency_statistics(latencies)

        condition_results[cond_name] = {
            "condition_type": cond_cfg["type"],
            "parameters": {k: v for k, v in cond_cfg.items() if k != "type"},
            "samples_evaluated": total_eval,
            "accuracy": round(acc, 4) if acc is not None else None,
            "mean_fake_probability": round(mean_score, 4) if mean_score is not None else None,
            "latency_p50_ms": lat_stats.get("median_p50_ms"),
            "latency_p95_ms": lat_stats.get("p95_ms"),
        }

    report = {
        "experiment_timestamp": datetime.now(timezone.utc).isoformat(),
        "experiment_type": "SYNTHETIC_PERTURBATION_EXPERIMENT",
        "benchmark_substitute": False,
        "disclaimer": (
            "This synthetic perturbation test assesses detector stability under controlled "
            "acoustic degradations. It is NOT an empirical substitute for real-world benchmark evaluation."
        ),
        "source_manifest": str(manifest_path),
        "decision_threshold_used": decision_threshold,
        "perturbation_conditions": condition_results,
    }

    out_file = out_dir / "robustness_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def main():
    parser = argparse.ArgumentParser(description="Run synthetic robustness perturbations on audio dataset")
    parser.add_argument("--manifest", required=True, type=Path, help="Path to evaluation manifest CSV")
    parser.add_argument("--dataset-root", default=None, type=Path, help="Root folder for audio files")
    parser.add_argument("--output-dir", default=Path("evaluation_results/robustness"), type=Path)
    parser.add_argument("--threshold", default=0.50, type=float, help="Decision threshold")
    args = parser.parse_args()

    run_robustness_experiments(
        manifest_path=args.manifest,
        dataset_root=args.dataset_root,
        output_dir=args.output_dir,
        decision_threshold=args.threshold,
    )


if __name__ == "__main__":
    main()
