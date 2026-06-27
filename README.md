# RupeeRadar

AI-powered personal finance assistant that analyzes bank statements and shows where your money goes.

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | React, TypeScript, Tailwind CSS, Vite |
| Backend | Python, FastAPI, SQLAlchemy, pandas |
| Database | SQLite (local) |
| LLM | [Groq](https://groq.com) (`llama-3.3-70b-versatile`) |

## Project structure

```
RupeeRadar/
├── backend/          # FastAPI API & processing pipeline
├── frontend/         # React dashboard
├── sample-data/      # Anonymized bank statement fixtures
└── docs/             # Architecture, implementation plan, edge cases
```

## Prerequisites

- Python 3.9+
- Node.js 18+

## Setup

### 1. Environment

```bash
cp .env.example .env
```

Edit `.env` and set your Groq API key (required from Phase 2):

```
GROQ_API_KEY=your_key_here
```

Get a key at [console.groq.com](https://console.groq.com).

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health check: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api/v1` to the backend.

## Sample data

An anonymized HDFC-style CSV is at `sample-data/hdfc_sample.csv` for local testing once upload is implemented in Phase 1.

## Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

## Implementation phases

| Phase | Status | Scope |
|-------|--------|-------|
| **0** | Done | Project scaffolding, health check, Groq config |
| **1** | Next | CSV upload → parse → categorize → dashboard |
| **2** | Planned | Groq categorization, recurring detection |
| **3** | Planned | Multi-bank, report export, deployment |

See [`docs/implementation-plan.md`](docs/implementation-plan.md) for details.

## Documentation

- [`docs/context.md`](docs/context.md) — Project requirements
- [`docs/architecture.md`](docs/architecture.md) — System design
- [`docs/implementation-plan.md`](docs/implementation-plan.md) — Phase-wise build plan
- [`docs/edge-cases.md`](docs/edge-cases.md) — Corner cases & test matrix
