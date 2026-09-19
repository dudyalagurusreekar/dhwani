<<<<<<< HEAD
from collections import deque


class AudioBuffer:

    def __init__(
        self,
        max_chunks=5
    ):

        self.chunks = deque(
            maxlen=max_chunks
        )

    def add(
        self,
        audio_bytes
    ):

        self.chunks.append(
            audio_bytes
        )

    def get_audio(self):

        return b"".join(
            self.chunks
        )

    def clear(self):

        self.chunks.clear()

    def size(self):

=======
from collections import deque


class AudioBuffer:

    def __init__(
        self,
        max_chunks=5
    ):

        self.chunks = deque(
            maxlen=max_chunks
        )

    def add(
        self,
        audio_bytes
    ):

        self.chunks.append(
            audio_bytes
        )

    def get_audio(self):

        return b"".join(
            self.chunks
        )

    def clear(self):

        self.chunks.clear()

    def size(self):

>>>>>>> 3b89e99 (Integrate W2V2 detection with Android and backend)
        return len(self.chunks)