from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, settings
from .evaluation import EvaluationInput, EvaluationResult, is_qualified, provider_for
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
from .stores import EvaluationRecord, MemoryStore, RoleRecord, RoleStore, RoleStoreError, RuntimeBatch, RuntimeFile


logger = logging.getLogger(__name__)


def profile_snapshot(profile: RoleRecord) -> dict:
    return {
        "profile_id": profile.id,
        "name": profile.name,
        "evaluation_prompt": profile.evaluation_prompt,
        "passing_score": profile.passing_score,
        "requirements": [item.to_dict() for item in profile.requirements],
    }


def batch_counts(batch: RuntimeBatch) -> dict[str, int]:
    counts = Counter(item.status for item in batch.files)
    return {key: counts.get(key, 0) for key in ("pending", "ready", "processing", "completed", "failed", "unreadable")}


def serialise_file(file: RuntimeFile) -> FileOut:
    return FileOut.model_validate(file)


def serialise_evaluation(evaluation: EvaluationRecord | None) -> EvaluationOut | None:
    return EvaluationOut.model_validate(evaluation) if evaluation else None


def serialise_batch(batch: RuntimeBatch) -> BatchOut:
    return BatchOut(
        id=batch.id,
        status=batch.status,
        profile_id=batch.profile_id,
        criteria_snapshot=batch.criteria_snapshot,
        files=[serialise_file(item) for item in batch.files],
        counts=batch_counts(batch),
    )


def locate_batch(runtime_store: MemoryStore, batch_id: str) -> RuntimeBatch:
    batch = runtime_store.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="未找到该批次")
    return batch


def locate_profile(role_store: RoleStore, profile_id: str, active_only: bool = False) -> RoleRecord:
    profile = role_store.get(profile_id, active_only=active_only)
    if not profile:
        raise HTTPException(status_code=404, detail="未找到该岗位")
    return profile


def expire_pending_batches(runtime_store: MemoryStore, runtime_settings: Settings) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=runtime_settings.pending_input_retention_minutes)
    expired = 0
    with runtime_store.lock:
        for batch in list(runtime_store._batches.values()):
            if batch.status != "pending" or batch.created_at >= cutoff:
                continue
            batch.status = "expired"
            batch.finished_at = datetime.now(timezone.utc)
            for file in batch.files:
                if file.status in {"pending", "ready"}:
                    file.status = "failed"
                    file.error = "临时上传内容已过期，请重新上传"
                file.extracted_text = None
            expired += 1
    return expired


def evaluate_batch(runtime_store: MemoryStore, runtime_settings: Settings, batch_id: str) -> None:
    batch = runtime_store.get_batch(batch_id)
    if not batch:
        return
    snapshot = batch.criteria_snapshot or {}
    provider = provider_for(runtime_settings)
    for file in list(batch.files):
        with runtime_store.lock:
            if file.status != "ready":
                continue
            file.status = "processing"
            resume_text = file.extracted_text or ""
        try:
            item = EvaluationInput(
                prompt=snapshot["evaluation_prompt"],
                requirements=snapshot["requirements"],
                resume_text=resume_text,
            )
            result: EvaluationResult | None = None
            last_error: Exception | None = None
            for _ in range(2):
                try:
                    result = asyncio.run(provider.evaluate(item))
                    break
                except Exception as exc:
                    last_error = exc
            if result is None:
                raise last_error or ValueError("评分结果无效")
            evaluation = EvaluationRecord(
                id=_new_id(),
                score=result.score,
                qualified=is_qualified(result.score, snapshot["passing_score"]),
                reason=result.reason,
                satisfied=[finding.requirement for finding in result.satisfied],
                unmet=result.unmet,
                evidence=[finding.model_dump() for finding in result.satisfied],
                provider=runtime_settings.evaluation_provider,
            )
            with runtime_store.lock:
                file.evaluation = evaluation
                file.status = "completed"
        except Exception as exc:
            logger.warning("Resume evaluation failed file_id=%s error_type=%s", file.id, type(exc).__name__)
            with runtime_store.lock:
                file.evaluation = EvaluationRecord(
                    id=_new_id(),
                    provider=runtime_settings.evaluation_provider,
                    error="评分服务未返回有效结果",
                )
                file.status = "failed"
                file.error = "评分服务未返回有效结果"
        finally:
            with runtime_store.lock:
                file.extracted_text = None
    with runtime_store.lock:
        batch.status = "completed"
        batch.finished_at = datetime.now(timezone.utc)


