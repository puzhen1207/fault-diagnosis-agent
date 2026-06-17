from __future__ import annotations

import time
from typing import Any, Literal, TypedDict

from fault_diagnosis_agent.config import settings
from fault_diagnosis_agent.llm import optional_llm
from fault_diagnosis_agent.models import (
    FinalAnswerTrace,
    RAGPipelineTrace,
    ReasoningTrace,
    SolutionTrace,
)
from fault_diagnosis_agent.retrieval.fault_types import (
    FAULT_LABELS,
    classify_fault_type,
    classify_fault_type_with_trace,
)
from fault_diagnosis_agent.retrieval.hybrid_retriever import FaultHybridRetriever


class FaultDiagnosisState(TypedDict, total=False):
    user_query: str
    top_k: int
    extracted_entities: dict[str, str | None]
    fault_type: str
    retrieved_items: list[tuple[Any, float]]
    root_cause: str
    solution_steps: list[str]
    risk_warning: str
    need_more_info: bool
    missing_info: str
    final_answer: str
    next_step: Literal["classify", "retrieve", "reason", "generate", "ask_missing", "end"]


def classify_node(state: FaultDiagnosisState) -> FaultDiagnosisState:
    retriever = FaultHybridRetriever(settings.kb_path)
    _, entities = retriever.retrieve(state["user_query"], k=1)
    state["extracted_entities"] = entities
    state["fault_type"] = classify_fault_type(state["user_query"])
    state["need_more_info"] = False
    state["missing_info"] = ""
    return state


def need_more_info_router(state: FaultDiagnosisState) -> str:
    entities = state.get("extracted_entities", {})
    if state.get("fault_type") == "unknown" and not (entities.get("device") and entities.get("indicator")):
        state["need_more_info"] = True
        state["missing_info"] = "请明确是哪个设备或指标异常，例如压缩机压力、分离器液位、干管压力或气井积液。"
        return "ask_missing"
    return "retrieve"


def ask_missing_node(state: FaultDiagnosisState) -> FaultDiagnosisState:
    state["root_cause"] = ""
    state["solution_steps"] = []
    state["risk_warning"] = "信息不足时不要执行现场操作。"
    state["final_answer"] = state.get("missing_info", "请补充故障设备和异常指标。")
    return state


def retrieve_node(state: FaultDiagnosisState) -> FaultDiagnosisState:
    retriever = FaultHybridRetriever(settings.kb_path)
    query = f"{state['user_query']} {state.get('fault_type', '')} 处理流程 风险提示"
    state["retrieved_items"], state["extracted_entities"] = retriever.retrieve(query, k=state.get("top_k", 5))
    return state


def reason_node(state: FaultDiagnosisState) -> FaultDiagnosisState:
    items = [item for item, _ in state.get("retrieved_items", [])]
    if not items:
        state["root_cause"] = "当前知识库未检索到对应流程，无法给出可靠根因判断。"
        return state

    primary = items[0]
    local_reason = "；".join(primary.root_causes[:3]) or f"{primary.title}通常与{primary.device}{primary.indicator}{primary.condition}相关，需要结合现场趋势确认。"
    threshold_note = _threshold_note(state)
    root_cause = f"{local_reason}{threshold_note}"

    if optional_llm.enabled:
        context = "\n".join(item.searchable_text() for item in items[:3])
        prompt = (
            "你是油气田故障诊断专家。仅基于给定知识，用不超过150字分析根因。\n"
            f"用户描述：{state['user_query']}\n相关知识：{context}"
        )
        try:
            root_cause = optional_llm.invoke(prompt)
        except Exception:
            pass

    state["root_cause"] = root_cause[:220]
    return state


def generate_solution_node(state: FaultDiagnosisState) -> FaultDiagnosisState:
    items = [item for item, _ in state.get("retrieved_items", [])]
    if not items or not items[0].steps:
        state["solution_steps"] = ["当前知识库未包含该故障的标准流程，请联系技术科获取最新版本。"]
        state["risk_warning"] = "请谨慎操作，避免扩大故障。"
        return state

    primary = items[0]
    raw_steps = [f"{idx}. [{step.step_id}] {step.text}" for idx, step in enumerate(primary.steps, start=1)]
    validated = _validate_steps(raw_steps, primary)
    state["solution_steps"] = validated
    state["risk_warning"] = primary.risks[0] if primary.risks else "处置后需持续观察压力、液位和气量变化，避免报警再次触发。"
    return state


def generate_final_node(state: FaultDiagnosisState) -> FaultDiagnosisState:
    if state.get("need_more_info"):
        return state
    items = [item for item, _ in state.get("retrieved_items", [])]
    reference = items[0].title if items else "通用知识"
    steps = "\n".join(state.get("solution_steps", []))
    state["final_answer"] = (
        f"**故障根因分析**\n{state.get('root_cause', '')}\n\n"
        f"**处置方案**\n{steps}\n\n"
        f"**风险提示**\n{state.get('risk_warning', '')}\n\n"
        f"> 参考依据：{reference}"
    )
    return state


