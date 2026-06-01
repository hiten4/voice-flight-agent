"""
TTS with full-duplex interruption.

When the user speaks during TTS playback:
  1. Playback stops immediately.
  2. The audio the user spoke DURING the duplex stream is saved to a file.
  3. speak() returns that captured audio path via a module-level variable
     so main.py can reuse it instead of opening the recorder fresh.

Usage in main.py:
    speak(text, ...)
    captured = get_interrupted_audio()   # None if not interrupted
    if captured:
        user_input = transcribe_audio(captured)
    else:
        user_input = listen()            # normal recording
"""

import os
import time
import asyncio
import threading
import numpy as np
from collections import deque
from scipy.io.wavfile import write as wav_write

POST_SPEECH_DELAY = 0.4

EDGE_VOICE_MAP = {
    "en": "en-US-AriaNeural",
    "gu": "gu-IN-DhwaniNeural",
    "hi": "hi-IN-SwaraNeural",
}

# Holds the path to audio captured during an interruption (or None)
_interrupted_audio_path: str | None = None

def get_interrupted_audio() -> str | None:
    """Call after speak() — returns saved mic audio path if user interrupted, else None."""
    return _interrupted_audio_path

def _set_interrupted_audio(path: str | None):
    global _interrupted_audio_path
    _interrupted_audio_path = path


# ---------------------------------------------------------------------------
# TTS generation
# ---------------------------------------------------------------------------

def _speak_edge(text, lang, wav_file):
    try:
        import edge_tts
    except ImportError:
        return False
    voice   = EDGE_VOICE_MAP.get(lang, "en-US-AriaNeural")
    mp3_tmp = wav_file.replace(".wav", "_edge.mp3")
    async def _gen():
        await edge_tts.Communicate(text, voice).save(mp3_tmp)
    try:
        asyncio.run(_gen())
        return _to_wav(mp3_tmp, wav_file)
    except Exception as e:
        print(f"[TTS] edge-tts: {e}")
        return False

def _speak_gtts(text, lang, mp3_file, wav_file):
    try:
        from gtts import gTTS
        gTTS(text=text, lang=lang, tld="com").save(mp3_file)
        return _to_wav(mp3_file, wav_file)
    except Exception as e:
        print(f"[TTS] gTTS: {e}")
        return False

def _to_wav(mp3, wav):
    try:
        import subprocess
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", mp3, wav],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
        )
        return r.returncode == 0 and os.path.exists(wav)
    except FileNotFoundError:
        return False


# ---------------------------------------------------------------------------
# Public speak()
# ---------------------------------------------------------------------------

def speak(text, lang="gu", interruptible=True):
    _set_interrupted_audio(None)   # clear previous

    os.makedirs("temp", exist_ok=True)
    ts       = int(time.time())
    mp3_file = f"temp/response_{lang}_{ts}.mp3"
    wav_file = f"temp/response_{lang}_{ts}.wav"

    wav_ready = _speak_edge(text, lang, wav_file) or _speak_gtts(text, lang, mp3_file, wav_file)

    if wav_ready:
        if interruptible:
            _play_duplex(wav_file, ts)
        else:
            _play_simple(wav_file)
        return

    try:
        import winsound
        winsound.PlaySound(wav_file, winsound.SND_FILENAME)
        time.sleep(POST_SPEECH_DELAY)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Simple playback (non-interruptible)
# ---------------------------------------------------------------------------

def _play_simple(wav_file):
    try:
        import sounddevice as sd
        import soundfile as sf
        data, sr = sf.read(wav_file)
        sd.play(data, sr)
        sd.wait()
    except KeyboardInterrupt:
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass
    except Exception as e:
        print(f"[TTS] Simple play error: {e}")
    time.sleep(POST_SPEECH_DELAY)


# ---------------------------------------------------------------------------
# Duplex (interruptible) playback — captures user speech during interruption
# ---------------------------------------------------------------------------

DUPLEX_SR   = 16000
VAD_CHUNK   = int(DUPLEX_SR * 0.096)   # 96ms
BLOCK_SIZE  = 512
WARMUP_SEC  = 0.4                       # ignore VAD for first N seconds (echo)
WARMUP_BLOCKS = int(WARMUP_SEC * DUPLEX_SR / BLOCK_SIZE)


