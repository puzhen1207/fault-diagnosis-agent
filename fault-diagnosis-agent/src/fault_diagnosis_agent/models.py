from __future__ import annotations

from typing import Any

try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover - lets core scripts run before dependencies are installed
    class _FieldInfo:
        def __init__(self, default: Any = None, default_factory: Any = None, **_: Any) -> None:
            self.default = default
            self.default_factory = default_factory

        def value(self) -> Any:
            if self.default_factory:
                return self.default_factory()
            return self.default

    def Field(default: Any = None, **kwargs: Any) -> Any:
        return _FieldInfo(default=default, **kwargs)

    class BaseModel:
        def __init__(self, **data: Any) -> None:
            annotations = getattr(self, "__annotations__", {})
            for key in annotations:
                default = getattr(self.__class__, key, None)
                if key in data:
                    value = data[key]
                elif isinstance(default, _FieldInfo):
                    value = default.value()
                else:
                    value = default
                setattr(self, key, value)

        @classmethod
        def model_validate(cls, data: dict[str, Any]) -> "BaseModel":
            return cls(**data)

        def model_dump(self) -> dict[str, Any]:
            result = {}
            for key in getattr(self, "__annotations__", {}):
                value = getattr(self, key)
                if isinstance(value, list):
                    result[key] = [item.model_dump() if hasattr(item, "model_dump") else item for item in value]
                elif hasattr(value, "model_dump"):
                    result[key] = value.model_dump()
                else:
                    result[key] = value
            return result


class DiagnoseRequest(BaseModel):
    query: str = Field(..., min_length=1, description="自然语言故障描述")
    session_id: str = Field(default="default", description="会话 ID，用于多轮诊断")
    top_k: int = Field(default=5, ge=1, le=10)


class Reference(BaseModel):
    id: str
    title: str
    fault_type: str
    score: float = 0.0


class DiagnoseResponse(BaseModel):
    answer: str
    root_cause: str
    steps: list[str]
    risk: str
    fault_type: str
    entities: dict[str, Any]
    need_more_info: bool = False
    missing_info: str = ""
    references: list[Reference] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    session_id: str
    query: str
    answer: str
    rating: int = Field(..., ge=1, le=5)
    comment: str = ""


class KnowledgeStep(BaseModel):
    step_id: str
    text: str
    source: str = ""


class FaultKnowledgeItem(BaseModel):
    id: str
    title: str
    fault_type: str
    type: str = "fault_procedure"
    device: str = ""
    indicator: str = ""
    condition: str = ""
    aliases: list[str] = Field(default_factory=list)
    root_causes: list[str] = Field(default_factory=list)
    steps: list[KnowledgeStep] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "FaultKnowledgeItem":
        payload = dict(data)
        payload["steps"] = [
            step if isinstance(step, KnowledgeStep) else KnowledgeStep(**step)
            for step in payload.get("steps", [])
        ]
        return cls(**payload)

    def searchable_text(self) -> str:
        parts = [
            self.title,
            self.fault_type,
            self.device,
            self.indicator,
            self.condition,
            " ".join(self.aliases),
            " ".join(self.root_causes),
            " ".join(step.text for step in self.steps),
            " ".join(self.risks),
            self.content,
        ]
        return "\n".join(part for part in parts if part)


# ---------------------------------------------------------------------------
# RAG 全链路追踪相关模型（新增）
# ---------------------------------------------------------------------------


class EntityExtractionTrace(BaseModel):
    """实体提取过程记录：记录用户查询及各槽位匹配到的原文。"""

    raw_query: str
    device_match: str | None = None
    indicator_match: str | None = None
    condition_match: str | None = None
    threshold_match: str | None = None
    result: dict[str, str | None] = Field(default_factory=dict)


class FaultTypeCandidate(BaseModel):
    """单个候选故障类型打分结果。"""

    fault_type: str
    label: str = ""
    matched_keywords: list[str] = Field(default_factory=list)
    keyword_score: float = 0.0
    heuristic_applied: bool = False


