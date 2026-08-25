from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, sessionmaker

from .config import Settings, settings
from .database import Base, get_session, make_session_factory
from .evaluation import EvaluationInput, is_qualified, provider_for
from .models import Evaluation, EvaluationBatch, JobProfile, ResumeFile, RoleRequirement
from .parsers import extract_resume_text
from .schemas import (
    BatchOut,
    BatchStart,
    CandidateOut,
    EvaluationOut,
    FileOut,
    ReorderRequirements,
    RequirementInput,
    RequirementOut,
    RequirementUpdate,
    RoleCreate,
    RoleOut,
    RoleUpdate,
)


def profile_snapshot(profile: JobProfile) -> dict:
    return {
        "profile_id": profile.id,
        "name": profile.name,
        "evaluation_prompt": profile.evaluation_prompt,
        "passing_score": profile.passing_score,
        "requirements": [
            {"id": item.id, "description": item.description, "priority": item.priority, "position": item.position}
            for item in profile.requirements
        ],
    }


def batch_counts(batch: EvaluationBatch) -> dict[str, int]:
    counts = Counter(item.status for item in batch.files)
    return {key: counts.get(key, 0) for key in ("pending", "ready", "processing", "completed", "failed", "unreadable")}


def serialise_batch(batch: EvaluationBatch) -> BatchOut:
    return BatchOut(
        id=batch.id,
        status=batch.status,
        profile_id=batch.profile_id,
        criteria_snapshot=batch.criteria_snapshot,
        files=[FileOut.model_validate(item) for item in batch.files],
        counts=batch_counts(batch),
    )


def locate_batch(session: Session, batch_id: str) -> EvaluationBatch:
    batch = session.scalar(select(EvaluationBatch).where(EvaluationBatch.id == batch_id).options(selectinload(EvaluationBatch.files)))
    if not batch:
        raise HTTPException(status_code=404, detail="未找到该批次")
    return batch


def locate_profile(session: Session, profile_id: str, active_only: bool = False) -> JobProfile:
    statement = select(JobProfile).where(JobProfile.id == profile_id).options(selectinload(JobProfile.requirements))
    profile = session.scalar(statement)
    if not profile or (active_only and profile.archived):
        raise HTTPException(status_code=404, detail="未找到该岗位")
    return profile


def evaluate_batch(factory: sessionmaker[Session], runtime_settings: Settings, batch_id: str) -> None:
    session = factory()
    try:
        batch = locate_batch(session, batch_id)
        snapshot = batch.criteria_snapshot or {}
        provider = provider_for(runtime_settings)
        for file in batch.files:
            if file.status != "ready":
                continue
            file.status = "processing"
            session.commit()
            try:
                item = EvaluationInput(prompt=snapshot["evaluation_prompt"], requirements=snapshot["requirements"], resume_text=file.extracted_text or "")
                last_error: Exception | None = None
                result = None
                for _ in range(2):
                    try:
                        result = __import__("asyncio").run(provider.evaluate(item))
                        break
                    except Exception as exc:
                        last_error = exc
                if result is None:
                    raise last_error or ValueError("评分结果无效")
                qualified = is_qualified(result.score, snapshot["passing_score"])
                session.add(
                    Evaluation(
                        resume_file_id=file.id,
                        score=result.score,
                        qualified=qualified,
                        reason=result.reason,
                        satisfied=[item.requirement for item in result.satisfied],
                        unmet=result.unmet,
                        evidence=[item.model_dump() for item in result.satisfied],
                        provider=runtime_settings.evaluation_provider,
                    )
                )
                file.status = "completed"
            except Exception as exc:  # Each file must fail independently.
                file.status = "failed"
                file.error = "评分服务未返回有效结果"
                session.add(Evaluation(resume_file_id=file.id, provider=runtime_settings.evaluation_provider, error=str(exc)))
            session.commit()
        batch.status = "completed"
        session.commit()
    finally:
        session.close()


