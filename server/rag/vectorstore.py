import os, json, time
import numpy as np
import faiss
from typing import List, Dict, Tuple
from .embeddings import build_embedder, emb_space_id

def _paths():
    base = os.getenv("KB_DIR", "./kb")
    sid = emb_space_id()
    kb_dir = os.path.join(base, sid)
    os.makedirs(kb_dir, exist_ok=True)
    return kb_dir, os.path.join(kb_dir, "index.faiss"), os.path.join(kb_dir, "meta.json")

def _load_meta(meta_path: str) -> List[Dict]:
    if os.path.exists(meta_path):
        return json.load(open(meta_path, "r", encoding="utf-8"))
    return []

def _save_meta(meta_path: str, meta: List[Dict]):
    json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def load_index():
    kb_dir, idx_path, meta_path = _paths()
    meta = _load_meta(meta_path)
    if os.path.exists(idx_path):
        index = faiss.read_index(idx_path)
        return index, meta
    return None, meta

def save_index(index, meta):
    kb_dir, idx_path, meta_path = _paths()
    faiss.write_index(index, idx_path)
    _save_meta(meta_path, meta)

def add_docs(docs: List[Dict]) -> int:
    if not docs:
        return 0
    embedder = build_embedder()
    texts = [d["text"] for d in docs]
    vecs = embedder.embed(texts).astype("float32")
    dim = vecs.shape[1]
    index, meta = load_index()
    if index is None:
        index = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(vecs)
    index.add(vecs)
    for d in docs:
        meta.append({
            "source": d.get("source", ""),
            "meta": d.get("meta", {}),
            "text": d["text"],
            "ts": int(time.time())
        })
    save_index(index, meta)
    return len(docs)

def search(query: str, topk: int = 5) -> List[Dict]:
    embedder = build_embedder()
    qvec = embedder.embed([query]).astype("float32")
    faiss.normalize_L2(qvec)
    index, meta = load_index()
    if index is None or len(meta) == 0:
        return []
    D, I = index.search(qvec, min(topk, len(meta)))
    hits = []
    for score, idx in zip(D[0].tolist(), I[0].tolist()):
        if idx == -1:
            continue
        m = meta[idx]
        hits.append({"score": float(score), "text": m["text"], "source": m.get("source", ""), "meta": m.get("meta", {})})
    return hits
