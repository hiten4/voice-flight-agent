from gtts import gTTS
from playsound import playsound


def speak_gujarati(text):

    tts = gTTS(
        text=text,
        lang="gu"
    )

    audio_file = "response.mp3"

    tts.save(audio_file)

    playsound(audio_file)