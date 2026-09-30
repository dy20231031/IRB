from types import SimpleNamespace

import pytest

from src.agent import api
from src.agent.llm import validate_proposals, extract_facts


def test_proposals_need_explicit_confirmation(scoped):
    raw = [{"field": "collect_name", "value": "yes", "evidence": "이름을 받습니다"}]
    session = api.start("cuk", scoped, narrative="이름을 받습니다", use_ai=True, extractor=lambda _: raw)
    assert "collect_name" not in session.answers
    without = api.confirm(session)
    assert "collect_name" not in without.answers
    confirmed = api.confirm(session, {"collect_name": "yes"})
    assert confirmed.answers["collect_name"] == "yes"
    assert confirmed.origins["collect_name"] == "user_confirmed_ai"


def test_conflict_cannot_silently_overwrite_manual(scoped):
    raw = [{"field": "collect_phone", "value": "yes", "evidence": "번호를 받습니다"}]
    session = api.start("cuk", {**scoped, "collect_phone": "no"}, narrative="번호를 받습니다", use_ai=True, extractor=lambda _: raw)
    assert session.proposals[0].conflict
    with pytest.raises(ValueError):
        api.confirm(session, {"collect_phone": "yes"})
    assert api.confirm(session).answers["collect_phone"] == "no"


@pytest.mark.parametrize("raw", [
    [{"field": "delete_all_documents", "value": "yes", "evidence": "이름"}],
    [{"field": "collect_name", "value": "maybe", "evidence": "이름"}],
    [{"field": "collect_name", "value": "yes", "evidence": "없는 원문"}],
    [{"field": "collect_name", "value": "yes", "evidence": ""}],
    [{"field": "collect_name", "value": "yes", "evidence": "이름"}] * 2,
    {"facts": []},
])
def test_invalid_extraction_rejected(raw):
    with pytest.raises(ValueError):
        validate_proposals(raw, "이름을 받습니다", {})


def test_api_failure_is_safe_fallback_without_sensitive_error(scoped):
    def failing(_):
        raise RuntimeError("secret-api-key and private research details")
    session = api.start("cuk", scoped, narrative="가상 예시", use_ai=True, extractor=failing)
    assert session.mode == "ai_unavailable"
    assert "secret-api-key" not in session.message
    assert not session.proposals
    assert api.confirm(session).phase == "questions"


def test_no_key_is_manual_fallback(scoped, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    session = api.start("cuk", scoped, narrative="가상 예시", use_ai=True)
    assert session.mode == "ai_unavailable"


def test_unproposed_field_cannot_be_confirmed(scoped):
    with pytest.raises(ValueError):
        api.confirm(api.start("cuk", scoped), {"collect_name": "yes"})


def test_provider_adapter_uses_schema_timeout_and_no_storage(monkeypatch):
    import openai
    calls = {}

    class FakeClient:
        def __init__(self, **kwargs):
            calls["config"] = kwargs
            self.responses = self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def parse(self, **kwargs):
            calls["request"] = kwargs
            parsed = kwargs["text_format"].model_validate({"facts": [{"field": "collect_name", "value": "yes", "evidence": "이름을 받습니다"}]})
            return SimpleNamespace(output_parsed=parsed)

    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    assert extract_facts("이름을 받습니다")[0]["field"] == "collect_name"
    assert calls["config"]["timeout"] == 25.0
    assert calls["config"]["max_retries"] == 0
    assert calls["request"]["store"] is False
    assert calls["request"]["input"][1]["content"] == "이름을 받습니다"
