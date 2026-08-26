import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from app.stores import MemoryStore, RoleStore, RoleStoreError


def test_role_store_initializes_empty_file_and_round_trips_role(tmp_path):
    path = tmp_path / "roles.json"
    store = RoleStore(path)

    assert store.list() == []
    role = store.create(
        name="Python 后端工程师",
        evaluation_prompt="根据岗位要求评分",
        passing_score=80,
        requirements=[{"description": "Python", "priority": "required"}],
    )

    reloaded = RoleStore(path)
    assert reloaded.get(role.id).name == "Python 后端工程师"
    assert reloaded.get(role.id).requirements[0].description == "Python"
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert "resume_text" not in json.dumps(persisted, ensure_ascii=False)
    assert "score" not in persisted["roles"][0]


def test_role_store_rejects_malformed_json_without_overwriting(tmp_path):
    path = tmp_path / "roles.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(RoleStoreError, match="岗位规则文件格式无效"):
        RoleStore(path)
    assert path.read_text(encoding="utf-8") == "{broken"


def test_role_store_rejects_invalid_score_and_priority_in_json(tmp_path):
    path = tmp_path / "roles.json"
    path.write_text(
        json.dumps({"version": 1, "roles": [{"id": "r", "name": "岗位", "evaluation_prompt": "评分", "passing_score": 101, "archived": False, "requirements": [{"id": "q", "description": "Python", "priority": "other", "position": 0}]}]}),
        encoding="utf-8",
    )
    with pytest.raises(RoleStoreError, match="岗位规则文件格式无效"):
        RoleStore(path)


def test_role_store_rejects_duplicate_active_names(tmp_path):
    store = RoleStore(tmp_path / "roles.json")
    store.create("同名岗位", "评分", 80, [])
    with pytest.raises(RoleStoreError, match="岗位名称已存在"):
        store.create("同名岗位", "评分", 90, [])


def test_role_store_serializes_concurrent_writes(tmp_path):
    path = tmp_path / "roles.json"

    def create(index: int):
        RoleStore(path).create(f"岗位 {index}", "评分", 80, [])

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(create, range(8)))
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert len(payload["roles"]) == 8


def test_memory_store_does_not_survive_a_new_process_store():
    store = MemoryStore(retention_minutes=30)
    batch = store.create_batch()
    batch.files.append(store.new_file(batch.id, "candidate.pdf", "application/pdf"))

    assert store.get_batch(batch.id) is batch
    assert MemoryStore(retention_minutes=30).get_batch(batch.id) is None


def test_memory_store_expires_terminal_batches_after_ttl():
    store = MemoryStore(retention_minutes=1)
    batch = store.create_batch()
    batch.status = "completed"
    batch.finished_at = datetime.now(timezone.utc) - timedelta(minutes=2)
    assert store.get_batch(batch.id) is None
