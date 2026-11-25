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
    Eligible preventive services bypass prior authorization
    under the prototype's modeled coverage rules.
    """
    res = evaluate_prior_authorization(cpt_code="99395", is_preventive=True, rule=None)

    assert res.pa_status == PAStatusEnum.NOT_INDICATED
    assert res.pa_required is False
    assert len(res.checklist) == 0
    assert "preventive" in res.determination_summary.lower()
    assert "exempt" in res.determination_summary.lower()
    assert "modeled" in res.determination_summary.lower()


def test_unmapped_procedure_rule_fallback():
    """
    TC-ERR-01 / Fallback: Procedure without active coverage rule.
    Must return INSUFFICIENT_INFORMATION.
    """
    res = evaluate_prior_authorization(cpt_code="99999", is_preventive=False, rule=None)
    assert res.pa_status == PAStatusEnum.INSUFFICIENT_INFORMATION
    assert res.pa_required is False
    assert len(res.checklist) == 0


def test_diagnosis_matches_coverage_rule():
    """A matching diagnosis allows normal rule evaluation."""
    rule = {
        "pa_required": True,
        "supported_diagnoses": ["M25.561", "M25.562"],
        "required_documents": ["Physical therapy records"],
    }

    res = evaluate_prior_authorization(
        cpt_code="73721", is_preventive=False, rule=rule, icd10_code="M25.561"
    )

    assert res.pa_status == PAStatusEnum.LIKELY_REQUIRED
    assert res.pa_required is True
    assert len(res.checklist) == 1


def test_diagnosis_does_not_match_coverage_rule():
    """An unmatched diagnosis triggers insufficient information."""
    rule = {"pa_required": True, "supported_diagnoses": ["M25.561", "M25.562"]}

    res = evaluate_prior_authorization(
        cpt_code="73721", is_preventive=False, rule=rule, icd10_code="R51.9"
    )

    assert res.pa_status == PAStatusEnum.INSUFFICIENT_INFORMATION
    assert len(res.checklist) == 0


def test_missing_required_diagnosis():
    """A missing diagnosis triggers safe fallback."""
    rule = {"pa_required": True, "supported_diagnoses": ["M25.561", "M25.562"]}

    res = evaluate_prior_authorization(
        cpt_code="73721", is_preventive=False, rule=rule, icd10_code=None
    )

    assert res.pa_status == PAStatusEnum.INSUFFICIENT_INFORMATION


def test_diagnosis_code_normalization():
    """Diagnosis matching ignores case and surrounding spaces."""
    rule = {"pa_required": True, "supported_diagnoses": ["M25.561"]}

    res = evaluate_prior_authorization(
        cpt_code="73721", is_preventive=False, rule=rule, icd10_code=" m25.561 "
    )

    assert res.pa_status == PAStatusEnum.LIKELY_REQUIRED


def test_invalid_authorization_rule():
    """An incomplete rule must not imply authorization is unnecessary."""
    rule = {"required_documents": []}

    res = evaluate_prior_authorization(cpt_code="73721", is_preventive=False, rule=rule)

    assert res.pa_status == PAStatusEnum.INSUFFICIENT_INFORMATION


def test_invalid_diagnosis_criteria():
    """Incorrectly configured diagnosis criteria trigger safe fallback."""
    rule = {"pa_required": True, "supported_diagnoses": "M25.561"}

    res = evaluate_prior_authorization(
        cpt_code="73721", is_preventive=False, rule=rule, icd10_code="M25.561"
    )

    assert res.pa_status == PAStatusEnum.INSUFFICIENT_INFORMATION
