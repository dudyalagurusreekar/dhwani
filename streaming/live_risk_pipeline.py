"""
EchoShield Live Risk Pipeline
=============================
Real-time integration connecting:
REAL AUDIO (MICROPHONE / FILE)
    ↓
ROLLING AUDIO BUFFER (64,600 samples @ 16 kHz)
    ↓
SPEECH ACTIVITY GATE / VAD PRE-FILTER
    ↓
if NON_SPEECH:
    Bypass W2V2 inference -> emit NO_SPEECH structured event
if SPEECH:
    REAL W2V2-AASIST DETECTOR ADAPTER
        ↓
    EXISTING RISK ENGINE (Fusion + Temporal Aggregation)
        ↓
    LIVE STRUCTURED RISK EVENTS

Active detector: W2V2-AASIST (Real)
AASIST: Unavailable
Acoustic: Unavailable
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
    VAD speech activity gating, W2V2-AASIST spoof inference, and multi-window
    temporal risk scoring.
    """

    def __init__(
        self,
        model_path: Optional[str | Path] = None,
        vad_threshold_db: float = DEFAULT_VAD_THRESHOLD_DB,
    ):
        self.sample_rate = SAMPLE_RATE
        self.window_samples = WINDOW_SAMPLES
        self.window_seconds = WINDOW_SECONDS
        self.analysis_interval = ANALYSIS_INTERVAL

        print("Initializing EchoShield Live Risk Pipeline...")

        # Initialize VAD speech activity gate
        self.vad_gate = EnergyVADGate(
            energy_threshold_db=vad_threshold_db,
            sample_rate=self.sample_rate,
        )
        print(f"VAD Gate initialized (Threshold: {vad_threshold_db:.1f} dBFS)")

        # Initialize W2V2-AASIST adapter
        try:
            if model_path:
                self.adapter = W2V2AASISTAdapter(model_path=model_path)
            else:
                self.adapter = W2V2AASISTAdapter()
        except Exception as e:
            print(f"[ERROR] Failed to load W2V2-AASIST model: {e}", file=sys.stderr)
            raise

        # Check execution provider
        providers = self.adapter.detector.session.get_providers()
        print(f"Execution Providers: {providers}")
        if "CUDAExecutionProvider" in providers:
            print("CUDA/GPU acceleration is active.")
        else:
            print("Running on CPU execution provider.")

        # Initialize RiskEngine
        self.risk_engine = RiskEngine()

        # Audio rolling buffer
        self.buffer: deque = deque(maxlen=self.window_samples)

        # Performance & session metrics
        self.window_count = 0
        self.speech_windows = 0
        self.non_speech_windows = 0
        self.w2v2_executions = 0

        self.vad_latencies: List[float] = []
        self.w2v2_latencies: List[float] = []
        self.total_processing_times: List[float] = []
        self.analysis_intervals: List[float] = []
        self.risk_scores: List[float] = []
        self.risk_levels_count = {
            "LOW": 0,
            "SUSPICIOUS": 0,
            "HIGH": 0,
            "NO_SPEECH": 0,
        }
        self.active_detectors = [self.adapter.MODEL_NAME]
        self.events: List[Dict[str, Any]] = []

    def reset_metrics(self) -> None:
        """Reset session metrics and buffer."""
        self.buffer.clear()
        self.window_count = 0
        self.speech_windows = 0
        self.non_speech_windows = 0
        self.w2v2_executions = 0
        self.vad_latencies.clear()
        self.w2v2_latencies.clear()
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
        conditional W2V2-AASIST inference, and temporal risk scoring.
        """
        t_start = time.perf_counter()
        self.window_count += 1

        if timestamp_str is None:
            timestamp_str = datetime.now().isoformat()

        # 1. Speech Activity / VAD Gate
        vad_res = self.vad_gate.is_speech(audio_window, sample_rate=self.sample_rate)
        vad_lat = float(vad_res["latency_ms"])
        self.vad_latencies.append(vad_lat)

        # -------------------------------------------------------------
        # BRANCH A: NON-SPEECH (Silence / Background Noise)
        # -------------------------------------------------------------
        if not vad_res["speech_detected"]:
            self.non_speech_windows += 1
            self.risk_levels_count["NO_SPEECH"] += 1

            t_end = time.perf_counter()
            total_proc_ms = (t_end - t_start) * 1000.0
            self.total_processing_times.append(total_proc_ms)

            # Temporal engine update is bypassed for non-speech windows
            # to preserve genuine speech spoofing history without distortion.
            event: Dict[str, Any] = {
                "window_id": self.window_count,
                "timestamp": timestamp_str,
                "audio": {
                    "sample_rate": self.sample_rate,
                    "window_samples": len(audio_window),
                    "window_seconds": round(len(audio_window) / self.sample_rate, 4),
                },
                "vad": {
                    "speech_detected": False,
                    "speech_activity_score": vad_res["speech_activity_score"],
                    "energy_db": vad_res["energy_db"],
                    "rms": vad_res["rms"],
                    "active_frame_ratio": vad_res["active_frame_ratio"],
                    "zcr": vad_res["zcr"],
                    "status": "NON_SPEECH",
                    "reason": vad_res["reason"],
                    "latency_ms": vad_lat,
                },
                "detectors": [],
                "risk_status": "NO_SPEECH",
            }

            self.events.append(event)
            self._print_window_report(event)
            return event

        # -------------------------------------------------------------
        # BRANCH B: SPEECH DETECTED (Run W2V2-AASIST + RiskEngine)
        # -------------------------------------------------------------
        self.speech_windows += 1
        self.w2v2_executions += 1

        # Run real W2V2-AASIST detector
        detector_result = self.adapter.predict_audio(
            audio_window,
            sample_rate=self.sample_rate,
        )
        detector_result["status"] = "REAL"

        # Risk orchestration: ONLY real detector result passed.
        # model_agreement=False because only 1 detector is currently available.
        risk_output = self.risk_engine.update(
            [detector_result],
            model_agreement=False,
        )

        t_end = time.perf_counter()
        total_proc_ms = (t_end - t_start) * 1000.0

        # Record metrics
        w2v2_lat = float(detector_result["latency_ms"])
        self.w2v2_latencies.append(w2v2_lat)
        self.total_processing_times.append(total_proc_ms)

        risk_score = float(risk_output["risk_score"])
        self.risk_scores.append(risk_score)
        risk_level = str(risk_output["risk_level"])
        self.risk_levels_count[risk_level] = self.risk_levels_count.get(risk_level, 0) + 1

        # Construct structured speech event dictionary
        event: Dict[str, Any] = {
            "window_id": self.window_count,
            "timestamp": timestamp_str,
            "audio": {
                "sample_rate": self.sample_rate,
                "window_samples": len(audio_window),
                "window_seconds": round(len(audio_window) / self.sample_rate, 4),
            },
            "vad": {
                "speech_detected": True,
                "speech_activity_score": vad_res["speech_activity_score"],
                "energy_db": vad_res["energy_db"],
                "rms": vad_res["rms"],
                "active_frame_ratio": vad_res["active_frame_ratio"],
                "zcr": vad_res["zcr"],
                "status": "SPEECH",
                "reason": vad_res["reason"],
                "latency_ms": vad_lat,
            },
            "detectors": [
                {
                    "model": detector_result["model"],
                    "raw_score": round(float(detector_result["raw_score"]), 4),
                    "latency_ms": round(w2v2_lat, 2),
                    "score_direction": detector_result["score_direction"],
                    "status": "REAL",
                    "metadata": detector_result.get("metadata", {}),
                }
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

        print("==================================================")
        print("ECHOSHIELD LIVE RISK MONITOR")
        print("============================")
        print(f"Window: {window_id:03d}")
        print(f"Timestamp: {ts}")
        print()
        print("VAD")
        print(f"  status: {vad['status']}")
        print(f"  speech_activity_score: {vad['speech_activity_score']:.3f}")
        print(f"  energy_db: {vad['energy_db']:.1f} dB")
        print(f"  reason: {vad['reason']}")

        if vad["status"] == "NON_SPEECH":
            print()
            print("STATUS")
            print(f"  risk_status: {event['risk_status']}")
            print("  note: W2V2-AASIST inference bypassed (non-speech)")
            print("==================================================")
            print()
            return

        # Speech event sections
        d = event["detectors"][0]
        fusion = event["fusion"]
        temporal = event["temporal"]
        reasons = event["reasons"]

        print()
        print("DETECTORS")
        print(f"{d['model']}")
        print(f"  spoof_score: {d['raw_score']:.3f}")
        print(f"  latency_ms: {d['latency_ms']:.1f}")
        print(f"  status: {d['status']}")
        print()
        print("FUSION")
        print(f"  fused_score: {fusion['fused_score']:.3f}")
        print(f"  active_models: {fusion['active_models']}")
        print()
        print("TEMPORAL")
        print(f"  moving_average: {temporal['moving_average']:.3f}")
        print(f"  ema: {temporal['ema']:.3f}")
        print(f"  trend: {temporal['trend']:.3f}")
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

        if self.vad_latencies:
            avg_vad = sum(self.vad_latencies) / len(self.vad_latencies)
            print(f"VAD Latency (avg):        {avg_vad:.2f} ms")

        if self.w2v2_latencies:
            avg_lat = sum(self.w2v2_latencies) / len(self.w2v2_latencies)
            min_lat = min(self.w2v2_latencies)
            max_lat = max(self.w2v2_latencies)
            sorted_lat = sorted(self.w2v2_latencies)
            med_lat = sorted_lat[len(sorted_lat) // 2]
            print(f"W2V2 Latency (avg):       {avg_lat:.2f} ms")
            print(f"W2V2 Latency (median):    {med_lat:.2f} ms")
            print(f"W2V2 Latency (min/max):   {min_lat:.2f} ms / {max_lat:.2f} ms")
        else:
            print("W2V2 Latency:             N/A (no speech windows executed)")

        if self.total_processing_times:
            avg_proc = sum(self.total_processing_times) / len(self.total_processing_times)
            print(f"Avg total processing:     {avg_proc:.2f} ms")

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
        Run test stream using a pre-recorded audio file.
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
        # Verify microphone availability
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
        description="EchoShield Live Risk Pipeline - Real-time Voice Spoof Monitoring"
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
