import sounddevice as sd
from scipy.io.wavfile import write
import os

def record_audio(filename="temp/input.wav", duration=5, sample_rate=16000):

    os.makedirs("temp", exist_ok=True)

    print("Recording started...")

    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="int16"
    )

    sd.wait()

    write(filename, sample_rate, audio)

    print("Recording completed.")

    return filename