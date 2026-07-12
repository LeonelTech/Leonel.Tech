"""API smoke tests via FastAPI TestClient."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from acervo.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_health_and_locales():
    client = _client()
    assert client.get("/api/health").json()["status"] == "ok"
    locales = client.get("/api/locales").json()
    assert locales["default"] == "pt-BR"
    msgs = client.get("/api/locales/pt-BR").json()
    assert "copy.validated" in msgs


def test_destination_inside_source_rejected(tmp_path: Path):
    client = _client()
    src = tmp_path / "src"
    (src / "inner").mkdir(parents=True)
    col = client.post("/api/collections", json={"name": "C"}).json()
    media = client.post(
        "/api/media",
        json={"collection_identifier": col["identifier"], "label": "m", "source_root": str(src)},
    ).json()
    resp = client.post(
        "/api/sessions",
        json={
            "collection_identifier": col["identifier"],
            "media_identifier": media["identifier"],
            "source_root": str(src),
            "destination_root": str(src / "inner"),
        },
    )
    assert resp.status_code == 400


def test_full_flow_via_api(tmp_path: Path):
    client = _client()
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("alpha", encoding="utf-8")
    (src / "b.txt").write_text("beta", encoding="utf-8")
    dest = tmp_path / "dst"

    col = client.post("/api/collections", json={"name": "Case A"}).json()
    media = client.post(
        "/api/media",
        json={"collection_identifier": col["identifier"], "label": "disk", "source_root": str(src)},
    ).json()
    sess = client.post(
        "/api/sessions",
        json={
            "collection_identifier": col["identifier"],
            "media_identifier": media["identifier"],
            "source_root": str(src),
            "destination_root": str(dest),
        },
    ).json()
    stats = client.post(f"/api/sessions/{sess['identifier']}/run").json()
    assert stats["validated"] == 2

    files = client.get(f"/api/sessions/{sess['identifier']}/files").json()
    assert files["file_count"] == 2
    assert all(f["content_sha256"] for f in files["files"])
