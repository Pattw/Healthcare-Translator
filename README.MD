# Healthcare-Translator

## Health Coverage & Cost Decision-Support System

Healthcare-Translator is a web-based healthcare decision-support prototype designed to improve insurance coverage transparency, prior authorization guidance, and patient cost estimation.

The system evaluates CPT/HCPCS procedure codes, ICD-10 diagnosis codes, insurance benefit parameters, patient accumulators, and modeled payer coverage rules to generate estimated financial responsibility and clinical documentation requirements.

The application provides two specialized interfaces: a technical provider console and a plain-language patient portal.

## Key Features

- **Prior Authorization Evaluation:** Determines whether prior authorization is likely required, not indicated, or cannot be determined from available information.
- **Diagnosis-Based Rule Evaluation:** Evaluates ICD-10 diagnosis codes against configured procedure-specific coverage criteria.
- **Financial Calculation Engine:** Calculates deductibles, copayments, coinsurance, and estimated patient and insurance plan responsibility using Python Decimal arithmetic.
- **Out-of-Pocket Maximum Enforcement:** Limits eligible patient responsibility and provides an itemized explanation of cost reductions.
- **Clinical Documentation Checklist:** Dynamically generates documentation requirements from stored payer policies.
- **Benefit Accumulator Visualization:** Displays current and projected deductible and out-of-pocket spending.
- **Dual-Audience Interface:** Presents technical information to healthcare providers and simplified explanations to patients.
- **Safe Fallback Handling:** Identifies missing or unsupported information without presenting unsupported authorization determinations.

## Technology Stack

| Layer           | Technologies               |
| --------------- | -------------------------- |
| Backend         | Python, FastAPI, Uvicorn   |
| Data Validation | Pydantic                   |
| Database        | PostgreSQL, Supabase       |
| Frontend        | HTML5, CSS3, JavaScript    |
| API             | REST, JSON                 |
| Testing         | Pytest, FastAPI TestClient |
| Version Control | Git, GitHub                |

## System Architecture

The application uses a layered architecture consisting of:

1. **Presentation Layer:** Provider and patient web interfaces.
2. **Application Layer:** FastAPI endpoints and request processing.
3. **Business Logic Layer:** Independent financial calculation and prior authorization engines.
4. **Data Layer:** PostgreSQL database hosted through Supabase.

The database contains four primary entities:

- `procedures`
- `insurance_plans`
- `patients`
- `coverage_rules`

## Installation and Configuration

### 1. Clone the Repository

```bash
git clone https://github.com/Pattw/Healthcare-Translator.git
cd Healthcare-Translator
```

### 2. Configure the Python Environment

The application was developed and tested using Python 3.14.

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the required dependencies:

```bash
python -m pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_key
```

The Supabase database must contain the required tables and populated demonstration datasets.

The database structure is defined in `schema.sql`.

Never commit environment credentials or API keys to version control.

## Running Locally

### Terminal 1 — Backend API

From the project root:

```bash
source .venv/bin/activate
cd backend
python -m uvicorn main:app --reload --port 8000
```

Backend API:

http://127.0.0.1:8000

Interactive API documentation:

http://127.0.0.1:8000/docs

### Terminal 2 — Frontend

Open a separate terminal from the project root:

```bash
cd frontend
python3 -m http.server 5500
```

Open the application in your browser:

http://localhost:5500/coverage_check.html

Both servers must remain running while using the application.

## API Endpoints

| Method | Endpoint                    | Description                                         |
| ------ | --------------------------- | --------------------------------------------------- |
| GET    | `/api/v1/patients`          | Retrieve synthetic patient records                  |
| GET    | `/api/v1/procedures`        | Retrieve supported procedures                       |
| GET    | `/api/v1/diagnoses`         | Retrieve supported diagnosis codes                  |
| POST   | `/api/v1/evaluate-coverage` | Evaluate authorization guidance and estimated costs |

## Automated Testing

From the project root, with the virtual environment activated:

```bash
PYTHONPATH=backend python -m pytest -v
```

API and integration tests require valid Supabase credentials and the configured demonstration database.

### Verification Results

As of November 25, 2026:

| Test Category         | Passed | Failed |
| --------------------- | -----: | -----: |
| Financial Calculation |      8 |      0 |
| API                   |      6 |      0 |
| Integration           |      9 |      0 |
| Prior Authorization   |      9 |      0 |
| **Total**             | **32** |  **0** |

Testing includes:

- Deductible absorption and coinsurance calculation
- Preventive care and flat copayment scenarios
- Out-of-pocket maximum enforcement
- Financial reconciliation and accumulator accuracy
- Diagnosis matching and normalization
- Missing and invalid coverage criteria
- Clinical documentation extraction
- Invalid procedure and patient handling
- Database-backed API integration

## Healthcare Standards Context

The prototype is informed by healthcare interoperability and coverage evaluation workflows, including:

- CPT and HCPCS procedural coding
- ICD-10-CM diagnostic coding
- CMS healthcare pricing reference information
- HL7 Da Vinci Coverage Requirements Discovery (CRD)
- HL7 Da Vinci Documentation Templates and Rules (DTR)

The application does not implement full production FHIR interoperability or direct payer integration.

## Limitations

This application is an academic prototype and is not intended for production clinical or insurance use.

- All patient information is synthetic.
- Insurance policies and reimbursement parameters are modeled or illustrative.
- Supported procedures, plans, and diagnosis mappings are limited.
- Prior authorization results are guidance, not official payer determinations.
- Financial calculations are estimates, not guarantees of final patient liability.
- Red-flag exceptions and appeal criteria are not automatically evaluated.
- Production EHR, payer, and claims-processing integrations are outside the project scope.

## Academic Context

Developed as an individual software engineering project for CIS 434 — Software Engineering.

The project demonstrates requirements engineering, relational database design, modular software architecture, REST API development, financial calculation logic, user interface design, and automated software verification.