def create_app(runtime_settings: Settings | None = None) -> FastAPI:
    active_settings = runtime_settings or settings
    active_settings.upload_dir.mkdir(parents=True, exist_ok=True)
    factory = make_session_factory(active_settings.database_url)
    Base.metadata.create_all(factory.kw["bind"])

    app = FastAPI(title="AI Resume Review API", version="0.1.0")
    app.state.session_factory = factory
    app.state.settings = active_settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def session_dependency():
        yield from get_session(factory)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/roles", response_model=list[RoleOut])
    def list_roles(session: Session = Depends(session_dependency)):
        return session.scalars(
            select(JobProfile).where(JobProfile.archived.is_(False)).options(selectinload(JobProfile.requirements)).order_by(JobProfile.updated_at.desc())
        ).all()

    @app.post("/api/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
    def create_role(payload: RoleCreate, session: Session = Depends(session_dependency)):
        profile = JobProfile(name=payload.name.strip(), evaluation_prompt=payload.evaluation_prompt, passing_score=payload.passing_score)
        profile.requirements = [
            RoleRequirement(description=item.description, priority=item.priority, position=index)
            for index, item in enumerate(payload.requirements)
        ]
        session.add(profile)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="岗位名称已存在") from None
        session.refresh(profile)
        return profile

    @app.get("/api/roles/{profile_id}", response_model=RoleOut)
    def get_role(profile_id: str, session: Session = Depends(session_dependency)):
        return locate_profile(session, profile_id)

    @app.put("/api/roles/{profile_id}", response_model=RoleOut)
    def update_role(profile_id: str, payload: RoleUpdate, session: Session = Depends(session_dependency)):
        profile = locate_profile(session, profile_id, active_only=True)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(profile, field, value.strip() if field == "name" else value)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="岗位名称已存在") from None
        session.refresh(profile)
        return profile

    @app.delete("/api/roles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_role(profile_id: str, session: Session = Depends(session_dependency)):
        profile = locate_profile(session, profile_id)
        used = session.scalar(select(EvaluationBatch.id).where(EvaluationBatch.profile_id == profile.id).limit(1))
        if used:
            profile.archived = True
        else:
            session.delete(profile)
        session.commit()

    @app.post("/api/roles/{profile_id}/requirements", response_model=RequirementOut, status_code=status.HTTP_201_CREATED)
    def add_requirement(profile_id: str, payload: RequirementInput, session: Session = Depends(session_dependency)):
        profile = locate_profile(session, profile_id, active_only=True)
        requirement = RoleRequirement(
            profile_id=profile.id, description=payload.description, priority=payload.priority, position=len(profile.requirements)
        )
        session.add(requirement)
        session.commit()
        session.refresh(requirement)
        return requirement

    @app.patch("/api/roles/{profile_id}/requirements/{requirement_id}", response_model=RequirementOut)
    def update_requirement(profile_id: str, requirement_id: str, payload: RequirementUpdate, session: Session = Depends(session_dependency)):
        locate_profile(session, profile_id, active_only=True)
        requirement = session.scalar(select(RoleRequirement).where(RoleRequirement.id == requirement_id, RoleRequirement.profile_id == profile_id))
        if not requirement:
            raise HTTPException(status_code=404, detail="未找到该岗位要求")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(requirement, field, value)
        session.commit()
        session.refresh(requirement)
        return requirement

    @app.delete("/api/roles/{profile_id}/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_requirement(profile_id: str, requirement_id: str, session: Session = Depends(session_dependency)):
        locate_profile(session, profile_id, active_only=True)
        requirement = session.scalar(select(RoleRequirement).where(RoleRequirement.id == requirement_id, RoleRequirement.profile_id == profile_id))
        if not requirement:
            raise HTTPException(status_code=404, detail="未找到该岗位要求")
        session.delete(requirement)
        session.commit()

    @app.post("/api/roles/{profile_id}/requirements/reorder", response_model=list[RequirementOut])
    def reorder_requirements(profile_id: str, payload: ReorderRequirements, session: Session = Depends(session_dependency)):
        profile = locate_profile(session, profile_id, active_only=True)
        known = {item.id: item for item in profile.requirements}
        if set(payload.requirement_ids) != set(known):
            raise HTTPException(status_code=422, detail="排序列表必须包含该岗位全部要求")
        for position, requirement_id in enumerate(payload.requirement_ids):
            known[requirement_id].position = position
        session.commit()
        return session.scalars(select(RoleRequirement).where(RoleRequirement.profile_id == profile_id).order_by(RoleRequirement.position)).all()

    @app.post("/api/batches", response_model=BatchOut, status_code=status.HTTP_201_CREATED)
    def create_batch(session: Session = Depends(session_dependency)):
        batch = EvaluationBatch()
        session.add(batch)
        session.commit()
        session.refresh(batch)
        return serialise_batch(batch)

    @app.post("/api/batches/{batch_id}/files", response_model=list[FileOut], status_code=status.HTTP_201_CREATED)
    async def upload_files(batch_id: str, files: list[UploadFile] = File(...), session: Session = Depends(session_dependency)):
        batch = locate_batch(session, batch_id)
        if batch.status != "pending":
            raise HTTPException(status_code=409, detail="已经开始的批次不能继续上传")
        if len(batch.files) + len(files) > active_settings.max_batch_files:
            raise HTTPException(status_code=422, detail=f"每批最多上传 {active_settings.max_batch_files} 份简历")
        uploaded: list[ResumeFile] = []
        for upload in files:
            filename = upload.filename or "unnamed"
            suffix = Path(filename).suffix.lower()
            content = await upload.read()
            file = ResumeFile(batch_id=batch.id, original_name=Path(filename).name, content_type=upload.content_type)
            if suffix not in {".pdf", ".docx"}:
                file.status, file.error = "failed", "仅支持 PDF 和 DOCX 简历"
            elif len(content) > active_settings.max_upload_bytes:
                file.status, file.error = "failed", "文件超过大小限制"
            else:
                storage_key = f"{uuid4()}{suffix}"
                try:
                    text = extract_resume_text(filename, content)
                    (active_settings.upload_dir / storage_key).write_bytes(content)
                    file.storage_key, file.extracted_text, file.status = storage_key, text, "ready"
                except Exception as exc:
                    file.status, file.error = "unreadable", str(exc)
            session.add(file)
            uploaded.append(file)
        session.commit()
        return [FileOut.model_validate(item) for item in uploaded]

    @app.post("/api/batches/{batch_id}/start", response_model=BatchOut)
    def start_batch(batch_id: str, payload: BatchStart, background_tasks: BackgroundTasks, session: Session = Depends(session_dependency)):
        batch = locate_batch(session, batch_id)
        if batch.status != "pending":
            raise HTTPException(status_code=409, detail="该批次已开始")
        ready_files = [item for item in batch.files if item.status == "ready"]
        if not ready_files:
            raise HTTPException(status_code=422, detail="没有可评估的简历")
        profile = locate_profile(session, payload.profile_id, active_only=True)
        batch.profile_id, batch.criteria_snapshot = profile.id, profile_snapshot(profile)
        batch.status, batch.started_at = "processing", datetime.now(timezone.utc)
        session.commit()
        session.refresh(batch)
        background_tasks.add_task(evaluate_batch, factory, active_settings, batch.id)
        return serialise_batch(batch)

    @app.get("/api/batches/{batch_id}", response_model=BatchOut)
    def get_batch(batch_id: str, session: Session = Depends(session_dependency)):
        return serialise_batch(locate_batch(session, batch_id))

    @app.get("/api/batches/{batch_id}/results", response_model=list[CandidateOut])
    def list_results(
        batch_id: str,
        state: str | None = Query(default=None, pattern="^(qualified|unqualified|failed)$"),
        min_score: int | None = Query(default=None, ge=0, le=100),
        max_score: int | None = Query(default=None, ge=0, le=100),
        session: Session = Depends(session_dependency),
    ):
        batch = locate_batch(session, batch_id)
        candidates: list[CandidateOut] = []
        for file in batch.files:
            evaluation = session.scalar(select(Evaluation).where(Evaluation.resume_file_id == file.id))
            if state == "failed" and file.status != "failed":
                continue
            if state == "qualified" and (not evaluation or evaluation.qualified is not True):
                continue
            if state == "unqualified" and (not evaluation or evaluation.qualified is not False):
                continue
            if evaluation and min_score is not None and (evaluation.score is None or evaluation.score < min_score):
                continue
            if evaluation and max_score is not None and (evaluation.score is None or evaluation.score > max_score):
                continue
            candidates.append(CandidateOut(file=FileOut.model_validate(file), evaluation=EvaluationOut.model_validate(evaluation) if evaluation else None))
        return candidates

    @app.get("/api/evaluations/{evaluation_id}", response_model=CandidateOut)
    def get_evaluation(evaluation_id: str, session: Session = Depends(session_dependency)):
        evaluation = session.scalar(select(Evaluation).where(Evaluation.id == evaluation_id).options(selectinload(Evaluation.resume_file)))
        if not evaluation:
            raise HTTPException(status_code=404, detail="未找到评分结果")
        return CandidateOut(file=FileOut.model_validate(evaluation.resume_file), evaluation=EvaluationOut.model_validate(evaluation))

    return app


app = create_app()
