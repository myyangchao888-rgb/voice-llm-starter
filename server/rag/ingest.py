import os
from typing import List, Dict
from pypdf import PdfReader

def read_text_from_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in [".txt", ".md", ".markdown"]:
        return open(path, "r", encoding="utf-8", errors="ignore").read()
    if ext == ".pdf":
        txt = []
        try:
            reader = PdfReader(path)
            for p in reader.pages:
                txt.append(p.extract_text() or "")
            return "\n".join(txt)
        except Exception:
            return ""
    try:
        return open(path, "r", encoding="utf-8", errors="ignore").read()
    except Exception:
        return ""

def simple_chunks(text: str, size: int, overlap: int) -> List[str]:
    text = text.strip().replace("\r\n", "\n").replace("\r", "\n")
    if not text:
        return []
    out = []
    i = 0
    n = len(text)
    while i < n:
        out.append(text[i:i+size])
        i += max(1, size - overlap)
    return out

def build_docs_from_files(files: List[str], chunk_size: int, chunk_overlap: int) -> List[Dict]:
    docs = []
    for f in files:
        content = read_text_from_file(f)
        if not content:
            continue
        chunks = simple_chunks(content, chunk_size, chunk_overlap)
        for j, ch in enumerate(chunks):
            docs.append({"text": ch, "source": os.path.basename(f), "meta": {"chunk_id": j}})
    return docs
