"""
kb.py — Knowledge base loader and solution retrieval.

Uses simple keyword overlap scoring (no external vector DB needed).
The LLM in the Solution Mapper Agent makes the final selection.
"""
import json
import re
from typing import List, Dict, Any
import config


_KB: List[Dict[str, Any]] | None = None


def _load() -> List[Dict[str, Any]]:
    global _KB
    if _KB is None:
        with open(config.KB_FILE, "r", encoding="utf-8") as f:
            _KB = json.load(f)
    return _KB


def _score(entry: Dict, text: str) -> float:
    """Score a KB entry against requirement text using keyword overlap."""
    text_lower = text.lower()
    keywords: List[str] = entry.get("keywords", [])
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    return hits / len(keywords)


def retrieve_top(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Return top-k KB entries most relevant to the query string."""
    kb = _load()
    scored = [(entry, _score(entry, query)) for entry in kb]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [entry for entry, score in scored[:top_k] if score > 0] or [scored[0][0]]


def get_all() -> List[Dict[str, Any]]:
    return _load()


def feature_group_lookup(feature_group: str) -> Dict[str, Any] | None:
    """Exact match on feature_group field."""
    kb = _load()
    for entry in kb:
        if entry["feature_group"].lower() == feature_group.lower():
            return entry
    return None
