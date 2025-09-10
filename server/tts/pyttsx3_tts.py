import tempfile, pyttsx3

def tts_to_wav_bytes(text: str) -> bytes:
    engine = pyttsx3.init()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        tmp = f.name
    engine.save_to_file(text, tmp)
    engine.runAndWait()
    with open(tmp, "rb") as rf:
        return rf.read()
