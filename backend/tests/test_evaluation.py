import asyncio
import os

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.evaluation import AgentScopeProvider, EvaluationInput, EvaluationResult, HeuristicProvider, is_qualified, parse_structured_result, provider_for
from app.parsers import extract_resume_text


def text_pdf(text: str) -> bytes:
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream",
    ]
    result = b"%PDF-1.4\n"; offsets = [0]
    for index, item in enumerate(objects, start=1):
        offsets.append(len(result)); result += f"{index} 0 obj\n".encode() + item + b"\nendobj\n"
    xref = len(result); result += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    result += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    return result + f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()


def test_extracts_text_pdf_and_rejects_empty_content():
    assert "Python FastAPI" in extract_resume_text("candidate.pdf", text_pdf("Python FastAPI experience delivery"))
    with pytest.raises(ValueError, match="未能提取"):
        extract_resume_text("empty.pdf", text_pdf(""))


def test_structured_result_and_threshold_boundaries():
    with pytest.raises(ValidationError):
        EvaluationResult(score=101, reason="invalid")
    assert is_qualified(80, 80) is True
    assert is_qualified(84, 85) is False


def test_development_provider_returns_evidence():
    output = asyncio.run(HeuristicProvider().evaluate(EvaluationInput(prompt="评分", requirements=[{"description": "Python FastAPI", "priority": "required"}], resume_text="五年 Python FastAPI 开发经验")))
    assert output.score == 100
    assert output.satisfied[0].evidence


def test_heuristic_provider_uses_freeform_job_rules_without_structured_requirements():
    output = asyncio.run(HeuristicProvider().evaluate(EvaluationInput(
        prompt="1、负责电商视觉与活动页面；\n2、熟悉 AI 工作流；\n3、性格开朗优先。",
        requirements=[],
        resume_text="负责电商视觉与活动页面，熟悉 AI 工作流。",
    )))
    assert output.score > 50
    assert any("电商视觉" in finding.requirement for finding in output.satisfied)
    assert not any("性格开朗" in item for item in output.unmet)


def test_json_fallback_parses_fenced_object_and_rejects_invalid_shape():
    parsed = parse_structured_result('```json\n{"score": 72, "reason": "证据不足", "satisfied": [], "unmet": ["Docker"]}\n```')
    assert parsed.score == 72
    with pytest.raises(ValueError):
        parse_structured_result("不是 JSON")


def test_bailian_provider_alias_uses_agentscope(monkeypatch):
    class Sentinel:
        def __init__(self, _settings):
            pass

    monkeypatch.setattr("app.evaluation.AgentScopeProvider", Sentinel)
    assert isinstance(provider_for(Settings(evaluation_provider="bailian")), Sentinel)


def test_bailian_provider_requires_backend_key():
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        AgentScopeProvider(Settings(evaluation_provider="bailian", openai_api_key=None))
    with pytest.raises(RuntimeError, match="OPENAI_MODEL"):
        AgentScopeProvider(Settings(evaluation_provider="bailian", openai_api_key="secret", openai_model=""))


def test_bailian_provider_awaits_async_agent_and_parses_structured_output(monkeypatch):
    class FakeReply:
        structured_output = {
            "score": 88,
            "reason": "证据充分",
            "satisfied": [{"requirement": "Python", "evidence": "五年 Python 经验"}],
            "unmet": [],
        }

        def get_text_content(self):
            return ""

    class FakeAgent:
        def __init__(self, **_kwargs):
            pass

        async def reply(self, *_args, **_kwargs):
            return FakeReply()

    monkeypatch.setattr("agentscope.agent.Agent", FakeAgent)
    monkeypatch.setattr("agentscope.model.OpenAIChatModel", lambda **_kwargs: object())
    provider = AgentScopeProvider(Settings(evaluation_provider="bailian", openai_api_key="secret"))

    result = asyncio.run(
        provider.evaluate(
            EvaluationInput(
                prompt="评分",
                requirements=[{"description": "Python", "priority": "required"}],
                resume_text="五年 Python 经验",
            )
        )
    )

    assert result.score == 88
    assert result.reason == "证据充分"
    assert result.satisfied[0].evidence == "五年 Python 经验"


@pytest.mark.parametrize(
    "text",
    [
        '{"score": 72, "reason": "文本结果", "satisfied": [], "unmet": []}',
        '```json\n{"score": 73, "reason": "代码块结果", "satisfied": [], "unmet": []}\n```',
    ],
)
def test_bailian_provider_parses_json_text_fallback(monkeypatch, text):
    class FakeReply:
        structured_output = None

        def get_text_content(self):
            return text

    class FakeAgent:
        def __init__(self, **_kwargs):
            pass

        async def reply(self, *_args, **_kwargs):
            return FakeReply()

    monkeypatch.setattr("agentscope.agent.Agent", FakeAgent)
    monkeypatch.setattr("agentscope.model.OpenAIChatModel", lambda **_kwargs: object())
    provider = AgentScopeProvider(Settings(evaluation_provider="bailian", openai_api_key="secret"))

    result = asyncio.run(provider.evaluate(EvaluationInput(prompt="评分", requirements=[], resume_text="简历")))

    assert result.score in {72, 73}
    assert result.satisfied == []


def test_bailian_provider_rejects_malformed_text_fallback(monkeypatch):
    class FakeReply:
        structured_output = None

        def get_text_content(self):
            return "这不是评分 JSON"

    class FakeAgent:
        def __init__(self, **_kwargs):
            pass

        async def reply(self, *_args, **_kwargs):
            return FakeReply()

    monkeypatch.setattr("agentscope.agent.Agent", FakeAgent)
    monkeypatch.setattr("agentscope.model.OpenAIChatModel", lambda **_kwargs: object())
    provider = AgentScopeProvider(Settings(evaluation_provider="bailian", openai_api_key="secret"))

    with pytest.raises(ValueError, match="有效 JSON"):
        asyncio.run(provider.evaluate(EvaluationInput(prompt="评分", requirements=[], resume_text="简历")))


@pytest.mark.skipif(os.getenv("RUN_BAILIAN_SMOKE") != "1", reason="显式设置 RUN_BAILIAN_SMOKE=1 才运行百炼联网冒烟测试")
def test_bailian_live_smoke_is_explicitly_opt_in():
    provider = provider_for(Settings(evaluation_provider="bailian"))
    result = asyncio.run(provider.evaluate(EvaluationInput(prompt="只返回结构化评分", requirements=[], resume_text="有五年后端开发经验。")))
    assert 0 <= result.score <= 100
