import asyncio
import math
from pathlib import Path
import struct
import sys
import websockets

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


async def test():
    uri = "ws://127.0.0.1:8000/ws/audio?session_id=test-session"

    # Generate 1 second of synthetic 440 Hz audio (16 kHz, 16-bit PCM)
    samples = [
        int(10000 * math.sin(2 * math.pi * 440 * i / 16000))
        for i in range(16000)
    ]
    audio_chunk = b"".join(struct.pack("<h", sample) for sample in samples)

    try:
        async with websockets.connect(uri) as ws:
            print("[INFO] Connected to external live server WebSocket at 127.0.0.1:8000")
            await ws.send(audio_chunk)
            response = await ws.recv()
            print("[PASS] Server response:")
            print(response)
            return
    except (ConnectionRefusedError, OSError):
        print("[INFO] External server not detected on port 8000; testing via in-process FastAPI TestClient...")

    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    with client.websocket_connect("/ws/audio?session_id=test-session") as ws:
        ws.send_bytes(audio_chunk)
        response = ws.receive_json()
        print("[PASS] In-process WebSocket response received:")
        print(response)


asyncio.run(test())
