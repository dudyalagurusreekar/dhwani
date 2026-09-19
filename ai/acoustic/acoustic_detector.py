import numpy as np
import librosa


TARGET_SR = 16000
N_MFCC = 20


def extract_features(audio, sr):
    """
    Extract acoustic features from an audio waveform.

    Returns:
        numpy array containing:
        - MFCC statistics
        - delta MFCC statistics
        - spectral centroid
        - spectral bandwidth
        - spectral rolloff
        - zero crossing rate
        - RMS energy
    """

    # Convert to mono
    if audio.ndim > 1:
        audio = np.mean(audio, axis=1)

    # Normalize safely
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val

    # MFCC
    mfcc = librosa.feature.mfcc(
        y=audio,
        sr=sr,
        n_mfcc=N_MFCC,
        n_fft=512,
        hop_length=160
    )

    # Delta MFCC
    delta = librosa.feature.delta(mfcc)

    # Spectral features
    spectral_centroid = librosa.feature.spectral_centroid(
        y=audio,
        sr=sr,
        n_fft=512,
        hop_length=160
    )

    spectral_bandwidth = librosa.feature.spectral_bandwidth(
        y=audio,
        sr=sr,
        n_fft=512,
        hop_length=160
    )

    spectral_rolloff = librosa.feature.spectral_rolloff(
        y=audio,
        sr=sr,
        n_fft=512,
        hop_length=160
    )

    zero_crossing = librosa.feature.zero_crossing_rate(
        audio,
        hop_length=160
    )

    rms = librosa.feature.rms(
        y=audio,
        frame_length=512,
        hop_length=160
    )

    features = []

    # Mean + standard deviation for MFCCs
    features.extend(np.mean(mfcc, axis=1))
    features.extend(np.std(mfcc, axis=1))

    # Mean + standard deviation for delta MFCCs
    features.extend(np.mean(delta, axis=1))
    features.extend(np.std(delta, axis=1))

    # Mean + standard deviation for spectral features
    for feature in [
        spectral_centroid,
        spectral_bandwidth,
        spectral_rolloff,
        zero_crossing,
        rms
    ]:
        features.append(np.mean(feature))
        features.append(np.std(feature))

    return np.asarray(features, dtype=np.float32)


def load_audio(path):
    """
    Load audio and convert it to 16 kHz mono.
    """

    audio, sr = librosa.load(
        path,
        sr=TARGET_SR,
        mono=True
    )

    return audio, sr


def extract_from_file(path):
    """
    Convenience function for extracting features directly
    from an audio file.
    """

    audio, sr = load_audio(path)

    return extract_features(audio, sr)


if __name__ == "__main__":

    import sys

    if len(sys.argv) != 2:
        print("Usage:")
        print("python acoustic_detector.py <audio.wav>")
        sys.exit(1)

    audio_path = sys.argv[1]

    features = extract_from_file(audio_path)

    print("========================================")
    print("ACOUSTIC FEATURE EXTRACTION: PASS")
    print("========================================")
    print("Feature dimension:", features.shape)
    print("Sample rate:", TARGET_SR)
    print("Number of MFCCs:", N_MFCC)
    print("========================================")