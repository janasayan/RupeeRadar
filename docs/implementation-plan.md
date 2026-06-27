# RupeeRadar — Phase-Wise Implementation Plan

This document breaks down the build into three phases aligned with [`architecture.md`](architecture.md). Each phase delivers a working, testable increment toward the final prototype.

---

## Overview

| Phase | Goal | Duration (est.) | Exit criteria |
|-------|------|-----------------|---------------|
| **Phase 1** | End-to-end vertical slice (upload → dashboard) | 3–5 days | User uploads CSV, sees categorized transactions, metrics, and 3 insights |
| **Phase 2** | Intelligence & recurring detection | 2–4 days | LLM fallback, recurring payments, charts, category override |
| **Phase 2.5** | Needs/wants classification & savings recommendations | 1–2 days | Recommendations panel visible; salary input; ranked suggestions for over-budget wants |
| **Phase 3** | Polish & deliverable | 2–3 days | Multi-bank support, report export, TTL, deployed demo |

**Stack (per architecture):** React + TypeScript + Tailwind · FastAPI · SQLite · pandas · Recharts

**Build order principle:** Backend pipeline first → API → frontend → integration test → move to next phase.

---

## Phase 1 — Vertical Slice (MVP)

### Objective

Prove the full user journey with deterministic logic only: **upload a bank CSV → parse → clean → rule-based categorize → compute metrics → show dashboard with 3 template insights**.

No LLM, no recurring detection, no report export yet.

### 1.1 Project Scaffolding

| # | Task | Details | Output |
|---|------|---------|--------|
| 1.1.1 | Initialize repo structure | Create `backend/`, `frontend/`, `sample-data/` per architecture §15 | Folder layout |
| 1.1.2 | Backend bootstrap | FastAPI app, `requirements.txt` (fastapi, uvicorn, pandas, sqlalchemy, pydantic, python-multipart) | `backend/app/main.py` runs on `:8000` |
| 1.1.3 | Frontend bootstrap | Vite + React + TypeScript + Tailwind | `frontend/` runs on `:5173` |
| 1.1.4 | CORS & API proxy | Configure CORS on backend; Vite proxy to `/api/v1` | Frontend can call backend |
| 1.1.5 | Environment config | `.env.example` with `DATABASE_URL`, `MAX_UPLOAD_SIZE_MB`, `CORS_ORIGINS` | Config documented |
| 1.1.6 | Sample data | Create anonymized HDFC-style CSV fixture with messy UPI strings | `sample-data/hdfc_sample.csv` |

**Checkpoint:** Both servers start; health endpoint `GET /api/v1/health` returns OK.

---

### 1.2 Data Layer

| # | Task | Details | Output |
|---|------|---------|--------|
| 1.2.1 | SQLAlchemy models | `UploadSession`, `Transaction`, `AnalysisResult` (defer `RecurringGroup` to Phase 2) | `backend/app/models/` |
| 1.2.2 | Pydantic schemas | Request/response DTOs matching architecture §3 | `backend/app/models/schemas.py` |
| 1.2.3 | Database setup | SQLite via SQLAlchemy; auto-create tables on startup | `backend/app/services/database.py` |
| 1.2.4 | Session service | Create session, update status, fetch by ID | `backend/app/services/session.py` |

**Schema (Phase 1 minimum):**

```
upload_sessions  → id, filename, file_type, status, uploaded_at, error_message
transactions     → id, session_id, date, description_raw, description_clean,
                   amount, type, balance, category, category_confidence
analysis_results → session_id, metrics (JSON), insights (JSON), generated_at
```

**Checkpoint:** Can create a session and insert transactions via unit test.

---

### 1.3 Pipeline — Parse & Clean

