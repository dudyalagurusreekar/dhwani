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