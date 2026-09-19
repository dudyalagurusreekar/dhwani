from .buffer import AudioBuffer
from .capture import AudioChunk
from .vad import is_speech


class StreamManager:

    def __init__(self):

        self.buffers = {}

    def get_buffer(
        self,
        session_id
    ):

        if session_id not in self.buffers:

            self.buffers[session_id] = (
                AudioBuffer(
                    max_chunks=5
                )
            )

        return self.buffers[
            session_id
        ]

    def process_chunk(
        self,
        chunk: AudioChunk
    ):

        speech = is_speech(
            chunk.audio_bytes
        )

        if speech:

            buffer = self.get_buffer(
                chunk.session_id
            )

            buffer.add(
                chunk.audio_bytes
            )

        return {

            "session_id":
                chunk.session_id,

            "sequence":
                chunk.sequence,

            "sample_rate":
                chunk.sample_rate,

            "duration_ms":
                chunk.duration_ms,

            "speech":
                speech
        }