| # | Task | Details | Output |
|---|------|---------|--------|
| 1.3.1 | Parser protocol | Define `StatementParser` interface (architecture §4.1) | `backend/app/parsers/base.py` |
| 1.3.2 | HDFC CSV parser | Header detection, map date/description/debit/credit/balance columns | `backend/app/parsers/hdfc.py` |
| 1.3.3 | Parser registry | Select parser by filename/heuristics; extensible for Phase 3 | `backend/app/parsers/registry.py` |
| 1.3.4 | Cleaner module | Strip UPI noise, normalize dates (ISO 8601), amount signs (debits negative), dedup hash | `backend/app/pipeline/cleaner.py` |
| 1.3.5 | Merchant extraction | Regex + dictionary for Swiggy, Zomato, Amazon, etc. | Part of `cleaner.py` |
| 1.3.6 | Pipeline orchestrator | Run parse → clean sequentially; collect warnings | `backend/app/pipeline/orchestrator.py` |

**Canonical output (architecture §3.2):**

```json
{ "date": "2025-06-01", "description_raw": "...", "amount": -450.00, "type": "debit", "balance": 12500.00 }
```

**Unit tests:**

- [ ] Parses HDFC sample CSV → expected row count
- [ ] Normalizes `DD-MM-YYYY` and `DD/MM/YY` dates
- [ ] Deduplicates identical rows
- [ ] Strips UPI prefix from descriptions

**Checkpoint:** `orchestrator.run(file)` returns cleaned `list[Transaction]`.

---

### 1.4 Pipeline — Categorize, Metrics, Insights

| # | Task | Details | Output |
|---|------|---------|--------|
| 1.4.1 | Category enum & rules | 10 categories (architecture §3.3); keyword/merchant rule table | `backend/app/config/categories.py` |
| 1.4.2 | Rule-based categorizer | Match rules → assign category + confidence (1.0 for rules); default `Other` at 0.0 | `backend/app/pipeline/categorizer.py` |
| 1.4.3 | Metrics calculator | Income, spend, savings, savings rate, top categories, biggest transaction | `backend/app/pipeline/metrics.py` |
| 1.4.4 | Template insights | Generate ≥ 3 insights with real ₹ amounts (architecture §4.6 tier 1) | `backend/app/pipeline/insights.py` |
| 1.4.5 | Wire full pipeline | orchestrator: parse → clean → categorize → metrics → insights → persist | Updated `orchestrator.py` |

**Insight templates (minimum 3):**

1. Top category spend: *"You spent ₹X on {category} — your largest category."*
2. Biggest transaction: *"Your biggest transaction was ₹Y to {merchant} on {date}."*
3. Summary: *"Total income ₹A, total spend ₹B, savings ₹C."*

**Unit tests:**

- [ ] `SWIGGY` → Food, `NETFLIX` → Subscriptions, `SALARY` → Salary
- [ ] Metrics sum correctly on fixture data
- [ ] Insights reference actual amounts from fixture

**Checkpoint:** Full pipeline produces `AnalysisResult` from sample CSV.

---

### 1.5 API (Phase 1 Endpoints)

| # | Task | Endpoint | Notes |
|---|------|----------|-------|
| 1.5.1 | Upload & process | `POST /api/v1/upload` | Multipart file; sync processing; returns `session_id` + status |
| 1.5.2 | Session status | `GET /api/v1/sessions/{id}` | Status, filename, row count, warnings |
| 1.5.3 | Transactions | `GET /api/v1/sessions/{id}/transactions` | Paginated; include raw + clean description |
| 1.5.4 | Analytics | `GET /api/v1/sessions/{id}/analytics` | Metrics JSON |
| 1.5.5 | Insights | `GET /api/v1/sessions/{id}/insights` | Array of insight strings |

**Validation (architecture §4.1):**

- Reject files > 10 MB
- Reject empty/unparseable files with clear error
- Return parse warnings in session metadata

**Checkpoint:** Postman/curl upload → all GET endpoints return valid JSON.

---

### 1.6 Frontend (Phase 1 UI)

