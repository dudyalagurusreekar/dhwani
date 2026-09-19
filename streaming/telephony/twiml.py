"""
TwiML Generator for Dhwani Voice Streams
Generates standard Twilio Voice XML directing inbound and outbound calls
to stream live audio into Dhwani's WebSocket media receiver.
"""

from typing import Optional, Dict
import xml.etree.ElementTree as ET


def generate_twiml_media_stream(
    stream_url: str,
    greeting_text: Optional[str] = "Connecting to Dhwani secure voice protection.",
    custom_parameters: Optional[Dict[str, str]] = None,
    track: str = "inbound_track",
) -> str:
    """
    Generate TwiML response XML instructing Twilio to fork/connect call audio
    to the Dhwani media stream WebSocket.

    Args:
        stream_url: Public WSS URL (e.g. wss://example.ngrok-free.app/twilio/media)
        greeting_text: Text announced to caller before streaming (optional)
        custom_parameters: Key-value parameters passed into the 'start' message
        track: Audio track to stream: 'inbound_track', 'outbound_track', or 'both_tracks'

    Returns:
        XML string compliant with Twilio Voice TwiML specification.
    """
    response = ET.Element("Response")

    if greeting_text:
        say = ET.SubElement(response, "Say", voice="Polly.Joanna")
        say.text = greeting_text

    connect = ET.SubElement(response, "Connect")
    stream = ET.SubElement(connect, "Stream", url=stream_url, track=track)

    if custom_parameters:
        for k, v in custom_parameters.items():
            param = ET.SubElement(stream, "Parameter", name=k, value=str(v))

    # Keep call active while streaming is connected
    ET.SubElement(response, "Pause", length="120")

    return ET.tostring(response, encoding="utf-8", xml_declaration=True).decode("utf-8")
