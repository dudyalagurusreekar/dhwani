<<<<<<< HEAD
import asyncio
import websockets


async def test():
    session_id = "test-session-123"

    uri = f"ws://127.0.0.1:8000/ws/audio?session_id={session_id}"

    async with websockets.connect(uri) as websocket:
        print("WebSocket connected!")

        # 1 second of silent 16-bit PCM audio at 16 kHz
        audio = b"\x00\x00" * 16000

        await websocket.send(audio)

        response = await websocket.recv()

        print("Server response:")
        print(response)


asyncio.run(test())
=======
import asyncio
import math
import struct
import websockets


async def test():
    uri = "ws://127.0.0.1:8000/ws/audio?session_id=test-session"

    async with websockets.connect(uri) as ws:
        print("Connected to WebSocket!")

        # Generate 1 second of synthetic 440 Hz audio
        # 16 kHz, 16-bit PCM
        samples = [
            int(10000 * math.sin(2 * math.pi * 440 * i / 16000))
            for i in range(16000)
        ]

        # Convert samples to raw 16-bit PCM bytes
        audio_chunk = b"".join(
            struct.pack("<h", sample)
            for sample in samples
        )

        await ws.send(audio_chunk)

        response = await ws.recv()

        print("Server response:")
        print(response)


asyncio.run(test())
>>>>>>> 3b89e99 (Integrate W2V2 detection with Android and backend)