| # | Task | Component | Details |
|---|------|-----------|---------|
| 1.6.1 | API client | `src/api/client.ts` | Typed fetch wrappers for Phase 1 endpoints |
| 1.6.2 | Landing page | `pages/Landing.tsx` | Hero, value prop, upload zone |
| 1.6.3 | File upload | `components/FileUpload.tsx` | Drag-drop, accept `.csv`, progress spinner |
| 1.6.4 | Processing status | `components/ProcessingStatus.tsx` | Loading state during sync upload |
| 1.6.5 | Dashboard page | `pages/Dashboard.tsx` | Route `/analysis/:sessionId` |
| 1.6.6 | Summary cards | `components/SummaryCards.tsx` | Income, spend, savings, savings rate |
| 1.6.7 | Category breakdown | `components/CategoryChart.tsx` | Simple bar chart (Recharts) |
| 1.6.8 | Transaction table | `components/TransactionTable.tsx` | Sortable; show raw + clean description + category badge |
| 1.6.9 | Insights panel | `components/InsightCards.tsx` | Display ≥ 3 insight cards |
| 1.6.10 | Error states | Shared component | Unsupported format, empty file, parse warnings |

**UX (architecture §6.4):**

- Show `description_raw` alongside `description_clean`
- Display parse warnings if any rows skipped
- Link to download sample CSV template on error

**Checkpoint:** Upload sample CSV in browser → dashboard renders with all sections populated.

---

### 1.7 Phase 1 Testing & Documentation

| # | Task | Details |
|---|------|---------|
| 1.7.1 | Backend unit tests | Parsers, cleaner, categorizer, metrics, insights |
| 1.7.2 | Integration test | Full pipeline on `hdfc_sample.csv` golden file |
| 1.7.3 | README | Setup instructions, how to run locally, sample upload |
| 1.7.4 | Manual E2E | Upload → verify categories, metrics, insights in UI |

### Phase 1 Definition of Done

- [ ] User uploads HDFC-format CSV via web UI
- [ ] Transactions appear cleaned and rule-categorized
- [ ] Dashboard shows income, spend, savings, category chart, transaction table
- [ ] At least 3 template insights with real amounts displayed
- [ ] Parse warnings surfaced when applicable
- [ ] Backend tests pass on fixture data
- [ ] README documents local setup

---

## Phase 2 — Intelligence & Detection

### Objective

Add **LLM categorization fallback**, **recurring payment detection**, **monthly trend chart**, and **user category override** — closing gaps on architecture requirements for AI categorization and recurring detection.

### 2.1 LLM Categorization

| # | Task | Details | Output |
|---|------|---------|--------|
| 2.1.1 | LLM service abstraction | Provider-agnostic interface; read `LLM_API_KEY` from env | `backend/app/services/llm.py` |
| 2.1.2 | Batch categorization prompt | Send 20–50 unmatched txns; structured JSON response; few-shot UPI examples | Prompt in `categorizer.py` |
| 2.1.3 | Hybrid categorizer flow | Rules → merchant dict → LLM → `Other` if confidence < 0.6 | Updated `categorizer.py` |
| 2.1.4 | Graceful degradation | If LLM unavailable, rules-only with UI badge "AI categorization unavailable" | Error handling per architecture §9.1 |
| 2.1.5 | Privacy guard | Send only `description_clean`, amount, type — never full file | Validated in LLM service |

**Unit tests:**

- [ ] Unmatched transaction batched to LLM mock returns valid category
- [ ] Low confidence (< 0.6) → `Other`
- [ ] LLM failure falls back to rules without crashing pipeline

**Checkpoint:** Messy unknown merchants get LLM-assigned categories.

---

### 2.2 Recurring Payment Detection

| # | Task | Details | Output |
|---|------|---------|--------|
| 2.2.1 | RecurringGroup model | Add DB table per architecture §3.1 | `backend/app/models/` |
| 2.2.2 | Detection algorithm | Group by fuzzy description; ≥ 2 occurrences; amount ±5%; monthly interval | `backend/app/pipeline/recurring.py` |
| 2.2.3 | Pipeline integration | Run after categorization; set `is_recurring` + `recurring_group_id` on transactions | Updated orchestrator |
| 2.2.4 | Recurring metrics | Add `recurring_total` to analytics | Updated `metrics.py` |
| 2.2.5 | Recurring insight template | *"We detected N recurring payments totalling ₹Z/month."* | Updated `insights.py` |
| 2.2.6 | API endpoint | `GET /api/v1/sessions/{id}/recurring` | List of recurring groups |

