from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import FastAPI

from fault_diagnosis_agent.config import settings
from fault_diagnosis_agent.diagnosis import response_payload
from fault_diagnosis_agent.graph import FaultDiagnosisRunner
from fault_diagnosis_agent.models import DiagnoseRequest, DiagnoseResponse, FeedbackRequest
from fault_diagnosis_agent.retrieval.fault_types import FAULT_LABELS

app = FastAPI(
    title="油气田故障诊断智能问答 Agent",
    version="0.1.0",
    description="基于 LangGraph 状态机、规则实体识别和本地知识库检索的故障诊断 API。",
)

runner = FaultDiagnosisRunner()


@app.get("/health")
async def health() -> dict[str, object]:
    return {"status": "ok", "knowledge_base": str(settings.kb_path), "kb_exists": settings.kb_path.exists()}


@app.get("/fault-types")
async def fault_types() -> dict[str, str]:
    return FAULT_LABELS


@app.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(request: DiagnoseRequest) -> dict[str, object]:
    state = runner.invoke(request.query, top_k=request.top_k, session_id=request.session_id)
    return response_payload(state)


@app.post("/feedback")
async def feedback(request: FeedbackRequest) -> dict[str, object]:
    settings.feedback_path.parent.mkdir(parents=True, exist_ok=True)
    record = request.model_dump()
    record["created_at"] = datetime.now(timezone.utc).isoformat()
    with settings.feedback_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True, "path": str(settings.feedback_path)}

