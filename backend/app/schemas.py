from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


PROTECTED_TERMS = ("年龄", "性别", "婚育", "民族", "宗教", "race", "gender", "age", "pregnan", "religion")


class RequirementInput(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    priority: str = Field(default="required", pattern="^(required|preferred)$")

    @field_validator("description")
    @classmethod
    def disallow_protected_characteristics(cls, value: str) -> str:
        if any(term in value.lower() for term in PROTECTED_TERMS):
            raise ValueError("岗位要求不得包含敏感个人特征")
        return value


class RequirementUpdate(RequirementInput):
    position: int | None = Field(default=None, ge=0)


class RequirementOut(RequirementInput):
    id: str
    position: int
    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    evaluation_prompt: str = Field(min_length=1)
    passing_score: int = Field(default=80, ge=0, le=100)
    requirements: list[RequirementInput] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    evaluation_prompt: str | None = Field(default=None, min_length=1)
    passing_score: int | None = Field(default=None, ge=0, le=100)


class RoleOut(BaseModel):
    id: str
    name: str
    evaluation_prompt: str
    passing_score: int
    archived: bool
    requirements: list[RequirementOut]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReorderRequirements(BaseModel):
    requirement_ids: list[str]


class BatchStart(BaseModel):
    profile_id: str


class FileOut(BaseModel):
    id: str
    original_name: str
    status: str
    error: str | None
    model_config = ConfigDict(from_attributes=True)


class EvaluationOut(BaseModel):
    id: str
    score: int | None
    qualified: bool | None
    reason: str | None
    satisfied: list[str]
    unmet: list[str]
    evidence: list[dict]
    provider: str | None
    error: str | None
    model_config = ConfigDict(from_attributes=True)


class CandidateOut(BaseModel):
    file: FileOut
    evaluation: EvaluationOut | None


class BatchOut(BaseModel):
    id: str
    status: str
    profile_id: str | None
    criteria_snapshot: dict | None
    files: list[FileOut]
    counts: dict[str, int]
    model_config = ConfigDict(from_attributes=True)
