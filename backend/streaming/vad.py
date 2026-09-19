import numpy as np


def is_speech(
    audio_bytes: bytes,
    threshold: float = 0.01
):

    if not audio_bytes:

        return False

    audio = np.frombuffer(
        audio_bytes,
        dtype=np.int16
    ).astype(np.float32)

    audio = audio / 32768.0

    rms = np.sqrt(
        np.mean(audio ** 2)
    )

    return bool(
        rms > threshold
    )