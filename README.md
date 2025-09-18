# Voice LLM Starter v0.6（含知识库检索 / RAG）

一个开箱即用的语音对话演示，集成了：

- WebSocket 语音对话（ASR、LLM、TTS）
- 文档知识库检索（RAG）
- 多种 LLM/ASR/TTS Provider 扩展

## 快速开始

1. 安装依赖

   ```bash
   pip install -r requirements.txt
   ```

   运行本地语音识别时需要安装 `ffmpeg`。

2. 启动服务

   ```bash
   uvicorn server.main:app --reload
   ```

   启动后访问 <http://localhost:8000/web> 打开简单的 Web 演示界面。

## 功能概览

### 语音对话

- WebSocket `/ws` 支持文本或音频消息。
- ASR：支持 `faster_whisper`（本地）或 `openai`。
- TTS：默认 `pyttsx3`，将回答转换为音频返回。

### 知识库（RAG）

- `POST /api/kb/ingest` 上传文档并切分后存入向量库（FAISS）。
- `POST /api/kb/search` 在向量库中搜索相关片段。
- 在 `/ws` 或 `/api/chat` 中可通过参数启用知识库补全。

## 环境变量

可在根目录 `.env` 中配置：

- `DEFAULT_PROVIDER` / `DEFAULT_MODEL`
- `DEFAULT_ASR_BACKEND` / `DEFAULT_TTS_BACKEND`
- `KB_CHUNK_SIZE` / `KB_CHUNK_OVERLAP`
- `FASTER_WHISPER_MODEL` 等

### 调用阿里云 NPL 模型

1. 在 [DashScope](https://dashscope.aliyun.com/) 申请 API Key。
2. 在 `.env` 设置：

   ```env
   DEFAULT_PROVIDER=aliyun
   ALIYUN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
   ALIYUN_API_KEY=你的Key
   DEFAULT_MODEL=qwen-turbo
   ```

3. 重启服务后即可通过通义千问模型进行对话。

## 目录说明

- `server/`：FastAPI 服务端实现
- `web/`：前端演示页面

欢迎根据项目需求自行扩展 Provider 或 UI。
