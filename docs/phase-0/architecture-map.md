# Dhwani Phase 0: System Architecture Map
**Project:** Dhwani (ध्वनि) / EchoShield AI  
**Target Branch:** `master`  
**Reference Commit:** `a45e40aa6fec462cc770325b41802f8629e4b1f7`  

---

## 1. End-to-End System Architecture

```mermaid
graph TD
    subgraph INGESTION["1. Ingestion Sources"]
        MIC["Microphone Audio Source<br/>(ai/common/media_sources.py)"]
        FILE["File Upload (.wav, .mp3, .flac)<br/>(backend/routes/media_analysis.py)"]
        YT["YouTube Video URL<br/>(ai/common/media_sources.py)"]
        TWILIO["Twilio Inbound Voice Call<br/>(backend/routes/twilio_routes.py)"]
    end

    subgraph PREPROCESS["2. Decoding & Acoustic Preprocessing"]
        DEC["G.711 u-law / FFmpeg Decoder<br/>(streaming/telephony/audio_decoder.py)"]
        RESAMP["16 kHz Mono Resampler<br/>(librosa / soundfile)"]
        VAD["Energy VAD Gate<br/>(streaming/vad_gate.py)"]
        QUAL["Audio Quality Analyzer<br/>(ai/acoustic/audio_quality.py)"]
    end

    subgraph DETECTION["3. Multi-Model Detection Ensemble"]
        ACOUSTIC["Acoustic Detector (Handcrafted CPU)<br/>(ai/acoustic/acoustic_detector.py)"]
        W2V2["W2V2-AASIST (Self-Supervised Wav2Vec2)<br/>(ai/ssl_detector/w2v2_aasist_adapter.py)"]
        AASIST["AASIST (SincNet + Temporal GAT)<br/>(ai/aasist/aasist_adapter.py)"]
        AASISTL["AASIST-L (Lightweight GAT)<br/>(ai/aasist/aasist_l_adapter.py)"]
        SPK["ECAPA-TDNN Speaker Consistency<br/>(ai/speaker/speaker_consistency.py)"]
    end

    subgraph FUSION["4. Risk Fusion & Policy Evaluation"]
        ADAPT["Adaptive Reliability Fusion<br/>(risk_engine/adaptive_fusion.py)"]
        CONSENSUS["Model Agreement & Consensus<br/>(risk_engine/model_agreement.py)"]
        ATTRIB["Attack Attribution (TTS / VC / Replay)<br/>(ai/common/attack_attribution.py)"]
        POLICY["Active Call Interceptor & Mitigation<br/>(ai/prevention/call_interceptor.py)"]
    end

    subgraph SECURITY["5. Security & Provenance Ledger"]
        SANDBOX["Ephemeral Audio Buffer (Zero-Retention)<br/>(security/privacy.py)"]
        HASHER["SHA-256 AudioHasher & Provenance Token<br/>(security/hasher.py)"]
        CHAIN1["Global AuditHashChain (In-Memory)<br/>(security/pipeline.py)"]
        CHAIN2["Incidents AuditHashChain (data/audit_ledger.jsonl)<br/>(backend/routes/incidents.py)"]
    end

    subgraph OUTPUT["6. Telemetry & Alert Outlets"]
        DASH["Next.js Cyber Dashboard<br/>(ws://localhost:8000/ws/dashboard)"]
        NOTIF["Notification Service (SMS/WhatsApp/Email)<br/>(backend/notifications/service.py)"]
        INC_API["Incidents REST API<br/>(GET /api/incidents)"]
    end

    %% Ingestion to Preprocessing
    FILE --> RESAMP
    YT --> RESAMP
    MIC --> RESAMP
    TWILIO --> DEC --> RESAMP
    RESAMP --> SANDBOX
    SANDBOX --> HASHER
    SANDBOX --> VAD
    VAD -- "Speech Detected" --> QUAL
    VAD -- "Silence/Noise" --> DASH

    %% Detection Layer
    QUAL --> ACOUSTIC
    QUAL -.->|Blocked: Missing ONNX| W2V2
    QUAL -.->|Blocked: Missing ONNX| AASIST
    QUAL -.->|Blocked: Missing ONNX| AASISTL
    QUAL -.->|Blocked: Missing ONNX| SPK

    %% Fusion
    ACOUSTIC --> ADAPT
    W2V2 -.-> ADAPT
    AASIST -.-> ADAPT
    AASISTL -.-> ADAPT
    SPK -.-> ADAPT
    ADAPT --> CONSENSUS --> ATTRIB --> POLICY

    %% Security Ledger
    POLICY --> CHAIN1
    POLICY -.->|Architectural Disconnect| CHAIN2
    CHAIN2 --> INC_API

    %% Telemetry & Alerting
    POLICY --> DASH
    POLICY -.->|Disconnected: Not Invoked| NOTIF

    classDef operational fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef blocked fill:#7f1d1d,stroke:#ef4444,stroke-width:2px,color:#fff;
    classDef disconnected fill:#78350f,stroke:#f59e0b,stroke-width:2px,color:#fff;

    class ACOUSTIC,QUAL,VAD,SANDBOX,HASHER,DEC,RESAMP,FILE operational;
    class W2V2,AASIST,AASISTL,SPK blocked;
    class CHAIN1,CHAIN2,NOTIF disconnected;
```

