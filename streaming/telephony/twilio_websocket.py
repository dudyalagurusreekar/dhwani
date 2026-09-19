"""
Twilio Media Stream WebSocket Handler for Dhwani / EchoShield AI
Processes real-time inbound/outbound telephony streams, resamples audio to 16 kHz,
evaluates VAD and multi-model voice cloning detection, applies non-destructive
prevention policies, and broadcasts telemetry to the frontend dashboard.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect

from streaming.telephony.audio_decoder import TelephonyAudioDecoder
from streaming.telephony.call_session import CallSession
from streaming.vad_gate import VADGate
from backend.services.detector import detect_voice
from backend.services.risk_engine import assess_risk
from backend.websocket.dashboard import broadcast_event

logger = logging.getLogger("dhwani.telephony")

# Registry of active live telephone calls
ACTIVE_TELEPHONY_SESSIONS: Dict[str, CallSession] = {}


async def handle_twilio_media_stream(websocket: WebSocket):
    """
    WebSocket consumer endpoint for Twilio Media Streams (G.711 u-law @ 8 kHz).
    """
    await websocket.accept()
    logger.info("Twilio media stream connection accepted.")

    decoder = TelephonyAudioDecoder(target_sample_rate=16000, source_sample_rate=8000)
    vad_gate = VADGate(energy_threshold_db=-38.0, speech_ratio_threshold=0.25)

    current_session: Optional[CallSession] = None
    stream_sid: Optional[str] = None

    try:
        while True:
            message_text = await websocket.receive_text()
            data = json.loads(message_text)
            event_type = data.get("event")

            if event_type == "connected":
                protocol = data.get("protocol", "Call")
                version = data.get("version", "1.0.0")
                logger.info(f"Twilio handshake verified. Protocol: {protocol} v{version}")

            elif event_type == "start":
                start_info = data.get("start", {})
                stream_sid = start_info.get("streamSid")
                call_sid = start_info.get("callSid", f"call_{int(datetime.now(timezone.utc).timestamp())}")
                custom_params = start_info.get("customParameters", {})

                caller = custom_params.get("from", custom_params.get("From", "INBOUND_CALLER"))
                callee = custom_params.get("to", custom_params.get("To", "DHWANI_GATEWAY"))

                current_session = CallSession(
                    call_sid=call_sid,
                    stream_sid=stream_sid,
                    from_number=caller,
                    to_number=callee,
                )
                ACTIVE_TELEPHONY_SESSIONS[stream_sid] = current_session

                logger.info(
                    f"Telephony Call Started: CallSID={call_sid}, StreamSID={stream_sid}, "
                    f"Caller={current_session.from_number_masked}"
                )

                # Broadcast call start event to frontend dashboard
                await broadcast_event("call_started", current_session.to_dict())

            elif event_type == "media":
                if not current_session:
                    continue

                media_info = data.get("media", {})
                payload_b64 = media_info.get("payload", "")
                if not payload_b64:
                    continue

                f32_16k, _ = decoder.process_twilio_media_chunk(payload_b64)
                windows = current_session.append_audio(f32_16k)

                for window in windows:
                    # Step 1: VAD Pre-Filter
                    is_speech, speech_ratio, energy_db = vad_gate.process_window(window)

                    if not is_speech:
                        # Non-speech window: bypass deep models, spend 0 GPU cycles
                        vad_payload = {
                            "call_sid": current_session.call_sid,
                            "stream_sid": current_session.stream_sid,
                            "window": current_session.windows_processed + 1,
                            "speech": False,
                            "speech_ratio": round(speech_ratio, 2),
                            "energy_db": round(energy_db, 1),
                            "risk_level": "NO_SPEECH",
                        }
                        await broadcast_event("vad_update", vad_payload)
                        continue

                    # Step 2: Multi-Model Detection (AASIST, AASIST-L, Acoustic, W2V2-AASIST)
                    detector_results = detect_voice(window)

                    # Step 3: Risk Evaluation, Adaptive Fusion & Inter-Model Consensus
                    risk_assessment = assess_risk(detector_results, session_id=current_session.call_sid)

                    # Step 4: Policy Enforcement
                    current_session.update_risk_telemetry(
                        risk_score=risk_assessment["risk_score"],
                        risk_level=risk_assessment["risk_level"],
                        consensus=risk_assessment.get("consensus_level", "NONE"),
                        attribution=risk_assessment.get("attack_vector", "UNKNOWN"),
                        reasons=risk_assessment.get("reasons", []),
                        countermeasure=risk_assessment.get("policy_action"),
                        detectors=detector_results,
                    )

                    # Broadcast real-time telemetry to frontend dashboard
                    telemetry_payload = {
                        "call_sid": current_session.call_sid,
                        "stream_sid": current_session.stream_sid,
                        "window": current_session.windows_processed,
                        "caller": current_session.from_number_masked,
                        "duration_sec": round(current_session.total_samples_received / 16000.0, 1),
                        "speech": True,
                        "speech_ratio": round(speech_ratio, 2),
                        "energy_db": round(energy_db, 1),
                        "risk_score": risk_assessment["risk_score"],
                        "risk_level": risk_assessment["risk_level"],
                        "consensus": risk_assessment.get("consensus_level", "NONE"),
                        "consensus_explanation": risk_assessment.get("consensus_explanation", ""),
                        "attribution": risk_assessment.get("attack_vector", "UNKNOWN"),
                        "policy_action": risk_assessment.get("policy_action"),
                        "policy_severity": risk_assessment.get("policy_severity"),
                        "policy_reason": risk_assessment.get("policy_reason"),
                        "reasons": risk_assessment.get("reasons", []),
                        "detectors": detector_results,
                    }
                    await broadcast_event("risk_update", telemetry_payload)

            elif event_type == "stop":
                logger.info(f"Twilio call stop received for StreamSID: {stream_sid}")
                if current_session:
                    current_session.status = "COMPLETED"
                    await broadcast_event("call_ended", current_session.to_dict())
                break

    except WebSocketDisconnect:
        logger.info(f"Twilio WebSocket disconnected for StreamSID: {stream_sid}")
        if current_session:
            current_session.status = "DISCONNECTED"
            await broadcast_event("call_ended", current_session.to_dict())
    except Exception as e:
        logger.error(f"Error handling Twilio media stream: {e}", exc_info=True)
    finally:
        if stream_sid and stream_sid in ACTIVE_TELEPHONY_SESSIONS:
            del ACTIVE_TELEPHONY_SESSIONS[stream_sid]
