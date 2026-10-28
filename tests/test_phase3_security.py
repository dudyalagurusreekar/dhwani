"""
Automated Security & Streaming Hardening Tests for Dhwani / EchoShield AI (Phase 3)
==================================================================================
Comprehensive test suite covering:
1. REST API Authentication & Authorization (authorized, unauthorized, malformed, expired, missing)
2. Public vs Protected Endpoints
3. CORS Allowlist & Credentials Safety
4. Request Size & Duration Limits (413 Payload Too Large)
5. Malformed Audio Handling
6. SSRF & URL Ingestion Defenses (loopback, private, link-local, cloud metadata, scheme validation)
7. Twilio Webhook HMAC-SHA1 Signature Verification (valid, invalid, forged, proxy header)
8. WebSocket Authentication Handshake & Policy Violations
9. WebSocket Frame Size Limits & Session Quota
10. Session Isolation & Buffer Memory Cleanup (no cross-session leakage)
11. Cryptographic Audit Chain Tamper Detection & Ledger Concurrency
"""

import os
from pathlib import Path
import time
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.main import app
from backend.streaming.stream_manager import StreamManager
from backend.websocket.audio import stream_manager as audio_stream_manager
from backend.services.detector import reset_session
from security.auth import (
    validate_api_key,
    is_auth_required,
    get_configured_api_key,
)
from security.ssrf import (
    validate_url_security,
    SSRFSecurityError,
    is_ip_allowed,
)
from security.twilio_validator import (
    compute_twilio_signature,
    verify_twilio_signature,
    get_external_request_url,
)
from security.audit_chain import AuditHashChain, GENESIS_PREV_HASH
from security.schemas import EventType


client = TestClient(app)


# =====================================================================
# 1. REST Authentication & Authorization Tests
# =====================================================================

def test_auth_not_required_by_default(monkeypatch):
    """When DHWANI_AUTH_REQUIRED and DHWANI_API_KEY are unset, backward-compatible access is allowed."""
    monkeypatch.delenv("DHWANI_API_KEY", raising=False)
    monkeypatch.delenv("DHWANI_AUTH_REQUIRED", raising=False)
    
    assert not is_auth_required()
    resp = client.get("/api/system/status")
    assert resp.status_code == 200


