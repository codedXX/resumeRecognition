from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


def identifier() -> str:
    return str(uuid4())


class JobProfile(Base):
    __tablename__ = "job_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    evaluation_prompt: Mapped[str] = mapped_column(Text)
    passing_score: Mapped[int] = mapped_column(Integer, default=80)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    requirements: Mapped[list["RoleRequirement"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="RoleRequirement.position"
    )


class RoleRequirement(Base):
    __tablename__ = "role_requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    profile_id: Mapped[str] = mapped_column(ForeignKey("job_profiles.id"), index=True)
    description: Mapped[str] = mapped_column(String(500))
    priority: Mapped[str] = mapped_column(String(20), default="required")
    position: Mapped[int] = mapped_column(Integer, default=0)
    profile: Mapped[JobProfile] = relationship(back_populates="requirements")


class EvaluationBatch(Base):
    __tablename__ = "evaluation_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("job_profiles.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    criteria_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    files: Mapped[list["ResumeFile"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class ResumeFile(Base):
    __tablename__ = "resume_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    batch_id: Mapped[str] = mapped_column(ForeignKey("evaluation_batches.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    batch: Mapped[EvaluationBatch] = relationship(back_populates="files")
    evaluation: Mapped["Evaluation | None"] = relationship(back_populates="resume_file", uselist=False, cascade="all, delete-orphan")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    resume_file_id: Mapped[str] = mapped_column(ForeignKey("resume_files.id"), unique=True, index=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qualified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    satisfied: Mapped[list] = mapped_column(JSON, default=list)
    unmet: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    resume_file: Mapped[ResumeFile] = relationship(back_populates="evaluation")
