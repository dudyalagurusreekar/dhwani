"""
EchoShield Live Multi-Model Risk Pipeline
=========================================
Real-time voice anti-spoofing and prevention system connecting:
REAL AUDIO (MICROPHONE / FILE / WEBSOCKET)
    ↓
ROLLING AUDIO BUFFER (64,600 samples @ 16 kHz mono, ~4.0375s)
    ↓
SPEECH ACTIVITY GATE / VAD PRE-FILTER (0.37 ms)
    ↓
if NON_SPEECH:
    Bypass deep models -> emit NO_SPEECH structured event (0 GPU cycles)
if SPEECH:
    AUDIO QUALITY ANALYZER (SNR, Clipping, Flatness, RMS)
        ↓
    TIERED / ENSEMBLE MULTI-MODEL DETECTORS:
    ├── Tier 1 (Fast Edge):
    │   ├── AASIST (CUDA, ~21 ms, 1.54 MB)
    │   ├── AASIST-L (CUDA, ~22 ms, 766 KB)
    │   └── ACOUSTIC (CPU Spectral/Cepstral, ~10 ms)
    └── Tier 2 (Deep SSL Escalation):
        └── W2V2-AASIST (CUDA, ~37 ms, 1.18 GB)
        ↓
    ADAPTIVE EVIDENCE FUSION (Quality-Weighted Dynamic Renormalization)
        ↓
    MULTI-MODEL AGREEMENT & CONSENSUS (Unanimous / Majority / Conflicted)
        ↓
    ATTACK ATTRIBUTION (Synthetic TTS / Voice Conversion / Physical Replay)
        ↓
    TEMPORAL RISK ENGINE (Moving Avg, EMA, Trend, Explainable Reasons)
        ↓
    ACTIVE MITIGATION & CALL INTERCEPTION (Allow / Honeypot / Disruption / Terminate)
        ↓
    STRUCTURED TELEMETRY BROADCAST (Console & WebSocket)
"""

import argparse
from collections import deque
from datetime import datetime
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable, Dict, List, Optional

# Preload NVIDIA CUDA / cuDNN DLLs on Windows
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.common.gpu_utils import setup_nvidia_dll_paths
setup_nvidia_dll_paths()

import numpy as np
import sounddevice as sd
import soundfile as sf
import librosa

