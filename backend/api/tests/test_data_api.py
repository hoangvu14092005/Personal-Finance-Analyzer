"""Tests for data export/privacy APIs."""
from __future__ import annotations

from app.models.entities import User
from fastapi.testclient import TestClient


class TestDataAuth:
    def test_export_requires_auth(self, client: TestClient) -> None:
        response = client.post("/api/v1/data/export", json={})
        assert response.status_code == 401


class TestDataExport:
    def test_create_and_get_export_status(self, client: TestClient, auth_user: User) -> None:
        create = client.post(
            "/api/v1/data/export",
            json={"include_receipts": False, "include_transactions": True, "include_chat": False},
        )

        assert create.status_code == 202
        created = create.json()
        assert created["status"] == "ready"
        assert created["download_url"] is not None
        assert created["included"] == ["transactions"]

        get_response = client.get(f"/api/v1/data/export/{created['export_id']}")
        assert get_response.status_code == 200
        assert get_response.json()["export_id"] == created["export_id"]

    def test_download_export_returns_zip(self, client: TestClient, auth_user: User) -> None:
        create = client.post("/api/v1/data/export", json={})
        assert create.status_code == 202
        export_id = create.json()["export_id"]

        download = client.get(f"/api/v1/data/export/{export_id}/download")
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/zip"
        # ZIP magic bytes "PK".
        assert download.content[:2] == b"PK"

    def test_download_unknown_export_returns_404(self, client: TestClient, auth_user: User) -> None:
        response = client.get("/api/v1/data/export/missing/download")
        assert response.status_code == 404

    def test_unknown_export_returns_404(self, client: TestClient, auth_user: User) -> None:
        response = client.get("/api/v1/data/export/missing")
        assert response.status_code == 404

    def test_bulk_receipt_delete_is_guarded(self, client: TestClient, auth_user: User) -> None:
        response = client.delete("/api/v1/data/receipt-files")
        assert response.status_code == 409
