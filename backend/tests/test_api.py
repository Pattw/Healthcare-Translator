import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient
from main import app

# Initialize the test client for the FastAPI application
client = TestClient(app)


def test_api_get_patients_catalog():
    """Verify GET /api/v1/patients returns a valid 200 list for the selector dropdown."""
    response = client.get("/api/v1/patients")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Verify expected schema keys
    assert "patient_id" in data[0]
    assert "first_name" in data[0]
    assert "plan_id" in data[0]


def test_api_get_procedures_catalog():
    """Verify GET /api/v1/procedures returns a valid 200 list of CPT codes."""
    response = client.get("/api/v1/procedures")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "cpt_code" in data[0]
    assert "description" in data[0]


def test_api_evaluate_coverage_valid_claim():
    """
    Verify POST /api/v1/evaluate-coverage calculates correctly for a valid claim.
    Tests Eleanor Vance (PAT-001) + Knee MRI (73721).
    """
    payload = {"patient_id": "PAT-001", "cpt_code": "73721", "icd10_code": "M25.561"}
    response = client.post("/api/v1/evaluate-coverage", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["patient_id"] == "PAT-001"
    assert data["procedure_code"] == "73721"
    assert data["pa_status"] == "LIKELY_REQUIRED"
    assert data["pa_required"] is True
    assert len(data["required_documents"]) > 0

    # Financial verification
    breakdown = data["financial_breakdown"]
    assert breakdown["total_allowed_amount"] == 552.0
    assert breakdown["deductible_applied"] == 552.0
    assert breakdown["total_patient_responsibility"] == 552.0
    assert breakdown["estimated_plan_responsibility"] == 0.0


def test_api_evaluate_coverage_preventive():
    """
    Verify POST /api/v1/evaluate-coverage correctly exempts preventive care (TC-PA-02).
    """
    payload = {"patient_id": "PAT-001", "cpt_code": "99395"}
    response = client.post("/api/v1/evaluate-coverage", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["is_preventive"] is True
    assert data["pa_status"] == "NOT_INDICATED"
    assert data["pa_required"] is False
    assert data["financial_breakdown"]["total_patient_responsibility"] == 0.0


def test_api_err_01_invalid_procedure_code():
    """
    TC-ERR-01: Verify defensive HTTP 404 on unmapped procedure code.
    """
    payload = {"patient_id": "PAT-001", "cpt_code": "99999"}
    response = client.post("/api/v1/evaluate-coverage", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_api_err_02_invalid_patient_id():
    """
    TC-ERR-02: Verify defensive HTTP 404 on non-existent patient ID.
    """
    payload = {"patient_id": "PAT-9999", "cpt_code": "73721"}
    response = client.post("/api/v1/evaluate-coverage", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
