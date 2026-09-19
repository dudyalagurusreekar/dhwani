"""
Twilio Inbound Webhook Routes for Dhwani / EchoShield AI
Generates TwiML instructing Twilio Programmable Voice to connect inbound call audio
to Dhwani's public/tunnel WSS /twilio/media endpoint.
"""

import os
from fastapi import APIRouter, Form, Request, Response
from streaming.telephony.twiml import generate_twiml_media_stream

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
    Returns TwiML XML instructing Twilio to fork live audio to /twilio/media.
    """
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
