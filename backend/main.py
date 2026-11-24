# main.py
import os
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

from adjudication import adjudicate_claim, AdjudicationInput
from prior_auth import evaluate_prior_authorization

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_KEY environment variables are required."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(
    title="Health Coverage Decision-Support Engine",
    description="Backend engine for Prior Authorization and Patient Cost Estimation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def quantize_money(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# --- Pydantic Schemas ---
class CoverageEvaluationRequest(BaseModel):
    patient_id: str
    cpt_code: str
    icd10_code: Optional[str] = None


class CostBreakdown(BaseModel):
    base_allowable: float
    contract_multiplier: float
    total_allowed_amount: float
    deductible_applied: float
    copay_applied: float
    coinsurance_applied: float
    oop_adjustment: float
    total_patient_responsibility: float
    estimated_plan_responsibility: float
    oop_max_reached: bool


class AccumulatorBreakdown(BaseModel):
    individual_deductible: float
    deductible_met_before: float
    deductible_met_after: float
    annual_oop_max: float
    oop_met_before: float
    oop_met_after: float


class CoverageEvaluationResponse(BaseModel):
    patient_id: str
    patient_name: str
    plan_name: str
    procedure_code: str
    procedure_name: str
    is_preventive: bool
    pa_required: bool
    pa_status: str
    denial_rationale: Optional[str]
    required_documents: List[str]
    financial_breakdown: CostBreakdown
    accumulators: AccumulatorBreakdown


