import asyncio
import json
import re
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field, SecretStr

from .config import Settings


class Finding(BaseModel):
    requirement: str
    evidence: str = Field(min_length=1)


class EvaluationResult(BaseModel):
    score: int = Field(ge=0, le=100)
    reason: str = Field(min_length=1)
    satisfied: list[Finding] = Field(default_factory=list)
    unmet: list[str] = Field(default_factory=list)


def parse_structured_result(value: object) -> EvaluationResult:
    """Validate native structured output or a JSON text fallback."""
    if isinstance(value, EvaluationResult):
        return value
    if isinstance(value, dict):
        return EvaluationResult.model_validate(value)
    if not isinstance(value, str):
        raise ValueError("评分结果不是 JSON 对象")
    text = value.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("评分结果不是有效 JSON") from exc
    return EvaluationResult.model_validate(payload)


@dataclass(frozen=True)
class EvaluationInput:
    prompt: str
    requirements: list[dict]
    resume_text: str


class EvaluationProvider(Protocol):
    async def evaluate(self, item: EvaluationInput) -> EvaluationResult: ...


SENSITIVE_TERMS = ("年龄", "性别", "婚", "民族", "religion", "gender", "race", "age", "pregnan")


class HeuristicProvider:
    """Local deterministic provider used for development and automated tests."""

    async def evaluate(self, item: EvaluationInput) -> EvaluationResult:
        text = item.resume_text.lower()
        requirements = [entry["description"] for entry in item.requirements] or _freeform_requirements(item.prompt)
        matched: list[Finding] = []
        unmet: list[str] = []
        for requirement in requirements:
            if _is_soft_preference(requirement) or any(term in requirement.lower() for term in SENSITIVE_TERMS):
                continue
            terms = _search_terms(requirement)
            matched_terms = [term for term in terms if term in text]
            if matched_terms and (len(matched_terms) >= 1 if any("\u4e00" <= char <= "\u9fff" for char in requirement) else len(matched_terms) == len(terms)):
                index = text.index(matched_terms[0])
                matched.append(Finding(requirement=requirement, evidence=item.resume_text[max(0, index - 60): index + 180]))
            else:
                unmet.append(requirement)
        scored_requirements = [requirement for requirement in requirements if not _is_soft_preference(requirement) and not any(term in requirement.lower() for term in SENSITIVE_TERMS)]
        score = round(100 * len(matched) / len(scored_requirements)) if scored_requirements else 50
        summary = "岗位要求匹配度良好。" if score >= 80 else "关键岗位要求尚未得到充分证据支持。"
        return EvaluationResult(score=score, reason=summary, satisfied=matched, unmet=unmet)


def _freeform_requirements(prompt: str) -> list[str]:
    fragments = re.split(r"(?:\r?\n|[；;])+", prompt)
    cleaned: list[str] = []
    for fragment in fragments:
        value = re.sub(r"^\s*(?:[一二三四五六七八九十]+|\d+)[、.)）:]?\s*", "", fragment).strip(" -•：:")
        if len(value) >= 2:
            cleaned.append(value)
    return cleaned or ([prompt.strip()] if prompt.strip() else [])


def _search_terms(requirement: str) -> list[str]:
    return [term for term in re.findall(r"[a-z0-9+#.-]+|[\u4e00-\u9fff]{2,}", requirement.lower()) if len(term) > 1]


def _is_soft_preference(requirement: str) -> bool:
    return any(token in requirement for token in ("优先", "加分", "性格", "气质", "开朗", "偏好"))


class AgentScopeProvider:
    """Production provider that uses AgentScope v2 structured output."""

    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise RuntimeError("使用 AgentScope 前必须配置 OPENAI_API_KEY")
        if not settings.openai_model:
            raise RuntimeError("使用 AgentScope 前必须配置 OPENAI_MODEL")
        if not settings.openai_base_url:
            raise RuntimeError("使用 AgentScope 前必须配置 OPENAI_BASE_URL")
        self.settings = settings

    async def evaluate(self, item: EvaluationInput) -> EvaluationResult:
        from agentscope.agent import Agent
        from agentscope.credential import OpenAICredential
        from agentscope.formatter import OpenAIChatFormatter
        from agentscope.message import Msg, TextBlock
        from agentscope.model import OpenAIChatModel

        credential = OpenAICredential(api_key=SecretStr(self.settings.openai_api_key), base_url=self.settings.openai_base_url)
        model = OpenAIChatModel(
            credential=credential,
            model=self.settings.openai_model,
            stream=False,
            formatter=OpenAIChatFormatter(),
        )
        system_prompt = (
            "你是招聘初筛助手。仅根据提供的简历文本和完整岗位规则评分。"
            "先区分岗位职责、候选人必要条件、优先条件和模糊的主观偏好；职责用于理解上下文，必要条件决定核心匹配，优先条件作为加分项。"
            "模糊偏好不能作为唯一淘汰理由。"
            "不得使用年龄、性别、婚育、民族、照片、宗教等敏感特征。"
            "每个结论必须给出原文证据；不确定时列为未满足。"
        )
        agent = Agent(name="ResumeEvaluator", system_prompt=system_prompt, model=model)
        user_prompt = json.dumps(
            {"job_prompt": item.prompt, "requirements": item.requirements, "resume_text": item.resume_text},
            ensure_ascii=False,
        )
        reply = await agent.reply(
            Msg(name="Recruiter", role="user", content=[TextBlock(text=user_prompt)]),
            structured_schema=EvaluationResult,
        )
        if reply.structured_output:
            return parse_structured_result(reply.structured_output)
        fallback = reply.get_text_content()
        if fallback:
            return parse_structured_result(fallback)
        raise ValueError("AgentScope 未返回结构化评分")


def provider_for(settings: Settings) -> EvaluationProvider:
    if settings.evaluation_provider.lower() in {"agentscope", "bailian"}:
        return AgentScopeProvider(settings)
    return HeuristicProvider()


def is_qualified(score: int, passing_score: int) -> bool:
    """The application, never model prose, owns the final threshold comparison."""
    return score >= passing_score
