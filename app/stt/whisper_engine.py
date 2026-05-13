from faster_whisper import WhisperModel


model = WhisperModel("small", device="cpu")


def transcribe_audio(audio_path):
    segments, _ = model.transcribe(audio_path)

    final_text = ""

    for segment in segments:
        final_text += segment.text + " "

    return final_text.strip()