import json
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def read_json(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


class Catalog:
    def __init__(self):
        self.sources = {s["id"]: s for s in read_json("sources.json")}
        self.institutions = {i["id"]: i for i in read_json("institutions.json")}
        questionnaire = read_json("questions.json")
        self.fields = questionnaire["fields"]
        self.questions = questionnaire["questions"]
        self.scope_fields = questionnaire["scope_fields"]
        rules = read_json("rules.json")
        self.version = rules["version"]
        self.rules = rules["rules"]
        self.max_rounds = 2
        self.max_questions = 3
        # Product review policy, NOT an institutional/legal validity period.
        self.source_review_days = 30
        self.validate()

    def validate(self):
        rule_ids = [r["id"] for r in self.rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("Duplicate rule ID")
        q_ids = [q["id"] for q in self.questions]
        if len(q_ids) != len(set(q_ids)):
            raise ValueError("Duplicate question ID")
        for source in self.sources.values():
            date.fromisoformat(source["checked_on"])
            if not source["url"].startswith("https://"):
                raise ValueError("Sources must have HTTPS URLs")
        for rule in self.rules:
            if rule["institution"] not in self.institutions:
                raise ValueError("Unknown institution")
            if not rule["source_ids"] or any(s not in self.sources for s in rule["source_ids"]):
                raise ValueError("Missing source")
            for expression in (rule["condition"], rule.get("exclusion_condition")):
                if expression is not None:
                    self._validate_expression(expression)
            if any(f not in self.fields for f in rule.get("review_fields", [])):
                raise ValueError("Unknown review field")
        for question in self.questions:
            if any(f not in self.fields for f in question["fields"]):
                raise ValueError("Unknown question field")

    def _validate_expression(self, expression):
        op = expression.get("op")
        if op in {"always", "unresolved"}:
            return
        if op == "equals":
            if expression.get("field") not in self.fields or expression.get("value") not in {"yes", "no"}:
                raise ValueError("Invalid comparison")
        elif op in {"any", "all"} and expression.get("items"):
            for child in expression["items"]:
                self._validate_expression(child)
        else:
            raise ValueError("Unsupported expression")


CATALOG = Catalog()
