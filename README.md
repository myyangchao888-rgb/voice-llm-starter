# Voice LLM Starter v0.5

一个可直接运行的“基于 HTML 的实时语音交互对话”项目模板：
- 后端：FastAPI + WebSocket
- 前端：纯 HTML / JS
- 模型：可在 **阿里云 DashScope（OpenAI 兼容模式）**、**OpenAI**、**Ollama/LM Studio（本地）** 之间切换
- 语音：麦克风录音（WebM/Opus）→ ASR（本地 faster-whisper 或 OpenAI Whisper）→ LLM 流式文本 → 本地 TTS（pyttsx3）→ 浏览器播放 WAV

> “实时”在此以近实时为主：当前示例采用“说完即上传”的方式做 ASR，LLM 文本是流式输出，TTS 生成后以 WAV 回放。你也可以扩展为**音频分片+VAD+双向流式**，实现更低延迟。

## 快速开始

1. Python 3.10+ 环境；系统需安装 `ffmpeg`（ASR 的 webm→wav 转码）。
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 复制 `.env.example` 为 `.env` 并填入你的 Key：
   - `ALIYUN_API_KEY`：阿里云 DashScope 的 API Key（OpenAI 兼容模式）
   - `OPENAI_API_KEY`：OpenAI API Key（如需）
   - 本地 `Ollama/LM Studio` 不严格校验 Key，可随意填写占位符
4. 运行：
   ```bash
   uvicorn server.main:app --host 0.0.0.0 --port 8080 --reload
   ```
5. 打开浏览器访问：`http://localhost:8080/`

## 使用说明

- 页面右上角可切换 Provider / Model / ASR / TTS；点击“应用设置”后生效。
- 文本对话：在输入框输入消息并发送；
- 语音对话：点击“🎤”开始录音，再次点击结束并发送；
- 返回内容：
  - `transcript`：识别出的用户文本；
  - `partial`：LLM 的流式片段；
  - `final`：LLM 完整回复；
  - `audio_chunk`：TTS 生成的一段 WAV（当前为一次性返回整段）。

## 切换模型

后端通过 **OpenAI 兼容**的 Chat Completions 接口统一调用：
- Aliyun（DashScope 兼容模式）：`ALIYUN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`
- OpenAI：`https://api.openai.com/v1`
- Ollama（本地）：`http://localhost:11434/v1`
- LM Studio（本地）：`http://localhost:1234/v1`

> 选择不同 Provider 后，请在“Model”框中填入相应模型名（例如：`qwen-turbo`、`gpt-4o-mini`、`llama3.1:8b-instruct-q4_K_M` 等）。

## ASR 后端

- `faster_whisper`（默认）：本地识别，需要安装 `ffmpeg`，首次运行会下载模型（`FASTER_WHISPER_MODEL`）
- `openai`：云端识别（Whisper API）

> 如果你希望用 **阿里云 NLS 实时 ASR**，可在 `server/asr/` 新增一个 Aliyun WebSocket ASR 模块，并在 `/ws` 分支里按需选择。

## TTS 后端

- `pyttsx3`（默认）：本地离线 TTS，简单可靠。
- 你也可以扩展 `server/tts/`，比如接入 Aliyun TTS 或 `edge-tts`，并在前端下拉中加入选项。

## 架构与扩展点

```
web/               # 前端：index.html + app.js + style.css
server/
  main.py          # FastAPI + WebSocket，协议：config/user_text/user_audio/reset
  providers/
    base.py        # Provider 抽象
    openai_compatible.py # OpenAI 兼容 Provider（Aliyun/OpenAI/Ollama/LM Studio 通用）
    factory.py     # 统一创建 Provider + 默认模型
  asr/
    whisper_local.py     # faster-whisper 本地识别
    openai_whisper.py    # OpenAI Whisper 识别
  tts/
    pyttsx3_tts.py       # 本地 TTS
.env.example       # 配置模板
requirements.txt
```

### 协议（WebSocket `/ws`）

- 下发配置：`{type: "config", provider, model, asr, tts}`
- 文本消息：`{type: "user_text", text}`
- 语音消息：`{type: "user_audio", data: "<base64 webm>"}`
- 重置会话：`{type: "reset"}`

服务端回包：
- `info/status/error`：状态提示
- `transcript`：ASR 文本
- `partial`：LLM 流式片段
- `final`：LLM 完整文本
- `audio_chunk`：Base64 WAV
- `audio_done`：音频流结束

## 常见问题

- **DashScope 403 或 401**：检查 `.env` 的 `ALIYUN_API_KEY`；并确认 `ALIYUN_BASE_URL` 填的是 **兼容模式** URL。
- **Ollama / LM Studio 无响应**：确认本地服务已启动，端口无冲突；模型已拉取/加载。
- **ASR 提示 ffmpeg 失败**：请先安装 ffmpeg，并确保命令行可调用。
- **faster-whisper 未安装**：注释掉 `requirements.txt` 里该项或切换到 `openai` ASR。

## 许可证

MIT
