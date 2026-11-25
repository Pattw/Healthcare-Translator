# prior_auth.py
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel


class PAStatusEnum(str, Enum):
    NOT_INDICATED = "NOT_INDICATED"
    LIKELY_REQUIRED = "LIKELY_REQUIRED"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


class PriorAuthEvaluationResponse(BaseModel):
    pa_status: PAStatusEnum
    pa_required: bool
    determination_summary: str
    checklist: List[str]


def evaluate_prior_authorization(
    cpt_code: str,
    is_preventive: bool,
    rule: Optional[Dict[str, Any]] = None,
    icd10_code: Optional[str] = None,
) -> PriorAuthEvaluationResponse:

    # 1. Modeled Preventive Care Exemption
    if is_preventive:
        return PriorAuthEvaluationResponse(
            pa_status=PAStatusEnum.NOT_INDICATED,
            pa_required=False,
            determination_summary=(
                "This preventive service is modeled as "
                "exempt from prior authorization and "
                "patient cost sharing."
            ),
            checklist=[],
        )

    # 2. No matching coverage policy found
    if not rule:
        return PriorAuthEvaluationResponse(
            pa_status=PAStatusEnum.INSUFFICIENT_INFORMATION,
            pa_required=False,
            determination_summary=(
                "No explicit payer policy configured "
                "for this procedure and plan combination."
            ),
            checklist=[],
        )

    # 3. Evaluate diagnosis-specific criteria, if configured
    supported_diagnoses = rule.get("supported_diagnoses")

    if supported_diagnoses is not None:
        if (
            not isinstance(supported_diagnoses, list)
            or not supported_diagnoses
            or not all(
                isinstance(code, str) and code.strip() for code in supported_diagnoses
            )
        ):
            return PriorAuthEvaluationResponse(
                pa_status=PAStatusEnum.INSUFFICIENT_INFORMATION,
                pa_required=False,
                determination_summary=(
                    "Diagnosis criteria are incomplete or incorrectly configured."
                ),
                checklist=[],
            )

        normalized_diagnoses = {code.strip().upper() for code in supported_diagnoses}

        diagnosis = (icd10_code or "").strip().upper()

        if not diagnosis:
            return PriorAuthEvaluationResponse(
                pa_status=PAStatusEnum.INSUFFICIENT_INFORMATION,
                pa_required=False,
                determination_summary=(
                    "A diagnosis code is required to evaluate this coverage rule."
                ),
                checklist=[],
            )

        if diagnosis not in normalized_diagnoses:
            return PriorAuthEvaluationResponse(
                pa_status=PAStatusEnum.INSUFFICIENT_INFORMATION,
                pa_required=False,
                determination_summary=(
                    "The selected diagnosis does not match "
                    "the configured criteria for this "
                    "procedure. Additional payer review "
                    "is required."
                ),
                checklist=[],
            )

    # 4. Validate authorization rule
    pa_required = rule.get("pa_required")

    if not isinstance(pa_required, bool):
        return PriorAuthEvaluationResponse(
            pa_status=PAStatusEnum.INSUFFICIENT_INFORMATION,
            pa_required=False,
            determination_summary=(
                "The available coverage rule does not "
                "contain a valid authorization requirement."
            ),
            checklist=[],
        )

    # 5. Extract clinical documentation checklist
    raw_docs = rule.get("required_documents") or []

    checklist = []

    for doc in raw_docs:
        if isinstance(doc, dict):
            checklist.append(doc.get("label") or doc.get("code", "Document item"))
        else:
            checklist.append(str(doc))

    # 6. Generate determination rationale
    rationale = rule.get("denial_rationale") or (
        "Procedure likely requires prior authorization under the modeled payer policy."
        if pa_required
        else "Prior authorization is not indicated under the modeled payer policy."
    )

    # 7. Return authorization guidance
    return PriorAuthEvaluationResponse(
        pa_status=(
            PAStatusEnum.LIKELY_REQUIRED if pa_required else PAStatusEnum.NOT_INDICATED
        ),
        pa_required=pa_required,
        determination_summary=rationale,
        checklist=checklist,
    )
