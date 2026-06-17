from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fault_diagnosis_agent.graph import build_fault_diagnosis_graph


MERMAID_FALLBACK = """flowchart TD
    A[故障分类与实体抽取] --> B{信息是否充足}
    B -- 否 --> C[追问补充信息]
    B -- 是 --> D[混合检索]
    D --> E[根因分析]
    E --> F[处置方案生成]
    F --> G[最终回答]
"""


def main() -> None:
    output = ROOT / "docs" / "fault_diagnosis_graph.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    graph = build_fault_diagnosis_graph()
    mermaid = MERMAID_FALLBACK
    if graph:
        try:
            mermaid = graph.get_graph().draw_mermaid()
        except Exception:
            mermaid = MERMAID_FALLBACK
    output.write_text(f"# Fault Diagnosis Graph\n\n```mermaid\n{mermaid}\n```\n", encoding="utf-8")
    print(f"Saved graph to {output}")


if __name__ == "__main__":
    main()