def run_diagnosis(query: str, top_k: int = 5) -> FaultDiagnosisState:
    """向后兼容：仅返回 state 字典。"""
    state: FaultDiagnosisState = {"user_query": query, "top_k": top_k}
    state = classify_node(state)
    route = need_more_info_router(state)
    if route == "ask_missing":
        return ask_missing_node(state)
    state = retrieve_node(state)
    state = reason_node(state)
    state = generate_solution_node(state)
    state = generate_final_node(state)
    return state


# ---------------------------------------------------------------------------
# 带追踪的完整 RAG 管线
# ---------------------------------------------------------------------------

ALLOWED_ACTIONS = ("检查", "确认", "关闭", "开启", "观察", "记录", "排查", "联系", "调整", "降低", "切换")


def run_diagnosis_with_trace(
    query: str, top_k: int = 5, session_id: str = "default"
) -> tuple[dict[str, Any], RAGPipelineTrace]:
    """完整运行一次 RAG 管线并返回 (final_state_dict, trace_object)。

    节点顺序：
        1. entity_extraction  (实体提取)
        2. fault_classification  (故障类型分类)
        3. retrieval  (检索)
        4. reasoning  (推理与根因)
        5. solution  (方案生成与动词校验)
        6. final_answer  (组装 Markdown 答案)
    """
    start_time = time.perf_counter()
    retriever = FaultHybridRetriever(settings.kb_path)

    # ---- 节点 1 & 2：实体提取 + 故障类型分类
    entity_trace = retriever.entity_extractor.extract_with_trace(query)
    entities = entity_trace.result
    fault_type, fault_trace = classify_fault_type_with_trace(query)

    # ---- 节点 3：检索（带完整打分追踪）
    retrieval_query = f"{query} {fault_type} 处理流程 风险提示"
    retrieved, _ret_entities, retrieval_trace = retriever.retrieve_with_trace(
        retrieval_query, k=top_k
    )

    # ---- 判断是否需要追问更多信息
    need_more_info = False
    missing_info = ""
    if fault_type == "unknown" and not (entities.get("device") and entities.get("indicator")):
        need_more_info = True
        missing_info = "请明确是哪个设备或指标异常，例如压缩机压力、分离器液位、干管压力或气井积液。"

    # ---- 节点 4：推理
    items = [item for item, _ in retrieved]
    primary_doc = items[0] if items else None
    llm_attempted = False
    llm_used = False
    llm_output: str | None = None

    if primary_doc is None:
        root_cause = "当前知识库未检索到对应流程，无法给出可靠根因判断。"
        root_causes_used: list[str] = []
    else:
        local_reason = (
            "；".join(primary_doc.root_causes[:3])
            or f"{primary_doc.title}通常与{primary_doc.device}{primary_doc.indicator}{primary_doc.condition}相关，需要结合现场趋势确认。"
        )
        threshold_note = _threshold_note_from_dict(entities)
        root_cause = f"{local_reason}{threshold_note}"
        root_causes_used = list(primary_doc.root_causes[:3])

        if optional_llm.enabled:
            llm_attempted = True
            context = "\n".join(item.searchable_text() for item in items[:3])
            prompt = (
                "你是油气田故障诊断专家。仅基于给定知识，用不超过150字分析根因。\n"
                f"用户描述：{query}\n相关知识：{context}"
            )
            try:
                llm_out = optional_llm.invoke(prompt)
                if llm_out:
                    root_cause = llm_out
                    llm_used = True
                    llm_output = llm_out
            except Exception:
                pass

    root_cause = root_cause[:220]

    reasoning_trace = ReasoningTrace(
        selected_primary_doc_title=primary_doc.title if primary_doc else "",
        selected_primary_doc_id=primary_doc.id if primary_doc else "",
        root_causes_used=root_causes_used,
        assembled_root_cause=root_cause,
        llm_attempted=llm_attempted,
        llm_used=llm_used,
        llm_output_if_any=llm_output,
    )

    # ---- 节点 5：方案生成
    if need_more_info or primary_doc is None or not primary_doc.steps:
        if need_more_info:
            solution_steps: list[str] = []
            risk_warning = "信息不足时不要执行现场操作。"
            steps_from_kb: list[dict[str, Any]] = []
            filtered_count = 0
        else:
            solution_steps = ["当前知识库未包含该故障的标准流程，请联系技术科获取最新版本。"]
            risk_warning = "请谨慎操作，避免扩大故障。"
            steps_from_kb = []
            filtered_count = 0
    else:
        steps_from_kb = [
            {"step_id": step.step_id, "text": step.text}
            for step in primary_doc.steps
        ]
        raw_steps = [
            f"{idx}. [{step.step_id}] {step.text}"
            for idx, step in enumerate(primary_doc.steps, start=1)
        ]
        allowed = ALLOWED_ACTIONS
        validated = [s for s in raw_steps if any(a in s for a in allowed)]
        filtered_count = len(raw_steps) - len(validated)
        if not validated:
            validated = raw_steps[:3]
            filtered_count = len(raw_steps) - len(validated)
        solution_steps = validated
        risk_warning = primary_doc.risks[0] if primary_doc.risks else "处置后需持续观察压力、液位和气量变化，避免报警再次触发。"

    solution_trace = SolutionTrace(
        primary_doc_title=primary_doc.title if primary_doc else "",
        primary_doc_id=primary_doc.id if primary_doc else "",
        steps_from_kb=steps_from_kb,
        validated_steps=solution_steps,
        steps_filtered_by_verb_check=filtered_count,
        risk=risk_warning,
    )

    # ---- 节点 6：最终答案组装
    if need_more_info:
        final_answer = missing_info
    else:
        reference_title = primary_doc.title if primary_doc else "通用知识"
        reference_score = round(retrieved[0][1], 4) if retrieved else 0.0
        steps_text = "\n".join(solution_steps)
        final_answer = (
            f"**故障根因分析**\n{root_cause}\n\n"
            f"**处置方案**\n{steps_text}\n\n"
            f"**风险提示**\n{risk_warning}\n\n"
            f"> 参考依据：{reference_title}"
        )
        reference_score_out = reference_score
        reference_title_out = reference_title

    if not need_more_info:
        final_trace = FinalAnswerTrace(
            root_cause_final=root_cause,
            solution_steps_final=solution_steps,
            risk_final=risk_warning,
            reference_title=reference_title_out,
            reference_score=reference_score_out,
            final_markdown=final_answer,
        )
    else:
        final_trace = FinalAnswerTrace(
            root_cause_final="",
            solution_steps_final=[],
            risk_final=risk_warning,
            reference_title="",
            reference_score=0.0,
            final_markdown=final_answer,
        )

    duration_ms = round((time.perf_counter() - start_time) * 1000.0, 3)

    # ---- 组装 pipeline trace
    kb_stats_dict = {}
    try:
        kb_stats_dict = retriever.get_kb_stats().model_dump()
    except Exception:
        pass

    pipeline_trace = RAGPipelineTrace(
        query=query,
        session_id=session_id,
        started_at=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        finished_at=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        duration_ms=duration_ms,
        entities=entity_trace,
        fault_classification=fault_trace,
        retrieval=retrieval_trace,
        reasoning=reasoning_trace,
        solution=solution_trace,
        final_answer=final_trace,
        kb_stats=kb_stats_dict,
    )

    # ---- 构造 state dict（与原 run_diagnosis 返回结构兼容）
    final_state: dict[str, Any] = {
        "user_query": query,
        "top_k": top_k,
        "extracted_entities": entities,
        "fault_type": fault_type,
        "retrieved_items": retrieved,
        "root_cause": root_cause,
        "solution_steps": solution_steps,
        "risk_warning": risk_warning,
        "need_more_info": need_more_info,
        "missing_info": missing_info,
        "final_answer": final_answer,
    }
    return final_state, pipeline_trace


