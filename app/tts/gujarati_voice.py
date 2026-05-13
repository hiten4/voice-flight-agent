from gtts import gTTS
from playsound import playsound



def speak_gujarati(text, output_file="temp/output.mp3"):
    tts = gTTS(text=text, lang="gu")

    tts.save(output_file)

    playsound(output_file)