from __future__ import annotations

from typing import Any, Literal, TypedDict

from fault_diagnosis_agent.config import settings
from fault_diagnosis_agent.llm import optional_llm
from fault_diagnosis_agent.models import FaultKnowledgeItem
from fault_diagnosis_agent.retrieval.fault_types import FAULT_LABELS, classify_fault_type
from fault_diagnosis_agent.retrieval.hybrid_retriever import FaultHybridRetriever


class FaultDiagnosisState(TypedDict, total=False):
    user_query: str
    top_k: int
    extracted_entities: dict[str, str | None]
    fault_type: str
    retrieved_items: list[tuple[FaultKnowledgeItem, float]]
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
    steps = [f"{idx}. [{step.step_id}] {step.text}" for idx, step in enumerate(primary.steps, start=1)]
    state["solution_steps"] = _validate_steps(steps, primary)
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


def _threshold_note(state: FaultDiagnosisState) -> str:
    threshold = state.get("extracted_entities", {}).get("threshold")
    if not threshold:
        return ""
    return f" 用户给出的阈值为{threshold}，需与站控系统报警阈值和文档阈值逐项核对。"


def _validate_steps(steps: list[str], item: FaultKnowledgeItem) -> list[str]:
    allowed_actions = ("检查", "确认", "关闭", "开启", "观察", "记录", "排查", "联系", "调整", "降低", "切换")
    validated = [step for step in steps if any(action in step for action in allowed_actions)]
    return validated or steps[:3]


def response_payload(state: FaultDiagnosisState) -> dict[str, Any]:
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

