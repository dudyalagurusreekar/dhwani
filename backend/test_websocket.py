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
