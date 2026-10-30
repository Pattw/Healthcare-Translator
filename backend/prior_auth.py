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
    icd10_code: Optional[str] = None
) -> PriorAuthEvaluationResponse:
    # 1. Preventive Care Exemption
    if is_preventive:
        return PriorAuthEvaluationResponse(
            pa_status=PAStatusEnum.NOT_INDICATED,
            pa_required=False,
            determination_summary="Preventive care procedure covered at 100% under standard ACA guidelines.",
            checklist=[]
        )

    # 2. No matching coverage policy found
    if not rule:
        return PriorAuthEvaluationResponse(
            pa_status=PAStatusEnum.INSUFFICIENT_INFORMATION,
            pa_required=False,
            determination_summary="No explicit payer policy configured for this procedure and plan combination.",
            checklist=[]
        )

    # 3. Rule exists: evaluate PA Requirement
    pa_required = bool(rule.get("pa_required", False))
    raw_docs = rule.get("required_documents") or []

    # Cleanly unpack document checklist strings from JSONB
    checklist = []
    for doc in raw_docs:
        if isinstance(doc, dict):
            checklist.append(doc.get("label") or doc.get("code", "Document item"))
        else:
            checklist.append(str(doc))

    rationale = rule.get("denial_rationale") or (
        "Procedure requires prior authorization under active payer policy."
        if pa_required else "Prior authorization is not required under this policy."
    )

    return PriorAuthEvaluationResponse(
        pa_status=PAStatusEnum.LIKELY_REQUIRED if pa_required else PAStatusEnum.NOT_INDICATED,
        pa_required=pa_required,
        determination_summary=rationale,
        checklist=checklist
    )