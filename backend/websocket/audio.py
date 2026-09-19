from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect
)

from streaming.capture import AudioChunk
from streaming.stream_manager import StreamManager

from services.detector import detect_voice
from services.risk_engine import calculate_risk


router = APIRouter()

stream_manager = StreamManager()


@router.websocket(
    "/ws/audio"
)
async def audio_stream(
    websocket: WebSocket
):

    await websocket.accept()

    session_id = (
        websocket.query_params.get(
            "session_id"
        )
    )

    if not session_id:

        await websocket.send_json({
            "error":
                "session_id required"
        })

        await websocket.close()

        return

    sequence = 0

    try:

        while True:

            # Receive raw audio
            audio_bytes = (
                await websocket.receive_bytes()
            )

            sequence += 1

            # Create chunk
            chunk = AudioChunk(

                session_id=
                    session_id,

                sequence=
                    sequence,

                audio_bytes=
                    audio_bytes,

                sample_rate=
                    16000,

                channels=
                    1
            )

            # VAD + buffer
            stream_result = (
                stream_manager
                .process_chunk(
                    chunk
                )
            )

            # No speech
            if not stream_result[
                "speech"
            ]:

                await websocket.send_json({

                    "session_id":
                        session_id,

                    "sequence":
                        sequence,

                    "speech":
                        False,

                    "status":
                        "NO_SPEECH"
                })

                continue

            # ML / mock detector
            prediction = (
                await detect_voice(
                    audio_bytes
                )
            )

            # Risk
            risk = calculate_risk(
                prediction[
                    "fake_probability"
                ]
            )

            # Final response
            result = {

                "session_id":
                    session_id,

                "sequence":
                    sequence,

                "speech":
                    True,

                "fake_probability":
                    prediction[
                        "fake_probability"
                    ],

                "real_probability":
                    prediction[
                        "real_probability"
                    ],

                "risk_score":
                    risk[
                        "risk_score"
                    ],

                "status":
                    risk[
                        "status"
                    ],

                "alert":
                    risk[
                        "alert"
                    ],

                "recommendation":
                    risk[
                        "recommendation"
                    ]
            }

            await websocket.send_json(
                result
            )

    except WebSocketDisconnect:

        print(
            f"Session {session_id} disconnected"
        )

    except Exception as e:

        print(
            f"WebSocket error: {e}"
        )