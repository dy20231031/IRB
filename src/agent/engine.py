"""Deterministic three-valued rules. Never execute code from a data file."""

from datetime import date

from .catalog import CATALOG
from .models import ANSWERS, Assessment, Decision


def validate_answers(answers):
    for key, value in answers.items():
        if key not in CATALOG.fields or value not in ANSWERS:
            raise ValueError(f"지원하지 않는 답변: {key}")


def dependencies(expression):
    if not expression:
        return set()
    if expression["op"] == "equals":
        return {expression["field"]}
    return set().union(*(dependencies(child) for child in expression.get("items", [])))


def evaluate_condition(expression, answers):
    op = expression["op"]
    if op == "always":
        return "yes"
    if op == "unresolved":
        return "unknown"
    if op == "equals":
        actual = answers.get(expression["field"], "unknown")
        if actual == "unknown":
            return "unknown"
        return "yes" if actual == expression["value"] else "no"
    values = [evaluate_condition(item, answers) for item in expression["items"]]
    if op == "any":
        return "yes" if "yes" in values else "unknown" if "unknown" in values else "no"
    if op == "all":
        return "no" if "no" in values else "unknown" if "unknown" in values else "yes"
    raise ValueError("지원하지 않는 조건 연산자")


def assess(institution, answers, *, today=None):
    if institution not in CATALOG.institutions:
        raise ValueError("지원 기관을 선택해 주세요.")
    validate_answers(answers)
    today = today or date.today()
    issues = [CATALOG.fields[f]["scope_issue"] for f in CATALOG.scope_fields if answers.get(f) != "yes"]
    warnings = [
        "공개 자료로 만든 초기 규칙입니다. 기관 담당자의 검수와 실제 접수 결과 검증은 아직 받지 않았습니다.",
        "준비 상태는 사용자 표시이며 파일 내용, 서명, 승인 가능성을 검증하지 않습니다.",
    ]
    decisions = []
    stale_sources = set()
    for rule in CATALOG.rules:
        if rule["institution"] != institution:
            continue
        fields = dependencies(rule["condition"]) | dependencies(rule.get("exclusion_condition")) | set(rule.get("review_fields", []))
        facts_used = {f: answers.get(f, "unknown") for f in sorted(fields)}
        status = "needs_confirmation"
        reason = rule["unknown_reason"]
        if evaluate_condition(rule["condition"], answers) == "yes":
            status, reason = "required", rule["required_reason"]
        elif rule.get("exclusion_condition") and evaluate_condition(rule["exclusion_condition"], answers) == "yes":
            status, reason = "not_applicable", rule["excluded_reason"]
        stale = False
        for source_id in rule["source_ids"]:
            source = CATALOG.sources[source_id]
            age = (today - date.fromisoformat(source["checked_on"])).days
            if age > CATALOG.source_review_days or age < 0:
                stale = True
                stale_sources.add(source_id)
        if issues:
            status = "needs_confirmation"
            reason = "지원 범위가 확인되지 않아 참고 항목으로만 표시합니다. " + reason
        if stale:
            status = "needs_confirmation"
            reason = "출처 재확인이 필요합니다. 이전 규칙의 안내: " + reason
        decisions.append(Decision(
            rule_id=rule["id"], document=rule["document"], status=status,
            delivery=rule["delivery"], reason=reason, details=rule["details"],
            source_ids=rule["source_ids"], facts_used=facts_used,
            unresolved_fields=[f for f, v in facts_used.items() if v == "unknown"],
            source_stale=stale,
        ))
    if stale_sources:
        warnings.append("출처 확인일로부터 30일 초과 또는 확인일 오류: " + ", ".join(sorted(stale_sources)) + ". 30일은 이 앱의 재검토 정책입니다.")
    warnings.extend(CATALOG.institutions[institution]["limitations"])
    return Assessment(institution, CATALOG.version, today.isoformat(), not issues, issues, decisions, warnings)


def next_questions(session):
    """Ask only unresolved, unasked facts; never re-ask an explicit unknown."""
    if session.phase != "questions" or session.rounds >= CATALOG.max_rounds:
        return []
    result = assess(session.institution, session.answers)
    if not result.scope_ok:
        return []
    needed = set()
    for decision in result.decisions:
        if decision.status == "needs_confirmation":
            needed.update(decision.unresolved_fields)
    questions = []
    for question in CATALOG.questions:
        if question["id"] in session.asked_questions:
            continue
        fields = [f for f in question["fields"] if f in needed and f not in session.seen_fields]
        if fields:
            questions.append({**question, "fields": fields})
    return questions[:CATALOG.max_questions]
