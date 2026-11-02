import pytest
from prior_auth import evaluate_prior_authorization, PAStatusEnum


def test_tc_pa_01_prior_auth_required_with_checklist():
    """
    TC-PA-01: CPT 73721 Knee MRI
    Active rule requiring prior auth with dynamic checklist unpack.
    """
    mock_rule = {
        "pa_required": True,
        "denial_rationale": "Knee MRI requests require documentation of failed conservative management.",
        "required_documents": [
            "Weight-bearing X-ray (within 60 days)",
            "Clinical notes documenting 6 weeks failed conservative therapy",
            "Physical therapy completion logs",
        ],
    }
    res = evaluate_prior_authorization(
        cpt_code="73721", is_preventive=False, rule=mock_rule
    )
    assert res.pa_status == PAStatusEnum.LIKELY_REQUIRED
    assert res.pa_required is True
    assert len(res.checklist) == 3
    assert "Weight-bearing X-ray (within 60 days)" in res.checklist
    assert "Physical therapy completion logs" in res.checklist


def test_tc_pa_02_preventive_care_exemption():
    """
    TC-PA-02: CPT 99395 Preventive Medicine
    Preventive services bypass prior authorization automatically.
    """
    res = evaluate_prior_authorization(cpt_code="99395", is_preventive=True, rule=None)
    assert res.pa_status == PAStatusEnum.NOT_INDICATED
    assert res.pa_required is False
    assert len(res.checklist) == 0
    assert "ACA" in res.determination_summary


def test_unmapped_procedure_rule_fallback():
    """
    TC-ERR-01 / Fallback: Procedure without active coverage rule.
    Must return INSUFFICIENT_INFORMATION.
    """
    res = evaluate_prior_authorization(cpt_code="99999", is_preventive=False, rule=None)
    assert res.pa_status == PAStatusEnum.INSUFFICIENT_INFORMATION
    assert res.pa_required is False
    assert len(res.checklist) == 0
