import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pytest
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_integration_tc_calc_01_eleanor_vance_unmet_deductible():
    """Verify live multi-table integration for unmet deductible absorption."""
    payload = {"patient_id": "PT-1001", "cpt_code": "73721"}
    response = client.post("/api/v1/evaluate-coverage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["financial_breakdown"]["total_allowed_amount"] == 552.0
    assert data["financial_breakdown"]["deductible_applied"] == 552.0
    assert data["financial_breakdown"]["total_patient_responsibility"] == 552.0
    assert data["financial_breakdown"]["estimated_plan_responsibility"] == 0.0


def test_integration_tc_calc_02_jordan_vance_coinsurance_split():
    """Verify live multi-table integration for deductible exhaust and coinsurance split."""
    payload = {"patient_id": "PT-1004", "cpt_code": "29881"}
    response = client.post("/api/v1/evaluate-coverage", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Base: 2200.00 * 1.15 = 2530.00. Deductible met: 1200 / 1500 (Remaining: 300).
    # 2530 - 300 = 2230. 20% coinsurance = 446.00. Patient owes 300 + 446 = 746.00.
    assert data["financial_breakdown"]["total_allowed_amount"] == 2530.0
    assert data["financial_breakdown"]["deductible_applied"] == 300.0
    assert data["financial_breakdown"]["coinsurance_applied"] == 446.0
    assert data["financial_breakdown"]["total_patient_responsibility"] == 746.0
    assert data["financial_breakdown"]["estimated_plan_responsibility"] == 1784.0


def test_integration_tc_calc_03_devon_washington_oop_clamp():
    """Verify live multi-table integration for out-of-pocket maximum clamping."""
    payload = {"patient_id": "PT-1007", "cpt_code": "H0015"}
    response = client.post("/api/v1/evaluate-coverage", json=payload)
    assert response.status_code == 200
    data = response.json()

    financial = data["financial_breakdown"]
    assert financial["oop_adjustment"] == 20.00

    assert (
        round(
            financial["deductible_applied"]
            + financial["copay_applied"]
            + financial["coinsurance_applied"]
            - financial["oop_adjustment"],
            2,
        )
        == financial["total_patient_responsibility"]
    )

    # Base: 600.00 * 1.00 = 600.00.
    # Tentative 20% coinsurance = 120.00.
    # Remaining OOP Max capacity = 7500.00 - 7400.00 = 100.00.
    # Patient liability is clamped to remaining capacity ($100.00).
    assert data["financial_breakdown"]["total_patient_responsibility"] == 100.0
    assert data["financial_breakdown"]["estimated_plan_responsibility"] == 500.0
    assert data["financial_breakdown"]["oop_max_reached"] is True


def test_integration_tc_pa_01_checklist_extraction():
    """Verify dynamic JSONB checklist extraction from Supabase."""
    payload = {"patient_id": "PT-1001", "cpt_code": "73721", "icd10_code": "M25.561"}
    response = client.post("/api/v1/evaluate-coverage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["pa_status"] == "LIKELY_REQUIRED"
    assert data["pa_required"] is True
    assert len(data["required_documents"]) == 3


def test_integration_tc_pa_02_preventive_aca_waiver():
    """Verify preventive care evaluates to $0 patient responsibility."""
    payload = {"patient_id": "PT-1003", "cpt_code": "99395"}
    response = client.post("/api/v1/evaluate-coverage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_preventive"] is True
    assert data["pa_status"] == "NOT_INDICATED"
    assert data["financial_breakdown"]["total_patient_responsibility"] == 0.0


def test_integration_tc_err_01_invalid_procedure():
    """Verify defensive fallback on unmapped procedure code."""
    payload = {"patient_id": "PT-1001", "cpt_code": "99999"}
    response = client.post("/api/v1/evaluate-coverage", json=payload)
    assert response.status_code == 404


def test_integration_tc_err_02_invalid_patient():
    """Verify defensive fallback on unknown patient ID."""
    payload = {"patient_id": "PT-9999", "cpt_code": "73721"}
    response = client.post("/api/v1/evaluate-coverage", json=payload)
    assert response.status_code == 404


def test_integration_diagnosis_mismatch():
    """Verify that an unmatched diagnosis triggers safe fallback."""
    payload = {"patient_id": "PT-1001", "cpt_code": "73721", "icd10_code": "R51.9"}

    response = client.post("/api/v1/evaluate-coverage", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["pa_status"] == "INSUFFICIENT_INFORMATION"
    assert len(data["required_documents"]) == 0
    assert data["financial_breakdown"]["total_patient_responsibility"] == 552.00


def test_integration_missing_diagnosis():
    """Verify safe fallback when a required diagnosis is omitted."""
    payload = {"patient_id": "PT-1001", "cpt_code": "73721"}

    response = client.post("/api/v1/evaluate-coverage", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["pa_status"] == "INSUFFICIENT_INFORMATION"
    assert len(data["required_documents"]) == 0
    assert data["financial_breakdown"]["total_patient_responsibility"] == 552.00