**Unit tests:**

- [ ] Netflix × 3 months → detected as monthly subscription
- [ ] EMI with stable amount → detected
- [ ] One-off purchase → not flagged recurring

**Checkpoint:** Recurring panel data available via API.

---

### 2.3 Category Override (API + UI)

| # | Task | Details | Output |
|---|------|---------|--------|
| 2.3.1 | PATCH endpoint | `PATCH /api/v1/sessions/{id}/transactions/{txn_id}` with `{ "category": "Food" }` | `api/routes/transactions.py` |
| 2.3.2 | Recompute on override | Optionally recalculate metrics + insights after override | Service layer hook |
| 2.3.3 | UI category editor | Dropdown on transaction row to change category | Updated `TransactionTable.tsx` |
| 2.3.4 | Optimistic update | React Query mutation + invalidation | `src/api/client.ts` |

**Checkpoint:** User can override a category; dashboard metrics update.

---

### 2.4 Enhanced Dashboard

| # | Task | Component | Details |
|---|------|-----------|---------|
| 2.4.1 | Monthly trend chart | `components/MonthlyTrendChart.tsx` | Line/bar chart of spend by month (Recharts) |
| 2.4.2 | Recurring panel | `components/RecurringList.tsx` | Cards: label, amount, frequency, category, last seen |
| 2.4.3 | Dashboard tabs | Updated `Dashboard.tsx` | Tabs: Summary · Transactions · Recurring · Insights |
| 2.4.4 | Confidence indicator | Category badge variant | Show low-confidence / AI-categorized badge |
| 2.4.5 | React Query setup | `@tanstack/react-query` | Replace raw fetch; parallel load transactions, analytics, insights, recurring |

**Checkpoint:** Dashboard shows monthly trend + recurring list + tab navigation.

---

### 2.5 Phase 2 Testing

| # | Task | Details |
|---|------|---------|
| 2.5.1 | Recurring detector unit tests | Multiple fixture patterns (EMI, subscription, rent) |
| 2.5.2 | LLM integration test | Mock LLM; verify hybrid flow |
| 2.5.3 | Golden file update | Expected output includes recurring groups |
| 2.5.4 | Manual E2E | Upload → verify recurring detected → override category → metrics refresh |

### Phase 2 Definition of Done

- [ ] Unmatched transactions categorized via LLM fallback
- [ ] Recurring payments detected and listed in UI
- [ ] Monthly spend trend chart visible
- [ ] User can override transaction category
- [ ] LLM failure degrades gracefully to rules-only
- [ ] ≥ 4 insights including recurring template (if recurring found)
- [ ] All Phase 1 functionality still works

---

## Phase 2.5 — Needs/Wants Classification & Savings Recommendations

### Objective

Build on Phase 2's categorized transactions to **classify every spend as a need or want**, compute whether the user is over their wants budget relative to salary, and surface **ranked, actionable savings suggestions** for over-budget want categories.

### 2.5.1 Needs/Wants Config & Transaction Tagging

| # | Task | Details | Output |
|---|------|---------|--------|
| 2.5.1.1 | Needs/wants mapping | Static dict: `Rent/EMI/Bills/Investments` → need; `Food`(delivery)/`Shopping`/`Travel`/`Subscriptions`/`Other` → want; `Food`(grocery) → need | `backend/app/config/needs_wants.py` |
| 2.5.1.2 | Food sub-classification | Extend categorizer: grocery merchants (Big Bazaar, DMart, Zepto, Blinkit) → need; delivery (Swiggy, Zomato) → want; rule-first, LLM fallback | Updated `categorizer.py` |
| 2.5.1.3 | `needs_wants` field on Transaction | Add `needs_wants: "need" | "want" | "income" | null` column to `transactions` table | DB migration + schema update |
| 2.5.1.4 | Populate field in pipeline | After categorization stage, set `needs_wants` from mapping | Updated orchestrator |

