from dataclasses import dataclass


@dataclass
class AudioChunk:

    session_id: str

    sequence: int

    audio_bytes: bytes

    sample_rate: int = 16000

    channels: int = 1

    @property
    def duration_ms(self):

        # PCM16 = 2 bytes/sample
        bytes_per_sample = 2

        samples = (
            len(self.audio_bytes)
            // bytes_per_sample
        )

        return int(
            samples
            / self.sample_rate
            * 1000
        )