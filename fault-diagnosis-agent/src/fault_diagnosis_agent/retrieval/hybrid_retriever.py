from __future__ import annotations

import json
import re
from pathlib import Path

from fault_diagnosis_agent.models import FaultKnowledgeItem
from fault_diagnosis_agent.retrieval.entity_extractor import FaultEntityExtractor
from fault_diagnosis_agent.retrieval.fault_types import classify_fault_type

try:
    import jieba
    from rank_bm25 import BM25Okapi
except Exception:  # pragma: no cover - optional dependency fallback
    jieba = None
    BM25Okapi = None


class FaultHybridRetriever:
    """Rule + lexical retrieval for fault procedures.

    It intentionally stays local and deterministic so the service can run before a
    vector database is connected. Qdrant or embedding retrieval can be added behind
    the same retrieve() interface later.
    """

    def __init__(self, knowledge_path: str | Path):
        self.knowledge_path = Path(knowledge_path)
        self.items = self._load_items()
        self.entity_extractor = FaultEntityExtractor()
        self._tokenized = [self._tokenize(item.searchable_text()) for item in self.items]
        self._bm25 = BM25Okapi(self._tokenized) if BM25Okapi and self._tokenized else None

    def retrieve(self, query: str, k: int = 5) -> tuple[list[tuple[FaultKnowledgeItem, float]], dict[str, str | None]]:
        entities = self.entity_extractor.extract(query)
        fault_type = classify_fault_type(query)
        query_tokens = self._tokenize(query)
        bm25_scores = self._bm25.get_scores(query_tokens) if self._bm25 else [0.0] * len(self.items)

        scored: list[tuple[FaultKnowledgeItem, float]] = []
        for idx, item in enumerate(self.items):
            score = float(bm25_scores[idx]) if idx < len(bm25_scores) else 0.0
            if fault_type != "unknown" and item.fault_type == fault_type:
                score += 20.0
            if entities.get("device") and entities["device"] in item.searchable_text():
                score += 6.0
            if entities.get("indicator") and entities["indicator"] in item.searchable_text():
                score += 4.0
            if entities.get("condition") and entities["condition"] in item.searchable_text():
                score += 4.0
            score += self._overlap_score(query, item.searchable_text())
            if score > 0:
                scored.append((item, score))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k], entities

    def _load_items(self) -> list[FaultKnowledgeItem]:
        if not self.knowledge_path.exists():
            return []
        data = json.loads(self.knowledge_path.read_text(encoding="utf-8"))
        return [FaultKnowledgeItem.model_validate(item) for item in data]

    def _tokenize(self, text: str) -> list[str]:
        if jieba:
            return [token.strip() for token in jieba.lcut(text) if token.strip()]
        return re.findall(r"[\w\u4e00-\u9fff]+", text)

    def _overlap_score(self, query: str, text: str) -> float:
        query_terms = set(self._tokenize(query))
        text_terms = set(self._tokenize(text))
        return float(len(query_terms & text_terms))

