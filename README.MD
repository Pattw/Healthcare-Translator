# Healthcare-Translator

Clinical decision support tool and insurance adjudication middleware. Evaluates procedural CPT codes against payer plan profiles, deductibles, prior authorization criteria, and patient liability out-of-pocket costs.

## Tech Stack
- **Backend:** Python, FastAPI, Uvicorn, Pydantic
- **Database:** PostgreSQL / Supabase
- **Frontend:** HTML5, CSS3, JavaScript

## Running Locally

### Backend API
```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8001
```

### Frontend
Open a second terminal and run:

```bash
python3 -m http.server 5500 --directory frontend
```

Then open your browser at:

http://localhost:5500

