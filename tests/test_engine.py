from datetime import date

import pytest

from src.agent.catalog import CATALOG
from src.agent.engine import assess, evaluate_condition


def decision(institution, answers, rule_id, **kwargs):
    return next(d for d in assess(institution, answers, **kwargs).decisions if d.rule_id == rule_id)


@pytest.mark.parametrize("field", ["collect_name", "collect_email", "collect_unique_id", "recruitment_identifiers", "compensation_identifiers", "followup_identifiers"])
def test_no_phone_does_not_remove_privacy_when_other_identifiers_exist(scoped, field):
    answers = {**scoped, "collect_phone": "no", field: "yes"}
    assert decision("cuk", answers, "cuk.participant_privacy").status == "required"


@pytest.mark.parametrize("updates", [
    {"collect_phone": "no"},
    {"collect_phone": "no", "other_data": "yes"},
    {"collect_phone": "no", "collect_media": "yes"},
    {"collect_phone": "no", "platform_identifiers": "yes"},
    {"collect_phone": "no", "linkage": "yes"},
    {k: "no" for k in CATALOG.fields if k not in CATALOG.scope_fields},
])
def test_privacy_never_excluded_without_an_institution_exclusion_rule(scoped, updates):
    assert decision("cuk", {**scoped, **updates}, "cuk.participant_privacy").status == "needs_confirmation"


def test_applicant_privacy_is_separate(scoped):
    result = decision("cuk", {**scoped, "collect_phone": "no"}, "cuk.researcher_privacy")
    assert result.status == "required"
    assert "collect_phone" not in result.facts_used


def test_sensitive_exclusion_requires_complete_inventory(scoped):
    answers = {**scoped, "collect_sensitive": "no", "other_data": "no", "external_data": "no"}
    assert decision("cuk", answers, "cuk.sensitive_consent").status == "needs_confirmation"
    answers["inventory_complete"] = "yes"
    assert decision("cuk", answers, "cuk.sensitive_consent").status == "not_applicable"
    answers["other_data"] = "unknown"
    assert decision("cuk", answers, "cuk.sensitive_consent").status == "needs_confirmation"


@pytest.mark.parametrize("value,status", [("yes", "required"), ("no", "not_applicable"), ("unknown", "needs_confirmation")])
@pytest.mark.parametrize("institution", ["cuk", "snue"])
def test_student_rule_is_three_valued(scoped, value, status, institution):
    assert decision(institution, {**scoped, "graduate_student": value}, institution + ".advisor").status == status


def test_cuk_cv_exception_is_not_copied_to_snue(scoped):
    answers = {**scoped, "all_fulltime_faculty": "yes"}
    assert decision("cuk", answers, "cuk.cv").status == "not_applicable"
    assert decision("snue", answers, "snue.cv").status == "required"


def test_snue_portal_tasks_are_not_file_requests(scoped):
    result = assess("snue", scoped)
    portal = {d.rule_id for d in result.decisions if d.delivery == "portal"}
    assert portal == {"snue.application", "snue.coi", "snue.pledge"}
    assert decision("snue", scoped, "snue.training").delivery == "file"


@pytest.mark.parametrize("field", CATALOG.scope_fields)
@pytest.mark.parametrize("value", ["no", "unknown"])
def test_out_of_scope_does_not_report_final_requirements(scoped, field, value):
    result = assess("cuk", {**scoped, field: value, "collect_name": "yes"})
    assert not result.scope_ok
    assert all(d.status == "needs_confirmation" for d in result.decisions)


def test_expired_source_downgrades_including_exclusions(scoped):
    result = assess("cuk", {**scoped, "graduate_student": "no"}, today=date(2027, 1, 1))
    assert all(d.status == "needs_confirmation" and d.source_stale for d in result.decisions)


def test_unknown_is_not_false():
    expr = {"op": "equals", "field": "collect_name", "value": "yes"}
    assert evaluate_condition(expr, {}) == "unknown"
    assert evaluate_condition(expr, {"collect_name": "no"}) == "no"


def test_invalid_input_rejected():
    with pytest.raises(ValueError):
        assess("other_university", {})
    with pytest.raises(ValueError):
        assess("cuk", {"collect_phone": False})


def test_every_conditional_rule_has_question_coverage():
    from src.agent.engine import dependencies
    covered = set(CATALOG.scope_fields) | {f for q in CATALOG.questions for f in q["fields"]}
    for rule in CATALOG.rules:
        fields = dependencies(rule["condition"]) | dependencies(rule.get("exclusion_condition")) | set(rule["review_fields"])
        assert fields <= covered
        assert rule["source_ids"]
