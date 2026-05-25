import os
import time
import wave
import struct
from gtts import gTTS


def _mp3_to_wav_via_ffmpeg(mp3_file, wav_file):
    """Try ffmpeg conversion. Returns True if successful."""
    try:
        import subprocess
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_file, wav_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10
        )
        return result.returncode == 0 and os.path.exists(wav_file)
    except FileNotFoundError:
        return False


def speak(text, lang="gu"):
    """
    Convert text to speech and play it silently (no popup window).

    Strategy:
    1. Save gTTS output as mp3
    2. Try ffmpeg mp3->wav conversion, play with winsound (no window)
    3. If ffmpeg not available, fall back to os.startfile (opens media player)
    """
    os.makedirs("temp", exist_ok=True)
    ts = int(time.time())
    mp3_file = f"temp/response_{lang}_{ts}.mp3"
    wav_file = f"temp/response_{lang}_{ts}.wav"

    tts_obj = gTTS(text=text, lang=lang)
    tts_obj.save(mp3_file)

    # Try clean path: ffmpeg + winsound (no window)
    if _mp3_to_wav_via_ffmpeg(mp3_file, wav_file):
        import winsound
        winsound.PlaySound(wav_file, winsound.SND_FILENAME)
        return

    # Fallback: sounddevice + soundfile if available
    try:
        import subprocess
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_file, wav_file],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        import sounddevice as sd
        import soundfile as sf
        data, samplerate = sf.read(wav_file)
        sd.play(data, samplerate)
        try:
            sd.wait()
        except KeyboardInterrupt:
            sd.stop()
        return
    except Exception:
        pass

    # Last resort: os.startfile (opens media player window)
    # Will be removed once ffmpeg PATH is fixed
    wait_seconds = max(2.5, len(text) * 0.07)
    os.startfile(os.path.abspath(mp3_file))
    time.sleep(wait_seconds)


def speak_gujarati(text):
    """Backward-compatible wrapper."""
    speak(text, lang="gu")