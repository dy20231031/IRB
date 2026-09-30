"""In-process application interface shared by Streamlit and tests."""

from copy import deepcopy

from .catalog import CATALOG
from .engine import assess, next_questions, validate_answers
from .models import Session


def start(institution, answers=None, *, narrative="", use_ai=False, extractor=None):
    answers = dict(answers or {})
    validate_answers(answers)
    if institution not in CATALOG.institutions:
        raise ValueError("지원 기관을 선택해 주세요.")
    session = Session(institution=institution, answers=answers,
                      origins={k: "user" for k in answers}, seen_fields=list(answers))
    if use_ai and narrative.strip():
        from .llm import extract_facts, validate_proposals
        try:
            raw = (extractor or extract_facts)(narrative)
            session.proposals = validate_proposals(raw, narrative, answers)
            session.mode = "ai"
            session.message = "AI가 제안한 내용을 직접 확인해 주세요. 미승인 제안은 판단에 쓰지 않습니다."
        except Exception:
            # Never echo an SDK exception: it may contain input or credentials.
            session.mode = "ai_unavailable"
            session.message = "AI 해석을 사용하지 못했습니다. API 설정을 확인하거나 객관식으로 계속 진행해 주세요."
    elif narrative.strip():
        session.message = "객관식 모드입니다. 입력한 설명은 자동 해석하거나 판단에 반영하지 않았습니다."
    return session


def _advance(session):
    questions = next_questions(session)
    session.active_questions = [q["id"] for q in questions]
    if not questions:
        session.phase = "report"
    return session


def confirm(session, accepted=None):
    if session.phase != "review":
        raise ValueError("입력 확인 단계에서만 실행할 수 있습니다.")
    updated = deepcopy(session)
    accepted = dict(accepted or {})
    validate_answers(accepted)
    proposals = {p.field: p for p in updated.proposals}
    for key, value in accepted.items():
        proposal = proposals.get(key)
        if proposal is None or proposal.conflict:
            raise ValueError("승인 가능한 AI 제안이 아닙니다.")
        updated.answers[key] = value
        updated.origins[key] = "user_confirmed_ai"
        if key not in updated.seen_fields:
            updated.seen_fields.append(key)
    updated.phase = "questions"
    return _advance(updated)


def rejudge(session, answers=None, *, stop=False):
    if session.phase != "questions":
        raise ValueError("추가 질문 단계에서만 실행할 수 있습니다.")
    updated = deepcopy(session)
    if stop:
        updated.phase, updated.active_questions = "report", []
        return updated
    current = next_questions(session)
    fields = {f for q in current for f in q["fields"]}
    answers = dict(answers or {})
    validate_answers(answers)
    if set(answers) - fields:
        raise ValueError("현재 질문에 포함되지 않은 답변입니다.")
    for field in fields:
        updated.answers[field] = answers.get(field, "unknown")
        updated.origins[field] = "user"
        if field not in updated.seen_fields:
            updated.seen_fields.append(field)
    updated.asked_questions.extend(q["id"] for q in current)
    updated.rounds += 1
    return _advance(updated)


def result(session, *, today=None):
    return assess(session.institution, session.answers, today=today)


def revise(session, corrections):
    """Explicit user edits begin a new bounded assessment; readiness is reset."""
    validate_answers(corrections)
    return start(session.institution, {**session.answers, **corrections})
