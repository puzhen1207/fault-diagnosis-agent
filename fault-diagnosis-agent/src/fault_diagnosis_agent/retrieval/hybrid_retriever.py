from __future__ import annotations

import json
import re
from pathlib import Path

from fault_diagnosis_agent.models import (
    DocumentScoreBreakdown,
    FaultKnowledgeItem,
    KnowledgeBaseStats,
    RetrievalTrace,
)
from fault_diagnosis_agent.retrieval.entity_extractor import FaultEntityExtractor
from fault_diagnosis_agent.retrieval.fault_types import classify_fault_type_with_trace

try:
    import jieba
    from rank_bm25 import BM25Okapi
except Exception:  # pragma: no cover - optional dependency fallback
    jieba = None
    BM25Okapi = None


class FaultHybridRetriever:
    """规则 + 词法检索的混合检索器。

    支持两种接口：
    - retrieve(query, k) -> (scored_items, entities_dict)  （向后兼容）
    - retrieve_with_trace(query, k) -> (scored_items, entities_dict, RetrievalTrace)
    - get_kb_stats() -> KnowledgeBaseStats
    """

    def __init__(self, knowledge_path: str | Path):
        self.knowledge_path = Path(knowledge_path)
        self.items = self._load_items()
        self.entity_extractor = FaultEntityExtractor()
        self._tokenized = [self._tokenize(item.searchable_text()) for item in self.items]
        self._bm25 = BM25Okapi(self._tokenized) if BM25Okapi and self._tokenized else None

    # ---- 向后兼容接口 --------------------------------------------------------
    def retrieve(
        self, query: str, k: int = 5
    ) -> tuple[list[tuple[FaultKnowledgeItem, float]], dict[str, str | None]]:
        """返回 (top-k 列表, entities 字典)，保持与原签名完全一致。"""
        scored, entities, _trace = self.retrieve_with_trace(query, k)
        return scored, entities

    # ---- 带追踪接口 ----------------------------------------------------------
    def retrieve_with_trace(
        self, query: str, k: int = 5
    ) -> tuple[
        list[tuple[FaultKnowledgeItem, float]],
        dict[str, str | None],
        RetrievalTrace,
    ]:
        """执行检索并返回完整的 RetrievalTrace，用于可视化。"""
        entity_trace = self.entity_extractor.extract_with_trace(query)
        entities = entity_trace.result
        fault_type, _ft_trace = classify_fault_type_with_trace(query)

        query_tokens = self._tokenize(query)
        bm25_scores = (
            self._bm25.get_scores(query_tokens)
            if self._bm25
            else [0.0] * len(self.items)
        )

        entity_match_debug: dict[str, str] = {
            key: value for key, value in [
                ("device", entities.get("device") or ""),
                ("indicator", entities.get("indicator") or ""),
                ("condition", entities.get("condition") or ""),
            ] if value
        }

        scored_items: list[tuple[FaultKnowledgeItem, float]] = []
        documents: list[DocumentScoreBreakdown] = []

        for idx, item in enumerate(self.items):
            bm25 = float(bm25_scores[idx]) if idx < len(bm25_scores) else 0.0

            fault_type_match = 20.0 if (
                fault_type != "unknown" and item.fault_type == fault_type
            ) else 0.0

            item_text = item.searchable_text()
            device_match = 6.0 if entities.get("device") and entities["device"] in item_text else 0.0
            indicator_match = 4.0 if entities.get("indicator") and entities["indicator"] in item_text else 0.0
            condition_match = 4.0 if entities.get("condition") and entities["condition"] in item_text else 0.0
            overlap = float(self._overlap_score(query, item_text))

            final_score = bm25 + fault_type_match + device_match + indicator_match + condition_match + overlap

            documents.append(
                DocumentScoreBreakdown(
                    doc_id=item.id,
                    title=item.title,
                    device=item.device,
                    indicator=item.indicator,
                    condition=item.condition,
                    bm25_score=round(bm25, 4),
                    fault_type_match_score=fault_type_match,
                    device_match_score=device_match,
                    indicator_match_score=indicator_match,
                    condition_match_score=condition_match,
                    overlap_score=round(overlap, 4),
                    final_score=round(final_score, 4),
                )
            )
            scored_items.append((item, final_score))

        # 降序排序
        scored_items.sort(key=lambda pair: pair[1], reverse=True)
        documents_sorted = sorted(documents, key=lambda d: d.final_score, reverse=True)

        top_k_results = documents_sorted[: max(k, 0)]
        top_k_scored = scored_items[: max(k, 0)]

        trace = RetrievalTrace(
            query_tokens=query_tokens,
            top_k=k,
            entity_match_debug=entity_match_debug,
            documents=documents_sorted,
            top_results=top_k_results,
        )
        return top_k_scored, entities, trace

    # ---- 知识库统计 ----------------------------------------------------------
    def get_kb_stats(self) -> KnowledgeBaseStats:
        """返回知识库的整体统计信息（设备/指标/条件分布、平均步骤数等）。"""
        total_items = len(self.items)
        device_dist: dict[str, int] = {}
        fault_type_dist: dict[str, int] = {}
        indicator_dist: dict[str, int] = {}
        condition_dist: dict[str, int] = {}
        total_steps = 0
        total_aliases = 0
        total_tokens = 0

        for item in self.items:
            device_dist[item.device or "(空)"] = device_dist.get(item.device or "(空)", 0) + 1
            fault_type_dist[item.fault_type] = fault_type_dist.get(item.fault_type, 0) + 1
            indicator_dist[item.indicator or "(空)"] = indicator_dist.get(item.indicator or "(空)", 0) + 1
            condition_dist[item.condition or "(空)"] = condition_dist.get(item.condition or "(空)", 0) + 1
            total_steps += len(item.steps)
            total_aliases += len(item.aliases)
            total_tokens += len(self._tokenize(item.searchable_text()))

        sample_items = [
            {
                "id": item.id,
                "title": item.title,
                "device": item.device,
                "indicator": item.indicator,
                "condition": item.condition,
            }
            for item in self.items[:5]
        ]

        return KnowledgeBaseStats(
            total_items=total_items,
            kb_path=str(self.knowledge_path),
            device_distribution=device_dist,
            fault_type_distribution=fault_type_dist,
            indicator_distribution=indicator_dist,
            condition_distribution=condition_dist,
            avg_steps_per_item=round(total_steps / total_items, 2) if total_items else 0.0,
            avg_aliases_per_item=round(total_aliases / total_items, 2) if total_items else 0.0,
            total_tokens=total_tokens,
            sample_items=sample_items,
        )

    # ---- 内部辅助 ------------------------------------------------------------
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
