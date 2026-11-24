# adjudication.py
from decimal import Decimal, ROUND_HALF_UP
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
    oop_adjustment: Decimal = Decimal("0.00")
    total_patient_responsibility: Decimal
    estimated_plan_responsibility: Decimal
    oop_max_reached: bool
    new_deductible_met_ytd: Decimal
    new_oop_met_ytd: Decimal


def adjudicate_claim(claim: AdjudicationInput) -> AdjudicationBreakdown:

    cents = Decimal("0.01")
    zero = Decimal("0.00")

    allowed = claim.allowed_amount.quantize(cents, rounding=ROUND_HALF_UP)

    rem_deductible = max(zero, claim.annual_deductible - claim.deductible_met_ytd)

    rem_oop = max(zero, claim.annual_oop_max - claim.oop_met_ytd)

    # 1. Preventive Service Exemption
    if claim.is_preventive:
        return AdjudicationBreakdown(
            allowed_amount=allowed,
            deductible_applied=zero,
            copay_applied=zero,
            coinsurance_applied=zero,
            oop_adjustment=zero,
            total_patient_responsibility=zero,
            estimated_plan_responsibility=allowed,
            oop_max_reached=(rem_oop == zero),
            new_deductible_met_ytd=claim.deductible_met_ytd,
            new_oop_met_ytd=claim.oop_met_ytd,
        )

    # 2. Flat Copay Branch
    if claim.is_copay_service:
        tentative_copay = min(claim.copay_amount, allowed).quantize(
            cents, rounding=ROUND_HALF_UP
        )

        patient_paid = min(tentative_copay, rem_oop).quantize(
            cents, rounding=ROUND_HALF_UP
        )

        oop_adjustment = (tentative_copay - patient_paid).quantize(
            cents, rounding=ROUND_HALF_UP
        )

        plan_paid = (allowed - patient_paid).quantize(cents, rounding=ROUND_HALF_UP)

        new_oop = min(claim.annual_oop_max, claim.oop_met_ytd + patient_paid)

        return AdjudicationBreakdown(
            allowed_amount=allowed,
            deductible_applied=zero,
            copay_applied=tentative_copay,
            coinsurance_applied=zero,
            oop_adjustment=oop_adjustment,
            total_patient_responsibility=patient_paid,
            estimated_plan_responsibility=plan_paid,
            oop_max_reached=(new_oop >= claim.annual_oop_max),
            new_deductible_met_ytd=claim.deductible_met_ytd,
            new_oop_met_ytd=new_oop,
        )

    # 3. Deductible + Coinsurance Branch

    deductible_applied = min(allowed, rem_deductible).quantize(
        cents, rounding=ROUND_HALF_UP
    )

    remaining_allowed = allowed - deductible_applied

    coinsurance_applied = (remaining_allowed * claim.coinsurance_rate).quantize(
        cents, rounding=ROUND_HALF_UP
    )

    calculated_liability = deductible_applied + coinsurance_applied

    # Enforce remaining out-of-pocket maximum
    patient_paid = min(calculated_liability, rem_oop).quantize(
        cents, rounding=ROUND_HALF_UP
    )

    # Record the reduction caused by the OOP limit
    oop_adjustment = (calculated_liability - patient_paid).quantize(
        cents, rounding=ROUND_HALF_UP
    )

    plan_paid = max(zero, allowed - patient_paid).quantize(
        cents, rounding=ROUND_HALF_UP
    )

    # Only actual patient payments advance the deductible.
    # Deductible responsibility is allocated before coinsurance.
    actual_deductible_paid = min(deductible_applied, patient_paid)

    new_deductible = min(
        claim.annual_deductible, claim.deductible_met_ytd + actual_deductible_paid
    )

    new_oop = min(claim.annual_oop_max, claim.oop_met_ytd + patient_paid)

    return AdjudicationBreakdown(
        allowed_amount=allowed,
        deductible_applied=deductible_applied,
        copay_applied=zero,
        coinsurance_applied=coinsurance_applied,
        oop_adjustment=oop_adjustment,
        total_patient_responsibility=patient_paid,
        estimated_plan_responsibility=plan_paid,
        oop_max_reached=(new_oop >= claim.annual_oop_max),
        new_deductible_met_ytd=new_deductible,
        new_oop_met_ytd=new_oop,
    )
