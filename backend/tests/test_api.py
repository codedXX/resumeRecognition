from datetime import datetime, timedelta, timezone
from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient

from app.config import Settings
from app.evaluation import EvaluationResult
from app.main import create_app
import app.main as main_module


def make_client(tmp_path, **overrides) -> TestClient:
    values = {
        "roles_file": tmp_path / "roles.json",
        "analysis_retention_minutes": 30,
        "pending_input_retention_minutes": 60,
        "evaluation_provider": "heuristic",
    }
    values.update(overrides)
    return TestClient(create_app(Settings(**values)))


def make_docx(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def create_role(client: TestClient, threshold: int = 80) -> dict:
    response = client.post(
        "/api/roles",
        json={
            "name": "Python 后端工程师",
            "evaluation_prompt": "评估候选人的 Python 后端能力",
            "passing_score": threshold,
            "requirements": [
                {"description": "Python FastAPI", "priority": "required"},
                {"description": "Docker", "priority": "preferred"},
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_pending_input_retention_defaults_to_one_hour():
    assert Settings().pending_input_retention_minutes == 60


def test_multiple_workers_are_rejected_for_volatile_runtime(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="单 worker"):
        create_app(Settings(roles_file=tmp_path / "roles.json", workers=2))


def test_role_crud_defaults_and_validates_threshold(tmp_path):
    client = make_client(tmp_path)
    response = client.post("/api/roles", json={"name": "数据分析师", "evaluation_prompt": "检查 SQL"})
    assert response.status_code == 201
    assert response.json()["passing_score"] == 80
    role_id = response.json()["id"]
    assert client.put(f"/api/roles/{role_id}", json={"passing_score": 101}).status_code == 422
    assert client.post(f"/api/roles/{role_id}/requirements", json={"description": "年龄小于 30 岁"}).status_code == 422
    requirement = client.post(f"/api/roles/{role_id}/requirements", json={"description": "SQL"})
    assert requirement.status_code == 201
    requirement_id = requirement.json()["id"]
    assert client.patch(f"/api/roles/{role_id}/requirements/{requirement_id}", json={"description": "PostgreSQL"}).status_code == 200
    assert client.delete(f"/api/roles/{role_id}/requirements/{requirement_id}").status_code == 204
    assert client.delete(f"/api/roles/{role_id}").status_code == 204


def test_roles_survive_new_app_but_analysis_is_ephemeral(tmp_path):
    first = make_client(tmp_path)
    role = create_role(first)
    batch = first.post("/api/batches").json()
    assert first.get(f"/api/batches/{batch['id']}").status_code == 200
    second = make_client(tmp_path)
    assert second.get(f"/api/roles/{role['id']}").status_code == 200
    assert second.get(f"/api/batches/{batch['id']}").status_code == 404
    assert not (tmp_path / "screening.db").exists()


def test_upload_only_prepares_then_explicit_start_evaluates(tmp_path):
    client = make_client(tmp_path)
    role = create_role(client)
    batch = client.post("/api/batches").json()
    upload = client.post(
        f"/api/batches/{batch['id']}/files",
        files=[("files", ("alice.docx", make_docx("Python FastAPI Docker 五年经验"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
    )
    assert upload.status_code == 201
    assert upload.json()[0]["status"] == "ready"
    assert client.get(f"/api/batches/{batch['id']}/results").json() == [{"file": upload.json()[0], "evaluation": None}]
    started = client.post(f"/api/batches/{batch['id']}/start", json={"profile_id": role["id"]})
    assert started.status_code == 200
    result = client.get(f"/api/batches/{batch['id']}/results").json()[0]
    assert result["evaluation"]["score"] == 100
    assert result["evaluation"]["qualified"] is True
    assert result["evaluation"]["evidence"]


def test_supported_upload_does_not_persist_resume_binary_or_text(tmp_path):
    client = make_client(tmp_path)
    batch = client.post("/api/batches").json()
    upload = client.post(
        f"/api/batches/{batch['id']}/files",
        files=[("files", ("ephemeral.docx", make_docx("Python FastAPI Docker 五年经验"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
    )
    assert upload.status_code == 201
    assert list((tmp_path / "uploads").glob("*")) == []
    runtime_file = client.app.state.runtime_store.get_batch(batch["id"]).files[0]
    assert runtime_file.extracted_text


def test_completed_evaluation_clears_extracted_text_but_keeps_result(tmp_path):
    client = make_client(tmp_path)
    role = create_role(client)
    batch = client.post("/api/batches").json()
    uploaded = client.post(
        f"/api/batches/{batch['id']}/files",
        files=[("files", ("completed.docx", make_docx("Python FastAPI Docker 五年经验"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
    ).json()[0]
    client.post(f"/api/batches/{batch['id']}/start", json={"profile_id": role["id"]})
    runtime_file = client.app.state.runtime_store.get_batch(batch["id"]).files[0]
    assert runtime_file.id == uploaded["id"]
    assert runtime_file.extracted_text is None
    assert client.get(f"/api/batches/{batch['id']}/results").json()[0]["evaluation"]["evidence"]


def test_expired_pending_batch_purges_text_and_rejects_start(tmp_path):
    client = make_client(tmp_path, pending_input_retention_minutes=1)
    role = create_role(client)
    batch = client.post("/api/batches").json()
    client.post(
        f"/api/batches/{batch['id']}/files",
        files=[("files", ("expired.docx", make_docx("Python FastAPI Docker 五年经验"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
    )
    runtime_batch = client.app.state.runtime_store.get_batch(batch["id"])
    runtime_batch.created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    expired = client.get(f"/api/batches/{batch['id']}")
    assert expired.status_code == 200
    assert expired.json()["status"] == "expired"
    assert client.post(f"/api/batches/{batch['id']}/start", json={"profile_id": role["id"]}).status_code == 409
    assert runtime_batch.files[0].extracted_text is None


def test_criteria_snapshot_and_threshold_boundary(tmp_path):
    client = make_client(tmp_path)
    role = create_role(client, threshold=85)
    batch = client.post("/api/batches").json()
    client.post(
        f"/api/batches/{batch['id']}/files",
        files=[("files", ("bob.docx", make_docx("Python FastAPI 开发经验，负责企业服务设计与交付。"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))],
    )
    client.post(f"/api/batches/{batch['id']}/start", json={"profile_id": role["id"]})
    assert client.put(f"/api/roles/{role['id']}", json={"passing_score": 20}).status_code == 200
    snapshot = client.get(f"/api/batches/{batch['id']}").json()["criteria_snapshot"]
    result = client.get(f"/api/batches/{batch['id']}/results").json()[0]["evaluation"]
    assert snapshot["passing_score"] == 85
    assert result["score"] == 50
    assert result["qualified"] is False
    assert len(client.get(f"/api/batches/{batch['id']}/results", params={"state": "unqualified"}).json()) == 1


def test_rejects_unsupported_file_without_blocking_valid_file(tmp_path):
    client = make_client(tmp_path)
    batch = client.post("/api/batches").json()
    upload = client.post(
        f"/api/batches/{batch['id']}/files",
        files=[
            ("files", ("notes.txt", b"not a resume", "text/plain")),
            ("files", ("carol.docx", make_docx("Python FastAPI 开发经验，负责企业服务设计与交付。"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ],
    )
    assert [item["status"] for item in upload.json()] == ["failed", "ready"]


def test_invalid_provider_result_marks_only_that_file_failed(tmp_path, monkeypatch, caplog):
    class SelectiveProvider:
        def __init__(self):
            self.calls = 0

        async def evaluate(self, _):
            self.calls += 1
            if self.calls <= 2:
                raise ValueError("invalid structured output")
            return EvaluationResult(score=92, reason="second file valid")

    provider = SelectiveProvider()
    monkeypatch.setattr(main_module, "provider_for", lambda _: provider)
    caplog.set_level("WARNING")
    client = make_client(tmp_path)
    role = create_role(client)
    batch = client.post("/api/batches").json()
    client.post(
        f"/api/batches/{batch['id']}/files",
        files=[
            ("files", ("dana.docx", make_docx("Python FastAPI Docker 五年经验"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ("files", ("erin.docx", make_docx("Python FastAPI Docker 六年经验"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ],
    )
    client.post(f"/api/batches/{batch['id']}/start", json={"profile_id": role["id"]})
    results = client.get(f"/api/batches/{batch['id']}/results").json()
    assert [item["file"]["status"] for item in results] == ["failed", "completed"]
    assert results[0]["evaluation"]["qualified"] is None
    assert results[0]["evaluation"]["score"] is None
    assert results[0]["evaluation"]["error"] == "评分服务未返回有效结果"
    assert results[1]["evaluation"]["score"] == 92
    log_text = " ".join(record.getMessage() for record in caplog.records)
    assert "invalid structured output" not in log_text
    assert "Python FastAPI Docker 六年经验" not in log_text
