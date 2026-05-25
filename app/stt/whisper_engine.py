from faster_whisper import WhisperModel

model = WhisperModel("small", device="cpu")


def transcribe_audio(audio_path):
    # Force language="en" so Whisper never auto-detects Spanish, Hindi, etc.
    # This prevents "tomorrow" being heard as Spanish phonetics.
    segments, _ = model.transcribe(audio_path, language="en")

    final_text = ""
    for segment in segments:
        final_text += segment.text + " "

    return final_text.strip()