import pyttsx3
import tempfile
import wave

def tts_to_wav_bytes(text: str) -> bytes:
    """
    Simple offline TTS using pyttsx3. Generates a WAV in memory.
    """
    engine = pyttsx3.init()
    # You can adjust voice/rate/volume here if needed.
    # engine.setProperty('rate', 180)
    # engine.setProperty('volume', 1.0)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        tmp_path = f.name
    engine.save_to_file(text, tmp_path)
    engine.runAndWait()

    with open(tmp_path, "rb") as wf:
        data = wf.read()
    return data
