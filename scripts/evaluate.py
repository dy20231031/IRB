"""Synthetic regression checks only; not an independently labeled accuracy score."""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.agent.catalog import CATALOG
from src.agent.engine import assess


def main():
    cases = json.loads((ROOT / "tests/fixtures/regression_cases.json").read_text(encoding="utf-8"))
    checked = 0
    failures = []
    for case in cases:
        answers = {f: "yes" for f in CATALOG.scope_fields} if case["in_scope"] else {}
        answers.update(case["answers"])
        result = assess(case["institution"], answers, today=date(2026, 10, 1))
        actual = {d.rule_id: d.status for d in result.decisions}
        for rule, expected in case["expected"].items():
            checked += 1
            if actual.get(rule) != expected:
                failures.append({"case": case["id"], "rule": rule, "expected": expected, "actual": actual.get(rule)})
    print(json.dumps({"kind": "synthetic_regression_not_accuracy", "cases": len(cases),
                      "assertions": checked, "failures": failures,
                      "independent_expert_validation": False}, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
