const log = document.getElementById('log');
const input = document.getElementById('text');
const sendBtn = document.getElementById('send');
const recordBtn = document.getElementById('record');
const applyBtn = document.getElementById('apply');
const resetBtn = document.getElementById('reset');
const providerSel = document.getElementById('provider');
const modelInput = document.getElementById('model');
const asrSel = document.getElementById('asr');
const ttsSel = document.getElementById('tts');
const kbChk = document.getElementById('kb');
const kbTopkInput = document.getElementById('kb_topk');
const filesInput = document.getElementById('files');
const ingestBtn = document.getElementById('ingest');
const ingestStatus = document.getElementById('ingest-status');
const player = document.getElementById('player');

let ws;
let mediaRecorder;
let chunks = [];
let currentBotDiv = null;

function ensureWS() {
  if (ws && ws.readyState === WebSocket.OPEN) return;
  ws = new WebSocket(`${location.origin.replace('http', 'ws')}/ws`);
  ws.addEventListener('message', (evt) => {
    const data = JSON.parse(evt.data);
    if (data.type === 'info' || data.type === 'status') {
      addMsg('系统', data.msg, 'info');
    } else if (data.type === 'error') {
      addMsg('错误', data.msg, 'info');
    } else if (data.type === 'transcript') {
      addMsg('我', data.text, 'user');
    } else if (data.type === 'partial') {
      appendBotPartial(data.text);
    } else if (data.type === 'final') {
      finishBotMessage(data.text);
    } else if (data.type === 'audio_chunk') {
      const b64 = data.data;
      const buf = base64ToArrayBuffer(b64);
      const blob = new Blob([buf], { type: data.mime || 'audio/wav' });
      const url = URL.createObjectURL(blob);
      player.src = url;
      player.play();
    }
  });
}

function addMsg(who, text, cls='bot') {
  const div = document.createElement('div');
  div.className = `msg ${cls}`;
  div.textContent = `${who}: ${text}`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function appendBotPartial(text) {
  if (!currentBotDiv) {
    currentBotDiv = document.createElement('div');
    currentBotDiv.className = 'msg bot';
    currentBotDiv.textContent = '助手: ';
    log.appendChild(currentBotDiv);
  }
  currentBotDiv.textContent += text;
  log.scrollTop = log.scrollHeight;
}

function finishBotMessage(finalText) {
  if (!currentBotDiv) appendBotPartial('');
  currentBotDiv.textContent = '助手: ' + finalText;
  currentBotDiv = null;
  log.scrollTop = log.scrollHeight;
}

function base64ToArrayBuffer(base64) {
  const binary_string = window.atob(base64);
  const len = binary_string.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) bytes[i] = binary_string.charCodeAt(i);
  return bytes.buffer;
}

applyBtn.addEventListener('click', () => {
  ensureWS();
  const msg = {
    type: 'config',
    provider: providerSel.value,
    model: modelInput.value || undefined,
    asr: asrSel.value,
    tts: ttsSel.value,
    kb: kbChk.checked,
    kb_topk: Number(kbTopkInput.value || 4)
  };
  ws.send(JSON.stringify(msg));
});

sendBtn.addEventListener('click', () => {
  ensureWS();
  const text = input.value.trim();
  if (!text) return;
  ws.send(JSON.stringify({ type: 'user_text', text }));
  input.value = '';
});

input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendBtn.click();
});

resetBtn.addEventListener('click', () => {
  ensureWS();
  ws.send(JSON.stringify({ type: 'reset' }));
});

recordBtn.addEventListener('click', async () => {
  ensureWS();
  if (!mediaRecorder || mediaRecorder.state === 'inactive') {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    chunks = [];
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
    mediaRecorder.onstop = async () => {
      const blob = new Blob(chunks, { type: 'audio/webm' });
      const b64 = await blobToBase64(blob);
      ws.send(JSON.stringify({ type: 'user_audio', data: b64 }));
      chunks = [];
    };
    mediaRecorder.start();
    recordBtn.textContent = '■ 结束录音';
  } else {
    mediaRecorder.stop();
    recordBtn.textContent = '🎤 按一下开始/结束';
  }
});

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      resolve(dataUrl.split(',')[1]);
    };
    reader.onerror = (err) => reject(err);
    reader.readAsDataURL(blob);
  });
}

ingestBtn.addEventListener('click', async () => {
  const files = filesInput.files;
  if (!files || files.length === 0) {
    ingestStatus.textContent = '请选择文件';
    return;
  }
  const form = new FormData();
  for (const f of files) form.append('files', f, f.name);
  ingestStatus.textContent = '上传中...';
  try {
    const resp = await fetch('/api/kb/ingest', { method: 'POST', body: form });
    const data = await resp.json();
    if (data.ok) ingestStatus.textContent = `已导入分片：${data.added_chunks}`;
    else ingestStatus.textContent = '导入失败';
  } catch (e) {
    ingestStatus.textContent = '网络错误';
  }
});

// init
ensureWS();
