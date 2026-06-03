"""
Always-on duplex conversation stream.

This replaces the old speak→wait→record loop with a phone-call model:
  - Mic is ALWAYS open
  - VAD detects when user starts and stops speaking
  - TTS plays agent responses and is cut off the moment user speaks
  - Speech is chunked into utterances and sent to a callback

The main interface:
    stream = ConversationStream(on_utterance_callback)
    stream.start()
    stream.speak(text, lang)   # play TTS; interrupted if user talks
    stream.stop()
"""

import threading
import queue
import time
import numpy as np
from collections import deque
from scipy.io.wavfile import write as wav_write
import os

SAMPLE_RATE  = 16000
BLOCK_SIZE   = 512
VAD_CHUNK = 512   # 32ms chunks — exact size required by Silero at 16kHz

# Tuning
VAD_THRESHOLD        = 0.5
SPEECH_HOLD_CHUNKS   = 5     # keep "speaking" alive N chunks after last detection
SILENCE_END_CHUNKS   = 8     # N silent chunks after speech = utterance complete (~768ms)
MIN_SPEECH_CHUNKS    = 3     # ignore blips shorter than this
WARMUP_AFTER_TTS_SEC = 0.35  # ignore VAD for this long after TTS ends (echo)


class ConversationStream:
    """
    Full-duplex stream: always listens, plays TTS when asked,
    fires on_utterance(audio_path) when user finishes a sentence.
    """

    def __init__(self, on_utterance):
        """
        on_utterance: callable(audio_path: str) called in a worker thread
                      when the user finishes speaking.
        """
        self._on_utterance  = on_utterance
        self._stream        = None
        self._running       = False

        # TTS output queue: deque of float32 samples to play
        self._out_buf       = deque()
        self._out_lock      = threading.Lock()
        self._tts_active    = False        # True while TTS audio remains in buffer
        self._tts_stopped   = threading.Event()  # set when TTS cut or drained

        # VAD state (callback thread only — no lock needed)
        self._vad_model     = None
        self._vad_buf       = np.zeros(0, dtype="float32")
        self._hold          = 0
        self._silence_count = 0
        self._in_speech     = False
        self._speech_chunks = 0
        self._warmup_blocks = 0            # blocks to ignore VAD after TTS

        # Mic recording buffer for current utterance
        self._mic_buf       = []
        # Rolling pre-speech buffer (last ~300ms) so we capture utterance start
        self._pre_buf       = deque(maxlen=10)   # 10 × 512 samples ≈ 320ms

        # Worker thread for utterance callbacks (keeps callback fast)
        self._utt_queue     = queue.Queue()
        self._worker        = threading.Thread(target=self._utt_worker, daemon=True)

        self._load_vad()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        try:
            import sounddevice as sd
        except ImportError:
            print("[Stream] sounddevice not available")
            return

        self._running = True
        self._worker.start()

        self._stream = sd.Stream(
            samplerate=SAMPLE_RATE,
            channels=(1, 1),
            dtype="float32",
            blocksize=BLOCK_SIZE,
            callback=self._callback,
        )
        self._stream.start()
        print("[Stream] Duplex stream started.")

    def stop(self):
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._utt_queue.put(None)   # sentinel to stop worker

    def speak(self, text: str, lang: str = "en", interruptible: bool = True):
        """
        Generate TTS audio and queue it for playback.
        Blocks until playback is done or interrupted by user speech.
        """
        wav_path = self._generate_tts(text, lang)
        if not wav_path:
            return

        samples = self._load_wav(wav_path)
        if samples is None:
            return

        # Queue samples for output
        self._tts_stopped.clear()
        with self._out_lock:
            self._out_buf.extend(samples)
            self._tts_active    = True
            self._warmup_blocks = int(WARMUP_AFTER_TTS_SEC * SAMPLE_RATE / BLOCK_SIZE)

        # Block until TTS drains or is interrupted
        self._tts_stopped.wait(timeout=120)

    def set_warmup(self, seconds: float):
        """Suppress VAD for N seconds (call after non-interruptible TTS)."""
        with self._out_lock:
            self._warmup_blocks = int(seconds * SAMPLE_RATE / BLOCK_SIZE)

    # ------------------------------------------------------------------
    # Callback (PortAudio thread — keep fast, no blocking)
    # ------------------------------------------------------------------

    def _callback(self, indata, outdata, frames, time_info, status):
        # --- OUTPUT ---
        # Always produce exactly `frames` samples — partial buffers get zero-padded
        chunk = np.zeros(frames, dtype="float32")
        with self._out_lock:
            n = min(frames, len(self._out_buf))
            if n > 0:
                for i in range(n):
                    chunk[i] = self._out_buf.popleft()

            if self._tts_active and len(self._out_buf) == 0:
                self._tts_active = False
                self._tts_stopped.set()

        outdata[:, 0] = chunk
        if outdata.shape[1] > 1:
            outdata[:, 1] = chunk

        # --- INPUT / VAD ---
        mic = indata[:, 0].copy()

        # Warmup: ignore VAD briefly after TTS to suppress echo
        with self._out_lock:
            wb = self._warmup_blocks
            if wb > 0:
                self._warmup_blocks -= 1

        if wb > 0:
            return

        # Always accumulate mic into a pre-speech ring buffer AND the active
        # utterance buffer — we decide what to keep after VAD fires.
        self._pre_buf.append(mic)         # rolling pre-speech context
        if self._in_speech:
            self._mic_buf.append(mic)

        self._vad_buf = np.concatenate([self._vad_buf, mic])

        while len(self._vad_buf) >= VAD_CHUNK:
            segment       = self._vad_buf[:VAD_CHUNK]
            self._vad_buf = self._vad_buf[VAD_CHUNK:]
            self._process_vad(segment)

    def _process_vad(self, segment: np.ndarray):
        conf = 0.0
        if self._vad_model is not None:
            try:
                import torch
                conf = self._vad_model(torch.from_numpy(segment), SAMPLE_RATE).item()
            except Exception as e:
                print(f"[VAD] inference error: {e}")

        is_speech = conf >= VAD_THRESHOLD
        # print(f"[VAD] conf={conf:.2f} speech={is_speech} in_speech={self._in_speech}", flush=True)

        if is_speech:
            self._hold          = SPEECH_HOLD_CHUNKS
            self._silence_count = 0

            if not self._in_speech:
                # Speech just started — seed mic_buf with pre-speech context
                self._in_speech     = True
                self._speech_chunks = 1
                # Include a few frames of pre-roll so we don't clip the start
                pre = list(self._pre_buf)
                self._mic_buf = pre  # pre_buf already has recent blocks

                # Interrupt TTS immediately
                if self._tts_active:
                    with self._out_lock:
                        self._out_buf.clear()
                        self._tts_active = False
                    self._tts_stopped.set()
                    print("[VAD] TTS interrupted.", flush=True)
            else:
                self._speech_chunks += 1

        else:
            if self._hold > 0:
                self._hold -= 1
                if self._in_speech:
                    self._speech_chunks += 1
            else:
                if self._in_speech:
                    self._silence_count += 1
                    if self._silence_count >= SILENCE_END_CHUNKS:
                        print(f"[VAD] Utterance end — {self._speech_chunks} chunks", flush=True)
                        if self._speech_chunks >= MIN_SPEECH_CHUNKS:
                            self._flush_utterance()
                        else:
                            print("[VAD] Too short, ignored.", flush=True)
                        self._in_speech     = False
                        self._mic_buf       = []
                        self._silence_count = 0
                        self._speech_chunks = 0

    def _flush_utterance(self):
        """Save mic buffer to file and queue for transcription."""
        if not self._mic_buf:
            return
        os.makedirs("temp", exist_ok=True)
        path = f"temp/utt_{int(time.time()*1000)}.wav"
        audio = np.concatenate(self._mic_buf)
        audio_i16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
        wav_write(path, SAMPLE_RATE, audio_i16)
        self._utt_queue.put(path)

    # ------------------------------------------------------------------
    # Worker thread — runs on_utterance outside the audio callback
    # ------------------------------------------------------------------

    def _utt_worker(self):
        while True:
            path = self._utt_queue.get()
            if path is None:
                break
            try:
                self._on_utterance(path)
            except Exception as e:
                print(f"[Stream] on_utterance error: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_vad(self):
        try:
            from silero_vad import load_silero_vad
            self._vad_model = load_silero_vad()
            print("[Stream] Silero VAD loaded.")
        except ImportError:
            try:
                import torch
                model, _ = torch.hub.load(
                    "snakers4/silero-vad", "silero_vad",
                    force_reload=False, trust_repo=True
                )
                self._vad_model = model
                print("[Stream] Silero VAD loaded via torch.hub.")
            except Exception as e:
                print(f"[Stream] VAD unavailable: {e}")

    def _generate_tts(self, text: str, lang: str) -> str | None:
        os.makedirs("temp", exist_ok=True)
        ts       = int(time.time())
        mp3_file = f"temp/tts_{ts}.mp3"
        wav_file = f"temp/tts_{ts}.wav"

        EDGE_VOICES = {"en": "en-US-AriaNeural", "gu": "gu-IN-DhwaniNeural", "hi": "hi-IN-SwaraNeural"}

        # edge-tts
        try:
            import edge_tts, asyncio
            async def _gen():
                await edge_tts.Communicate(text, EDGE_VOICES.get(lang, "en-US-AriaNeural")).save(mp3_file)
            asyncio.run(_gen())
            if self._to_wav(mp3_file, wav_file):
                return wav_file
        except Exception:
            pass

        # gTTS fallback
        try:
            from gtts import gTTS
            gTTS(text=text, lang=lang, tld="com").save(mp3_file)
            if self._to_wav(mp3_file, wav_file):
                return wav_file
        except Exception:
            pass

        return None

    def _to_wav(self, mp3, wav):
        try:
            import subprocess
            r = subprocess.run(
                ["ffmpeg", "-y", "-i", mp3, wav],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
            )
            return r.returncode == 0 and os.path.exists(wav)
        except FileNotFoundError:
            return False

    def _load_wav(self, wav_file) -> np.ndarray | None:
        try:
            import soundfile as sf
            data, sr = sf.read(wav_file, dtype="float32")
            if data.ndim > 1:
                data = data[:, 0]
            if sr != SAMPLE_RATE:
                n = int(len(data) * SAMPLE_RATE / sr)
                data = np.interp(np.linspace(0, len(data)-1, n), np.arange(len(data)), data).astype("float32")
            return data
        except Exception as e:
            print(f"[Stream] load_wav error: {e}")
            return None