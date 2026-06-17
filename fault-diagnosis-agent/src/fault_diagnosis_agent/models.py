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