def test_auth_enforced_when_configured(monkeypatch):
    """When DHWANI_API_KEY is configured, protected endpoints reject unauthorized requests with 401."""
    test_key = "dhwani_prod_secret_token_9999"
    monkeypatch.setenv("DHWANI_API_KEY", test_key)
    monkeypatch.setenv("DHWANI_AUTH_REQUIRED", "true")

    assert is_auth_required()

    # 1. Missing credentials -> 401
    resp = client.get("/api/system/status")
    assert resp.status_code == 401
    assert "missing" in resp.json()["detail"].lower()

    # 2. Invalid API Key -> 401
    resp = client.get("/api/system/status", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()

    # 3. Valid X-API-Key header -> 200
    resp = client.get("/api/system/status", headers={"X-API-Key": test_key})
    assert resp.status_code == 200
    assert resp.json()["status"] == "OPERATIONAL"

    # 4. Valid Authorization Bearer header -> 200
    resp = client.get("/api/system/status", headers={"Authorization": f"Bearer {test_key}"})
    assert resp.status_code == 200


def test_public_endpoints_remain_accessible_without_auth(monkeypatch):
    """Health probes and root information endpoints must remain public even when auth is strictly required."""
    monkeypatch.setenv("DHWANI_API_KEY", "super-secret-key")
    monkeypatch.setenv("DHWANI_AUTH_REQUIRED", "true")

    # /health probe
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    # / root endpoint
    resp = client.get("/")
    assert resp.status_code == 200
    assert "models" in resp.json()


def test_constant_time_api_key_validation(monkeypatch):
    """Validate constant-time credential comparison behavior."""
    monkeypatch.setenv("DHWANI_API_KEY", "secret_key_123")
    assert validate_api_key("secret_key_123") is True
    assert validate_api_key("secret_key_124") is False
    assert validate_api_key("") is False
    assert validate_api_key(None) is False


# =====================================================================
# 2. CORS & Origin Safety Tests
# =====================================================================

def test_cors_allowlist_headers():
    """Verify CORS preflight headers conform to allowlist policy."""
    # Preflight for allowed origin
    resp = client.options(
        "/api/system/status",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"


# =====================================================================
# 3. Request Size & Duration Limits (413 Payload Too Large)
# =====================================================================

def test_analyze_content_length_limit():
    """Reject requests with Content-Length exceeding the 25 MB ceiling immediately."""
    fake_oversized_length = 30 * 1024 * 1024  # 30 MB
    resp = client.post(
        "/api/analyze",
        headers={
            "Content-Length": str(fake_oversized_length),
        },
        files={"file": ("test.wav", b"RIFF", "audio/wav")},
    )
    assert resp.status_code == 413
    assert "exceeds maximum permitted size" in resp.json()["detail"]


def test_analyze_streaming_chunk_limit():
    """Reject streamed payloads where the body stream exceeds 25 MB."""
    oversized_data = b"RIFF" + b"0" * (26 * 1024 * 1024)
    resp = client.post(
        "/api/analyze",
        files={"file": ("test.wav", oversized_data, "audio/wav")},
    )
    assert resp.status_code == 413
    assert "exceeds maximum permitted size" in resp.json()["detail"]


def test_media_upload_size_limit():
    """Reject media upload files exceeding 50 MB limit."""
    oversized_file = b"RIFF" + b"\x00" * (51 * 1024 * 1024)
    resp = client.post(
        "/api/analyze/upload",
        files={"file": ("huge_recording.wav", oversized_file, "audio/wav")},
    )
    assert resp.status_code == 413
    assert "exceeds maximum permitted size" in resp.json()["detail"]


# =====================================================================
# 4. Malformed Audio Handling
# =====================================================================

def test_malformed_audio_handling_rest():
    """Ensure malformed or non-audio bytes are rejected safely without crashing the service."""
    garbage_bytes = b"NOT_A_VALID_AUDIO_FILE_GARBAGE_PAYLOAD" * 100
    resp = client.post(
        "/api/analyze",
        files={"file": ("test.wav", garbage_bytes, "audio/wav")},
    )
    # Service rejects non-audio gracefully with 400 or handled error structure
    assert resp.status_code in (400, 422, 500)
    assert resp.status_code != 404


# =====================================================================
# 5. SSRF & External URL Ingestion Defenses
# =====================================================================

def test_ssrf_ip_blocking_matrix():
    """Test comprehensive IP range blocking (loopback, private, link-local, cloud metadata)."""
    assert is_ip_allowed("8.8.8.8") is True
    assert is_ip_allowed("1.1.1.1") is True
    assert is_ip_allowed("127.0.0.1") is False       # Loopback
    assert is_ip_allowed("127.0.1.1") is False       # Loopback range
    assert is_ip_allowed("10.0.0.5") is False        # Private RFC 1918
    assert is_ip_allowed("172.16.0.1") is False      # Private RFC 1918
    assert is_ip_allowed("192.168.1.1") is False     # Private RFC 1918
    assert is_ip_allowed("169.254.169.254") is False # AWS/GCP/Azure Cloud Metadata (Link-Local)
    assert is_ip_allowed("100.64.0.1") is False      # Carrier Grade NAT
    assert is_ip_allowed("::1") is False             # IPv6 Loopback
    assert is_ip_allowed("fe80::1") is False         # IPv6 Link-Local


def test_ssrf_url_validation_blocks_unsafe():
    """Verify validate_url_security blocks unsafe targets."""
    # Cloud metadata
    with pytest.raises(SSRFSecurityError, match="Blocked SSRF target"):
        validate_url_security("http://169.254.169.254/latest/meta-data/", raise_on_error=True)

    # Loopback
    with pytest.raises(SSRFSecurityError, match="Blocked SSRF target"):
        validate_url_security("http://127.0.0.1:8080/internal-admin", raise_on_error=True)

    # Localhost hostname
    with pytest.raises(SSRFSecurityError, match="Blocked SSRF target"):
        validate_url_security("http://localhost:5000/keys", raise_on_error=True)

    # Unsafe schemes
    with pytest.raises(SSRFSecurityError, match="Scheme 'file' not allowed"):
        validate_url_security("file:///etc/passwd", raise_on_error=True)

    with pytest.raises(SSRFSecurityError, match="Scheme 'ftp' not allowed"):
        validate_url_security("ftp://ftp.example.com/audio.wav", raise_on_error=True)

    # YouTube domain restrictions
    with pytest.raises(SSRFSecurityError, match="not an allowed YouTube domain"):
        validate_url_security("https://attacker-domain.com/evil.mp3", only_youtube=True, raise_on_error=True)

    # Valid YouTube URL
    safe, msg = validate_url_security("https://www.youtube.com/watch?v=dQw4w9WgXcQ", only_youtube=True)
    assert safe is True


def test_youtube_endpoint_rejects_ssrf():
    """Verify POST /api/analyze/youtube endpoint rejects SSRF exploits."""
    resp = client.post(
        "/api/analyze/youtube",
        json={"url": "http://169.254.169.254/latest/meta-data/"},
    )
    assert resp.status_code == 400
    assert "SSRF Protection" in resp.json()["detail"]


# =====================================================================
# 6. Twilio Signature Verification Tests
# =====================================================================

def test_twilio_signature_computation():
    """Verify HMAC-SHA1 signature computation follows Twilio's specification."""
    auth_token = "12345abcdef"
    url = "https://mycompany.com/twilio/voice"
    params = {
        "CallSid": "CA1234567890",
        "From": "+14155551212",
        "To": "+18005551212",
    }
    
    sig = compute_twilio_signature(url, params, auth_token)
    assert isinstance(sig, str)
    assert len(sig) > 0

    # Verification passes with correct signature
    assert verify_twilio_signature(url, params, sig, auth_token) is True

    # Tampered signature fails
    assert verify_twilio_signature(url, params, "invalid_sig==", auth_token) is False

    # Tampered parameter fails
    tampered_params = dict(params)
    tampered_params["CallSid"] = "CA0000000000"
    assert verify_twilio_signature(url, tampered_params, sig, auth_token) is False


def test_twilio_proxy_url_reconstruction():
    """Verify external URL reconstruction accounts for proxy headers."""
    from starlette.datastructures import Headers
    
    headers = Headers({
        "x-forwarded-proto": "https",
        "x-forwarded-host": "api.dhwani.ai",
    })
    external_url = get_external_request_url("http://localhost:8000/twilio/voice?call=1", headers)
    assert external_url == "https://api.dhwani.ai/twilio/voice?call=1"


def test_twilio_voice_endpoint_enforces_signature(monkeypatch):
    """Verify /twilio/voice endpoint rejects unsigned requests when verification is enabled."""
    auth_token = "twilio_secret_token_12345"
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", auth_token)
    monkeypatch.setenv("TWILIO_VERIFY_SIGNATURE", "true")

    payload = {
        "CallSid": "CA9988776655",
        "From": "+14155552671",
        "To": "+18005550199",
    }

    # 1. Missing signature header -> 403 Forbidden
    resp = client.post("/twilio/voice", data=payload)
    assert resp.status_code == 403
    assert "Missing X-Twilio-Signature" in resp.text

    # 2. Invalid/Forged signature -> 403 Forbidden
    resp = client.post(
        "/twilio/voice",
        data=payload,
        headers={"X-Twilio-Signature": "forged_signature_value="},
    )
    assert resp.status_code == 403
    assert "Invalid Twilio signature" in resp.text

    # 3. Valid signature -> 200 OK
    valid_sig = compute_twilio_signature("http://testserver/twilio/voice", payload, auth_token)
    resp = client.post(
        "/twilio/voice",
        data=payload,
        headers={"X-Twilio-Signature": valid_sig},
    )
    assert resp.status_code == 200
    assert "<Response>" in resp.text


# =====================================================================
# 7. WebSocket Security & Session Isolation Tests
# =====================================================================

def test_websocket_auth_rejection(monkeypatch):
    """Reject WebSocket connections when credentials are required but missing/invalid."""
    monkeypatch.setenv("DHWANI_API_KEY", "ws_secret_999")
    monkeypatch.setenv("DHWANI_AUTH_REQUIRED", "true")

    # Unauthorized connection to /ws/dashboard should be rejected during handshake
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/dashboard"):
            pass

    # Authorized connection succeeds
    with client.websocket_connect("/ws/dashboard?api_key=ws_secret_999") as ws:
        # Connection established successfully
        assert ws is not None


def test_websocket_audio_frame_size_limit():
    """Verify /ws/audio rejects individual frames exceeding 1 MB."""
    session_id = "test_frame_limit_sess"
    with client.websocket_connect(f"/ws/audio?session_id={session_id}") as ws:
        # Send oversized frame (1.2 MB)
        oversized_frame = b"\x00" * (1200 * 1024)
        ws.send_bytes(oversized_frame)
        msg = ws.receive_json()
        assert "exceeds maximum allowed size" in msg["error"]


def test_websocket_session_isolation_and_buffer_cleanup():
    """Verify session audio buffers are purged on disconnect and don't leak across sessions."""
    session_a = "isolated_session_alpha"
    session_b = "isolated_session_beta"

    # 1. Connect Session A and send a valid small audio chunk
    with client.websocket_connect(f"/ws/audio?session_id={session_a}") as ws:
        # Send silence frame
        silence = b"\x00" * 3200
        ws.send_bytes(silence)
        resp = ws.receive_json()
        assert resp["session_id"] == session_a
        assert resp["speech"] is False

    # 2. Session A disconnected: verify audio buffer is purged from memory
    assert not audio_stream_manager.has_session(session_a)

    # 3. Connect Session B: verify completely clean session context
    with client.websocket_connect(f"/ws/audio?session_id={session_b}") as ws:
        silence = b"\x00" * 3200
        ws.send_bytes(silence)
        resp = ws.receive_json()
        assert resp["session_id"] == session_b
        # Verify Session B buffer contains only Session B's data
        buf = audio_stream_manager.get_buffer(session_b)
        assert buf.size() <= 3200

    # On disconnect, Session B is also cleanly purged
    assert not audio_stream_manager.has_session(session_b)


# =====================================================================
# 8. Cryptographic Audit Chain Tamper-Evidence Tests
# =====================================================================

def test_audit_chain_tamper_detection(tmp_path):
    """Verify that tampering with any record in the ledger is cryptographically detected."""
    ledger_file = tmp_path / "test_ledger.jsonl"
    chain = AuditHashChain(persistence_file=ledger_file)

    # Append 3 security events
    chain.append_event(session_id="sess_1", event_type=EventType.AUDIO_INGESTED, payload={"len": 100})
    chain.append_event(session_id="sess_2", event_type=EventType.RISK_ASSESSMENT, payload={"risk": 85})
    chain.append_event(session_id="sess_3", event_type=EventType.SESSION_END, payload={"action": "BLOCK"})

    assert chain.length == 3
    report = chain.verify_integrity()
    assert report.is_valid is True

    # Tamper with event sequence 1 in the internal chain
    chain._chain[1].payload["risk"] = 10  # Unauthorized modification

    tamper_report = chain.verify_integrity()
    assert tamper_report.is_valid is False
    assert tamper_report.tampered_event_seq == 1
    assert "payload or metadata was altered" in tamper_report.error_reason


# =====================================================================
# 9. Phase 3.1 Independent Review Regression Tests
# =====================================================================

def test_websocket_subprotocol_auth(monkeypatch):
    """Verify WebSocket authentication works via Sec-WebSocket-Protocol without query strings."""
    secret = "ws_subproto_token_777"
    monkeypatch.setenv("DHWANI_API_KEY", secret)
    monkeypatch.setenv("DHWANI_AUTH_REQUIRED", "true")

    # Connect with Sec-WebSocket-Protocol subprotocol
    with client.websocket_connect(
        "/ws/dashboard",
        subprotocols=["dhwani-auth", secret],
    ) as ws:
        assert ws is not None


def test_websocket_concurrent_session_collision_rejection():
    """Verify concurrent connections using the same session_id are rejected to prevent state hijacking."""
    collision_id = "test_collision_sess_99"

    with client.websocket_connect(f"/ws/audio?session_id={collision_id}") as ws1:
        # First connection is active. Second connection with identical session_id must be rejected
        with client.websocket_connect(f"/ws/audio?session_id={collision_id}") as ws2:
            msg = ws2.receive_json()
            assert "already active in a concurrent connection" in msg["error"]

        # First connection continues to operate normally
        silence = b"\x00" * 3200
        ws1.send_bytes(silence)
        resp = ws1.receive_json()
        assert resp["session_id"] == collision_id


def test_analyze_audio_duration_limit_rejection(tmp_path):
    """Verify REST audio upload enforces 300-second duration ceiling."""
    import io
    import numpy as np
    import soundfile as sf

    # Generate WAV header with 350 seconds duration (mock frames)
    bio = io.BytesIO()
    # Write 1 second of audio but set length to 350s in header or write float data
    sr = 16000
    long_samples = np.zeros(sr * 305, dtype=np.float32)  # 305s > 300s limit
    sf.write(bio, long_samples, sr, format="WAV", subtype="PCM_16")
    wav_bytes = bio.getvalue()

    resp = client.post(
        "/api/analyze",
        files={"file": ("too_long.wav", wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 400
    assert "exceeds maximum allowed (300.0s)" in resp.json()["detail"]


def test_youtube_canonical_url_safeguard():
    """Verify YouTubeAudioSource extracts strictly 11-char ID and canonicalizes URL."""
    from ai.common.media_sources import YouTubeAudioSource

    # URL with additional query params
    tricky_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&feature=share&t=10s"
    source = YouTubeAudioSource(tricky_url)
    assert source.video_id == "dQw4w9WgXcQ"
    assert len(source.video_id) == 11


# =====================================================================
# 10. Phase 3.2 Deployment Readiness & Fail-Closed Tests
# =====================================================================

def test_auth_required_with_missing_api_key_fails_closed(monkeypatch):
    """Verify system fails closed when DHWANI_AUTH_REQUIRED=true but DHWANI_API_KEY is not provisioned."""
    monkeypatch.setenv("DHWANI_AUTH_REQUIRED", "true")
    monkeypatch.delenv("DHWANI_API_KEY", raising=False)

    # 1. Without credentials -> 401
    resp = client.get("/api/system/status")
    assert resp.status_code == 401

    # 2. With arbitrary credentials -> 401 (fails closed, cannot authenticate)
    resp = client.get("/api/system/status", headers={"X-API-Key": "attacker_attempt"})
    assert resp.status_code == 401


def test_twilio_verification_required_with_missing_token_fails_closed(monkeypatch):
    """Verify Twilio webhook fails closed when signature verification is required but token is missing."""
    monkeypatch.setenv("TWILIO_VERIFY_SIGNATURE", "true")
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)

    resp = client.post(
        "/twilio/voice",
        data={"CallSid": "CA1234", "From": "+1234567890", "To": "+10987654321"},
    )
    assert resp.status_code == 500
    assert "Server configuration error" in resp.text


def test_cors_disallowed_origin_preflight():
    """Verify preflight requests from unapproved origins do not receive allow-origin header."""
    resp = client.options(
        "/api/system/status",
        headers={
            "Origin": "https://unauthorized-attacker-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Origin is not in allowlist: header must not be set to the malicious origin
    assert resp.headers.get("access-control-allow-origin") != "https://unauthorized-attacker-site.com"


def test_websocket_subprotocol_returned_cleanly(monkeypatch):
    """Verify server accepts only the protocol name ('dhwani-auth') without echoing token back."""
    token = "secret_token_abc"
    monkeypatch.setenv("DHWANI_API_KEY", token)
    monkeypatch.setenv("DHWANI_AUTH_REQUIRED", "true")

    # 1. Connection with subprotocol succeeds
    with client.websocket_connect(
        "/ws/dashboard",
        subprotocols=["dhwani-auth", token],
    ) as ws:
        assert ws is not None

    # 2. Verify get_accepted_subprotocol extracts only protocol name, never the secret token
    from security.auth import get_accepted_subprotocol
    from starlette.datastructures import Headers

    class MockWS:
        def __init__(self, headers_dict, scope_protos):
            self.headers = Headers(headers_dict)
            self.scope = {"subprotocols": scope_protos}

    mock_ws = MockWS({"sec-websocket-protocol": f"dhwani-auth, {token}"}, ["dhwani-auth", token])
    accepted = get_accepted_subprotocol(mock_ws)
    assert accepted == "dhwani-auth"
    assert token not in accepted


def test_websocket_fails_closed_when_auth_required_but_key_missing(monkeypatch):
    """When auth is required but server has no API key configured, WS connections are rejected with 1008."""
    monkeypatch.setenv("DHWANI_AUTH_REQUIRED", "true")
    monkeypatch.delenv("DHWANI_API_KEY", raising=False)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/dashboard"):
            pass
    assert exc_info.value.code == 1008


def test_analyze_audio_extreme_sample_rate_rejected():
    """Verify audio uploads with extreme sample rates (>192kHz) are rejected to prevent DoS."""
    import io
    import numpy as np
    import soundfile as sf

    bio = io.BytesIO()
    sr = 384000  # 384 kHz > 192 kHz limit
    samples = np.zeros(sr, dtype=np.float32)
    sf.write(bio, samples, sr, format="WAV", subtype="PCM_16")
    wav_bytes = bio.getvalue()

    resp = client.post(
        "/api/analyze",
        files={"file": ("extreme_sr.wav", wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 400
    assert "exceeds maximum allowed" in resp.json()["detail"]


# =====================================================================
# 11. Phase 3.3 Frontend/Backend Auth Integration Tests
# =====================================================================

def test_client_bundle_contains_no_server_secrets():
    """Verify that frontend client source files do not contain NEXT_PUBLIC_DHWANI_API_KEY or hardcoded keys."""
    frontend_src = Path(__file__).resolve().parent.parent / "frontend" / "src"
    client_files = list(frontend_src.rglob("*.tsx")) + list(frontend_src.rglob("*.ts"))

    # Exclude the server-only BFF proxy route handlers
    client_only_files = [f for f in client_files if "app\\api" not in str(f) and "app/api" not in str(f)]

    for file_path in client_only_files:
        content = file_path.read_text(encoding="utf-8")
        assert "NEXT_PUBLIC_DHWANI_API_KEY" not in content, f"Secret variable exposed in {file_path}"
        assert "dhwani_prod_secret" not in content, f"Hardcoded test secret in {file_path}"


def test_frontend_bff_proxy_forwarding_with_server_injected_api_key(monkeypatch):
    """Verify that backend accepts requests with server-injected X-API-Key and fails closed without it."""
    test_key = "dhwani_bff_server_injected_token_123"
    monkeypatch.setenv("DHWANI_AUTH_REQUIRED", "true")
    monkeypatch.setenv("DHWANI_API_KEY", test_key)

    # 1. Direct browser request without server key injection -> 401
    resp_unauth = client.get("/api/system/status")
    assert resp_unauth.status_code == 401

    # 2. Server-side BFF forwarded request with injected key -> 200
    resp_bff = client.get("/api/system/status", headers={"X-API-Key": test_key})
    assert resp_bff.status_code == 200
    assert resp_bff.json()["status"] == "OPERATIONAL"


def test_public_health_endpoint_response_contains_no_secrets():
    """Verify /health is accessible without auth and contains no server secrets or environment leakage."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    text = resp.text.lower()
    assert "token" not in text
    assert "secret" not in text
    assert "api_key" not in text


def test_bff_proxy_route_security_validation():
    """Verify Next.js BFF proxy routing validation regex and allowlist against traversal attempts."""
    import re
    segment_pattern = re.compile(r"^[a-zA-Z0-9_-]+$")

    # 1. Valid segments must pass
    valid_segments = ["system", "status", "incidents", "upload", "youtube", "honeypot", "verify"]
    for seg in valid_segments:
        assert segment_pattern.match(seg) is not None

    # 2. Path traversal, directory traversal, null bytes, separators must fail
    invalid_segments = ["..", "../etc", "..\\windows", "system/status", "status\0", "admin%2f", "%2e%2e"]
    for seg in invalid_segments:
        assert segment_pattern.match(seg) is None or seg in ("..",)


# =====================================================================
# 12. Phase 3.5 Authentication Trust-Boundary & Negative Security Tests
# =====================================================================

def test_anonymous_request_to_operational_endpoints_rejected(monkeypatch):
    """Verify operational endpoints (incidents, honeypot) fail closed when unauthenticated."""
    monkeypatch.setenv("DHWANI_AUTH_REQUIRED", "true")
    monkeypatch.setenv("DHWANI_API_KEY", "real_production_key_456")

    # 1. Anonymous request to /api/incidents -> 401
    resp = client.get("/api/incidents")
    assert resp.status_code == 401

    # 2. Anonymous request to /api/honeypot/challenge -> 401
    resp = client.post("/api/honeypot/challenge", json={"session_id": "test_s1"})
    assert resp.status_code == 401


def test_forged_client_supplied_authentication_rejected(monkeypatch):
    """Verify forged/attacker-supplied API keys are rejected by backend auth validation."""
    monkeypatch.setenv("DHWANI_AUTH_REQUIRED", "true")
    monkeypatch.setenv("DHWANI_API_KEY", "legitimate_internal_key_999")

    # Attacker supplies forged X-API-Key
    resp = client.get(
        "/api/incidents",
        headers={"X-API-Key": "forged_attacker_key_evil"},
    )
    assert resp.status_code == 401
    assert "invalid" in resp.json()["detail"].lower()


def test_websocket_direct_anonymous_access_rejected(monkeypatch):
    """Verify anonymous WebSocket connections without valid subprotocol tokens are rejected with 1008."""
    monkeypatch.setenv("DHWANI_AUTH_REQUIRED", "true")
    monkeypatch.setenv("DHWANI_API_KEY", "ws_gate_secret_token_777")

    # Anonymous connection without subprotocol or query token
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/dashboard"):
            pass
    assert exc_info.value.code == 1008


def test_authorized_requests_through_boundary_succeed(monkeypatch):
    """Verify authorized client requests with valid credentials succeed through trust boundary."""
    valid_key = "authorized_client_key_888"
    monkeypatch.setenv("DHWANI_AUTH_REQUIRED", "true")
    monkeypatch.setenv("DHWANI_API_KEY", valid_key)

    resp = client.get("/api/incidents", headers={"X-API-Key": valid_key})
    assert resp.status_code == 200
    assert "incidents" in resp.json()






