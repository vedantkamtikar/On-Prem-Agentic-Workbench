"""Integration tests for FastAPI routes and telemetry endpoints."""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure src is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from workbench.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["mode"] == "air_gapped_local"


def test_models_registry_endpoint(client):
    res = client.get("/models")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert len(data["models"]) >= 3


def test_hardware_telemetry_endpoint(client):
    res = client.get("/system/hardware")
    assert res.status_code == 200
    data = res.json()
    assert "vram" in data
    assert "system_ram" in data
    assert "invariants" in data
    assert data["invariants"]["ocr_compute"] == "CPU"


def test_network_audit_endpoint(client):
    res = client.get("/system/network-audit")
    assert res.status_code == 200
    data = res.json()
    assert "air_gap_compliant" in data
    assert "active_sockets" in data
    assert data["mode"] in ["AIR_GAP_STRICT_PASS", "WARNING"]


def test_kb_list_endpoint(client):
    res = client.get("/tools/kb/list")
    assert res.status_code == 200
    data = res.json()
    assert "documents" in data
    assert "total_chunks" in data


def test_deliverables_list_endpoint(client):
    res = client.get("/deliverables/list")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "deliverables" in data
    assert "total_files" in data
