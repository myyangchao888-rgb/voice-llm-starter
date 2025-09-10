import os, hashlib
import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer
from openai import OpenAI

def _l2_normalize(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True) + 1e-12
    return x / n

class LocalEmbeddings:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]) -> np.ndarray:
        embs = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(embs, dtype=np.float32)

class OpenAICompatEmbeddings:
    def __init__(self, base_url: str, api_key: str, model_name: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model_name = model_name

    def embed(self, texts: List[str]) -> np.ndarray:
        out = []
        step = 1000
        for i in range(0, len(texts), step):
            chunk = texts[i:i+step]
            resp = self.client.embeddings.create(model=self.model_name, input=chunk)
            vecs = [d.embedding for d in resp.data]
            out.extend(vecs)
        arr = np.asarray(out, dtype=np.float32)
        return _l2_normalize(arr)

def build_embedder():
    backend = os.getenv("EMBEDDING_BACKEND", "local").lower()
    if backend == "openai_compat":
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("ALIYUN_BASE_URL")
        api = os.getenv("OPENAI_API_KEY") or os.getenv("ALIYUN_API_KEY", "")
        model = os.getenv("EMBED_MODEL_OPENAI_COMPAT", "text-embedding-3-small")
        return OpenAICompatEmbeddings(base_url, api, model)
    model = os.getenv("EMBED_MODEL_LOCAL", "BAAI/bge-small-zh-v1.5")
    return LocalEmbeddings(model)

def emb_space_id() -> str:
    backend = os.getenv("EMBEDDING_BACKEND", "local").lower()
    local_model = os.getenv("EMBED_MODEL_LOCAL", "BAAI/bge-small-zh-v1.5")
    compat_model = os.getenv("EMBED_MODEL_OPENAI_COMPAT", "text-embedding-3-small")
    key = f"{backend}:{local_model}:{compat_model}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:8]