**Unit tests:**
- [ ] `Rent` → need, `Swiggy` → want, `Big Bazaar` → need, `Salary` → income
- [ ] Grocery rule takes priority over food-delivery rule for known merchants

**Checkpoint:** All transactions have `needs_wants` populated.

---

### 2.5.2 Salary Inference & Budget Settings

| # | Task | Details | Output |
|---|------|---------|--------|
| 2.5.2.1 | Salary inference | Take max `Salary`-category credit in period as `salary_monthly`; if multiple months, average | `backend/app/pipeline/recommendations.py` |
| 2.5.2.2 | User salary input | Optional field on dashboard: "Set your monthly salary (₹)" sent via `PATCH /sessions/{id}/recommendations/settings` | Frontend + API |
| 2.5.2.3 | Budget settings endpoint | `PATCH /sessions/{id}/recommendations/settings` with `{ salary_monthly?: number, wants_budget_pct?: number (default 30) }` → recompute | `backend/app/api/routes/recommendations.py` |

**Checkpoint:** API accepts salary and budget % override; recommendations recompute.

---

### 2.5.3 Recommendations Engine

| # | Task | Details | Output |
|---|------|---------|--------|
| 2.5.3.1 | Core algorithm | Sum want-category debits → `wants_actual`; compute `wants_budget`; if under budget emit positive summary only | `recommendations.py` |
| 2.5.3.2 | Over-budget detection | For each want category where `amount_spent > category_share_of_budget`, compute `potential_saving` | `recommendations.py` |
| 2.5.3.3 | LLM suggestion text | Prompt: category name, amount spent, suggested cap, top 3 merchants in category → one actionable sentence in ₹ terms | `recommendations.py` (uses `services/llm.py`) |
| 2.5.3.4 | Rank by saving potential | Sort recommendations by `potential_saving` descending | `recommendations.py` |
| 2.5.3.5 | Persist result | Save `SavingsRecommendation` entity (architecture §3.5) to `savings_recommendations` table | DB model + repo |
| 2.5.3.6 | GET endpoint | `GET /api/v1/sessions/{id}/recommendations` → `SavingsRecommendation` JSON | `api/routes/recommendations.py` |

**Template suggestion fallback (no LLM):** `"Consider reducing {category} spend from ₹{actual} to ₹{cap} to save ₹{saving}/month."`

**Unit tests:**
- [ ] Wants under budget → no recommendations, positive summary emitted
- [ ] Wants over budget → recommendations sorted by saving descending
- [ ] No salary inferred → recommendations skipped; fallback message returned
- [ ] `wants_budget_pct=0` edge case handled without division error

**Checkpoint:** `GET /recommendations` returns ranked suggestions for over-budget sessions.

---

### 2.5.4 Frontend — Recommendations Panel

| # | Task | Component | Details |
|---|------|-----------|---------|
| 2.5.4.1 | Needs vs Wants bar | `components/NeedsWantsBar.tsx` | Stacked bar: needs total / wants total / wants budget threshold line; colour green/amber/red |
| 2.5.4.2 | Recommendations panel | `components/RecommendationsPanel.tsx` | If under budget: green banner "You're within your ₹X wants budget 🎉". If over: ranked cards each showing category, amount spent, suggested cap, potential saving, suggestion text |
| 2.5.4.3 | Salary/budget settings | Inline form inside panel | Input for salary (₹) and wants % with "Recalculate" button; calls PATCH endpoint |
| 2.5.4.4 | Dashboard tab | Add "Recommendations" tab to `Dashboard.tsx` | Route stays `/analysis/:sessionId` |
| 2.5.4.5 | Category chart update | Update `CategoryChart.tsx` | Colour-code bars/slices: blue = need, orange = want |
| 2.5.4.6 | API client | `src/api/client.ts` | Add `getRecommendations()` and `updateRecommendationSettings()` typed wrappers |

