"""
VAD module — now a thin wrapper kept for API compatibility.

The actual VAD-during-playback logic lives inside gujarati_tts.py's
duplex stream callback, which is the only reliable way to do simultaneous
mic+speaker on Windows WASAPI.

This module's get_vad_listener() is still imported by main.py to call
vad.start() — that's now a no-op since we don't need a background stream.
"""


class VADListener:
    """Stub — real VAD runs inside the duplex playback stream."""
    def __init__(self):
        self.available = True   # report available so main.py proceeds

    def start(self):
        print("[VAD] Duplex-mode VAD active (runs inside TTS playback).")

    def stop(self):
        pass

    def pause(self):
        pass

    def resume(self):
        pass

    def is_speech(self):
        return False

    def reset(self):
        pass


_vad_listener = None

def get_vad_listener() -> VADListener:
    global _vad_listener
    if _vad_listener is None:
        _vad_listener = VADListener()
    return _vad_listener