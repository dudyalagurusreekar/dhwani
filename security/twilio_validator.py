"""
Dhwani / EchoShield AI - Twilio Webhook Signature Validator
===========================================================
Implements Twilio's official HMAC-SHA1 request validation specification
to defend against webhook spoofing and unauthorized telephony injection.
"""

import base64
import hashlib
import hmac
import os
from typing import Dict, Optional
from fastapi import Request


def compute_twilio_signature(url: str, params: Dict[str, str], auth_token: str) -> str:
    """
    Compute official Twilio HMAC-SHA1 signature:
    1. Take full request URL
    2. Sort POST parameter keys alphabetically
    3. Concatenate each key and value to URL
    4. Sign with HMAC-SHA1 using auth_token
    5. Base64 encode
    """
    data = url
    for key in sorted(params.keys()):
        data += key + params[key]

    mac = hmac.new(auth_token.encode("utf-8"), data.encode("utf-8"), hashlib.sha1)
    return base64.b64encode(mac.digest()).decode("utf-8").strip()


def verify_twilio_signature(
    url: str,
    params: Dict[str, str],
    signature: Optional[str],
    auth_token: Optional[str] = None,
) -> bool:
    """
    Verify incoming Twilio X-Twilio-Signature against computed signature.
    Uses constant-time comparison to prevent timing attacks.
    """
    token = auth_token or os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    if not token:
        # If no auth token is configured and verification not enforced, report false
        return False

    if not signature:
        return False

    expected_sig = compute_twilio_signature(url, params, token)
    return hmac.compare_digest(expected_sig, signature.strip())


from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse


def get_external_request_url(
    request: Union[Request, str],
    headers: Optional[Any] = None,
    fallback_path: str = "/twilio/voice",
) -> str:
    """
    Reconstruct the public URL of the incoming request as seen by Twilio,
    accounting for reverse proxies, ngrok tunnels, and X-Forwarded headers.
    """
    configured_base = os.getenv("TWILIO_PUBLIC_URL", "").strip().rstrip("/")
    if configured_base:
        if configured_base.endswith(fallback_path):
            return configured_base
        return f"{configured_base}{fallback_path}"

    if isinstance(request, str):
        parsed = urlparse(request)
        hdrs = headers or {}
        proto = hdrs.get("x-forwarded-proto", parsed.scheme or "http").lower()
        host = hdrs.get("x-forwarded-host", hdrs.get("host", parsed.netloc or "localhost:8000"))
        path = parsed.path or fallback_path
        query = f"?{parsed.query}" if parsed.query else ""
    else:
        proto = request.headers.get("x-forwarded-proto", request.url.scheme).lower()
        host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost:8000"))
        path = request.url.path
        query = f"?{request.url.query}" if request.url.query else ""

    # Standardize port if implicit
    if proto == "https" and host.endswith(":443"):
        host = host[:-4]
    elif proto == "http" and host.endswith(":80"):
        host = host[:-3]

    return f"{proto}://{host}{path}{query}"
