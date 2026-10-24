import re
import unicodedata
from pathlib import Path

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "ner_model"
_TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)

_tok = None
_model = None


def _load():
    global _tok, _model
    if _model is None:
        _tok = AutoTokenizer.from_pretrained(MODEL_DIR)
        _model = AutoModelForTokenClassification.from_pretrained(MODEL_DIR)
        _model.eval()
    return _tok, _model


def extract_entities(text: str) -> list[dict]:
    """Trả về danh sách {"text": ..., "label": ...} theo thứ tự xuất hiện."""
    tok, model = _load()
    text = unicodedata.normalize("NFC", text)
    tokens = _TOKEN_RE.findall(text)
    if not tokens:
        return []

    enc = tok(tokens, is_split_into_words=True, truncation=True,
              max_length=128, return_tensors="pt")
    with torch.no_grad():
        pred = model(**enc).logits[0].argmax(-1).tolist()

    tags = ["O"] * len(tokens)
    prev = None
    for idx, w in enumerate(enc.word_ids(0)):
        if w is not None and w != prev:
            tags[w] = model.config.id2label[pred[idx]]
        prev = w

    entities, start, cur = [], None, None
    for i, t in enumerate(tags + ["O"]):
        if start is not None and (t == "O" or t.startswith("B-") or t[2:] != cur):
            entities.append({"text": " ".join(tokens[start:i]), "label": cur})
            start, cur = None, None
        if t.startswith("B-") or (t.startswith("I-") and start is None):
            start, cur = i, t[2:]
    return entities