---

## 2. Request Flow Deep Dives

### Flow 1: File Audio Analysis (`POST /api/analyze/upload`)
- **Source Route:** `backend/routes/media_analysis.py` (`analyze_uploaded_file`)
- **Pipeline Class:** `ai/common/common_pipeline.py` (`UnifiedMediaPipeline`)

```mermaid
sequenceDiagram
    autonumber
    actor Client as User / Dashboard
    participant API as FastAPI (/api/analyze/upload)
    participant Pipe as UnifiedMediaPipeline
    participant VAD as Energy VAD Gate
    participant Det as DetectorService
    participant Risk as Risk Engine
    participant WS as WebSocket Broadcaster

    Client->>API: POST /api/analyze/upload (file, multipart/form-data)
    API->>API: Save to ephemeral temp file (Path: tempfile/dhwani_uploads)
    API->>WS: broadcast_event("analysis_started")
    API->>Pipe: analyze_source(FileAudioSource)
    Pipe->>Pipe: Load, resample to 16 kHz mono [-1.0, 1.0]
    Pipe->>Pipe: Compute evidence SHA-256 hash
    Pipe->>VAD: Sliced rolling 64600-sample windows (1s hop)
    alt Window is Voiced Speech
        VAD-->>Pipe: speech_detected = True
        Pipe->>Det: detect_voice_sync(window)
        Note over Det: Tries W2V2, AASIST, AASIST-L, Acoustic, ECAPA.<br/>4 models fail to load; runs Acoustic only.
        Det-->>Pipe: raw_scores, quality diagnostics
        Pipe->>Risk: assess_risk(detector_results, quality)
        Risk-->>Pipe: risk_score, attribution, consensus, policy_action
    else Window is Silence / Noise
        VAD-->>Pipe: speech_detected = False (Skip deep models)
    end
    API->>WS: broadcast_event("analysis_completed", result)
    API->>API: Unlink temporary file (unless DHWANI_RETAIN_AUDIO=true)
    API-->>Client: 200 OK (JSON Canonical AnalysisResult)
```

---

### Flow 2: Live Telephony Streaming (`POST /twilio/voice` & `WSS /twilio/media`)
- **Inbound Webhook:** `backend/routes/twilio_routes.py` (`twilio_inbound_voice_webhook`)
- **WebSocket Consumer:** `streaming/telephony/twilio_websocket.py` (`handle_twilio_media_stream`)
- **Session Manager:** `streaming/telephony/call_session.py` (`CallSession`)

