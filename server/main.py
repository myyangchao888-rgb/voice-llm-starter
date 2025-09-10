import os
import io
import base64
import json
import asyncio
import tempfile
from typing import List, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from server.providers.factory import build_provider
from server.asr.whisper_local import transcribe_with_faster_whisper
from server.asr.openai_whisper import transcribe_with_openai_base64
from server.tts.pyttsx3_tts import tts_to_wav_bytes

load_dotenv()

app = FastAPI(title="Voice LLM Starter v0.5", version="0.5")

# CORS: Adjust origins as needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend
static_dir = os.path.join(os.path.dirname(__file__), "..", "web")
app.mount("/web", StaticFiles(directory=static_dir), name="web")

@app.get("/")
def root():
    return HTMLResponse(open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8").read())

@app.post("/api/chat")
async def chat_api(payload: Dict[str, Any]):
    messages = payload.get("messages", [])
    provider_key = payload.get("provider", os.getenv("DEFAULT_PROVIDER", "aliyun"))
    model = payload.get("model", os.getenv("DEFAULT_MODEL", ""))
    provider, default_model = build_provider(provider_key)
    if not model:
        model = default_model

    # Collect full text (non-stream) for simplicity here
    text = ""
    for piece in provider.stream_chat(messages, model=model):
        text += piece
    return JSONResponse({"provider": provider.name(), "model": model, "text": text})

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    # Each connection keeps its own conversation state
    # messages: [{role: 'system'|'user'|'assistant', content: '...'}]
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": "You are a helpful assistant. Reply in the same language as the user."}
    ]

    # Defaults from env
    provider_key = os.getenv("DEFAULT_PROVIDER", "aliyun")
    model = os.getenv("DEFAULT_MODEL", "qwen-turbo")
    asr_backend = os.getenv("DEFAULT_ASR_BACKEND", "faster_whisper")
    tts_backend = os.getenv("DEFAULT_TTS_BACKEND", "pyttsx3")

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)

            if data.get("type") == "config":
                provider_key = data.get("provider", provider_key)
                model = data.get("model", model)
                asr_backend = data.get("asr", asr_backend)
                tts_backend = data.get("tts", tts_backend)
                await ws.send_text(json.dumps({"type": "info", "msg": f"Config updated: provider={provider_key}, model={model}, asr={asr_backend}, tts={tts_backend}"}))
                continue

            if data.get("type") == "user_text":
                user_text = data.get("text", "").strip()
                if not user_text:
                    await ws.send_text(json.dumps({"type": "error", "msg": "Empty text."}))
                    continue
                messages.append({"role": "user", "content": user_text})
                await ws.send_text(json.dumps({"type": "transcript", "text": user_text}))

                provider, default_model = build_provider(provider_key)
                use_model = model or default_model
                await ws.send_text(json.dumps({"type": "status", "msg": "LLM streaming..."}))

                # Stream partial tokens
                assistant_text = ""
                async def stream_llm():
                    nonlocal assistant_text
                    for piece in provider.stream_chat(messages, model=use_model):
                        assistant_text += piece
                        await ws.send_text(json.dumps({"type": "partial", "text": piece}))

                await stream_llm()
                messages.append({"role": "assistant", "content": assistant_text})
                await ws.send_text(json.dumps({"type": "final", "text": assistant_text}))

                # TTS
                if tts_backend == "pyttsx3":
                    wav_bytes = tts_to_wav_bytes(assistant_text)
                    b64 = base64.b64encode(wav_bytes).decode("utf-8")
                    await ws.send_text(json.dumps({"type": "audio_chunk", "data": b64, "mime": "audio/wav"}))
                    await ws.send_text(json.dumps({"type": "audio_done"}))
                else:
                    await ws.send_text(json.dumps({"type": "info", "msg": f"TTS backend '{tts_backend}' not implemented in this demo; using 'pyttsx3' recommended."}))

                continue

            if data.get("type") == "user_audio":
                # Expect a single base64 webm chunk for simplicity
                b64 = data.get("data", "")
                if not b64:
                    await ws.send_text(json.dumps({"type": "error", "msg": "No audio data."}))
                    continue

                await ws.send_text(json.dumps({"type": "status", "msg": "Transcribing..."}))

                # Transcribe
                if asr_backend == "openai":
                    try:
                        user_text = transcribe_with_openai_base64(b64)
                    except Exception as e:
                        await ws.send_text(json.dumps({"type": "error", "msg": f"OpenAI ASR failed: {e}"}))
                        continue
                else:
                    # Save to temp and try local faster-whisper via ffmpeg conversion if needed
                    import tempfile, subprocess, os, base64
                    raw = base64.b64decode(b64)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
                        webm_path = f.name
                        f.write(raw)

                    # Convert to wav mono 16k using ffmpeg (must be installed)
                    wav_path = webm_path.replace(".webm", ".wav")
                    try:
                        subprocess.run(["ffmpeg", "-y", "-i", webm_path, "-ac", "1", "-ar", "16000", wav_path],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                    except Exception as e:
                        await ws.send_text(json.dumps({"type": "error", "msg": f"ffmpeg conversion failed: {e}"}))
                        continue

                    try:
                        user_text = transcribe_with_faster_whisper(wav_path, os.getenv("FASTER_WHISPER_MODEL", "base"))
                    except Exception as e:
                        await ws.send_text(json.dumps({"type": "error", "msg": f"Local ASR failed: {e}"}))
                        continue

                user_text = user_text.strip()
                if not user_text:
                    await ws.send_text(json.dumps({"type": "error", "msg": "ASR produced empty text."}))
                    continue

                await ws.send_text(json.dumps({"type": "transcript", "text": user_text}))
                messages.append({"role": "user", "content": user_text})

                # LLM streaming
                provider, default_model = build_provider(provider_key)
                use_model = model or default_model
                await ws.send_text(json.dumps({"type": "status", "msg": f"LLM streaming with {provider.name()} / {use_model} ..."}))

                assistant_text = ""
                for piece in provider.stream_chat(messages, model=use_model):
                    assistant_text += piece
                    await ws.send_text(json.dumps({"type": "partial", "text": piece}))

                messages.append({"role": "assistant", "content": assistant_text})
                await ws.send_text(json.dumps({"type": "final", "text": assistant_text}))

                # TTS
                if tts_backend == "pyttsx3":
                    wav_bytes = tts_to_wav_bytes(assistant_text)
                    b64out = base64.b64encode(wav_bytes).decode("utf-8")
                    await ws.send_text(json.dumps({"type": "audio_chunk", "data": b64out, "mime": "audio/wav"}))
                    await ws.send_text(json.dumps({"type": "audio_done"}))
                else:
                    await ws.send_text(json.dumps({"type": "info", "msg": f"TTS backend '{tts_backend}' not implemented in this demo; using 'pyttsx3' recommended."}))

                continue

            if data.get("type") == "reset":
                messages = [{"role": "system", "content": "You are a helpful assistant. Reply in the same language as the user."}]
                await ws.send_text(json.dumps({"type": "info", "msg": "Conversation reset."}))
                continue

            await ws.send_text(json.dumps({"type": "error", "msg": f"Unknown message type: {data.get('type')}"}))

    except WebSocketDisconnect:
        return
    except Exception as e:
        try:
            await ws.send_text(json.dumps({"type": "error", "msg": f"Server error: {e}"}))
        except Exception:
            pass
