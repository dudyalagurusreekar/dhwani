"""
EchoShield Live Risk Pipeline
=============================
Multi-model real-time voice anti-spoofing and prevention system connecting:
REAL AUDIO (MICROPHONE / FILE)
    ↓
ROLLING AUDIO BUFFER (64,600 samples @ 16 kHz)
    ↓
SPEECH ACTIVITY GATE / VAD PRE-FILTER
    ↓
if NON_SPEECH:
    Bypass deep models -> emit NO_SPEECH structured event
if SPEECH:
    AUDIO QUALITY ANALYZER
        ↓
    MULTI-MODEL DETECTORS:
    ├── W2V2-AASIST (Real, CUDA)
    └── AASIST (Real, CUDA)
        ↓
    RISK ENGINE (Evidence Fusion + Cross-Model Agreement + Temporal Risk)
        ↓
    LIVE STRUCTURED RISK EVENTS

Active detectors: W2V2-AASIST (Real), AASIST (Real)
Acoustic: Unavailable (Phase 9)
"""

import argparse
from collections import deque
from datetime import datetime
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional

# ============================================================
# WINDOWS CUDA & CUDNN DLL REGISTRATION
# ============================================================
def _setup_nvidia_dll_paths() -> None:
    """
    On Windows with Python 3.8+, DLL dependencies for C-extensions
    must be explicitly added using os.add_dll_directory.
    Register installed CUDA and cuDNN binaries from the active environment.
    """
    if sys.platform != "win32":
        return

    site_packages_roots = [
        Path(sys.prefix) / "Lib" / "site-packages" / "nvidia",
    ]

    try:
        import site
        if hasattr(site, "getusersitepackages"):
            site_packages_roots.append(Path(site.getusersitepackages()) / "nvidia")
    except Exception:
        pass

    dll_dirs = []
    for root in site_packages_roots:
        if not root.exists():
            continue
        for dll_file in root.rglob("*.dll"):
            parent_dir = dll_file.parent.resolve()
            if parent_dir not in dll_dirs:
                dll_dirs.append(parent_dir)

    for d in dll_dirs:
        try:
            os.add_dll_directory(str(d))
        except (AttributeError, OSError):
            pass
        os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")

_setup_nvidia_dll_paths()

# Project root path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import sounddevice as sd
import soundfile as sf
import librosa

from ai.ssl_detector.w2v2_aasist_adapter import W2V2AASISTAdapter
from ai.aasist.aasist_adapter import AASISTAdapter
from ai.acoustic.audio_quality import AudioQualityAnalyzer
from risk_engine.risk_engine import RiskEngine
from streaming.vad_gate import EnergyVADGate


# ============================================================
# PIPELINE CONFIGURATION
# ============================================================
SAMPLE_RATE = 16000
WINDOW_SAMPLES = 64600                       # ~4.0375s model window
WINDOW_SECONDS = WINDOW_SAMPLES / SAMPLE_RATE
BLOCK_SIZE = 1600                            # 100ms microphone block
ANALYSIS_INTERVAL = 1.0                      # 1.0 second analysis hop
CHANNELS = 1                                 # Mono audio
DEFAULT_VAD_THRESHOLD_DB = -38.0            # VAD energy threshold in dBFS


