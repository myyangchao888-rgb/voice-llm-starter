import os
import base64
import tempfile
from typing import Optional
from openai import OpenAI

def transcribe_with_openai_base64(b64_webm: str, filename: str = "audio.webm") -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""), base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    raw = base64.b64decode(b64_webm)
    with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as fp:
        fp.write(raw)
        tmp = fp.name
    with open(tmp, "rb") as f:
        # Whisper model name may vary; "whisper-1" or newer audio transcription models.
        transcript = client.audio.transcriptions.create(model="whisper-1", file=f)
    text = getattr(transcript, "text", "")
    return text or ""