class FaultClassificationTrace(BaseModel):
    """故障类型分类过程记录。"""

    normalized: str = ""
    candidates: list[FaultTypeCandidate] = Field(default_factory=list)
    fallback_applied: bool = False
    all_candidates: list[FaultTypeCandidate] = Field(default_factory=list)
    selected_fault_type: str = "unknown"
    heuristic_applied: bool = False


class DocumentScoreBreakdown(BaseModel):
    """单条知识的打分明细（用于检索链路可视化）。"""

    doc_id: str = ""
    title: str = ""
    device: str = ""
    indicator: str = ""
    condition: str = ""
    bm25_score: float = 0.0
    fault_type_match_score: float = 0.0
    device_match_score: float = 0.0
    indicator_match_score: float = 0.0
    condition_match_score: float = 0.0
    overlap_score: float = 0.0
    final_score: float = 0.0


class RetrievalTrace(BaseModel):
    """检索过程记录。"""

    query_tokens: list[str] = Field(default_factory=list)
    top_k: int = 5
    entity_match_debug: dict[str, str] = Field(default_factory=dict)
    documents: list[DocumentScoreBreakdown] = Field(default_factory=list)
    top_results: list[DocumentScoreBreakdown] = Field(default_factory=list)


class ReasoningTrace(BaseModel):
    """推理过程记录。"""

    selected_primary_doc_title: str = ""
    selected_primary_doc_id: str = ""
    root_causes_used: list[str] = Field(default_factory=list)
    assembled_root_cause: str = ""
    llm_attempted: bool = False
    llm_used: bool = False
    llm_output_if_any: str | None = None


class SolutionTrace(BaseModel):
    """方案生成过程记录。"""

    primary_doc_title: str = ""
    primary_doc_id: str = ""
    steps_from_kb: list[dict[str, Any]] = Field(default_factory=list)
    validated_steps: list[str] = Field(default_factory=list)
    steps_filtered_by_verb_check: int = 0
    risk: str = ""


class FinalAnswerTrace(BaseModel):
    """最终答案组装记录。"""

    root_cause_final: str = ""
    solution_steps_final: list[str] = Field(default_factory=list)
    risk_final: str = ""
    reference_title: str = ""
    reference_score: float = 0.0
    final_markdown: str = ""


class RAGPipelineTrace(BaseModel):
    """完整 RAG 管线记录（一次诊断请求的完整追踪数据）。"""

    query: str = ""
    session_id: str = "default"
    started_at: str = ""
    finished_at: str = ""
    duration_ms: float = 0.0
    entities: EntityExtractionTrace | None = None
    fault_classification: FaultClassificationTrace | None = None
    retrieval: RetrievalTrace | None = None
    reasoning: ReasoningTrace | None = None
    solution: SolutionTrace | None = None
    final_answer: FinalAnswerTrace | None = None
    kb_stats: dict[str, Any] = Field(default_factory=dict)


class KnowledgeBaseStats(BaseModel):
    """知识库统计信息（用于 /kb/stats 接口与可视化）。"""

    total_items: int = 0
    kb_path: str = ""
    device_distribution: dict[str, int] = Field(default_factory=dict)
    fault_type_distribution: dict[str, int] = Field(default_factory=dict)
    indicator_distribution: dict[str, int] = Field(default_factory=dict)
    condition_distribution: dict[str, int] = Field(default_factory=dict)
    avg_steps_per_item: float = 0.0
    avg_aliases_per_item: float = 0.0
    total_tokens: int = 0
    sample_items: list[dict[str, Any]] = Field(default_factory=list)


class DiagnoseTraceResponse(BaseModel):
    """带 RAG 链路追踪的完整诊断响应。"""

    trace: RAGPipelineTrace | None = None
    answer: DiagnoseResponse | None = None
