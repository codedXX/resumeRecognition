import asyncio
import json
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
        requirements = [entry["description"] for entry in item.requirements]
        matched: list[Finding] = []
        unmet: list[str] = []
        for requirement in requirements:
            if any(term in requirement.lower() for term in SENSITIVE_TERMS):
                continue
            terms = [term for term in requirement.lower().replace("/", " ").split() if len(term) > 1]
            if terms and all(term in text for term in terms):
                index = text.index(terms[0])
                matched.append(Finding(requirement=requirement, evidence=item.resume_text[max(0, index - 60): index + 180]))
            else:
                unmet.append(requirement)
        score = round(100 * len(matched) / len(requirements)) if requirements else 50
        summary = "岗位要求匹配度良好。" if score >= 80 else "关键岗位要求尚未得到充分证据支持。"
        return EvaluationResult(score=score, reason=summary, satisfied=matched, unmet=unmet)


class AgentScopeProvider:
    """Production provider that uses AgentScope v2 structured output."""

    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise RuntimeError("使用 AgentScope 前必须配置 OPENAI_API_KEY")
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
            "你是招聘初筛助手。仅根据提供的简历文本和岗位要求评分。"
            "不得使用年龄、性别、婚育、民族、照片、宗教等敏感特征。"
            "每个结论必须给出原文证据；不确定时列为未满足。"
        )
        agent = Agent(name="ResumeEvaluator", system_prompt=system_prompt, model=model)
        user_prompt = json.dumps(
            {"job_prompt": item.prompt, "requirements": item.requirements, "resume_text": item.resume_text},
            ensure_ascii=False,
        )
        reply = await asyncio.to_thread(
            agent.reply,
            Msg(name="Recruiter", role="user", content=[TextBlock(text=user_prompt)]),
            EvaluationResult,
        )
        if not reply.structured_output:
            raise ValueError("AgentScope 未返回结构化评分")
        return EvaluationResult.model_validate(reply.structured_output)


def provider_for(settings: Settings) -> EvaluationProvider:
    if settings.evaluation_provider.lower() == "agentscope":
        return AgentScopeProvider(settings)
    return HeuristicProvider()


def is_qualified(score: int, passing_score: int) -> bool:
    """The application, never model prose, owns the final threshold comparison."""
    return score >= passing_score
