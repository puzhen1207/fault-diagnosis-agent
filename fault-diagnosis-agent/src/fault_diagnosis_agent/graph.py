from __future__ import annotations

from fault_diagnosis_agent.diagnosis import (
    FaultDiagnosisState,
    ask_missing_node,
    classify_node,
    generate_final_node,
    generate_solution_node,
    need_more_info_router,
    reason_node,
    retrieve_node,
    run_diagnosis,
)


def build_fault_diagnosis_graph():
    try:
        from langgraph.graph import END, StateGraph
    except Exception:
        return None

    workflow = StateGraph(FaultDiagnosisState)
    workflow.add_node("classify", classify_node)
    workflow.add_node("ask_missing", ask_missing_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("reason", reason_node)
    workflow.add_node("generate_solution", generate_solution_node)
    workflow.add_node("final", generate_final_node)

    workflow.set_entry_point("classify")
    workflow.add_conditional_edges(
        "classify",
        need_more_info_router,
        {"ask_missing": "ask_missing", "retrieve": "retrieve"},
    )
    workflow.add_edge("ask_missing", END)
    workflow.add_edge("retrieve", "reason")
    workflow.add_edge("reason", "generate_solution")
    workflow.add_edge("generate_solution", "final")
    workflow.add_edge("final", END)
    return workflow.compile()


class FaultDiagnosisRunner:
    def __init__(self) -> None:
        self.graph = build_fault_diagnosis_graph()

    def invoke(self, query: str, top_k: int = 5, session_id: str = "default") -> FaultDiagnosisState:
        state: FaultDiagnosisState = {"user_query": query, "top_k": top_k}
        if not self.graph:
            return run_diagnosis(query, top_k=top_k)
        config = {"configurable": {"thread_id": session_id}}
        return self.graph.invoke(state, config=config)