**Checkpoint:** Recommendations tab visible; settings form recalculates in real time.

---

### 2.5.5 Phase 2.5 Testing

| # | Task | Details |
|---|------|---------|
| 2.5.5.1 | Needs/wants unit tests | All 10 categories + food sub-types |
| 2.5.5.2 | Algorithm unit tests | Under budget, over budget, no salary, multiple months |
| 2.5.5.3 | LLM suggestion mock test | Mock LLM returns suggestion; verify text stored |
| 2.5.5.4 | Manual E2E | Upload sample CSV → Recommendations tab → adjust salary → verify recalculation |

### Phase 2.5 Definition of Done

- [ ] Every transaction has a `needs_wants` tag visible in transaction table
- [ ] Category chart colour-coded by need/want
- [ ] Needs vs Wants stacked bar on summary
- [ ] Recommendations panel shows ranked suggestions for over-budget sessions
- [ ] User can input salary and adjust wants % threshold
- [ ] Under-budget sessions show positive summary (no false alarm)
- [ ] LLM suggestion text generation degrades to template when LLM unavailable
- [ ] All Phase 1 & 2 functionality still works

---

## Phase 3 — Polish & Deliverable

### Objective

Make the prototype **evaluation-ready**: multi-bank support, report export, privacy controls (TTL/DELETE), LLM narrative insights, and a deployed demo URL.

### 3.1 Multi-Bank & Generic Parser

| # | Task | Details | Output |
|---|------|---------|--------|
| 3.1.1 | ICICI CSV parser | Second bank format | `backend/app/parsers/icici.py` |
| 3.1.2 | Generic CSV mapper | Fallback: auto-detect columns by header keywords (date, narration, debit, credit) | `backend/app/parsers/generic.py` |
| 3.1.3 | Excel support | `.xlsx` via openpyxl through generic parser | Parser extension |
| 3.1.4 | Sample templates | Downloadable sample CSVs for HDFC + ICICI | `sample-data/` + API or static route |
| 3.1.5 | Parser unit tests | Each parser against its fixture | `backend/tests/fixtures/` |

**Checkpoint:** Upload works for HDFC, ICICI, and a generic CSV export.

---

### 3.2 Report Export

| # | Task | Details | Output |
|---|------|---------|--------|
| 3.2.1 | HTML report template | Single-page summary: metrics, top categories, insights, recurring | `backend/app/templates/report.html` |
| 3.2.2 | Report endpoint | `GET /api/v1/sessions/{id}/report?format=html\|pdf` | `api/routes/report.py` |
| 3.2.3 | PDF generation | weasyprint or browser print-to-PDF | PDF download |
| 3.2.4 | Export UI | `components/ReportExport.tsx` | Download HTML/PDF button on dashboard |
| 3.2.5 | Print stylesheet | Screenshot-friendly layout | CSS in report template |

**Checkpoint:** User downloads a shareable PDF/HTML report from dashboard.

---

### 3.3 Privacy & Session Lifecycle

| # | Task | Details | Output |
|---|------|---------|--------|
| 3.3.1 | DELETE endpoint | `DELETE /api/v1/sessions/{id}` — purge all session data | `api/routes/sessions.py` |
| 3.3.2 | Session TTL | Background job or startup sweep; delete sessions older than `SESSION_TTL_HOURS` (default 24h) | `backend/app/services/ttl.py` |
| 3.3.3 | Raw file cleanup | Delete uploaded file from disk immediately after parse | Upload handler |
| 3.3.4 | UI purge button | "Delete my data" on dashboard | Frontend action |
| 3.3.5 | Privacy notice | Short note on upload page about data handling | Landing page copy |

**Checkpoint:** Session data purged on DELETE and after TTL expiry.

---

