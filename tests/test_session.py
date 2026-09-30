import json

import pytest

from src.agent import api
from src.agent.engine import next_questions
from src.agent.report import to_json, to_markdown


def test_bounded_followups_and_unknown_is_not_repeated(scoped):
    session = api.confirm(api.start("cuk", scoped))
    asked = set()
    while session.phase == "questions":
        questions = next_questions(session)
        assert 1 <= len(questions) <= 3
        current = {q["id"] for q in questions}
        assert not current & asked
        asked |= current
        session = api.rejudge(session, {})
    assert session.rounds == 2
    assert session.phase == "report"
    assert any(d.status == "needs_confirmation" for d in api.result(session).decisions)


def test_stop_preserves_unknowns_and_no_false_missing_label(scoped):
    session = api.confirm(api.start("cuk", scoped))
    session = api.rejudge(session, stop=True)
    data = json.loads(to_json(session, api.result(session)))
    assert session.rounds == 0 and session.phase == "report"
    assert set(data["readiness"].values()) == {"unknown"}
    assert "미제출" not in to_markdown(session, api.result(session))


def test_already_answered_unknown_not_asked_again(scoped):
    session = api.confirm(api.start("cuk", {**scoped, "collect_phone": "unknown"}))
    assert all("collect_phone" not in q["fields"] for q in next_questions(session))


def test_session_data_does_not_leak_between_users(scoped):
    first = api.start("cuk", {**scoped, "collect_name": "yes"})
    second = api.start("snue", scoped)
    first.readiness["cuk.protocol"] = "ready"
    assert "collect_name" not in second.answers
    assert not second.readiness


def test_state_transitions_do_not_mutate_previous_state(scoped):
    original = api.start("cuk", scoped)
    new = api.confirm(original)
    assert original.phase == "review"
    assert new.phase == "questions"
    original_answers = dict(new.answers)
    _ = api.rejudge(new, {})
    assert new.answers == original_answers and new.rounds == 0


def test_scope_block_stops_questions(scoped):
    session = api.confirm(api.start("snue", {**scoped, "adult_only": "no"}))
    assert session.phase == "report"
    assert not next_questions(session)


def test_revise_clears_readiness_and_recalculates(scoped):
    session = api.start("cuk", {**scoped, "collect_phone": "no"})
    session.readiness["cuk.participant_privacy"] = "ready"
    revised = api.revise(session, {"collect_phone": "yes"})
    assert not revised.readiness
    assert revised.phase == "review" and revised.rounds == 0
    assert next(d for d in api.result(revised).decisions if d.rule_id == "cuk.participant_privacy").status == "required"


def test_invalid_transition_and_answers_rejected(scoped):
    session = api.start("cuk", scoped)
    with pytest.raises(ValueError):
        api.rejudge(session, {})
    session = api.confirm(session)
    with pytest.raises(ValueError):
        api.confirm(session)
    with pytest.raises(ValueError):
        api.rejudge(session, {"adult_only": "no"})


def test_unconfirmed_narrative_not_exported(scoped):
    narrative = "PRIVATE_NARRATIVE: 이름은 받습니다."
    session = api.start("cuk", scoped, narrative=narrative)
    assert session.mode == "manual" and "collect_name" not in session.answers
    exported = to_json(session, api.result(session))
    assert "PRIVATE_NARRATIVE" not in exported
    assert "sources" in json.loads(exported)
