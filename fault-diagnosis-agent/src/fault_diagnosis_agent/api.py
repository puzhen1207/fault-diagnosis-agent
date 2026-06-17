from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fault_diagnosis_agent.config import settings
from fault_diagnosis_agent.diagnosis import response_payload, run_diagnosis_with_trace
from fault_diagnosis_agent.graph import FaultDiagnosisRunner
from fault_diagnosis_agent.models import DiagnoseRequest, DiagnoseResponse, FeedbackRequest
from fault_diagnosis_agent.retrieval.fault_types import FAULT_LABELS
from fault_diagnosis_agent.retrieval.hybrid_retriever import FaultHybridRetriever

app = FastAPI(
    title="油气田故障诊断智能问答 Agent",
    version="0.1.0",
    description="基于 LangGraph 状态机、规则实体识别和本地知识库检索的故障诊断 API。",
)

# ---- 静态资源挂载（若 static 目录存在） ------------------------------------
STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

runner = FaultDiagnosisRunner()


# ---------------------------------------------------------------------------
# 根路径：跳转到可视化首页（若存在）
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Diagnosis API running. See /docs for API documentation."}

@app.get("/trace.html", include_in_schema=False)
async def trace_page():
    return FileResponse(str(STATIC_DIR / "trace.html"))

@app.get("/kb.html", include_in_schema=False)
async def kb_page():
    return FileResponse(str(STATIC_DIR / "kb.html"))

@app.get("/items.html", include_in_schema=False)
async def items_page():
    return FileResponse(str(STATIC_DIR / "items.html"))

@app.get("/debug.html", include_in_schema=False)
async def debug_page():
    return FileResponse(str(STATIC_DIR / "debug.html"))
# ---------------------------------------------------------------------------
# 原有接口：保持完全不变
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 新增：带完整 RAG 追踪的诊断接口
# ---------------------------------------------------------------------------

@app.post("/diagnose/trace")
async def diagnose_with_trace(request: DiagnoseRequest) -> dict[str, object]:
    """带完整链路追踪的诊断接口。返回 answer + trace 两部分。"""
    state, trace = run_diagnosis_with_trace(
        query=request.query,
        top_k=request.top_k,
        session_id=request.session_id,
    )
    return {
        "answer": response_payload(state),
        "trace": trace.model_dump() if hasattr(trace, "model_dump") else trace,
    }


# ---------------------------------------------------------------------------
# 新增：知识库统计
# ---------------------------------------------------------------------------

@app.get("/kb/stats")
async def kb_stats() -> dict[str, object]:
    """返回知识库整体统计信息。"""
    retriever = FaultHybridRetriever(settings.kb_path)
    stats = retriever.get_kb_stats()
    return stats.model_dump() if hasattr(stats, "model_dump") else stats


# ---------------------------------------------------------------------------
# 新增：知识库条目列表（轻量版）
# ---------------------------------------------------------------------------

@app.get("/kb/items")
async def kb_items() -> list[dict[str, object]]:
    """返回知识库所有条目的轻量描述（不包含完整 content）。"""
    retriever = FaultHybridRetriever(settings.kb_path)
    items = retriever.items
    summary: list[dict[str, object]] = []
    for item in items:
        st = item.searchable_text()
        summary.append({
            "id": item.id,
            "title": item.title,
            "device": item.device,
            "indicator": item.indicator,
            "condition": item.condition,
            "fault_type": item.fault_type,
            "aliases_count": len(item.aliases),
            "steps_count": len(item.steps),
            "root_causes_count": len(item.root_causes),
            "searchable_text_preview": st[:150],
        })
    return summary


# ---------------------------------------------------------------------------
# 新增：单个知识库条目详情
# ---------------------------------------------------------------------------

@app.get("/kb/items/{item_id}")
async def kb_item_detail(item_id: str) -> dict[str, object]:
    """按 ID 返回完整的知识库条目。"""
    retriever = FaultHybridRetriever(settings.kb_path)
    for item in retriever.items:
        if item.id == item_id:
            return item.model_dump() if hasattr(item, "model_dump") else item.__dict__
    return {"error": "not found", "id": item_id}