def _new_id() -> str:
    from uuid import uuid4

    return str(uuid4())


def _handle_store_error(error: RoleStoreError) -> HTTPException:
    if "已存在" in str(error):
        return HTTPException(status_code=409, detail=str(error))
    return HTTPException(status_code=500, detail="岗位规则文件不可用")


def create_app(runtime_settings: Settings | None = None) -> FastAPI:
    active_settings = runtime_settings or settings
    if active_settings.workers != 1:
        raise ValueError("内存分析运行时仅支持单 worker")
    role_store = RoleStore(active_settings.roles_file)
    runtime_store = MemoryStore(active_settings.analysis_retention_minutes)

    app = FastAPI(title="AI Resume Review API", version="0.2.0")
    app.state.role_store = role_store
    app.state.runtime_store = runtime_store
    app.state.settings = active_settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/roles", response_model=list[RoleOut])
    def list_roles():
        return role_store.list()

    @app.post("/api/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
    def create_role(payload: RoleCreate):
        try:
            return role_store.create(
                name=payload.name.strip(),
                evaluation_prompt=payload.evaluation_prompt,
                passing_score=payload.passing_score,
                requirements=[item.model_dump() for item in payload.requirements],
            )
        except RoleStoreError as error:
            raise _handle_store_error(error) from error

    @app.get("/api/roles/{profile_id}", response_model=RoleOut)
    def get_role(profile_id: str):
        return locate_profile(role_store, profile_id)

    @app.put("/api/roles/{profile_id}", response_model=RoleOut)
    def update_role(profile_id: str, payload: RoleUpdate):
        fields = payload.model_dump(exclude_unset=True)
        if "name" in fields:
            fields["name"] = fields["name"].strip()
        try:
            return role_store.update(profile_id, fields)
        except KeyError:
            raise HTTPException(status_code=404, detail="未找到该岗位") from None
        except RoleStoreError as error:
            raise _handle_store_error(error) from error

    @app.delete("/api/roles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_role(profile_id: str):
        try:
            role_store.delete(profile_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="未找到该岗位") from None

    @app.post("/api/roles/{profile_id}/requirements", response_model=RequirementOut, status_code=status.HTTP_201_CREATED)
    def add_requirement(profile_id: str, payload: RequirementInput):
        try:
            return role_store.add_requirement(profile_id, payload.description, payload.priority)
        except KeyError:
            raise HTTPException(status_code=404, detail="未找到该岗位") from None

    @app.post("/api/roles/{profile_id}/requirements/reorder", response_model=list[RequirementOut])
    def reorder_requirements(profile_id: str, payload: ReorderRequirements):
        try:
            return role_store.reorder_requirements(profile_id, payload.requirement_ids)
        except KeyError:
            raise HTTPException(status_code=404, detail="未找到该岗位") from None
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.patch("/api/roles/{profile_id}/requirements/{requirement_id}", response_model=RequirementOut)
    def update_requirement(profile_id: str, requirement_id: str, payload: RequirementUpdate):
        try:
            return role_store.update_requirement(profile_id, requirement_id, payload.model_dump(exclude_unset=True))
        except KeyError:
            raise HTTPException(status_code=404, detail="未找到该岗位要求") from None

    @app.delete("/api/roles/{profile_id}/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_requirement(profile_id: str, requirement_id: str):
        try:
            role_store.delete_requirement(profile_id, requirement_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="未找到该岗位要求") from None

    @app.post("/api/batches", response_model=BatchOut, status_code=status.HTTP_201_CREATED)
    def create_batch():
        expire_pending_batches(runtime_store, active_settings)
        return serialise_batch(runtime_store.create_batch())

    @app.post("/api/batches/{batch_id}/files", response_model=list[FileOut], status_code=status.HTTP_201_CREATED)
    async def upload_files(batch_id: str, files: list[UploadFile] = File(...)):
        expire_pending_batches(runtime_store, active_settings)
        batch = locate_batch(runtime_store, batch_id)
        if batch.status != "pending":
            raise HTTPException(status_code=409, detail="已经开始的批次不能继续上传")
        if len(batch.files) + len(files) > active_settings.max_batch_files:
            raise HTTPException(status_code=422, detail=f"每批最多上传 {active_settings.max_batch_files} 份简历")
        uploaded: list[RuntimeFile] = []
        for upload in files:
            filename = Path(upload.filename or "unnamed").name
            suffix = Path(filename).suffix.lower()
            content = await upload.read()
            runtime_file = runtime_store.new_file(batch.id, filename, upload.content_type)
            if suffix not in {".pdf", ".docx"}:
                runtime_file.status, runtime_file.error = "failed", "仅支持 PDF 和 DOCX 简历"
            elif len(content) > active_settings.max_upload_bytes:
                runtime_file.status, runtime_file.error = "failed", "文件超过大小限制"
            else:
                try:
                    runtime_file.extracted_text = extract_resume_text(filename, content)
                    runtime_file.status = "ready"
                except Exception as error:
                    runtime_file.status, runtime_file.error = "unreadable", str(error)
            batch.files.append(runtime_file)
            uploaded.append(runtime_file)
        return [serialise_file(item) for item in uploaded]

    @app.post("/api/batches/{batch_id}/start", response_model=BatchOut)
    def start_batch(batch_id: str, payload: BatchStart, background_tasks: BackgroundTasks):
        expire_pending_batches(runtime_store, active_settings)
        batch = locate_batch(runtime_store, batch_id)
        if batch.status != "pending":
            raise HTTPException(status_code=409, detail="该批次已开始")
        ready_files = [item for item in batch.files if item.status == "ready"]
        if not ready_files:
            raise HTTPException(status_code=422, detail="没有可评估的简历")
        profile = locate_profile(role_store, payload.profile_id, active_only=True)
        with runtime_store.lock:
            batch.profile_id = profile.id
            batch.criteria_snapshot = profile_snapshot(profile)
            batch.status = "processing"
            batch.started_at = datetime.now(timezone.utc)
        background_tasks.add_task(evaluate_batch, runtime_store, active_settings, batch.id)
        return serialise_batch(batch)

    @app.delete("/api/batches/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_terminal_batch(batch_id: str):
        expire_pending_batches(runtime_store, active_settings)
        batch = locate_batch(runtime_store, batch_id)
        if batch.status not in {"completed", "expired"}:
            raise HTTPException(status_code=409, detail="仅已完成或已过期的批次可以开始新一轮评估")
        runtime_store.remove_batch(batch_id)

    @app.get("/api/batches/{batch_id}", response_model=BatchOut)
    def get_batch(batch_id: str):
        expire_pending_batches(runtime_store, active_settings)
        return serialise_batch(locate_batch(runtime_store, batch_id))

    @app.get("/api/batches/{batch_id}/results", response_model=list[CandidateOut])
    def list_results(
        batch_id: str,
        state: str | None = Query(default=None, pattern="^(qualified|unqualified|failed)$"),
        min_score: int | None = Query(default=None, ge=0, le=100),
        max_score: int | None = Query(default=None, ge=0, le=100),
    ):
        expire_pending_batches(runtime_store, active_settings)
        batch = locate_batch(runtime_store, batch_id)
        candidates: list[CandidateOut] = []
        for file in batch.files:
            evaluation = file.evaluation
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
            candidates.append(CandidateOut(file=serialise_file(file), evaluation=serialise_evaluation(evaluation)))
        return candidates

    @app.get("/api/evaluations/{evaluation_id}", response_model=CandidateOut)
    def get_evaluation(evaluation_id: str):
        for batch in list(runtime_store._batches.values()):
            for file in batch.files:
                if file.evaluation and file.evaluation.id == evaluation_id:
                    return CandidateOut(file=serialise_file(file), evaluation=serialise_evaluation(file.evaluation))
        raise HTTPException(status_code=404, detail="未找到评分结果")

    return app


app = create_app()