from ai.ssl_detector.w2v2_aasist_adapter import W2V2AASISTAdapter
from ai.aasist.aasist_adapter import AASISTAdapter
from ai.aasist.aasist_l_adapter import AASISTLAdapter
from ai.acoustic.acoustic_detector import AcousticDetector
from ai.acoustic.audio_quality import AudioQualityAnalyzer
from risk_engine.risk_engine import RiskEngine
from risk_engine.adaptive_fusion import AdaptiveFusionEngine
from risk_engine.model_agreement import ModelAgreementEngine
from ai.common.tiered_inference import TieredInferenceManager
from ai.common.attack_attribution import AttackAttributionEngine
from ai.prevention.call_interceptor import CallInterceptor
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
    VAD speech activity gating, audio quality analysis, multi-model spoof inference,
    adaptive fusion, model agreement, attack attribution, and active prevention.
    """

    def __init__(
        self,
        vad_threshold_db: float = DEFAULT_VAD_THRESHOLD_DB,
        tiered_mode: bool = False,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self.sample_rate = SAMPLE_RATE
        self.window_samples = WINDOW_SAMPLES
        self.window_seconds = WINDOW_SECONDS
        self.analysis_interval = ANALYSIS_INTERVAL
        self.tiered_mode = tiered_mode
        self.on_event = on_event

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

        # 3. Model Initializations
        print("Loading Deep Neural & Acoustic Detectors...")
        self.w2v2_adapter = W2V2AASISTAdapter()
        self.aasist_adapter = AASISTAdapter()
        self.aasist_l_adapter = AASISTLAdapter()
        self.acoustic_detector = AcousticDetector()

        self.active_detectors = [
            self.w2v2_adapter.MODEL_NAME,
            self.aasist_adapter.model_name,
            self.aasist_l_adapter.model_name,
            self.acoustic_detector.model_name,
        ]

        # 4. Tiered Inference Manager
        tier1 = [self.aasist_adapter, self.aasist_l_adapter, self.acoustic_detector]
        tier2 = [self.w2v2_adapter]
        self.tiered_manager = TieredInferenceManager(
            tier1_detectors=tier1,
            tier2_detectors=tier2,
            escalation_threshold=0.25,
            enabled=self.tiered_mode,
        )
        print(f"Tiered Inference Mode: {'ENABLED' if self.tiered_mode else 'FULL ENSEMBLE'}")

        # 5. Decision & Prevention Engines
        self.adaptive_fusion = AdaptiveFusionEngine()
        self.model_agreement_engine = ModelAgreementEngine(decision_threshold=0.40)
        self.attack_attribution_engine = AttackAttributionEngine(spoof_threshold=0.40)
        self.call_interceptor = CallInterceptor()
        self.risk_engine = RiskEngine()

        # Audio rolling buffer
        self.buffer: deque = deque(maxlen=self.window_samples)

        # Performance & session metrics
        self.window_count = 0
        self.speech_windows = 0
        self.non_speech_windows = 0
        self.detector_executions: Dict[str, int] = {m: 0 for m in self.active_detectors}

        self.vad_latencies: List[float] = []
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
        self.events: List[Dict[str, Any]] = []

    @property
    def w2v2_executions(self) -> int:
        return self.detector_executions.get("W2V2-AASIST", 0)

    @property
    def aasist_executions(self) -> int:
        return self.detector_executions.get("AASIST", 0)

    def reset_metrics(self) -> None:
        """Reset session metrics and buffer."""
        self.buffer.clear()
        self.window_count = 0
        self.speech_windows = 0
        self.non_speech_windows = 0
        for m in self.detector_executions:
            self.detector_executions[m] = 0
        self.vad_latencies.clear()
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
        quality analysis, multi-model spoof inference, adaptive fusion,
        agreement consensus, attack attribution, and prevention interceptor.
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
                "risk_score": 0.0,
                "risk_score_percent": 0.0,
                "risk_level": "NO_SPEECH",
                "action": {
                    "action": "ALLOW",
                    "severity": "INFO",
                    "policy_reason": "Non-speech audio passed (silence/background).",
                },
            }

            self.events.append(event)
            self._print_window_report(event)
            if self.on_event:
                self.on_event(event)
            return event

        # -------------------------------------------------------------
        # BRANCH B: SPEECH DETECTED (Run Multi-Model Inference)
        # -------------------------------------------------------------
        self.speech_windows += 1

        # Execute tiered / ensemble inference
        inference_out = self.tiered_manager.run_inference(
            audio_window,
            sample_rate=self.sample_rate,
        )
        detector_results = inference_out["results"]

        for d in detector_results:
            name = d.get("model", "UNKNOWN")
            self.detector_executions[name] = self.detector_executions.get(name, 0) + 1

        # Adaptive Reliability Fusion
        fusion_out = self.adaptive_fusion.fuse(detector_results, quality_res)

        # Multi-Model Agreement & Consensus
        agreement_out = self.model_agreement_engine.evaluate_agreement(detector_results)

        # Attack Attribution
        attribution_out = self.attack_attribution_engine.attribute_attack(
            risk_score=fusion_out["fused_score"],
            detector_results=detector_results,
            audio_quality=quality_res,
        )

        # Temporal Risk Engine update
        risk_output = self.risk_engine.update(
            detector_results,
            model_agreement=agreement_out["is_concordant"],
        )

        risk_score = float(risk_output["risk_score"])
        risk_level = str(risk_output["risk_level"])
        self.risk_scores.append(risk_score)
        self.risk_levels_count[risk_level] = self.risk_levels_count.get(risk_level, 0) + 1

        # Active Call Interception & Prevention Evaluation
        action_out = self.call_interceptor.evaluate_action(
            risk_score=risk_score,
            risk_level=risk_level,
            attribution=attribution_out,
            agreement=agreement_out,
        )

        t_end = time.perf_counter()
        total_proc_ms = (t_end - t_start) * 1000.0
        self.total_processing_times.append(total_proc_ms)

        # Append attribution / agreement explanations to temporal reasons
        reasons = list(risk_output["reasons"])
        if agreement_out["is_concordant"]:
            reasons.append(agreement_out["explanation"])
        if risk_score >= 0.40 and attribution_out["attribution_reasons"]:
            reasons.append(f"Attack vector: {attribution_out['primary_vector']} ({attribution_out['confidence']*100:.1f}%)")

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
            "detectors": detector_results,
            "tiered_inference": {
                "tier2_triggered": inference_out["tier2_triggered"],
                "escalation_reason": inference_out["escalation_reason"],
            },
            "fusion": fusion_out,
            "agreement": agreement_out,
            "attribution": attribution_out,
            "action": action_out,
            "temporal": risk_output["temporal"],
            "risk_score": round(risk_score, 4),
            "risk_score_percent": round(float(risk_output["risk_score_percent"]), 2),
            "risk_level": risk_level,
            "reasons": reasons,
        }

        self.events.append(event)
        self._print_window_report(event)
        if self.on_event:
            self.on_event(event)
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
        print(f"Window: {window_id:03d} | Timestamp: {ts}")
        print(f"VAD: {vad['status']} ({vad['energy_db']:.1f} dB, ratio: {vad.get('speech_ratio', 0.0):.2f}) | Quality: {q['quality_level']} (SNR: {q['estimated_snr_db']:.1f} dB)")

        if vad["status"] == "NON_SPEECH":
            print("STATUS: NO_SPEECH (Deep models bypassed)")
            print("==================================================")
            print()
            return

        detectors = event["detectors"]
        fusion = event["fusion"]
        agreement = event["agreement"]
        attrib = event["attribution"]
        action = event["action"]

        print()
        print("DETECTORS:")
        for d in detectors:
            print(f"  {d['model']:<12}: spoof={d['raw_score']:.3f} | {d['latency_ms']:.1f}ms")

        print()
        print(f"FUSION & CONSENSUS: Fused={fusion['fused_score']:.3f} | {agreement['consensus_level']} ({agreement['explanation']})")
        print(f"ATTRIBUTION:        {attrib['primary_vector']} ({attrib['confidence']*100:.1f}%)")
        print(f"ACTIVE MITIGATION:  {action['action']} [{action['severity']}] - {action['policy_reason']}")
        print(f"FINAL RISK SCORE:   {event['risk_score']:.3f} ({event['risk_score_percent']:.1f}%) -> [{event['risk_level']}]")
        print("REASONS:")
        for r in event["reasons"]:
            print(f"  * {r}")
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
        for m, count in self.detector_executions.items():
            print(f"  {m:<14} executions: {count}")
        if self.vad_latencies:
            print(f"VAD Latency (avg):        {np.mean(self.vad_latencies):.2f} ms")
        if self.quality_latencies:
            print(f"Audio Quality Latency:    {np.mean(self.quality_latencies):.2f} ms")
        if self.total_processing_times:
            print(f"Avg total processing:     {np.mean(self.total_processing_times):.2f} ms (median: {np.median(self.total_processing_times):.2f} ms)")
        if self.risk_scores:
            print(f"Average risk score:       {np.mean(self.risk_scores):.4f}")
            print(f"Highest risk score:       {np.max(self.risk_scores):.4f}")
        print(f"Risk levels breakdown:    {self.risk_levels_count}")
        print("==================================================")

    def run_file(
        self,
        file_path: str | Path,
        simulated_delay: float = 0.0,
        max_windows: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Run stream over audio file."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        print(f"Loading test audio file: {file_path}")
        audio_data, file_sr = sf.read(str(file_path), dtype="float32")
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)
        if file_sr != self.sample_rate:
            audio_data = librosa.resample(audio_data, orig_sr=file_sr, target_sr=self.sample_rate)

        total_samples = len(audio_data)
        if total_samples < self.window_samples:
            raise ValueError(f"Audio too short: {total_samples} samples < {self.window_samples} required.")

        self.reset_metrics()
        hop_samples = int(self.analysis_interval * self.sample_rate)

        for s in audio_data[:self.window_samples]:
            self.buffer.append(float(s))

        audio_cursor = self.window_samples

        try:
            while True:
                audio_window = np.array(self.buffer, dtype=np.float32)
                self.process_window(audio_window)

                if max_windows and self.window_count >= max_windows:
                    break

                if audio_cursor + hop_samples <= total_samples:
                    next_chunk = audio_data[audio_cursor : audio_cursor + hop_samples]
                    for s in next_chunk:
                        self.buffer.append(float(s))
                    audio_cursor += hop_samples
                else:
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
        """Run continuous real-time analysis from the local microphone."""
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

                    if len(self.buffer) >= self.window_samples:
                        elapsed = current_time - last_analysis_time
                        if elapsed >= self.analysis_interval:
                            if self.window_count > 0:
                                self.analysis_intervals.append(elapsed)

                            audio_window = np.array(self.buffer, dtype=np.float32)
                            self.process_window(audio_window)
                            last_analysis_time = time.perf_counter()

                            if max_windows and self.window_count >= max_windows:
                                print(f"Reached maximum window limit: {max_windows}")
                                break

                    time.sleep(0.01)

        except KeyboardInterrupt:
            print("\nStopping live microphone stream...")
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
    parser.add_argument(
        "--tiered",
        action="store_true",
        help="Enable tiered inference (bypasses heavy W2V2 model on clear bona fide audio).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        pipeline = LiveRiskPipeline(
            vad_threshold_db=args.vad_threshold,
            tiered_mode=args.tiered,
        )
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
