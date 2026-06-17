from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fault_diagnosis_agent.diagnosis import run_diagnosis


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate fault classification on test cases.")
    parser.add_argument("--cases", default="data/eval/test_cases.json")
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    correct = 0
    for case in cases:
        result = run_diagnosis(case["query"])
        predicted = result.get("fault_type")
        ok = predicted == case["expected_fault_type"]
        correct += int(ok)
        print(f"{'OK' if ok else 'FAIL'} | {case['query']} | predicted={predicted} expected={case['expected_fault_type']}")

    total = len(cases)
    print(f"Accuracy: {correct}/{total} = {correct / total:.1%}")


if __name__ == "__main__":
    main()