def _threshold_note(state: FaultDiagnosisState) -> str:
    threshold = state.get("extracted_entities", {}).get("threshold")
    if not threshold:
        return ""
    return f" 用户给出的阈值为{threshold}，需与站控系统报警阈值和文档阈值逐项核对。"


def _threshold_note_from_dict(entities: dict[str, str | None]) -> str:
    threshold = entities.get("threshold")
    if not threshold:
        return ""
    return f" 用户给出的阈值为{threshold}，需与站控系统报警阈值和文档阈值逐项核对。"


def _validate_steps(steps: list[str], item: Any) -> list[str]:
    validated = [step for step in steps if any(action in step for action in ALLOWED_ACTIONS)]
    return validated or steps[:3]


def response_payload(state: dict[str, Any]) -> dict[str, Any]:
    retrieved = state.get("retrieved_items", [])
    return {
        "answer": state.get("final_answer", ""),
        "root_cause": state.get("root_cause", ""),
        "steps": state.get("solution_steps", []),
        "risk": state.get("risk_warning", ""),
        "fault_type": state.get("fault_type", "unknown"),
        "entities": state.get("extracted_entities", {}),
        "need_more_info": state.get("need_more_info", False),
        "missing_info": state.get("missing_info", ""),
        "references": [
            {
                "id": item.id,
                "title": item.title,
                "fault_type": FAULT_LABELS.get(item.fault_type, item.fault_type),
                "score": round(score, 3),
            }
            for item, score in retrieved
        ],
    }
