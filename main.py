from app.audio.recorder import record_audio
from app.stt.whisper_engine import transcribe_audio
from app.tts.gujarati_voice import speak_gujarati


if __name__ == "__main__":

    audio_path = record_audio()

    text = transcribe_audio(audio_path)

    print("User Said:", text)

    response = "તમારો અવાજ સફળતાપૂર્વક પ્રાપ્ત થયો છે"

    speak_gujarati(response)