import json
from dataclasses import asdict

from .catalog import CATALOG
from .models import ANSWER_LABELS, DELIVERY_LABELS, STATUS_LABELS

READINESS_LABELS = {"unknown": "미확인", "preparing": "준비 중 (사용자 표시)", "ready": "준비함 (사용자 표시)"}


def report_data(session, assessment):
    used_sources = {s for d in assessment.decisions for s in d.source_ids}
    return {
        "schema_version": "1.0",
        "assessment": asdict(assessment),
        "institution_name": CATALOG.institutions[session.institution]["name"],
        "mode": session.mode,
        "rounds_used": session.rounds,
        "answers": session.answers,
        "answer_origins": session.origins,
        "readiness": {d.rule_id: session.readiness.get(d.rule_id, "unknown") for d in assessment.decisions},
        "sources": [CATALOG.sources[s] for s in sorted(used_sources)],
        "limitations": "입력 사실과 공개 자료 기준의 준비 안내입니다. 제출 적합성, 면제, 승인 여부를 결정하지 않습니다.",
        # Raw narrative, unconfirmed AI proposals, credentials are intentionally absent.
    }


def to_json(session, assessment):
    return json.dumps(report_data(session, assessment), ensure_ascii=False, indent=2)


def _cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def to_markdown(session, assessment):
    data = report_data(session, assessment)
    lines = ["# IRB 제출 준비 결과", "", f"기관: {data['institution_name']}",
             f"판단일: {assessment.evaluated_on} / 규칙: {assessment.rule_version}", "", data["limitations"], "",
             "## 확인할 사항", ""]
    lines += [f"- {message}" for message in assessment.scope_issues + assessment.warnings]
    lines += ["", "## 체크리스트", "", "| 항목 | 필요 여부 | 처리 방법 | 준비 상태 | 이유 |",
              "|---|---|---|---|---|"]
    for d in assessment.decisions:
        values = [d.document, STATUS_LABELS[d.status], DELIVERY_LABELS[d.delivery],
                  READINESS_LABELS[session.readiness.get(d.rule_id, "unknown")], d.reason]
        lines.append("| " + " | ".join(_cell(v) for v in values) + " |")
    lines += ["", "## 항목별 근거", ""]
    for d in assessment.decisions:
        lines += [f"### {d.rule_id}: {d.document}", "", d.details, ""]
        for source_id in d.source_ids:
            s = CATALOG.sources[source_id]
            lines.append(f"- [{s['title']}]({s['url']}) / 확인일 {s['checked_on']} / {s['version_note']}")
        facts = ", ".join(f"{CATALOG.fields[k]['label']}={ANSWER_LABELS[v]}" for k, v in d.facts_used.items())
        if facts:
            lines += ["", "판단에 사용한 답변: " + facts]
        lines.append("")
    return "\n".join(lines)
