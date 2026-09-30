"""Run with: python -m streamlit run app.py"""

import streamlit as st
from dotenv import load_dotenv

from src.agent import api
from src.agent.catalog import CATALOG
from src.agent.engine import next_questions
from src.agent.llm import configured, MAX_NARRATIVE
from src.agent.models import ANSWER_LABELS, STATUS_LABELS, DELIVERY_LABELS
from src.agent.report import READINESS_LABELS, to_json, to_markdown

load_dotenv(override=False)
st.set_page_config(page_title="IRB 준비 도우미", page_icon="📋", layout="wide")
st.markdown("""<style>
.block-container {max-width: 1120px; padding-top: 2.2rem;}
[data-testid="stMetric"] {background:#f0f5f7; padding:1rem; border-radius:12px;}
</style>""", unsafe_allow_html=True)


def reset():
    for key in list(st.session_state):
        del st.session_state[key]


def set_session(session):
    st.session_state["assessment_session"] = session
    st.session_state["revision"] = st.session_state.get("revision", 0) + 1


def answer_widget(field, key, value="unknown"):
    meta = CATALOG.fields[field]
    values = list(ANSWER_LABELS)
    return st.selectbox(meta["label"], values, index=values.index(value),
                        format_func=ANSWER_LABELS.get, help=meta["help"], key=key)


def initial_screen():
    st.subheader("연구의 기본 조건을 알려주세요")
    st.write("답을 모르면 그대로 두세요. 실제 이름, 연락처, 참가자 응답은 입력하지 마세요.")
    with st.expander("예시로 흐름 확인하기"):
        st.caption("실제 연구 자료가 없는 가상 예시입니다.")
        col1, col2 = st.columns(2)
        if col1.button("가톨릭대: 이름 수집 설문 예시", key="demo_cuk"):
            answers = {f: "yes" for f in CATALOG.scope_fields}
            answers.update(graduate_student="yes", all_fulltime_faculty="no", collect_name="yes", collect_phone="no")
            set_session(api.start("cuk", answers))
            st.rerun()
        if col2.button("서울교대: 대학원생 인터뷰 예시", key="demo_snue"):
            answers = {f: "yes" for f in CATALOG.scope_fields}
            answers.update(graduate_student="yes", all_fulltime_faculty="no", collect_media="yes")
            set_session(api.start("snue", answers))
            st.rerun()
    with st.form("initial_form"):
        institution = st.selectbox("제출할 기관", list(CATALOG.institutions),
                                   format_func=lambda k: CATALOG.institutions[k]["name"], key="institution")
        answers = {}
        cols = st.columns(2)
        for index, field in enumerate(CATALOG.scope_fields + ["graduate_student", "all_fulltime_faculty"]):
            with cols[index % 2]:
                answers[field] = answer_widget(field, f"initial_{field}")
        narrative = st.text_area("연구 설명 (AI 해석을 사용할 때만 반영)", max_chars=MAX_NARRATIVE,
            placeholder="예: 성인 교사를 인터뷰하고 음성을 녹음합니다. 설문에는 전화번호를 받지 않지만 보상 지급 때 연락처를 받습니다.", key="narrative")
        use_ai = st.checkbox("연구 설명을 OpenAI API로 보내 사실 추출 제안 받기", value=False,
                             disabled=not configured(), key="use_ai")
        if not configured():
            st.caption("현재 객관식 모드입니다. AI 해석은 서버의 API 키와 모델 설정 후 사용할 수 있습니다.")
        else:
            st.caption("선택한 경우 연구 설명이 외부 API로 전송됩니다. 실제 개인정보와 비공개 연구 원문은 넣지 마세요.")
        submitted = st.form_submit_button("입력 내용 확인", type="primary")
    if submitted:
        with st.spinner("입력 내용을 정리하고 있습니다."):
            set_session(api.start(institution, answers, narrative=narrative, use_ai=use_ai))
        st.rerun()


def review_screen(session):
    st.subheader("판단에 사용할 사실을 확인하세요")
    if session.message:
        st.info(session.message)
    st.dataframe([{"항목": CATALOG.fields[k]["label"], "답변": ANSWER_LABELS[v]}
                  for k, v in session.answers.items()], hide_index=True, width="stretch")
    accepted = {}
    epoch = st.session_state.get("revision", 0)
    with st.form("confirm_form"):
        for proposal in session.proposals:
            st.markdown(f"**{CATALOG.fields[proposal.field]['label']}**")
            st.text(f"설명에서 찾은 근거: {proposal.evidence}")
            if proposal.conflict:
                st.warning("객관식 답변과 충돌합니다. 기존 답변을 유지합니다. 결과 화면의 답변 수정에서 직접 정정할 수 있습니다.")
            else:
                value = answer_widget(proposal.field, f"{epoch}_proposal_{proposal.field}", proposal.value)
                if st.checkbox("확인 후 이 값을 반영", key=f"{epoch}_accept_{proposal.field}"):
                    accepted[proposal.field] = value
        submitted = st.form_submit_button("확인하고 계속", type="primary")
    st.caption("체크하지 않은 AI 제안은 판단에 사용하지 않습니다. 객관식 답변은 결과 화면에서 수정할 수 있습니다.")
    if submitted:
        st.session_state["assessment_session"] = api.confirm(session, accepted)
        st.rerun()