def _play_duplex(wav_file: str, ts: int):
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError:
        _play_simple(wav_file)
        return

    try:
        data, file_sr = sf.read(wav_file, dtype="float32")
    except Exception as e:
        print(f"[TTS] Could not read wav: {e}")
        return

    if data.ndim > 1:
        data = data[:, 0]
    if file_sr != DUPLEX_SR:
        data = _resample(data, file_sr, DUPLEX_SR)

    vad_model = _get_vad_model()

    # --- Shared state ---
    out_queue    = deque(data)
    stop_event   = threading.Event()
    mic_recorded = []          # accumulates ALL mic audio during playback
    vad_buf      = []
    hold         = [0]
    warmup       = [WARMUP_BLOCKS]
    was_interrupted = [False]

    def callback(indata, outdata, frames, time_info, status):
        # OUTPUT
        chunk = np.zeros(frames, dtype="float32")
        for i in range(frames):
            if out_queue:
                chunk[i] = out_queue.popleft()
        outdata[:] = chunk.reshape(-1, 1)
        if outdata.shape[1] > 1:
            outdata[:, 1] = chunk

        # Collect mic audio
        mic_chunk = indata[:, 0].copy()
        mic_recorded.append(mic_chunk)

        # Queue empty → playback done naturally
        if not out_queue and not stop_event.is_set():
            stop_event.set()
            return

        # VAD
        if vad_model is None:
            return

        if warmup[0] > 0:
            warmup[0] -= 1
            return

        vad_buf.extend(mic_chunk)
        while len(vad_buf) >= VAD_CHUNK:
            segment  = np.array(vad_buf[:VAD_CHUNK], dtype="float32")
            vad_buf[:] = vad_buf[VAD_CHUNK:]
            try:
                import torch
                conf = vad_model(torch.from_numpy(segment), DUPLEX_SR).item()
                if conf >= 0.5:
                    hold[0] = 4
                elif hold[0] > 0:
                    hold[0] -= 1

                if hold[0] > 0 and not stop_event.is_set():
                    print("\n[VAD] User speaking — stopping playback.")
                    was_interrupted[0] = True
                    stop_event.set()
            except Exception:
                pass

    try:
        with sd.Stream(
            samplerate=DUPLEX_SR,
            channels=(1, 1),
            dtype="float32",
            blocksize=BLOCK_SIZE,
            callback=callback,
        ):
            stop_event.wait(timeout=60)
    except Exception as e:
        print(f"[TTS] Duplex failed ({e}), falling back.")
        _play_simple(wav_file)
        return

    # If interrupted, save what the user said during playback
    if was_interrupted[0] and mic_recorded:
        captured_path = f"temp/interrupted_{ts}.wav"
        audio_int16 = _float_to_int16(np.concatenate(mic_recorded))
        wav_write(captured_path, DUPLEX_SR, audio_int16)
        _set_interrupted_audio(captured_path)
        print(f"[VAD] Captured {len(audio_int16)/DUPLEX_SR:.1f}s of speech during interruption.")
    else:
        time.sleep(POST_SPEECH_DELAY)


def _float_to_int16(audio: np.ndarray) -> np.ndarray:
    audio = np.clip(audio, -1.0, 1.0)
    return (audio * 32767).astype(np.int16)

def _resample(data, orig_sr, target_sr):
    if orig_sr == target_sr:
        return data
    new_len = int(len(data) * target_sr / orig_sr)
    return np.interp(
        np.linspace(0, len(data) - 1, new_len),
        np.arange(len(data)), data
    ).astype("float32")


# ---------------------------------------------------------------------------
# VAD model singleton
# ---------------------------------------------------------------------------
_vad_model_cache = None

def _get_vad_model():
    global _vad_model_cache
    if _vad_model_cache is not None:
        return _vad_model_cache
    try:
        from silero_vad import load_silero_vad
        _vad_model_cache = load_silero_vad()
        return _vad_model_cache
    except ImportError:
        pass
    try:
        import torch
        model, _ = torch.hub.load(
            "snakers4/silero-vad", "silero_vad",
            force_reload=False, trust_repo=True
        )
        _vad_model_cache = model
        return _vad_model_cache
    except Exception:
        return None


def speak_gujarati(text):
    speak(text, lang="gu")