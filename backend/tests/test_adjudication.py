from decimal import Decimal
import pytest
from adjudication import adjudicate_claim, AdjudicationInput


def test_tc_calc_01_unmet_deductible_absorption():
    """
    TC-CALC-01: Eleanor Vance scenario
    Allowed: $552.00, Deductible: $1,500.00, Deductible met: $200.00 (Remaining: $1,300.00).
    Whole allowed amount is absorbed by the deductible.
    """
    claim = AdjudicationInput(
        allowed_amount=Decimal("552.00"),
        is_preventive=False,
        is_copay_service=False,
        copay_amount=Decimal("0.00"),
        coinsurance_rate=Decimal("0.20"),
        annual_deductible=Decimal("1500.00"),
        deductible_met_ytd=Decimal("200.00"),
        annual_oop_max=Decimal("6000.00"),
        oop_met_ytd=Decimal("200.00"),
    )
    res = adjudicate_claim(claim)
    assert res.allowed_amount == Decimal("552.00")
    assert res.deductible_applied == Decimal("552.00")
    assert res.copay_applied == Decimal("0.00")
    assert res.coinsurance_applied == Decimal("0.00")
    assert res.total_patient_responsibility == Decimal("552.00")
    assert res.estimated_plan_responsibility == Decimal("0.00")
    assert res.new_deductible_met_ytd == Decimal("752.00")
    assert not res.oop_max_reached


def test_tc_calc_02_split_deductible_and_coinsurance():
    """
    TC-CALC-02: Jordan Vance scenario (Knee Surgery)
    Allowed: $2,530.00, Deductible: $1,500.00, Deductible met: $1,200.00 (Remaining: $300.00).
    $300 goes to deductible; remaining $2,230 splits 20% coinsurance ($446.00).
    """
    claim = AdjudicationInput(
        allowed_amount=Decimal("2530.00"),
        is_preventive=False,
        is_copay_service=False,
        copay_amount=Decimal("0.00"),
        coinsurance_rate=Decimal("0.20"),
        annual_deductible=Decimal("1500.00"),
        deductible_met_ytd=Decimal("1200.00"),
        annual_oop_max=Decimal("6000.00"),
        oop_met_ytd=Decimal("1200.00"),
    )
    res = adjudicate_claim(claim)
    assert res.allowed_amount == Decimal("2530.00")
    assert res.deductible_applied == Decimal("300.00")
    assert res.coinsurance_applied == Decimal("446.00")
    assert res.total_patient_responsibility == Decimal("746.00")
    assert res.estimated_plan_responsibility == Decimal("1784.00")
    assert res.new_deductible_met_ytd == Decimal("1500.00")
    assert not res.oop_max_reached


def test_tc_calc_03_out_of_pocket_max_clamp():
    """
    TC-CALC-03: Devon Washington scenario
    Patient has only $150 remaining OOP capacity ($7,500 - $7,350).
    Tentative coinsurance is $180.00, but patient pays only $150.00.
    """
    claim = AdjudicationInput(
        allowed_amount=Decimal("600.00"),
        is_preventive=False,
        is_copay_service=False,
        copay_amount=Decimal("0.00"),
        coinsurance_rate=Decimal("0.30"),
        annual_deductible=Decimal("500.00"),
        deductible_met_ytd=Decimal("500.00"),
        annual_oop_max=Decimal("7500.00"),
        oop_met_ytd=Decimal("7350.00"),
    )
    res = adjudicate_claim(claim)
    assert res.coinsurance_applied == Decimal("180.00")
    assert res.total_patient_responsibility == Decimal("150.00")
    assert res.estimated_plan_responsibility == Decimal("450.00")
    assert res.oop_max_reached is True
    assert res.new_oop_met_ytd == Decimal("7500.00")


def test_preventive_aca_zero_cost():
    """
    TC-PA-02 math verification:
    Preventive services must return zero patient liability.
    """
    claim = AdjudicationInput(
        allowed_amount=Decimal("175.00"),
        is_preventive=True,
        is_copay_service=False,
        copay_amount=Decimal("0.00"),
        coinsurance_rate=Decimal("0.20"),
        annual_deductible=Decimal("1500.00"),
        deductible_met_ytd=Decimal("0.00"),
        annual_oop_max=Decimal("6000.00"),
        oop_met_ytd=Decimal("0.00"),
    )
    res = adjudicate_claim(claim)
    assert res.total_patient_responsibility == Decimal("0.00")
    assert res.estimated_plan_responsibility == Decimal("175.00")
    assert res.deductible_applied == Decimal("0.00")


def test_flat_copay_service():
    """
    Evaluation & Management copay verification (e.g. $45 specialist copay).
    """
    claim = AdjudicationInput(
        allowed_amount=Decimal("115.00"),
        is_preventive=False,
        is_copay_service=True,
        copay_amount=Decimal("45.00"),
        coinsurance_rate=Decimal("0.00"),
        annual_deductible=Decimal("1500.00"),
        deductible_met_ytd=Decimal("0.00"),
        annual_oop_max=Decimal("5000.00"),
        oop_met_ytd=Decimal("200.00"),
    )
    res = adjudicate_claim(claim)
    assert res.copay_applied == Decimal("45.00")
    assert res.deductible_applied == Decimal("0.00")
    assert res.total_patient_responsibility == Decimal("45.00")
    assert res.estimated_plan_responsibility == Decimal("70.00")
    # SO Copay does not advance deductible
    assert res.new_deductible_met_ytd == Decimal("0.00")
    assert res.new_oop_met_ytd == Decimal("245.00")
