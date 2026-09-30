from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.agent.catalog import CATALOG

APP = Path(__file__).resolve().parents[1] / "app.py"


def click_label(at, label):
    return next(b for b in at.button if b.label == label).click().run()


def test_cuk_flow_stop_export_and_reset(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=15).run()
    assert not at.exception
    assert at.checkbox("use_ai").disabled
    at.button("demo_cuk").click().run()
    click_label(at, "확인하고 계속")
    assert at.session_state["assessment_session"].phase == "questions"
    at.button("stop_questions").click().run()
    assert not at.exception
    assert at.session_state["assessment_session"].phase == "report"
    assert len(at.get("download_button")) == 2
    assert any("참가자 개인정보" in row["항목"] and row["필요 여부"] == "준비 필요" for row in at.dataframe[0].value.to_dict("records"))
    at.button("reset").click().run()
    assert not at.exception
    assert at.selectbox("institution").value == "cuk"
    assert "assessment_session" not in at.session_state


def test_snue_two_rounds_then_report():
    at = AppTest.from_file(APP, default_timeout=15).run()
    at.button("demo_snue").click().run()
    click_label(at, "확인하고 계속")
    click_label(at, "답변 반영")
    click_label(at, "답변 반영")
    assert not at.exception
    session = at.session_state["assessment_session"]
    assert session.phase == "report" and session.rounds == 2
    rows = at.dataframe[0].value.to_dict("records")
    assert sum(row["처리 방법"] == "eIRB 입력" for row in rows) == 3


def test_missing_scope_shows_partial_report():
    at = AppTest.from_file(APP, default_timeout=15).run()
    click_label(at, "입력 내용 확인")
    click_label(at, "확인하고 계속")
    assert not at.exception
    assert at.session_state["assessment_session"].phase == "report"
    assert any("참고 목록" in error.value for error in at.error)
    assert all(row["필요 여부"] == "확인 필요" for row in at.dataframe[0].value.to_dict("records"))


def test_form_answers_and_edit_reset_old_readiness():
    at = AppTest.from_file(APP, default_timeout=15).run()
    for field in CATALOG.scope_fields:
        at.selectbox(f"initial_{field}").set_value("yes")
    at.selectbox("initial_graduate_student").set_value("no")
    at.selectbox("initial_all_fulltime_faculty").set_value("yes")
    click_label(at, "입력 내용 확인")
    click_label(at, "확인하고 계속")
    at.selectbox("q_0_collect_name").set_value("yes")
    at.selectbox("q_0_collect_phone").set_value("no")
    click_label(at, "답변 반영")
    click_label(at, "답변 반영")
    assert not at.exception
    at.selectbox("1_ready_cuk.protocol").set_value("ready").run()
    assert at.session_state["assessment_session"].readiness["cuk.protocol"] == "ready"
    at.selectbox("1_edit_collect_name").set_value("no")
    click_label(at, "수정 내용 확인")
    click_label(at, "확인하고 계속")
    assert not at.exception
    session = at.session_state["assessment_session"]
    assert session.phase == "report"
    assert session.answers["collect_name"] == "no"
    assert session.readiness["cuk.protocol"] == "unknown"
