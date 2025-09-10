import os, io, json, base64, tempfile, subprocess
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from server.providers.factory import build_provider
from server.asr.whisper_local import transcribe_with_faster_whisper
from server.asr.openai_whisper import transcribe_with_openai_base64
from server.tts.pyttsx3_tts import tts_to_wav_bytes
from server.rag.vectorstore import add_docs, search
from server.rag.ingest import build_docs_from_files

load_dotenv()

app = FastAPI(title="Voice LLM Starter v0.6 (RAG)", version="0.6")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "..", "web")
app.mount("/web", StaticFiles(directory=static_dir), name="web")

@app.get("/")
def root():
    return HTMLResponse(open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8").read())

@app.post("/api/kb/ingest")
async def kb_ingest(files: List[UploadFile] = File(default=[])):
    tmp_paths = []
    for f in files:
        suffix = os.path.splitext(f.filename)[1] or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as fp:
            content = await f.read()
            fp.write(content)
            tmp_paths.append(fp.name)
    chunk_size = int(os.getenv("KB_CHUNK_SIZE", "800"))
    chunk_overlap = int(os.getenv("KB_CHUNK_OVERLAP", "120"))
    docs = build_docs_from_files(tmp_paths, chunk_size, chunk_overlap)
    n = add_docs(docs)
    return {"ok": True, "added_chunks": n}

@app.post("/api/kb/search")
async def kb_search(payload: Dict[str, Any]):
    q = payload.get("q", "")
    topk = int(payload.get("topk", 5))
    return {"ok": True, "hits": search(q, topk)}

@app.post("/api/chat")
async def chat_api(payload: Dict[str, Any]):
    messages = payload.get("messages", [])
    provider_key = payload.get("provider", os.getenv("DEFAULT_PROVIDER", "aliyun"))
    model = payload.get("model", os.getenv("DEFAULT_MODEL", ""))
    use_kb = bool(payload.get("kb", False))
    kb_topk = int(payload.get("kb_topk", 4))

    if use_kb and messages:
        last_user = next((m for m in reversed(messages) if m.get("role") == "user"), None)
        if last_user:
            hits = search(last_user.get("content", ""), kb_topk)
            if hits:
                ctx = "\n\n".join([f"【片段{i+1} score={h['score']:.3f} 来自: {h['source']}】\n{h['text']}" for i,h in enumerate(hits)])
                messages = [{"role":"system","content": "你可以使用下面的知识库片段回答问题，尽量引用片段编号。"}] +                            [{"role":"system","content": ctx}] + messages

    provider, default_model = build_provider(provider_key)
    if not model:
        model = default_model
    text = ""
    for piece in provider.stream_chat(messages, model=model):
        text += piece
    return JSONResponse({"provider": provider.name(), "model": model, "text": text})

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": "You are a helpful assistant. Reply in the same language as the user."}
    ]

    provider_key = os.getenv("DEFAULT_PROVIDER", "aliyun")
    model = os.getenv("DEFAULT_MODEL", "qwen-turbo")
    asr_backend = os.getenv("DEFAULT_ASR_BACKEND", "faster_whisper")
    tts_backend = os.getenv("DEFAULT_TTS_BACKEND", "pyttsx3")
    kb_enabled = False
    kb_topk = 4

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)

            if data.get("type") == "config":
                provider_key = data.get("provider", provider_key)
                model = data.get("model", model)
                asr_backend = data.get("asr", asr_backend)
                tts_backend = data.get("tts", tts_backend)
                kb_enabled = bool(data.get("kb", kb_enabled))
                kb_topk = int(data.get("kb_topk", kb_topk))
                await ws.send_text(json.dumps({"type": "info", "msg": f"Config updated: provider={provider_key}, model={model}, asr={asr_backend}, tts={tts_backend}, kb={kb_enabled}, kb_topk={kb_topk}"}))
                continue

            if data.get("type") == "user_text":
                user_text = (data.get("text") or "").strip()
                if not user_text:
                    await ws.send_text(json.dumps({"type": "error", "msg": "Empty text."}))
                    continue
                messages.append({"role": "user", "content": user_text})
                await ws.send_text(json.dumps({"type": "transcript", "text": user_text}))

                local_messages = messages[:]
                if kb_enabled:
                    hits = search(user_text, kb_topk)
                    if hits:
                        ctx = "\n\n".join([f"【片段{i+1} score={h['score']:.3f} 来自: {h['source']}】\n{h['text']}" for i,h in enumerate(hits)])
                        local_messages = [{"role":"system","content": "你可以使用下面的知识库片段回答问题，尽量引用片段编号。"}] +                                          [{"role":"system","content": ctx}] + local_messages

                provider, default_model = build_provider(provider_key)
                use_model = model or default_model
                await ws.send_text(json.dumps({"type": "status", "msg": "LLM streaming..."}))

                assistant_text = ""
                for piece in provider.stream_chat(local_messages, model=use_model):
                    assistant_text += piece
                    await ws.send_text(json.dumps({"type": "partial", "text": piece}))

                messages.append({"role": "assistant", "content": assistant_text})
                await ws.send_text(json.dumps({"type": "final", "text": assistant_text}))

                if tts_backend == "pyttsx3":
                    wav = tts_to_wav_bytes(assistant_text)
                    b64 = base64.b64encode(wav).decode("utf-8")
                    await ws.send_text(json.dumps({"type": "audio_chunk", "data": b64, "mime": "audio/wav"}))
                    await ws.send_text(json.dumps({"type": "audio_done"}))
                continue

            if data.get("type") == "user_audio":
                b64 = data.get("data", "")
                if not b64:
                    await ws.send_text(json.dumps({"type": "error", "msg": "No audio data."}))
                    continue

                await ws.send_text(json.dumps({"type": "status", "msg": "Transcribing..."}))
                if asr_backend == "openai":
                    try:
                        user_text = transcribe_with_openai_base64(b64)
                    except Exception as e:
                        await ws.send_text(json.dumps({"type": "error", "msg": f"OpenAI ASR failed: {e}"}))
                        continue
                else:
                    raw = base64.b64decode(b64)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
                        f.write(raw)
                        webm = f.name
                    wav = webm.replace(".webm", ".wav")
                    try:
                        subprocess.run(["ffmpeg", "-y", "-i", webm, "-ac", "1", "-ar", "16000", wav],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                    except Exception as e:
                        await ws.send_text(json.dumps({"type": "error", "msg": f"ffmpeg conversion failed: {e}"}))
                        continue
                    try:
                        user_text = transcribe_with_faster_whisper(wav, os.getenv("FASTER_WHISPER_MODEL", "base"))
                    except Exception as e:
                        await ws.send_text(json.dumps({"type": "error", "msg": f"Local ASR failed: {e}"}))
                        continue

                user_text = (user_text or "").strip()
                if not user_text:
                    await ws.send_text(json.dumps({"type": "error", "msg": "ASR produced empty text."}))
                    continue

                await ws.send_text(json.dumps({"type": "transcript", "text": user_text}))
                messages.append({"role": "user", "content": user_text})

                local_messages = messages[:]
                if kb_enabled:
                    hits = search(user_text, kb_topk)
                    if hits:
                        ctx = "\n\n".join([f"【片段{i+1} score={h['score']:.3f} 来自: {h['source']}】\n{h['text']}" for i,h in enumerate(hits)])
                        local_messages = [{"role":"system","content": "你可以使用下面的知识库片段回答问题，尽量引用片段编号。"}] +                                          [{"role":"system","content": ctx}] + local_messages

                provider, default_model = build_provider(provider_key)
                use_model = model or default_model
                await ws.send_text(json.dumps({"type": "status", "msg": f"LLM streaming with {provider.name()} / {use_model} ..."}))

                assistant_text = ""
                for piece in provider.stream_chat(local_messages, model=use_model):
                    assistant_text += piece
                    await ws.send_text(json.dumps({"type": "partial", "text": piece}))

                messages.append({"role": "assistant", "content": assistant_text})
                await ws.send_text(json.dumps({"type": "final", "text": assistant_text}))

                if tts_backend == "pyttsx3":
                    wav = tts_to_wav_bytes(assistant_text)
                    b64out = base64.b64encode(wav).decode("utf-8")
                    await ws.send_text(json.dumps({"type": "audio_chunk", "data": b64out, "mime": "audio/wav"}))
                    await ws.send_text(json.dumps({"type": "audio_done"}))
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