class LiveRiskPipeline:
    """
    Orchestrates continuous audio acquisition, rolling window extraction,
    VAD speech activity gating, audio quality analysis, multi-model spoof inference
    (W2V2-AASIST + AASIST), evidence fusion, and temporal risk scoring.
    """

    def __init__(
        self,
        model_path: Optional[str | Path] = None,
        aasist_model_path: Optional[str | Path] = None,
        vad_threshold_db: float = DEFAULT_VAD_THRESHOLD_DB,
    ):
        self.sample_rate = SAMPLE_RATE
        self.window_samples = WINDOW_SAMPLES
        self.window_seconds = WINDOW_SECONDS
        self.analysis_interval = ANALYSIS_INTERVAL

        print("Initializing EchoShield Multi-Model Live Risk Pipeline...")

        # 1. Speech Activity / VAD Gate
        self.vad_gate = EnergyVADGate(
            energy_threshold_db=vad_threshold_db,
            sample_rate=self.sample_rate,
        )
        print(f"VAD Gate initialized (Threshold: {vad_threshold_db:.1f} dBFS)")

        # 2. Audio Quality Analyzer
        self.quality_analyzer = AudioQualityAnalyzer(sample_rate=self.sample_rate)
        print("Audio Quality Analyzer initialized.")

        # 3. Model 1: W2V2-AASIST Adapter
        try:
            if model_path:
                self.w2v2_adapter = W2V2AASISTAdapter(model_path=model_path)
            else:
                self.w2v2_adapter = W2V2AASISTAdapter()
        except Exception as e:
            print(f"[ERROR] Failed to load W2V2-AASIST model: {e}", file=sys.stderr)
            raise

        # 4. Model 2: AASIST Adapter
        try:
            if aasist_model_path:
                self.aasist_adapter = AASISTAdapter(model_path=aasist_model_path)
            else:
                self.aasist_adapter = AASISTAdapter()
        except Exception as e:
            print(f"[ERROR] Failed to load AASIST model: {e}", file=sys.stderr)
            raise

        # Check execution providers
        w2v2_provider = self.w2v2_adapter.detector.session.get_providers()[0]
        aasist_provider = self.aasist_adapter.session.get_providers()[0]
        print(f"W2V2-AASIST Provider: {w2v2_provider}")
        print(f"AASIST Provider:      {aasist_provider}")

        # 5. Risk Engine
        self.risk_engine = RiskEngine()

        # Audio rolling buffer
        self.buffer: deque = deque(maxlen=self.window_samples)

        # Performance & session metrics
        self.window_count = 0
        self.speech_windows = 0
        self.non_speech_windows = 0
        self.w2v2_executions = 0
        self.aasist_executions = 0

        self.vad_latencies: List[float] = []
        self.w2v2_latencies: List[float] = []
        self.aasist_latencies: List[float] = []
        self.quality_latencies: List[float] = []
        self.total_processing_times: List[float] = []
        self.analysis_intervals: List[float] = []
        self.risk_scores: List[float] = []
        self.risk_levels_count = {
            "LOW": 0,
            "SUSPICIOUS": 0,
            "HIGH": 0,
            "NO_SPEECH": 0,
        }
        self.active_detectors = [
            self.w2v2_adapter.MODEL_NAME,
            self.aasist_adapter.model_name,
        ]
        self.events: List[Dict[str, Any]] = []

    def reset_metrics(self) -> None:
        """Reset session metrics and buffer."""
        self.buffer.clear()
        self.window_count = 0
        self.speech_windows = 0
        self.non_speech_windows = 0
        self.w2v2_executions = 0
        self.aasist_executions = 0
        self.vad_latencies.clear()
        self.w2v2_latencies.clear()
        self.aasist_latencies.clear()
        self.quality_latencies.clear()
        self.total_processing_times.clear()
        self.analysis_intervals.clear()
        self.risk_scores.clear()
        self.risk_levels_count = {
            "LOW": 0,
            "SUSPICIOUS": 0,
            "HIGH": 0,
            "NO_SPEECH": 0,
        }
        self.events.clear()

    def process_window(
        self,
        audio_window: np.ndarray,
        timestamp_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a single 64,600-sample audio window through VAD gating,
        quality analysis, multi-model spoof inference, and temporal risk scoring.
        """
        t_start = time.perf_counter()
        self.window_count += 1

        if timestamp_str is None:
            timestamp_str = datetime.now().isoformat()

        # 1. Speech Activity / VAD Gate
        vad_res = self.vad_gate.is_speech(audio_window, sample_rate=self.sample_rate)
        vad_lat = float(vad_res["latency_ms"])
        self.vad_latencies.append(vad_lat)

        speech_present = bool(vad_res["speech_detected"])
        speech_ratio = float(vad_res["speech_ratio"])

        # 2. Audio Quality Analysis (Computed for all windows)
        quality_res = self.quality_analyzer.analyze(audio_window, self.sample_rate)
        self.quality_latencies.append(float(quality_res["latency_ms"]))

        # -------------------------------------------------------------
        # BRANCH A: NON-SPEECH (Silence / Background Noise)
        # -------------------------------------------------------------
        if not speech_present:
            self.non_speech_windows += 1
            self.risk_levels_count["NO_SPEECH"] += 1

            t_end = time.perf_counter()
            total_proc_ms = (t_end - t_start) * 1000.0
            self.total_processing_times.append(total_proc_ms)

            # Structured non-speech event
            event: Dict[str, Any] = {
                "window_id": self.window_count,
                "timestamp": timestamp_str,
                "speech_present": False,
                "speech_ratio": speech_ratio,
                "audio": {
                    "sample_rate": self.sample_rate,
                    "window_samples": len(audio_window),
                    "window_seconds": round(len(audio_window) / self.sample_rate, 4),
                },
                "vad": vad_res,
                "audio_quality": quality_res,
                "detectors": [],
                "risk_status": "NO_SPEECH",
            }

            self.events.append(event)
            self._print_window_report(event)
            return event

        # -------------------------------------------------------------
        # BRANCH B: SPEECH DETECTED (Run W2V2-AASIST + AASIST + RiskEngine)
        # -------------------------------------------------------------
        self.speech_windows += 1
        self.w2v2_executions += 1
        self.aasist_executions += 1

        # Run Model 1: W2V2-AASIST
        w2v2_result = self.w2v2_adapter.predict_audio(
            audio_window,
            sample_rate=self.sample_rate,
        )
        w2v2_result["status"] = "REAL"
        w2v2_lat = float(w2v2_result["latency_ms"])
        self.w2v2_latencies.append(w2v2_lat)

        # Run Model 2: AASIST
        aasist_result = self.aasist_adapter.predict_audio(
            audio_window,
            sample_rate=self.sample_rate,
        )
        aasist_result["status"] = "REAL"
        aasist_lat = float(aasist_result["latency_ms"])
        self.aasist_latencies.append(aasist_lat)

        # Multi-model agreement check:
        # Both models indicate spoof (score >= 0.40) or both indicate bona fide (score < 0.40)
        w2v2_score = float(w2v2_result["raw_score"])
        aasist_score = float(aasist_result["raw_score"])
        model_agreement = (
            (w2v2_score >= 0.40 and aasist_score >= 0.40)
            or (w2v2_score < 0.40 and aasist_score < 0.40)
        )

        # Risk orchestration: Both real detector results passed.
        risk_output = self.risk_engine.update(
            [w2v2_result, aasist_result],
            model_agreement=model_agreement,
        )

        t_end = time.perf_counter()
        total_proc_ms = (t_end - t_start) * 1000.0
        self.total_processing_times.append(total_proc_ms)

        risk_score = float(risk_output["risk_score"])
        self.risk_scores.append(risk_score)
        risk_level = str(risk_output["risk_level"])
        self.risk_levels_count[risk_level] = self.risk_levels_count.get(risk_level, 0) + 1

        # Construct structured multi-model speech event dictionary
        event = {
            "window_id": self.window_count,
            "timestamp": timestamp_str,
            "speech_present": True,
            "speech_ratio": speech_ratio,
            "audio": {
                "sample_rate": self.sample_rate,
                "window_samples": len(audio_window),
                "window_seconds": round(len(audio_window) / self.sample_rate, 4),
            },
            "vad": vad_res,
            "audio_quality": quality_res,
            "detectors": [
                {
                    "model": w2v2_result["model"],
                    "raw_score": round(float(w2v2_result["raw_score"]), 4),
                    "latency_ms": round(w2v2_lat, 2),
                    "score_direction": w2v2_result["score_direction"],
                    "status": "REAL",
                    "metadata": w2v2_result.get("metadata", {}),
                },
                {
                    "model": aasist_result["model"],
                    "raw_score": round(float(aasist_result["raw_score"]), 4),
                    "latency_ms": round(aasist_lat, 2),
                    "score_direction": aasist_result["score_direction"],
                    "status": "REAL",
                    "metadata": aasist_result.get("metadata", {}),
                },
            ],
            "fusion": risk_output["fusion"],
            "temporal": risk_output["temporal"],
            "risk_score": round(risk_score, 4),
            "risk_score_percent": round(float(risk_output["risk_score_percent"]), 2),
            "risk_level": risk_level,
            "reasons": risk_output["reasons"],
        }

        self.events.append(event)
        self._print_window_report(event)
        return event

    def _print_window_report(self, event: Dict[str, Any]) -> None:
        """Print clean live report for each processed window."""
        window_id = event["window_id"]
        ts = event["timestamp"]
        vad = event["vad"]
        q = event["audio_quality"]

        print("==================================================")
        print("ECHOSHIELD MULTI-MODEL LIVE RISK MONITOR")
        print("========================================")
        print(f"Window: {window_id:03d}")
        print(f"Timestamp: {ts}")
        print()
        print("VAD")
        print(f"  status: {vad['status']}")
        print(f"  speech_activity_score: {vad['speech_activity_score']:.3f}")
        print(f"  energy_db: {vad['energy_db']:.1f} dB")
        print(f"  speech_ratio: {vad.get('speech_ratio', 0.0):.2f}")
        print()
        print("AUDIO QUALITY")
        print(f"  quality_level: {q['quality_level']} (score: {q['quality_score']:.2f})")
        print(f"  estimated_snr: {q['estimated_snr_db']:.1f} dB")
        print(f"  clipping_ratio: {q['clipping_ratio']:.4f}")
        print(f"  spectral_flatness: {q['spectral_flatness']:.4f}")

        if vad["status"] == "NON_SPEECH":
            print()
            print("STATUS")
            print(f"  risk_status: {event['risk_status']}")
            print("  note: Detector inferences bypassed (non-speech)")
            print("==================================================")
            print()
            return

        # Speech event sections
        detectors = event["detectors"]
        fusion = event["fusion"]
        temporal = event["temporal"]
        reasons = event["reasons"]

        print()
        print("DETECTORS (REAL)")
        for d in detectors:
            print(f"  {d['model']}: spoof_score={d['raw_score']:.3f}, latency={d['latency_ms']:.1f} ms, status={d['status']}")
        print()
        print("FUSION")
        print(f"  fused_score: {fusion['fused_score']:.3f}")
        print(f"  active_models: {fusion['active_models']}")
        print(f"  weights sum: {fusion['total_active_weight']:.2f}")
        print()
        print("TEMPORAL")
        print(f"  moving_average: {temporal['moving_average']:.3f}")
        print(f"  ema: {temporal['ema']:.3f}")
        print(f"  trend: {temporal['trend']:.3f}")
        print(f"  agreement: {temporal.get('model_agreement')}")
        print()
        print("RISK")
        print(f"  risk_score: {event['risk_score']:.3f}")
        print(f"  risk_percent: {event['risk_score_percent']:.1f}%")
        print(f"  level: {event['risk_level']}")
        print()
        print("REASONS")
        if reasons:
            for r in reasons:
                print(f"  * {r}")
        else:
            print("  * None")
        print("==================================================")
        print()

    def print_session_summary(self) -> None:
        """Print comprehensive metrics upon stream completion or termination."""
        print()
        print("==================================================")
        print("ECHOSHIELD LIVE RISK MONITOR - SESSION SUMMARY")
        print("==================================================")
        print(f"Total windows analyzed:   {self.window_count}")
        print(f"Speech windows:           {self.speech_windows}")
        print(f"Non-speech windows:       {self.non_speech_windows}")
        print(f"W2V2 executions:          {self.w2v2_executions}")
        print(f"AASIST executions:        {self.aasist_executions}")

        if self.vad_latencies:
            avg_vad = sum(self.vad_latencies) / len(self.vad_latencies)
            print(f"VAD Latency (avg):        {avg_vad:.2f} ms")

        if self.quality_latencies:
            avg_q = sum(self.quality_latencies) / len(self.quality_latencies)
            print(f"Audio Quality Latency (avg): {avg_q:.2f} ms")

        if self.w2v2_latencies:
            avg_w2v2 = sum(self.w2v2_latencies) / len(self.w2v2_latencies)
            sorted_w2v2 = sorted(self.w2v2_latencies)
            med_w2v2 = sorted_w2v2[len(sorted_w2v2) // 2]
            print(f"W2V2 Latency (avg):       {avg_w2v2:.2f} ms (median: {med_w2v2:.2f} ms)")
        else:
            print("W2V2 Latency:             N/A")

        if self.aasist_latencies:
            avg_aasist = sum(self.aasist_latencies) / len(self.aasist_latencies)
            sorted_aasist = sorted(self.aasist_latencies)
            med_aasist = sorted_aasist[len(sorted_aasist) // 2]
            print(f"AASIST Latency (avg):     {avg_aasist:.2f} ms (median: {med_aasist:.2f} ms)")
        else:
            print("AASIST Latency:           N/A")

        if self.total_processing_times:
            avg_proc = sum(self.total_processing_times) / len(self.total_processing_times)
            sorted_proc = sorted(self.total_processing_times)
            med_proc = sorted_proc[len(sorted_proc) // 2]
            print(f"Avg total processing:     {avg_proc:.2f} ms (median: {med_proc:.2f} ms)")

        if self.analysis_intervals:
            avg_interval = sum(self.analysis_intervals) / len(self.analysis_intervals)
            print(f"Avg analysis interval:    {avg_interval:.3f} s")

        if self.risk_scores:
            avg_risk = sum(self.risk_scores) / len(self.risk_scores)
            max_risk = max(self.risk_scores)
            print(f"Average risk score:       {avg_risk:.4f} ({avg_risk * 100:.1f}%)")
            print(f"Highest risk score:       {max_risk:.4f} ({max_risk * 100:.1f}%)")
        else:
            print("Average risk score:       N/A (no speech windows)")

        print(
            f"Risk levels breakdown:    LOW={self.risk_levels_count['LOW']}, "
            f"SUSPICIOUS={self.risk_levels_count['SUSPICIOUS']}, "
            f"HIGH={self.risk_levels_count['HIGH']}, "
            f"NO_SPEECH={self.risk_levels_count['NO_SPEECH']}"
        )
        print(f"Active detectors:         {self.active_detectors}")
        print("==================================================")

    def run_file(
        self,
        file_path: str | Path,
        simulated_delay: float = 0.0,
        max_windows: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run multi-model test stream using a pre-recorded audio file.
        Passes audio in 1.0-second hops through the rolling buffer.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        print(f"Loading test audio file: {file_path}")
        audio_data, file_sr = sf.read(str(file_path), dtype="float32")

        # Downmix stereo to mono if needed
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)

        # Resample to 16 kHz if needed
        if file_sr != self.sample_rate:
            print(f"Resampling audio from {file_sr} Hz to {self.sample_rate} Hz...")
            audio_data = librosa.resample(
                audio_data,
                orig_sr=file_sr,
                target_sr=self.sample_rate,
            )

        total_samples = len(audio_data)
        total_seconds = total_samples / self.sample_rate
        print(f"Audio loaded: {total_samples} samples ({total_seconds:.2f} seconds)")

        if total_samples < self.window_samples:
            raise ValueError(
                f"Audio too short for analysis: {total_samples} samples "
                f"< {self.window_samples} required."
            )

        self.reset_metrics()
        hop_samples = int(self.analysis_interval * self.sample_rate)  # 16,000 samples

        # Feed initial window (first 64,600 samples)
        for s in audio_data[:self.window_samples]:
            self.buffer.append(float(s))

        audio_cursor = self.window_samples

        try:
            while True:
                # Analyze current buffer content
                audio_window = np.array(self.buffer, dtype=np.float32)
                if self.window_count > 0:
                    self.analysis_intervals.append(
                        simulated_delay if simulated_delay > 0 else 1.0
                    )

                self.process_window(audio_window)

                if max_windows and self.window_count >= max_windows:
                    break

                # Advance by hop_samples
                if audio_cursor + hop_samples <= total_samples:
                    next_chunk = audio_data[audio_cursor : audio_cursor + hop_samples]
                    for s in next_chunk:
                        self.buffer.append(float(s))
                    audio_cursor += hop_samples
                else:
                    # End of file reached
                    break

                if simulated_delay > 0:
                    time.sleep(simulated_delay)

        except KeyboardInterrupt:
            print("\nFile streaming interrupted by user.")
        finally:
            self.print_session_summary()

        return self.events

    def run_microphone(
        self,
        max_windows: Optional[int] = None,
        device_index: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run continuous real-time analysis from the local microphone.
        """
        try:
            devices = sd.query_devices()
            if not devices:
                raise RuntimeError("No audio devices found on system.")
        except Exception as e:
            print(f"[ERROR] SoundDevice device query failed: {e}", file=sys.stderr)
            raise

        self.reset_metrics()

        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"[AUDIO STREAM STATUS] {status}", file=sys.stderr)
            samples = indata[:, 0]
            for s in samples:
                self.buffer.append(float(s))

        print(f"Opening microphone stream (Device: {device_index or 'Default'})...")
        print(f"Sample rate:        {self.sample_rate} Hz")
        print(f"Window duration:    {self.window_seconds:.3f} s ({self.window_samples} samples)")
        print(f"Analysis interval:  {self.analysis_interval:.1f} s")
        print(f"VAD Threshold:      {self.vad_gate.energy_threshold_db:.1f} dBFS")
        print(f"Active Models:      {self.active_detectors}")
        print()
        print(f"Buffer will fill for {self.window_seconds:.1f} seconds before first window.")
        print("Press Ctrl+C at any time to stop and view the session summary.")
        print()

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=CHANNELS,
                dtype="float32",
                blocksize=BLOCK_SIZE,
                device=device_index,
                callback=audio_callback,
            ):
                last_analysis_time = time.perf_counter()

                while True:
                    current_time = time.perf_counter()

                    # Wait until rolling buffer is full
                    if len(self.buffer) >= self.window_samples:
                        elapsed = current_time - last_analysis_time
                        if elapsed >= self.analysis_interval:
                            if self.window_count > 0:
                                self.analysis_intervals.append(elapsed)

                            # Copy rolling buffer snapshot
                            audio_window = np.array(self.buffer, dtype=np.float32)

                            self.process_window(audio_window)
                            last_analysis_time = time.perf_counter()

                            if max_windows and self.window_count >= max_windows:
                                print(f"Reached maximum window limit: {max_windows}")
                                break

                    time.sleep(0.01)

        except KeyboardInterrupt:
            print("\nStopping live microphone stream...")
        except Exception as e:
            print(f"\n[STREAM ERROR] Microphone stream encountered an error: {e}", file=sys.stderr)
            raise
        finally:
            self.print_session_summary()

        return self.events


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="EchoShield Multi-Model Live Risk Pipeline - Real-time Voice Spoof Monitoring"
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to an audio file (e.g. real_speech.wav) to analyze instead of microphone.",
    )
    parser.add_argument(
        "--max-windows",
        type=int,
        default=None,
        help="Maximum number of windows to process before stopping (default: unlimited).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Simulated delay in seconds between windows in file mode (default: 0.0).",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Audio input device index for microphone mode.",
    )
    parser.add_argument(
        "--vad-threshold",
        type=float,
        default=DEFAULT_VAD_THRESHOLD_DB,
        help=f"VAD energy threshold in dBFS (default: {DEFAULT_VAD_THRESHOLD_DB}).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        pipeline = LiveRiskPipeline(vad_threshold_db=args.vad_threshold)
    except Exception as e:
        print(f"Pipeline initialization failed: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.file:
            pipeline.run_file(
                file_path=args.file,
                simulated_delay=args.delay,
                max_windows=args.max_windows,
            )
        else:
            pipeline.run_microphone(
                max_windows=args.max_windows,
                device_index=args.device,
            )
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Pipeline execution halted: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
