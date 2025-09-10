import os
from faster_whisper import WhisperModel

def transcribe_with_faster_whisper(audio_path: str, model_size: str = "base") -> str:
    compute_type = "int8" if os.getenv("WHISPER_INT8", "1") == "1" else "float16"
    model = WhisperModel(model_size, device="auto", compute_type=compute_type)
    segments, info = model.transcribe(audio_path, beam_size=1, vad_filter=True)
    return "".join([seg.text for seg in segments]).strip()
