# adjudication.py
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from pydantic import BaseModel

class AdjudicationInput(BaseModel):
    allowed_amount: Decimal
    is_preventive: bool = False
    is_copay_service: bool = False
    copay_amount: Decimal = Decimal("0.00")
    coinsurance_rate: Decimal = Decimal("0.20")
    annual_deductible: Decimal = Decimal("0.00")
    deductible_met_ytd: Decimal = Decimal("0.00")
    annual_oop_max: Decimal = Decimal("999999.00")
    oop_met_ytd: Decimal = Decimal("0.00")

class AdjudicationBreakdown(BaseModel):
    allowed_amount: Decimal
    deductible_applied: Decimal
    copay_applied: Decimal
    coinsurance_applied: Decimal
    total_patient_responsibility: Decimal
    estimated_plan_responsibility: Decimal
    oop_max_reached: bool
    new_deductible_met_ytd: Decimal
    new_oop_met_ytd: Decimal

def adjudicate_claim(claim: AdjudicationInput) -> AdjudicationBreakdown:
    cents = Decimal("0.01")
    allowed = claim.allowed_amount.quantize(cents, rounding=ROUND_HALF_UP)

    # 1. Preventive Service Exemption (ACA Mandate: $0 cost share)
    if claim.is_preventive:
        return AdjudicationBreakdown(
            allowed_amount=allowed,
            deductible_applied=Decimal("0.00"),
            copay_applied=Decimal("0.00"),
            coinsurance_applied=Decimal("0.00"),
            total_patient_responsibility=Decimal("0.00"),
            estimated_plan_responsibility=allowed,
            oop_max_reached=False,
            new_deductible_met_ytd=claim.deductible_met_ytd,
            new_oop_met_ytd=claim.oop_met_ytd
        )

    rem_deductible = max(Decimal("0.00"), claim.annual_deductible - claim.deductible_met_ytd)
    rem_oop = max(Decimal("0.00"), claim.annual_oop_max - claim.oop_met_ytd)

    # 2. Flat Copay Branch (e.g. Office Visits / Evaluation & Management)
    if claim.is_copay_service:
        tentative_copay = min(claim.copay_amount, allowed)
        patient_paid = min(tentative_copay, rem_oop).quantize(cents, rounding=ROUND_HALF_UP)
        plan_paid = (allowed - patient_paid).quantize(cents, rounding=ROUND_HALF_UP)

        return AdjudicationBreakdown(
            allowed_amount=allowed,
            deductible_applied=Decimal("0.00"),
            copay_applied=patient_paid,
            coinsurance_applied=Decimal("0.00"),
            total_patient_responsibility=patient_paid,
            estimated_plan_responsibility=plan_paid,
            oop_max_reached=(patient_paid >= rem_oop and rem_oop > 0),
            new_deductible_met_ytd=claim.deductible_met_ytd,
            new_oop_met_ytd=claim.oop_met_ytd + patient_paid
        )

    # 3. Deductible + Coinsurance Branch (e.g. Advanced Imaging, Surgery)
    deductible_applied = min(allowed, rem_deductible)
    remaining_allowed = allowed - deductible_applied

    coinsurance_applied = (remaining_allowed * claim.coinsurance_rate).quantize(cents, rounding=ROUND_HALF_UP)
    calculated_liability = deductible_applied + coinsurance_applied

    if calculated_liability > rem_oop:
        patient_paid = rem_oop.quantize(cents, rounding=ROUND_HALF_UP)
        oop_reached = True
    else:
        patient_paid = calculated_liability.quantize(cents, rounding=ROUND_HALF_UP)
        oop_reached = False

    plan_paid = max(Decimal("0.00"), allowed - patient_paid).quantize(cents, rounding=ROUND_HALF_UP)

    return AdjudicationBreakdown(
        allowed_amount=allowed,
        deductible_applied=deductible_applied.quantize(cents, rounding=ROUND_HALF_UP),
        copay_applied=Decimal("0.00"),
        coinsurance_applied=coinsurance_applied,
        total_patient_responsibility=patient_paid,
        estimated_plan_responsibility=plan_paid,
        oop_max_reached=oop_reached,
        new_deductible_met_ytd=min(claim.annual_deductible, claim.deductible_met_ytd + deductible_applied),
        new_oop_met_ytd=min(claim.annual_oop_max, claim.oop_met_ytd + patient_paid)
    )