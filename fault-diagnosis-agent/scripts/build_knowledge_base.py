from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fault_diagnosis_agent.retrieval.document_processor import FaultDocumentParser, save_knowledge


def main() -> None:
    parser = argparse.ArgumentParser(description="Build fault diagnosis knowledge base from a Word document.")
    parser.add_argument("--doc", required=True, help="Path to 知识.docx or another operation manual.")
    parser.add_argument("--output", default="data/processed/fault_knowledge.json")
    args = parser.parse_args()

    items = FaultDocumentParser(args.doc).parse()
    save_knowledge(items, args.output)
    print(f"Saved {len(items)} knowledge items to {args.output}")


if __name__ == "__main__":
    main()

