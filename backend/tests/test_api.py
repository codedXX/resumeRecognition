from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
import app.main as main_module


def make_client(tmp_path) -> TestClient:
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'screening.db'}", upload_dir=tmp_path / "uploads")
    return TestClient(create_app(settings))


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


def test_role_crud_defaults_and_validates_threshold(tmp_path):
    client = make_client(tmp_path)
    response = client.post("/api/roles", json={"name": "数据分析师", "evaluation_prompt": "检查 SQL"})
    assert response.status_code == 201
    assert response.json()["passing_score"] == 80
    profile_id = response.json()["id"]
    assert client.put(f"/api/roles/{profile_id}", json={"passing_score": 101}).status_code == 422
    assert client.post(f"/api/roles/{profile_id}/requirements", json={"description": "年龄小于 30 岁"}).status_code == 422
    requirement = client.post(f"/api/roles/{profile_id}/requirements", json={"description": "SQL"})
    assert requirement.status_code == 201
    assert client.patch(f"/api/roles/{profile_id}/requirements/{requirement.json()['id']}", json={"description": "PostgreSQL"}).status_code == 200
    assert client.delete(f"/api/roles/{profile_id}/requirements/{requirement.json()['id']}").status_code == 204
    assert client.delete(f"/api/roles/{profile_id}").status_code == 204


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
    assert client.get("/data/uploads/carol.docx").status_code == 404


def test_invalid_provider_result_marks_only_that_file_failed(tmp_path, monkeypatch):
    class BrokenProvider:
        async def evaluate(self, _):
            raise ValueError("invalid structured output")

    monkeypatch.setattr(main_module, "provider_for", lambda _: BrokenProvider())
    client = make_client(tmp_path)
    role = create_role(client)
    batch = client.post("/api/batches").json()
    client.post(f"/api/batches/{batch['id']}/files", files=[("files", ("dana.docx", make_docx("Python FastAPI Docker 五年经验"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))])
    client.post(f"/api/batches/{batch['id']}/start", json={"profile_id": role["id"]})
    result = client.get(f"/api/batches/{batch['id']}/results", params={"state": "failed"}).json()[0]
    assert result["file"]["status"] == "failed"
    assert result["evaluation"]["qualified"] is None
    assert result["evaluation"]["score"] is None
