import os
import tempfile
from typing import Optional

# local ASR using faster-whisper if available
def transcribe_with_faster_whisper(audio_path: str, model_size: str = "base") -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("faster-whisper is not installed. Install it or switch ASR backend.")

    compute_type = "int8" if os.getenv("WHISPER_INT8", "1") == "1" else "float16"
    model = WhisperModel(model_size, device="auto", compute_type=compute_type)
    segments, info = model.transcribe(audio_path, beam_size=1, vad_filter=True)
    text = "".join([seg.text for seg in segments]).strip()
    return text or ""
