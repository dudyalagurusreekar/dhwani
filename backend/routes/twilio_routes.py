"""
Twilio Inbound Webhook Routes for Dhwani / EchoShield AI
Generates TwiML instructing Twilio Programmable Voice to connect inbound call audio
to Dhwani's public/tunnel WSS /twilio/media endpoint.
"""

import os
from fastapi import APIRouter, Form, HTTPException, Request, Response
from streaming.telephony.twiml import generate_twiml_media_stream
from security.twilio_validator import get_external_request_url, verify_twilio_signature

router = APIRouter(prefix="/twilio", tags=["Twilio Telephony"])


@router.post("/voice")
async def twilio_inbound_voice_webhook(
    request: Request,
    CallSid: str = Form(""),
    From: str = Form(""),
    To: str = Form(""),
):
    """
    Twilio Voice webhook for inbound calls.
    Enforces HMAC-SHA1 signature verification when TWILIO_AUTH_TOKEN is configured.
    Returns TwiML XML instructing Twilio to fork live audio to /twilio/media.
    """
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    verify_enforced = os.getenv("TWILIO_VERIFY_SIGNATURE", "false").lower() in ("true", "1")

    # If auth token configured or verification strictly enforced, validate signature
    if auth_token or verify_enforced:
        if not auth_token:
            return Response(
                content="Server configuration error: TWILIO_AUTH_TOKEN is required for signature verification.",
                status_code=500,
                media_type="text/plain",
            )

        signature = request.headers.get("x-twilio-signature")
        if not signature:
            return Response(
                content="Missing X-Twilio-Signature header.",
                status_code=403,
                media_type="text/plain",
            )

        # Form params submitted by Twilio
        form_data = {
            "CallSid": CallSid,
            "From": From,
            "To": To,
        }
        # Include any additional form parameters
        try:
            raw_form = await request.form()
            for k, v in raw_form.items():
                if isinstance(v, str):
                    form_data[k] = v
        except Exception:
            pass

        ext_url = get_external_request_url(request, "/twilio/voice")
        if not verify_twilio_signature(url=ext_url, params=form_data, signature=signature, auth_token=auth_token):
            return Response(
                content="Invalid Twilio signature.",
                status_code=403,
                media_type="text/plain",
            )
    # Public WSS endpoint (e.g. wss://example.ngrok-free.app/twilio/media)
    public_wss_base = os.getenv("TWILIO_STREAM_PUBLIC_URL", "").strip()

    if not public_wss_base:
        # Fallback to current host request URL converted to wss://
        host = request.headers.get("host", "localhost:8000")
        scheme = "wss" if request.url.scheme == "https" else "ws"
        stream_url = f"{scheme}://{host}/twilio/media"
    elif public_wss_base.endswith("/twilio/media"):
        stream_url = public_wss_base
    else:
        stream_url = f"{public_wss_base.rstrip('/')}/twilio/media"

    custom_params = {
        "from": From,
        "to": To,
        "callSid": CallSid,
    }

    twiml_xml = generate_twiml_media_stream(
        stream_url=stream_url,
        greeting_text="Connecting to Dhwani secure voice protection gateway.",
        custom_parameters=custom_params,
        track="inbound_track",
    )

    return Response(content=twiml_xml, media_type="application/xml")