def questions_screen(session):
    questions = next_questions(session)
    st.subheader(f"추가 확인 {session.rounds + 1} / {CATALOG.max_rounds}")
    st.write("서류 판단에 남아 있는 질문만 보여드립니다. 아직 모름으로 답한 질문을 반복하지 않습니다.")
    with st.form(f"questions_{session.rounds}"):
        answers = {}
        for q in questions:
            st.markdown(f"**{q['title']}**")
            st.caption(q["purpose"])
            for field in q["fields"]:
                answers[field] = answer_widget(field, f"q_{session.rounds}_{field}")
        submitted = st.form_submit_button("답변 반영", type="primary")
    if submitted:
        st.session_state["assessment_session"] = api.rejudge(session, answers)
        st.rerun()
    if st.button("추가 질문을 멈추고 저장된 답변으로 결과 보기", key="stop_questions"):
        st.session_state["assessment_session"] = api.rejudge(session, stop=True)
        st.rerun()


def report_screen(session):
    assessment = api.result(session)
    st.subheader("내 연구의 제출 준비 목록")
    if not assessment.scope_ok:
        st.error("지원 범위가 확인되지 않아 아래 항목은 참고 목록입니다.")
        for issue in assessment.scope_issues:
            st.write("- " + issue)
    st.info(CATALOG.institutions[session.institution]["submission"])
    cols = st.columns(3)
    for col, (status, label) in zip(cols, STATUS_LABELS.items()):
        col.metric(label, sum(d.status == status for d in assessment.decisions))
    with st.expander("이 결과의 적용 범위와 확인할 사항", expanded=True):
        for warning in assessment.warnings:
            st.write("- " + warning)
    st.dataframe([{"항목": d.document, "필요 여부": STATUS_LABELS[d.status], "처리 방법": DELIVERY_LABELS[d.delivery]}
                  for d in assessment.decisions], hide_index=True, width="stretch")
    st.caption("아래 항목을 펼치면 판단 이유, 사용한 답변, 기관 출처를 확인하고 준비 상태를 기록할 수 있습니다.")
    epoch = st.session_state.get("revision", 0)
    for decision in assessment.decisions:
        with st.expander(f"{STATUS_LABELS[decision.status]} | {decision.document}"):
            st.write(decision.reason)
            st.write(decision.details)
            st.caption(f"규칙 {decision.rule_id} / 버전 {assessment.rule_version}")
            if decision.facts_used:
                st.dataframe([{"판단에 사용한 항목": CATALOG.fields[k]["label"], "답변": ANSWER_LABELS[v]}
                              for k, v in decision.facts_used.items()], hide_index=True, width="stretch")
            for source_id in decision.source_ids:
                source = CATALOG.sources[source_id]
                st.markdown(f"[{source['title']}]({source['url']})")
                st.caption(f"확인일 {source['checked_on']} / {source['locator']} / {source['version_note']}")
            if decision.status != "not_applicable":
                values = list(READINESS_LABELS)
                label = "준비 상태 (파일 내용 검증 아님)" if decision.delivery != "institution_confirmation" else "기관 확인 진행 상태 (사용자 표시)"
                session.readiness[decision.rule_id] = st.selectbox(label, values,
                    index=values.index(session.readiness.get(decision.rule_id, "unknown")),
                    format_func=READINESS_LABELS.get, key=f"{epoch}_ready_{decision.rule_id}")
    st.markdown("**결과 내려받기**")
    st.caption("내려받는 파일에는 확인한 답변, 판단 근거와 준비 상태가 포함됩니다. 연구 설명 원문은 포함하지 않습니다.")
    col1, col2 = st.columns(2)
    col1.download_button("읽기용 보고서 (.md)", to_markdown(session, assessment),
                         file_name="irb-preparation-report.md", mime="text/markdown")
    col2.download_button("개발 및 검토용 결과 (.json)", to_json(session, assessment),
                         file_name="irb-preparation-report.json", mime="application/json")
    with st.expander("답변 수정 후 다시 판단하기"):
        st.caption("수정하면 준비 상태를 초기화하고 다시 확인합니다. 기관을 바꾸려면 새 연구로 시작하세요.")
        with st.form(f"edit_{epoch}"):
            edits = {f: answer_widget(f, f"{epoch}_edit_{f}", session.answers.get(f, "unknown")) for f in CATALOG.fields}
            changed = st.form_submit_button("수정 내용 확인", type="primary")
        if changed:
            set_session(api.revise(session, edits))
            st.rerun()


st.title("IRB 제출 준비 도우미")
st.write("연구 조건을 확인하고, 기관별 제출 항목과 근거를 정리합니다.")
session = st.session_state.get("assessment_session")
phase = session.phase if session else "initial"
steps = {"initial": "1. 기본 입력", "review": "2. 사실 확인", "questions": "3. 추가 확인", "report": "4. 준비 목록"}
st.caption(" → ".join(f"[{label}]" if key == phase else label for key, label in steps.items()))
with st.sidebar:
    st.markdown("### 이번 버전의 범위")
    st.write("두 기관의 성인 설문 또는 인터뷰 연구, 신규심의, 일반 동의 절차를 지원합니다.")
    st.caption("미성년자, 대리 동의, 임상시험, 인체유래물, 심의면제 판단은 확장 대상입니다.")
    if session:
        st.write(CATALOG.institutions[session.institution]["name"])
        st.caption({"manual": "객관식 모드", "ai": "AI 사실 추출 사용", "ai_unavailable": "AI 해석 실패 후 객관식 진행"}[session.mode])
    st.button("새 연구로 시작", on_click=reset, key="reset")
    st.caption(f"규칙 {CATALOG.version}\n기관 담당자 검수 전인 개발용 버전입니다.")
if phase == "initial":
    initial_screen()
elif phase == "review":
    review_screen(session)
elif phase == "questions":
    questions_screen(session)
else:
    report_screen(session)
