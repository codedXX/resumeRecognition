from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4


def now() -> datetime:
    return datetime.now(timezone.utc)


def identifier() -> str:
    return str(uuid4())


class RoleStoreError(RuntimeError):
    pass


@dataclass
class RequirementRecord:
    id: str
    description: str
    priority: str
    position: int

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "priority": self.priority,
            "position": self.position,
        }


@dataclass
class RoleRecord:
    id: str
    name: str
    evaluation_prompt: str
    passing_score: int
    archived: bool
    created_at: str
    updated_at: str
    requirements: list[RequirementRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "evaluation_prompt": self.evaluation_prompt,
            "passing_score": self.passing_score,
            "archived": self.archived,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "requirements": [item.to_dict() for item in self.requirements],
        }

    @classmethod
    def from_dict(cls, value: dict) -> "RoleRecord":
        required = ("id", "name", "evaluation_prompt", "passing_score", "archived", "requirements")
        if not isinstance(value, dict) or any(key not in value for key in required):
            raise RoleStoreError("岗位规则文件格式无效")
        if not str(value["id"]).strip() or not str(value["name"]).strip() or not str(value["evaluation_prompt"]).strip():
            raise RoleStoreError("岗位规则文件格式无效")
        passing_score = int(value["passing_score"])
        if passing_score < 0 or passing_score > 100:
            raise RoleStoreError("岗位规则文件格式无效")
        requirements = []
        for index, item in enumerate(value["requirements"]):
            if not isinstance(item, dict) or not {"id", "description", "priority", "position"}.issubset(item):
                raise RoleStoreError("岗位规则文件格式无效")
            if item["priority"] not in {"required", "preferred"} or int(item["position"]) < 0 or not str(item["description"]).strip():
                raise RoleStoreError("岗位规则文件格式无效")
            requirements.append(
                RequirementRecord(
                    id=str(item["id"]),
                    description=str(item["description"]),
                    priority=str(item["priority"]),
                    position=int(item.get("position", index)),
                )
            )
        return cls(
            id=str(value["id"]),
            name=str(value["name"]),
            evaluation_prompt=str(value["evaluation_prompt"]),
            passing_score=passing_score,
            archived=bool(value["archived"]),
            created_at=str(value.get("created_at") or now().isoformat()),
            updated_at=str(value.get("updated_at") or now().isoformat()),
            requirements=sorted(requirements, key=lambda item: item.position),
        )


