from dataclasses import dataclass, field
from typing import Literal

Answer = Literal["yes", "no", "unknown"]
Requirement = Literal["required", "not_applicable", "needs_confirmation"]
ANSWERS = {"yes", "no", "unknown"}
ANSWER_LABELS = {"unknown": "아직 모름", "yes": "예", "no": "아니요"}
STATUS_LABELS = {
    "required": "준비 필요",
    "not_applicable": "현재 조건에서 비해당",
    "needs_confirmation": "확인 필요",
}
DELIVERY_LABELS = {
    "file": "파일 준비",
    "portal": "eIRB 입력",
    "institution_confirmation": "기관에 확인",
}


@dataclass
class Proposal:
    field: str
    value: Answer
    evidence: str
    conflict: bool = False


@dataclass
class Session:
    institution: str
    answers: dict[str, Answer] = field(default_factory=dict)
    origins: dict[str, str] = field(default_factory=dict)
    proposals: list[Proposal] = field(default_factory=list)
    phase: str = "review"
    rounds: int = 0
    asked_questions: list[str] = field(default_factory=list)
    active_questions: list[str] = field(default_factory=list)
    # Explicitly answered 'unknown' is also recorded, so it is not asked again.
    seen_fields: list[str] = field(default_factory=list)
    mode: str = "manual"
    message: str = ""
    readiness: dict[str, str] = field(default_factory=dict)


@dataclass
class Decision:
    rule_id: str
    document: str
    status: Requirement
    delivery: str
    reason: str
    details: str
    source_ids: list[str]
    facts_used: dict[str, Answer]
    unresolved_fields: list[str]
    source_stale: bool = False


@dataclass
class Assessment:
    institution: str
    rule_version: str
    evaluated_on: str
    scope_ok: bool
    scope_issues: list[str]
    decisions: list[Decision]
    warnings: list[str]