# --- API Routes ---
@app.post("/api/v1/evaluate-coverage", response_model=CoverageEvaluationResponse)
def evaluate_coverage(request: CoverageEvaluationRequest):
    # 1. Fetch Patient Record
    pat_res = (
        supabase.table("patients")
        .select("*")
        .eq("patient_id", request.patient_id)
        .execute()
    )
    if not pat_res.data:
        raise HTTPException(
            status_code=404, detail=f"Patient '{request.patient_id}' not found."
        )
    patient = pat_res.data[0]
    plan_id = patient.get("plan_id")
    if not plan_id:
        raise HTTPException(
            status_code=400, detail="Patient has no associated insurance plan."
        )

    # 2. Fetch Procedure Record
    proc_res = (
        supabase.table("procedures")
        .select("*")
        .eq("cpt_code", request.cpt_code)
        .execute()
    )
    if not proc_res.data:
        raise HTTPException(
            status_code=404, detail=f"Procedure code '{request.cpt_code}' not found."
        )
    procedure = proc_res.data[0]

    # 3. Fetch Insurance Plan Record
    plan_res = (
        supabase.table("insurance_plans").select("*").eq("plan_id", plan_id).execute()
    )
    if not plan_res.data:
        raise HTTPException(
            status_code=404, detail=f"Insurance plan '{plan_id}' not found."
        )
    plan = plan_res.data[0]

    # 4. Fetch Matching Coverage Rule
    rule_res = (
        supabase.table("coverage_rules")
        .select("*")
        .eq("cpt_code", request.cpt_code)
        .eq("plan_id", plan_id)
        .execute()
    )
    rule = rule_res.data[0] if rule_res.data else None

    is_preventive = bool(procedure.get("is_preventive", False))

    # --- Call Prior Auth Module ---
    pa_result = evaluate_prior_authorization(
        cpt_code=request.cpt_code,
        is_preventive=is_preventive,
        rule=rule,
        icd10_code=request.icd10_code,
    )

    # --- Prepare Adjudication Inputs ---
    base_cost = Decimal(str(procedure["base_allowable_cost"]))
    multiplier = Decimal(str(plan.get("contract_multiplier", 1.00)))
    total_allowed = quantize_money(base_cost * multiplier)

    category = procedure.get("category", "").upper()
    is_copay = False
    copay_amount = Decimal("0.00")
    coinsurance_rate = Decimal("0.20")

    if category == "IMAGING":
        coinsurance_rate = Decimal(str(plan.get("imaging_coinsurance", 0.20)))
    elif category in ("SURGERY", "OUTPATIENT_SURGERY"):
        coinsurance_rate = Decimal(
            str(plan.get("outpatient_surgery_coinsurance", 0.20))
        )
    elif category == "EVALUATION":
        is_copay = True
        copay_amount = Decimal(str(plan.get("specialist_copay", 0.00)))

    adj_input = AdjudicationInput(
        allowed_amount=total_allowed,
        is_preventive=is_preventive,
        is_copay_service=is_copay,
        copay_amount=copay_amount,
        coinsurance_rate=coinsurance_rate,
        annual_deductible=Decimal(str(plan["individual_deductible"])),
        deductible_met_ytd=Decimal(str(patient["deductible_met_ytd"])),
        annual_oop_max=Decimal(str(plan["oop_max"]))
        if plan.get("oop_max") is not None
        else Decimal("999999.00"),
        oop_met_ytd=Decimal(str(patient["oop_met_ytd"])),
    )

    # --- Call Adjudication Module ---
    financial = adjudicate_claim(adj_input)

    indiv_ded = float(plan.get("individual_deductible", 0.00))
    ded_before = float(patient.get("deductible_met_ytd", 0.00))
    ded_after = float(financial.new_deductible_met_ytd)

    oop_limit = float(plan["oop_max"]) if plan.get("oop_max") is not None else 999999.00
    oop_before = float(patient.get("oop_met_ytd", 0.00))
    oop_after = float(financial.new_oop_met_ytd)

    # Return statement executes unconditionally
    return CoverageEvaluationResponse(
        patient_id=patient["patient_id"],
        patient_name=f"{patient['first_name']} {patient['last_name']}",
        plan_name=plan.get("plan_name", patient.get("plan_id", "Sample Plan")),
        procedure_code=procedure["cpt_code"],
        procedure_name=procedure["description"],
        is_preventive=is_preventive,
        pa_required=pa_result.pa_required,
        pa_status=pa_result.pa_status.value,
        denial_rationale=pa_result.determination_summary,
        required_documents=pa_result.checklist,
        financial_breakdown=CostBreakdown(
            base_allowable=float(base_cost),
            contract_multiplier=float(multiplier),
            total_allowed_amount=float(financial.allowed_amount),
            deductible_applied=float(financial.deductible_applied),
            copay_applied=float(financial.copay_applied),
            coinsurance_applied=float(financial.coinsurance_applied),
            oop_adjustment=float(financial.oop_adjustment),
            total_patient_responsibility=float(financial.total_patient_responsibility),
            estimated_plan_responsibility=float(
                financial.estimated_plan_responsibility
            ),
            oop_max_reached=financial.oop_max_reached,
        ),
        accumulators=AccumulatorBreakdown(
            individual_deductible=indiv_ded,
            deductible_met_before=ded_before,
            deductible_met_after=ded_after,
            annual_oop_max=oop_limit,
            oop_met_before=oop_before,
            oop_met_after=oop_after,
        ),
    )


@app.get("/api/v1/patients")
def get_patients():
    return (
        supabase.table("patients")
        .select("patient_id, first_name, last_name, plan_id")
        .execute()
        .data
    )


@app.get("/api/v1/procedures")
def get_procedures():
    return (
        supabase.table("procedures")
        .select("cpt_code, description, category, is_preventive")
        .execute()
        .data
    )


@app.get("/api/v1/diagnoses")
def get_diagnoses():
    return [
        {"icd10_code": "M25.561", "description": "Pain in right knee"},
        {"icd10_code": "M25.562", "description": "Pain in left knee"},
        {"icd10_code": "M54.50", "description": "Low back pain, unspecified"},
        {"icd10_code": "R51.9", "description": "Headache, unspecified"},
        {
            "icd10_code": "Z00.00",
            "description": "General adult medical exam without abnormal findings",
        },
    ]