@contextmanager
def _file_lock(path: Path):
    """Small cross-platform advisory lock for the role JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class RoleStore:
    version = 1

    def __init__(self, path: Path):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self._thread_lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._locked():
            if not self.path.exists():
                self._write_unlocked([])
            else:
                self._read_unlocked()

    @contextmanager
    def _locked(self):
        with self._thread_lock, _file_lock(self.lock_path):
            yield

    def _read_unlocked(self) -> list[RoleRecord]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("version") != self.version or not isinstance(payload.get("roles"), list):
                raise ValueError
            return [RoleRecord.from_dict(item) for item in payload["roles"]]
        except (OSError, ValueError, TypeError, json.JSONDecodeError, RoleStoreError) as exc:
            raise RoleStoreError("岗位规则文件格式无效") from exc

    def _write_unlocked(self, roles: list[RoleRecord]) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = {"version": self.version, "roles": [role.to_dict() for role in roles]}
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)

    @staticmethod
    def _ensure_unique_name(roles: list[RoleRecord], name: str, current_id: str | None = None) -> None:
        if any(not role.archived and role.name == name and role.id != current_id for role in roles):
            raise RoleStoreError("岗位名称已存在")

    def list(self) -> list[RoleRecord]:
        with self._locked():
            return [role for role in self._read_unlocked() if not role.archived]

    def get(self, role_id: str, active_only: bool = False) -> RoleRecord | None:
        with self._locked():
            role = next((item for item in self._read_unlocked() if item.id == role_id), None)
            if role is None or (active_only and role.archived):
                return None
            return role

    def create(self, name: str, evaluation_prompt: str, passing_score: int, requirements: list[dict]) -> RoleRecord:
        with self._locked():
            roles = self._read_unlocked()
            self._ensure_unique_name(roles, name)
            timestamp = now().isoformat()
            role = RoleRecord(
                id=identifier(),
                name=name,
                evaluation_prompt=evaluation_prompt,
                passing_score=passing_score,
                archived=False,
                created_at=timestamp,
                updated_at=timestamp,
                requirements=[
                    RequirementRecord(
                        id=identifier(),
                        description=item["description"],
                        priority=item["priority"],
                        position=index,
                    )
                    for index, item in enumerate(requirements)
                ],
            )
            roles.append(role)
            self._write_unlocked(roles)
            return role

    def update(self, role_id: str, fields: dict) -> RoleRecord:
        with self._locked():
            roles = self._read_unlocked()
            role = next((item for item in roles if item.id == role_id), None)
            if role is None or role.archived:
                raise KeyError(role_id)
            if "name" in fields:
                self._ensure_unique_name(roles, fields["name"], role_id)
            for field in ("name", "evaluation_prompt", "passing_score"):
                if field in fields:
                    setattr(role, field, fields[field])
            role.updated_at = now().isoformat()
            self._write_unlocked(roles)
            return role

    def delete(self, role_id: str) -> None:
        with self._locked():
            roles = self._read_unlocked()
            if not any(role.id == role_id for role in roles):
                raise KeyError(role_id)
            self._write_unlocked([role for role in roles if role.id != role_id])

    def add_requirement(self, role_id: str, description: str, priority: str) -> RequirementRecord:
        with self._locked():
            roles = self._read_unlocked()
            role = next((item for item in roles if item.id == role_id and not item.archived), None)
            if role is None:
                raise KeyError(role_id)
            requirement = RequirementRecord(identifier(), description, priority, len(role.requirements))
            role.requirements.append(requirement)
            role.updated_at = now().isoformat()
            self._write_unlocked(roles)
            return requirement

    def update_requirement(self, role_id: str, requirement_id: str, fields: dict) -> RequirementRecord:
        with self._locked():
            roles = self._read_unlocked()
            role = next((item for item in roles if item.id == role_id and not item.archived), None)
            requirement = next((item for item in role.requirements if item.id == requirement_id), None) if role else None
            if requirement is None:
                raise KeyError(requirement_id)
            for field in ("description", "priority", "position"):
                if field in fields:
                    setattr(requirement, field, fields[field])
            role.updated_at = now().isoformat()
            self._write_unlocked(roles)
            return requirement

    def delete_requirement(self, role_id: str, requirement_id: str) -> None:
        with self._locked():
            roles = self._read_unlocked()
            role = next((item for item in roles if item.id == role_id and not item.archived), None)
            if role is None or not any(item.id == requirement_id for item in role.requirements):
                raise KeyError(requirement_id)
            role.requirements = [item for item in role.requirements if item.id != requirement_id]
            for position, item in enumerate(role.requirements):
                item.position = position
            role.updated_at = now().isoformat()
            self._write_unlocked(roles)

    def reorder_requirements(self, role_id: str, requirement_ids: list[str]) -> list[RequirementRecord]:
        with self._locked():
            roles = self._read_unlocked()
            role = next((item for item in roles if item.id == role_id and not item.archived), None)
            if role is None or set(requirement_ids) != {item.id for item in role.requirements}:
                raise ValueError("排序列表必须包含该岗位全部要求")
            known = {item.id: item for item in role.requirements}
            role.requirements = [known[item_id] for item_id in requirement_ids]
            for position, item in enumerate(role.requirements):
                item.position = position
            role.updated_at = now().isoformat()
            self._write_unlocked(roles)
            return role.requirements


@dataclass
class EvaluationRecord:
    id: str
    score: int | None = None
    qualified: bool | None = None
    reason: str | None = None
    satisfied: list[str] = field(default_factory=list)
    unmet: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    provider: str | None = None
    error: str | None = None


@dataclass
class RuntimeFile:
    id: str
    batch_id: str
    original_name: str
    content_type: str | None
    status: str = "pending"
    error: str | None = None
    extracted_text: str | None = None
    evaluation: EvaluationRecord | None = None
    created_at: datetime = field(default_factory=now)


@dataclass
class RuntimeBatch:
    id: str
    status: str = "pending"
    profile_id: str | None = None
    criteria_snapshot: dict | None = None
    files: list[RuntimeFile] = field(default_factory=list)
    created_at: datetime = field(default_factory=now)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class MemoryStore:
    def __init__(self, retention_minutes: int = 30):
        self.retention = timedelta(minutes=retention_minutes)
        self._batches: dict[str, RuntimeBatch] = {}
        self.lock = threading.RLock()

    def _cleanup_unlocked(self) -> None:
        cutoff = now() - self.retention
        expired = [
            batch_id
            for batch_id, batch in self._batches.items()
            if batch.finished_at is not None and batch.finished_at < cutoff
        ]
        for batch_id in expired:
            self._batches.pop(batch_id, None)

    def create_batch(self) -> RuntimeBatch:
        with self.lock:
            self._cleanup_unlocked()
            batch = RuntimeBatch(id=identifier())
            self._batches[batch.id] = batch
            return batch

    def new_file(self, batch_id: str, original_name: str, content_type: str | None) -> RuntimeFile:
        return RuntimeFile(id=identifier(), batch_id=batch_id, original_name=original_name, content_type=content_type)

    def get_batch(self, batch_id: str) -> RuntimeBatch | None:
        with self.lock:
            self._cleanup_unlocked()
            return self._batches.get(batch_id)

    def remove_batch(self, batch_id: str) -> None:
        with self.lock:
            self._batches.pop(batch_id, None)