### 3.4 LLM-Enhanced Insights

| # | Task | Details | Output |
|---|------|---------|--------|
| 3.4.1 | Narrative insight prompt | Feed metrics summary + top categories + recurring total (no PII) | Updated `insights.py` |
| 3.4.2 | Blend template + LLM | Always show 3 template insights; add 2–3 LLM narratives if available | Insight array |
| 3.4.3 | Trend detection | Simple month-over-month category delta for LLM context | Pre-processing in metrics |

**Example LLM insight:** *"Food delivery spending increased 40% from January to March — consider setting a monthly cap."*

**Checkpoint:** Dashboard shows mix of template and LLM-generated insights.

---

### 3.5 Deployment & DevOps

**Deployment targets:** Backend → [Railway](https://railway.app) · Frontend → [Vercel](https://vercel.com)

| # | Task | Details | Output |
|---|------|---------|--------|
| 3.5.1 | Backend Dockerfile | `backend/Dockerfile` — Python 3.11 slim, `uvicorn` entrypoint, SQLite volume mount | Container builds and runs on Railway |
| 3.5.2 | docker-compose.yml | api + web + sqlite volume for local dev parity | One-command local run |
| 3.5.3 | Railway config | `railway.toml` with build command, start command, and health-check path (`/api/v1/health`); set env vars (`DATABASE_URL`, `LLM_API_KEY`, `CORS_ORIGINS`) in Railway dashboard | Railway service live |
| 3.5.4 | Vercel config | `vercel.json` at repo root: rewrites `/api/v1/*` → Railway backend URL; set `VITE_API_BASE_URL` env var in Vercel dashboard | Frontend deployed on Vercel |
| 3.5.5 | CORS update | Set `CORS_ORIGINS` on Railway to include the Vercel production URL (e.g. `https://rupeeradar.vercel.app`) | Cross-origin requests work |
| 3.5.6 | Production Vite build | `vite build` output in `frontend/dist/` served by Vercel CDN | Static assets optimized |
| 3.5.7 | Env documentation | All vars documented in `.env.example`; Railway + Vercel var names noted | Config reproducible |

**Environment variables:**

| Variable | Where set | Notes |
|----------|-----------|-------|
| `DATABASE_URL` | Railway | SQLite path or Postgres URL if upgraded |
| `LLM_API_KEY` | Railway | Groq / OpenAI key |
| `CORS_ORIGINS` | Railway | Comma-separated; must include Vercel URL |
| `VITE_API_BASE_URL` | Vercel | Railway backend URL (e.g. `https://rupeeradar-api.up.railway.app`) |

**Checkpoint:** `docker compose up` runs full stack locally; Railway backend and Vercel frontend live at public URLs.

---

### 3.6 Final Testing & Demo Prep

| # | Task | Details |
|---|------|---------|
| 3.6.1 | Golden files | 3–5 anonymized statements with expected outputs |
| 3.6.2 | Full E2E test | Upload → dashboard → recurring → override → export → delete |
| 3.6.3 | Error scenario testing | Bad file, empty file, LLM down, large file |
| 3.6.4 | Demo script | Step-by-step walkthrough for evaluators | `docs/demo-script.md` |
| 3.6.5 | README finalization | Architecture link, demo URL, feature list, privacy notes |

### Phase 3 Definition of Done

- [ ] HDFC + ICICI + generic CSV supported
- [ ] HTML/PDF report downloadable and shareable
- [ ] Session DELETE and TTL working
- [ ] LLM narrative insights displayed alongside templates
- [ ] Railway backend and Vercel frontend deployed at public URLs
- [ ] Docker Compose runs full stack locally; backend also deployable on Railway
- [ ] All evaluation criteria from `context.md` addressed

---

## Cross-Phase Dependency Graph

```
Phase 1                          Phase 2                         Phase 2.5                       Phase 3
────────                         ─────────                       ──────────                      ─────────
Scaffolding ──────────────────────────────────────────────────────────────────────────────────────────────▶ Docker/deploy
    │
    ▼
Data models ──▶ RecurringGroup model ──▶ needs_wants field + SavingsRecommendation model ──▶ TTL/DELETE
    │
    ▼
Parser (HDFC) ──▶ ICICI + generic parsers
    │
    ▼
Cleaner ──────────────────────────────────────────────────────────────────────────────────────────────────▶ (stable)
    │
    ▼
Rule categorizer ──▶ LLM hybrid + food sub-classification ──▶ needs_wants tagging ──▶ LLM narrative insights
    │
    ▼
Metrics ──▶ + recurring metrics ──▶ + wants_actual / wants_budget ──▶ trend for LLM context
    │
    ▼
Template insights ──▶ + recurring insight ──▶ + savings recommendations ──▶ + LLM insights
    │
    ▼
API (5 endpoints) ──▶ + recurring, PATCH ──▶ + /recommendations, PATCH settings ──▶ + report, DELETE
    │
    ▼
Dashboard (basic) ──▶ + charts, recurring, override ──▶ + NeedsWantsBar, RecommendationsPanel ──▶ + export, privacy UI
```

---

## Requirements Coverage by Phase

| `context.md` requirement | Phase 1 | Phase 2 | Phase 2.5 | Phase 3 |
|----------------------------|---------|---------|-----------|---------|
| Accept bank statement data | ✅ CSV upload | | | ✅ Multi-bank |
| Extract/clean transactions | ✅ | | | |
| Categorize expenses | ✅ Rules | ✅ LLM fallback | ✅ food sub-type | |
| Detect recurring payments | | ✅ | | |
| Calculate metrics | ✅ | ✅ + recurring | ✅ + wants budget | |
| Human-readable insights | ✅ Templates (3) | ✅ + recurring | ✅ + savings recs | ✅ LLM narratives |
| Needs vs wants classification | | | ✅ | |
| Savings recommendations | | | ✅ | |
| Dashboard / report | ✅ Basic dashboard | ✅ Charts, tabs | ✅ Recs panel | ✅ PDF/HTML export |
| Privacy-conscious handling | Basic (no auth) | | | ✅ TTL, DELETE |
| Handle messy descriptions | ✅ Cleaner | ✅ LLM | | |
| End-to-end workflow | ✅ | ✅ | ✅ | ✅ Railway + Vercel deployed |

---

## Suggested Task Order (First 10 Tasks)

When starting implementation, execute in this order:

1. **1.1.1–1.1.3** — Scaffold backend + frontend
2. **1.1.6** — Create sample HDFC CSV fixture
3. **1.2.1–1.2.4** — Database models + session service
4. **1.3.1–1.3.6** — Parser + cleaner + orchestrator
5. **1.4.1–1.4.5** — Categorizer + metrics + insights
6. **1.5.1–1.5.5** — API endpoints
7. **1.7.1–1.7.2** — Unit + integration tests
8. **1.6.1–1.6.10** — Frontend (can parallelize with 7)
9. **1.7.4** — Manual E2E verification
10. **Phase 2.1.1** — Begin LLM integration

---

## Risk Register

| Risk | Impact | Mitigation | Phase |
|------|--------|------------|-------|
| Bank CSV format differs from fixture | Parse failures | Generic column mapper fallback | 3 |
| LLM API unavailable or costly | Poor categorization for unknown merchants | Rules-first; degrade gracefully | 2 |
| Recurring false positives | Noisy recurring panel | Tune tolerance; require ≥ 2 months | 2 |
| Large statements slow sync pipeline | Timeout UX | Paginate UI; background jobs if >5s | 2–3 |
| Sensitive data exposure | Privacy violation | TTL, DELETE, no PII logging | 3 |
| PDF parsing complexity | Delayed delivery | CSV-first; PDF as stretch only | 3 (optional) |

---

## Source

Derived from [`docs/architecture.md`](architecture.md), [`docs/context.md`](context.md), and [`docs/problemStatement.txt`](problemStatement.txt).