```mermaid
sequenceDiagram
    autonumber
    actor Twilio as Twilio Programmable Voice
    participant Webhook as /twilio/voice
    participant WS as /twilio/media (WebSocket)
    participant Decoder as TelephonyAudioDecoder
    participant Session as CallSession
    participant VAD as VADGate
    participant Det as DetectorService
    participant DashWS as /ws/dashboard

    Twilio->>Webhook: POST /twilio/voice (CallSid, From, To)
    Note over Webhook: No Twilio signature verification performed!
    Webhook-->>Twilio: 200 OK (TwiML XML with <Connect><Stream url="/twilio/media">)
    Twilio->>WS: WebSocket Connect (G.711 u-law 8 kHz stream)
    WS->>WS: event: "connected" (Handshake logged)
    WS->>WS: event: "start" (CallSession initialized, phone masked)
    WS->>DashWS: broadcast_event("call_started")
    loop Every 20ms Audio Chunk
        Twilio->>WS: event: "media" (base64 payload)
        WS->>Decoder: process_twilio_media_chunk(base64)
        Decoder-->>WS: float32 @ 16 kHz
        WS->>Session: append_audio(chunk)
        alt 64600-sample window ready
            Session-->>WS: window
            WS->>VAD: process_window(window)
            alt Speech Detected
                WS->>Det: await detect_voice(window)
                Det-->>WS: detector_results (Acoustic fallback)
                WS->>Session: update_risk_telemetry(risk_score, policy_action)
                WS->>DashWS: broadcast_event("risk_update", telemetry_payload)
            else Silence
                WS->>DashWS: broadcast_event("vad_update", no_speech)
            end
        end
    end
    Twilio->>WS: event: "stop"
    WS->>DashWS: broadcast_event("call_ended")
```

---

## 3. Critical Architectural Disconnects & Fractures

### 3.1 Dual Disconnected Audit Hash Chains
The repository maintains two completely disjoint cryptographic hash chain instances:

1. **Global Provenance Chain:**  
   - Declared in: `security/middleware.py` (`_GLOBAL_PIPELINE`)
   - Queried by: `backend/routes/audit.py` (`/api/audit/verify`, `/trail`, `/latest`, `/certificate`)
   - Written by: `backend/routes/analyze.py`
   - Persistence: **In-Memory only** by default (`persistence_file=None`). All entries disappear on restart.

2. **Incidents Ledger Chain:**  
   - Declared in: `backend/routes/incidents.py` (`audit_chain = AuditHashChain(persistence_file="data/audit_ledger.jsonl")`)
   - Queried by: `backend/routes/incidents.py` (`/api/incidents`, `/api/incidents/verify/chain`)
   - Persistence: Persisted to `data/audit_ledger.jsonl`.
   - In-Memory Incident Store: `INCIDENT_RECORDS: Dict = {}` is **not restored** from `data/audit_ledger.jsonl` upon server restart.

**Consequence:** An event recorded via `/api/analyze` is never visible in `/api/incidents`, and an incident verified via `/api/incidents/verification` does not update the audit certificate in `/api/audit/certificate`.

---

### 3.2 Unconnected Notification Service
- **Implementation:** `backend/notifications/service.py` provides `NotificationService` supporting Twilio SMS, WhatsApp, Email (SMTP), and Console alerts with cooldown deduplication.
- **Reality:** Grep analysis reveals that `dispatch_security_alert` is **only called inside `tests/test_notifications.py`**.
- Neither `backend/routes/analyze.py`, `backend/routes/media_analysis.py`, `backend/routes/incidents.py`, nor `streaming/telephony/twilio_websocket.py` ever instantiates or calls `NotificationService` when a critical deepfake or high-risk session is detected.

---

### 3.3 Module Import Rebinder Bug in System Telemetry
- **File:** `backend/routes/system.py`
- Line 12 imports detectors statically at load time:
  ```python
  from backend.services.detector import _AASIST_MODEL, _AASIST_L_MODEL, _ACOUSTIC_MODEL, _W2V2_MODEL, _SPEAKER_ENGINE
  ```
- Because these variables are `None` when `system.py` is first imported, Python binds local references to `None`.
- When `_init_detectors()` executes later, it rebinds the global variables in `detector.py`, but `system.py`'s local bindings remain `None`.
- **Result:** `GET /api/system/status` always returns `"active_models": []`, even when the Acoustic Detector is loaded and operational.

---

### 3.4 Shared Mutable State in Singleton Detectors
- `ai/speaker/speaker_consistency.py` maintains `self.anchor_embedding` and `self.recent_embeddings` on the `SpeakerConsistencyEngine` instance.
- `backend/services/detector.py` instantiates `_SPEAKER_ENGINE` as a module-level global singleton.
- **Consequence:** In a multi-user or multi-call environment, incoming audio from User B will compare against the enrolled vocal anchor of User A, corrupting speaker consistency evaluation across sessions.
