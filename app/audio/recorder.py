import os
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 500    # amplitude below this = silence
SILENCE_DURATION = 0.8     # seconds of silence before stopping
MAX_DURATION = 10          # hard cap in seconds


def record_audio(filename="temp/input.wav"):
    """
    Record audio and stop automatically after the user stops speaking.
    Stops when SILENCE_DURATION seconds of silence detected, or MAX_DURATION reached.
    """
    os.makedirs("temp", exist_ok=True)

    print("Recording started... (speak now, recording stops when you pause)")

    chunk_size = int(SAMPLE_RATE * 0.1)   # 100ms chunks
    max_chunks = int(MAX_DURATION / 0.1)
    silence_chunks_needed = int(SILENCE_DURATION / 0.1)

    recorded = []
    silence_count = 0
    speech_detected = False

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
        for _ in range(max_chunks):
            chunk, _ = stream.read(chunk_size)
            recorded.append(chunk.copy())

            amplitude = np.abs(chunk).mean()

            if amplitude > SILENCE_THRESHOLD:
                speech_detected = True
                silence_count = 0
            else:
                if speech_detected:
                    silence_count += 1

            # Stop once speech has been detected and silence follows
            if speech_detected and silence_count >= silence_chunks_needed:
                break

    print("Recording completed.")

    audio = np.concatenate(recorded, axis=0)
    write(filename, SAMPLE_RATE, audio)

    return filename