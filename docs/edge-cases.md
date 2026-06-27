# RupeeRadar — Edge Cases & Corner Cases

This document catalogs known edge cases, boundary conditions, and failure scenarios for RupeeRadar. Use it during implementation and testing to ensure the pipeline, API, and UI handle real-world Indian bank statement data gracefully.

**Sources:** [`architecture.md`](architecture.md) · [`implementation-plan.md`](implementation-plan.md)

---

## How to Read This Document

| Column | Meaning |
|--------|---------|
| **ID** | Unique reference for tests and issue tracking |
| **Phase** | When the case must be handled (1, 2, 3) |
| **Priority** | `P0` = must handle before demo · `P1` = should handle · `P2` = nice to have |
| **Component** | Pipeline stage or layer affected |

**Expected behavior** describes what the system should do — not necessarily what is implemented yet.

---

## 1. File Upload & Ingestion

| ID | Edge case | Expected behavior | Phase | Priority |
|----|-----------|-------------------|-------|----------|
| UP-01 | Empty file (0 bytes) | Reject with error: *"No transactions found"*; session status `failed` | 1 | P0 |
| UP-02 | File exceeds max size (> 10 MB) | Reject before parsing; HTTP 413 with clear message | 1 | P0 |
| UP-03 | Unsupported file type (`.txt`, `.json`, `.doc`) | Reject with supported formats list (CSV, XLSX, PDF) | 1 | P0 |
| UP-04 | Renamed file (`.csv` extension but not CSV content) | Attempt parse; fail gracefully with format error | 1 | P1 |
| UP-05 | Password-protected PDF | Reject with message: *"Password-protected files are not supported"* | 3 | P1 |
| UP-06 | Corrupted / truncated CSV | Parse partial rows if possible; return warnings; fail if zero valid rows | 1 | P0 |
| UP-07 | CSV with wrong encoding (UTF-16, Latin-1) | Try UTF-8 first, fallback encodings; warn if characters garbled | 1 | P1 |
| UP-08 | CSV with BOM (byte order mark) | Strip BOM before parsing; do not treat as column name | 1 | P1 |
| UP-09 | Upload while previous session still processing | Allow new upload (new session); do not block or overwrite | 1 | P2 |
| UP-10 | Duplicate upload of identical file | Create new session; dedup within session only, not across sessions | 1 | P2 |
| UP-11 | File with only headers, no data rows | Reject: *"No transactions found"* | 1 | P0 |
| UP-12 | Multipart upload with no file field | HTTP 422 validation error | 1 | P1 |
| UP-13 | Excel file with multiple sheets | Parse first sheet with transactions; warn if others ignored | 3 | P2 |
| UP-14 | Excel with merged header cells | Unmerge or use first row heuristic; log warning | 3 | P2 |

---

## 2. Parsing & Extraction

| ID | Edge case | Expected behavior | Phase | Priority |
|----|-----------|-------------------|-------|----------|
| PR-01 | Unknown bank format (no matching parser) | Fall back to generic column mapper (Phase 3); else clear error + sample template link | 1/3 | P0 |
| PR-02 | Header row not on first line (preamble text) | Skip preamble lines; detect header by keyword heuristics | 1 | P1 |
| PR-03 | Missing required column (no date column) | Fail with message indicating which column could not be detected | 1 | P0 |
| PR-04 | Missing description/narration column | Fail or use placeholder; do not silently drop rows | 1 | P0 |
| PR-05 | Single amount column (signed) instead of debit/credit split | Parse signed amount directly; infer type from sign | 1 | P0 |
| PR-06 | Separate debit and credit columns with both populated | Reject row or prefer debit; log warning | 1 | P1 |
| PR-07 | Debit and credit columns both empty for a row | Skip row; increment skipped count in warnings | 1 | P0 |
| PR-08 | Amount with currency symbol (`₹`, `Rs.`, `INR`) | Strip symbols and commas before parsing | 1 | P0 |
| PR-09 | Amount in parentheses `(1,500.00)` indicating debit | Treat as negative debit per accounting convention | 1 | P1 |
| PR-10 | Amount as integer without decimals (`450`) | Parse as `450.00` | 1 | P0 |
| PR-11 | Scientific notation in amount (`1.5E3`) | Parse correctly or skip with warning | 2 | P2 |
| PR-12 | Partial parse (462 rows, 12 invalid) | Import valid rows; return *"Imported 450 of 462 rows"* + warning list | 1 | P0 |
| PR-13 | Statement spans multiple years | Parse all; metrics default to full range | 1 | P0 |
| PR-14 | Statement with only one transaction | Process successfully; insights adapt to single-row data | 1 | P1 |
| PR-15 | PDF with scanned images (no text layer) | Fail with *"Could not extract text; try CSV export"* | 3 | P2 |
| PR-16 | PDF with multi-page tables split across pages | Stitch rows where possible; warn on broken rows | 3 | P2 |
| PR-17 | Generic CSV with non-English column headers | Match by synonym list (`txn date`, `narration`, `withdrawal`, `deposit`) | 3 | P1 |
| PR-18 | Extra metadata columns (ref no., cheque no.) | Ignore extra columns; store ref in `metadata` if useful | 1 | P2 |

---

## 3. Cleaning & Normalization

| ID | Edge case | Expected behavior | Phase | Priority |
|----|-----------|-------------------|-------|----------|
| CL-01 | Date format `DD-MM-YYYY` | Normalize to ISO `YYYY-MM-DD` | 1 | P0 |
| CL-02 | Date format `DD/MM/YY` (2-digit year) | Infer century (e.g. `25` → `2025`); warn if ambiguous | 1 | P0 |
| CL-03 | Date format `01-Jun-2025` | Parse month abbreviations | 1 | P1 |
| CL-04 | Invalid date (`32-13-2025`, `00-00-0000`) | Skip row; add to warnings | 1 | P0 |
| CL-05 | Future-dated transaction | Accept but flag in warnings (possible statement error) | 1 | P2 |
| CL-06 | Duplicate rows (identical date, amount, description) | Deduplicate via hash; log count removed | 1 | P0 |
| CL-07 | Near-duplicate rows (same day, same amount, slightly different description) | Keep both; do not over-deduplicate | 1 | P1 |
| CL-08 | Reversal / refund (credit after debit for same merchant) | Keep both as separate transactions; do not net | 1 | P1 |
| CL-09 | UPI description variants (`UPI-SWIGGY`, `UPI/DR/SWIGGY`, `UPI-Swiggy@paytm`) | Strip noise; extract merchant `Swiggy` | 1 | P0 |
| CL-10 | NEFT/IMPS with long reference strings | Preserve `description_raw`; extract counterparty name where possible | 1 | P1 |
| CL-11 | Empty or whitespace-only description | Skip row or categorize as `Other` with zero confidence | 1 | P0 |
| CL-12 | Description contains account number | Do not expose in LLM payload; mask in logs | 2 | P0 |
| CL-13 | Very long description (> 500 chars) | Truncate for display; preserve full text in `description_raw` | 1 | P2 |
| CL-14 | Credit recorded as positive in debit column (bank error) | Use column semantics over sign when debit/credit columns exist | 1 | P1 |
| CL-15 | Zero-amount transaction | Skip or include with warning; exclude from spend/income totals | 1 | P1 |
| CL-16 | Balance column missing | Set `balance` to `null`; pipeline continues | 1 | P1 |
| CL-17 | Balance column inconsistent with amount | Do not use balance for calculations; log optional warning | 1 | P2 |
| CL-18 | Mixed case merchant names (`swiggy`, `SWIGGY`, `Swiggy`) | Normalize to consistent case for matching | 1 | P0 |
| CL-19 | Transaction on month boundary (31 Jan vs 1 Feb) | Assign to correct calendar month for monthly aggregations | 1 | P0 |
| CL-20 | Self-transfer between own accounts | May appear as debit + credit pair; categorize both; optional `Other` or `Investments` | 2 | P2 |

---

## 4. Categorization

| ID | Edge case | Expected behavior | Phase | Priority |
|----|-----------|-------------------|-------|----------|
| CT-01 | Known merchant in rule table (`SWIGGY`) | Assign category with confidence `1.0` | 1 | P0 |
| CT-02 | Unknown merchant, no rule match | LLM fallback (Phase 2); else `Other` at confidence `0.0` | 1/2 | P0 |
| CT-03 | Description matches multiple rules | Use most specific rule or highest-priority rule; document precedence | 1 | P1 |
| CT-04 | Generic description (`UPI PAYMENT`, `POS TXN`) | LLM or `Other`; flag low confidence in UI | 2 | P0 |
| CT-05 | Salary credit with non-standard label (`ACME CORP PAYROLL`) | Rule + LLM should map to `Salary` | 1/2 | P0 |
| CT-06 | Investment credit (redemption, dividend) | Map to `Investments`, not `Salary` | 2 | P1 |
| CT-07 | Rent paid via UPI to individual (no "RENT" keyword) | LLM or recurring detection may help; default `Other` acceptable | 2 | P1 |
| CT-08 | Amazon purchase (Shopping vs Subscriptions vs Bills) | Use amount/context heuristics; Prime → Subscriptions, order → Shopping | 2 | P1 |
| CT-09 | LLM returns invalid category name | Reject response; assign `Other` | 2 | P0 |
| CT-10 | LLM returns confidence < 0.6 | Assign `Other`; show review badge in UI | 2 | P0 |
| CT-11 | LLM API timeout or rate limit | Retry once; then rules-only; show degradation badge | 2 | P0 |
| CT-12 | LLM returns malformed JSON | Fall back to `Other` for affected batch | 2 | P0 |
| CT-13 | LLM API key missing or invalid | Rules-only categorization; no pipeline crash | 2 | P0 |
| CT-14 | Credit categorized as expense category | Allow but flag; metrics use `type` field, not category alone | 1 | P1 |
| CT-15 | User overrides category via PATCH | Persist override; optionally recompute metrics and insights | 2 | P0 |
| CT-16 | User overrides to same category | Idempotent; no unnecessary recompute | 2 | P2 |
| CT-17 | Override on transaction in recurring group | Update transaction only; recurring group label unchanged unless recomputed | 2 | P2 |
| CT-18 | Batch of 500+ unmatched transactions | Batch LLM calls in chunks of 20–50; do not exceed token limits | 2 | P1 |
| CT-19 | Merchant name embedded in UPI handle (`paytmqr@paytm`) | Extract best-effort merchant; avoid false rule matches | 1 | P1 |
| CT-20 | Cash withdrawal (ATM) | Categorize as `Other` or dedicated handling; exclude from merchant rules | 1 | P2 |

---

## 5. Recurring Payment Detection

| ID | Edge case | Expected behavior | Phase | Priority |
|----|-----------|-------------------|-------|----------|
| RC-01 | Monthly subscription (Netflix, same amount, 3+ months) | Detect as `monthly` recurring group | 2 | P0 |
| RC-02 | EMI with fixed amount | Detect as `monthly`; category `EMI` | 2 | P0 |
| RC-03 | Rent paid on varying day (1st vs 3rd) | Allow interval tolerance ~28–32 days | 2 | P1 |
| RC-04 | Amount varies within ±5% (GST, forex fee) | Still group if within tolerance | 2 | P1 |
| RC-05 | Amount varies > 5% (tiered utility bill) | Do not group; or group with `unknown` frequency | 2 | P1 |
| RC-06 | Only one occurrence of merchant | Do not flag as recurring | 2 | P0 |
| RC-07 | Two occurrences in same month | Do not flag as monthly recurring (need span ≥ 2 months) | 2 | P0 |
| RC-08 | Same merchant, different amounts (Swiggy orders) | Do not group as recurring subscription | 2 | P0 |
| RC-09 | Fuzzy description drift (`NETFLIX.COM` vs `NETFLIX INDIA`) | Token overlap / Levenshtein grouping | 2 | P1 |
| RC-10 | SIP investment (monthly debit to Zerodha/Groww) | Detect as recurring; category `Investments` | 2 | P1 |
| RC-11 | Annual insurance premium (single debit) | Not detected as recurring without 2+ occurrences | 2 | P2 |
| RC-12 | Weekly recurring (rare) | Detect `weekly` cadence if intervals ~7 days | 2 | P2 |
| RC-13 | Stopped subscription (2 months then nothing) | Still show historical recurring group with last seen date | 2 | P1 |
| RC-14 | Duplicate recurring groups (same merchant split) | Merge groups with same normalized merchant | 2 | P2 |
| RC-15 | No recurring payments in statement | Recurring panel shows empty state; skip recurring insight | 2 | P0 |
| RC-16 | Salary credit (monthly) | Do not flag salary as recurring expense | 2 | P1 |
| RC-17 | Refund breaks recurring pattern | Exclude refund from interval calculation | 2 | P2 |

---

## 6. Metrics & Aggregations

| ID | Edge case | Expected behavior | Phase | Priority |
|----|-----------|-------------------|-------|----------|
| MT-01 | No income (only debits) | Total income = 0; savings negative; savings rate undefined or 0% | 1 | P0 |
| MT-02 | No expenses (only credits) | Total spend = 0; savings = income | 1 | P0 |
| MT-03 | Income equals spend | Savings = 0; savings rate = 0% | 1 | P0 |
| MT-04 | Spend exceeds income (deficit) | Show negative savings; insight highlights overspend | 1 | P0 |
| MT-05 | Division by zero for savings rate | When income = 0, display *"N/A"* or omit rate | 1 | P0 |
| MT-06 | Single category dominates (> 90% spend) | Top category insight still valid | 1 | P0 |
| MT-07 | All transactions categorized as `Other` | Top category = `Other`; insight reflects low categorization coverage | 1 | P1 |
| MT-08 | Tie for top category (equal spend) | Pick one deterministically (alphabetical or first by date) | 1 | P2 |
| MT-09 | Biggest transaction tie (same amount) | Return all tied or pick most recent | 1 | P2 |
| MT-10 | Statement covers partial month | Monthly filter uses calendar month of txn date | 1 | P1 |
| MT-11 | "This month" filter with no txns in current month | Show empty state or fall back to latest month with data | 2 | P1 |
| MT-12 | Large outlier (one ₹5L debit) | Include in metrics; biggest transaction insight reflects it | 1 | P0 |
| MT-13 | Recurring total with mixed frequencies | Sum monthly equivalents; document assumption | 2 | P1 |
| MT-14 | Category override changes top category | Recompute metrics on PATCH | 2 | P0 |
| MT-15 | Floating-point rounding (₹0.01 drift) | Use decimal type; round display to 2 places | 1 | P1 |
| MT-16 | Very large statement (5,000+ rows) | Metrics computation must complete in acceptable time (< 5s) | 2 | P1 |
| MT-17 | Transactions outside statement date order | Sort by date for trends; metrics unaffected | 1 | P1 |

---

## 7. Insight Generation

| ID | Edge case | Expected behavior | Phase | Priority |
|----|-----------|-------------------|-------|----------|
| IN-01 | Fewer than 3 distinct insight sources | Still produce ≥ 3 insights (summary, top category, biggest txn) | 1 | P0 |
| IN-02 | No debits (income only) | Insights focus on income; skip spend category insight | 1 | P1 |
| IN-03 | No recurring detected | Omit recurring template; use alternate template | 2 | P0 |
| IN-04 | Insight amounts must match metrics | Template values derived from same metrics object | 1 | P0 |
| IN-05 | LLM insight contradicts metrics | Prefer template insights; discard or flag LLM output | 3 | P1 |
| IN-06 | LLM unavailable for narrative insights | Show template insights only (≥ 3) | 3 | P0 |
| IN-07 | Month-over-month trend with only one month | Skip trend insight; no false "increase/decrease" | 3 | P1 |
| IN-08 | Category override after insights generated | Regenerate insights on recompute | 2 | P1 |
| IN-09 | Very small spend (₹50 total) | Insights still cite actual amounts; no division errors | 1 | P2 |
| IN-10 | Unicode / special chars in merchant name for insight text | Escape for display; preserve in insight string | 1 | P2 |

---

## 8. API & Session Lifecycle

| ID | Edge case | Expected behavior | Phase | Priority |
|----|-----------|-------------------|-------|----------|
| AP-01 | GET session with invalid UUID | HTTP 404 | 1 | P0 |
| AP-02 | GET session before processing complete | Return status `processing`; frontend polls | 1 | P0 |
| AP-03 | GET session that failed | Return status `failed` + `error_message` | 1 | P0 |
| AP-04 | GET transactions with invalid session ID | HTTP 404 | 1 | P0 |
| AP-05 | Pagination: page beyond last page | Return empty list, not error | 1 | P1 |
| AP-06 | Pagination: page size = 0 or negative | Default to sensible page size (e.g. 50) | 1 | P2 |
| AP-07 | PATCH transaction not in session | HTTP 404 | 2 | P0 |
| AP-08 | PATCH with invalid category enum | HTTP 422 validation error | 2 | P0 |
| AP-09 | DELETE session | Purge session, transactions, analysis, recurring groups | 3 | P0 |
| AP-10 | DELETE already-deleted session | HTTP 404 (idempotent acceptable: 204) | 3 | P1 |
| AP-11 | Access session after TTL expiry | HTTP 404; data purged | 3 | P0 |
| AP-12 | Concurrent GET requests for same session | Safe; read-only | 1 | P1 |
| AP-13 | Report export for failed session | HTTP 400 or 404 with clear message | 3 | P1 |
| AP-14 | Report export format invalid (`?format=doc`) | HTTP 422; support `html` and `pdf` only | 3 | P2 |
| AP-15 | CORS request from unauthorized origin | Block per `CORS_ORIGINS` config | 1 | P1 |

---

## 9. Frontend & UX

| ID | Edge case | Expected behavior | Phase | Priority |
|----|-----------|-------------------|-------|----------|
| UX-01 | User navigates to `/analysis/invalid-id` | Show error page; link back to upload | 1 | P0 |
| UX-02 | Network error during upload | Show retry option; do not lose selected file | 1 | P0 |
| UX-03 | Slow processing (> 5s) | Show loading spinner; optional stage indicator | 1 | P1 |
| UX-04 | Parse warnings present | Display warning banner with count and details | 1 | P0 |
| UX-05 | Empty transaction table after filter | Show "No transactions match filter" | 1 | P1 |
| UX-06 | Chart with single category | Render chart without error | 1 | P1 |
| UX-07 | Chart with all zero values | Show empty state | 1 | P2 |
| UX-08 | Very long transaction table (2000+ rows) | Paginate or virtualize; do not render all at once | 2 | P1 |
| UX-09 | Category override network failure | Revert optimistic update; show error toast | 2 | P1 |
| UX-10 | Mobile viewport | Responsive layout; table scrolls horizontally | 1 | P2 |
| UX-11 | Browser refresh on dashboard | Re-fetch session data; no localStorage of financial data | 1 | P0 |
| UX-12 | Back button from dashboard | Return to landing; session still valid until TTL | 1 | P2 |
| UX-13 | PDF report download fails | Show error; offer HTML fallback | 3 | P1 |
| UX-14 | Delete my data confirmation | Confirm dialog before DELETE | 3 | P1 |

---

## 10. Privacy & Security

| ID | Edge case | Expected behavior | Phase | Priority |
|----|-----------|-------------------|-------|----------|
| PV-01 | Raw file on disk after parse | Delete immediately post-parse | 3 | P0 |
| PV-02 | Account number in description sent to LLM | Strip/mask before LLM call | 2 | P0 |
| PV-03 | Full statement sent to LLM | Never; batch descriptions only | 2 | P0 |
| PV-04 | Transaction data in application logs | Log counts and IDs only; no amounts/descriptions | 1 | P0 |
| PV-05 | Session accessible without auth (prototype) | Acceptable for demo; document in privacy notice | 1 | P1 |
| PV-06 | User guesses another session UUID | Return 404 if not found; no enumeration leak | 1 | P1 |
| PV-07 | LLM provider logs prompts | Use provider with minimal retention; document in privacy notice | 2 | P1 |
| PV-08 | Report PDF shared publicly | User responsibility; no account IDs in report | 3 | P2 |
| PV-09 | SQLite file on shared machine | Document local-only demo risk | 1 | P2 |

---

## 11. Performance & Scale

| ID | Edge case | Expected behavior | Phase | Priority |
|----|-----------|-------------------|-------|----------|
| PF-01 | Statement with ~2,000 rows | Sync processing acceptable (< 10s) | 1 | P0 |
| PF-02 | Statement with 5,000+ rows | Consider background job + polling; or warn user | 2/3 | P1 |
| PF-03 | LLM batch for 200 unmatched txns | Sequential batches; total time bounded | 2 | P1 |
| PF-04 | Multiple simultaneous uploads | Handle concurrently; separate sessions | 2 | P2 |
| PF-05 | Database growth from many sessions | TTL sweep prevents unbounded growth | 3 | P0 |
| PF-06 | Memory spike loading large CSV | Stream or chunk parse if needed | 3 | P2 |

---

## 12. Indian Bank & UPI Specific Cases

Real-world messy data called out in architecture and implementation plan fixtures.

| ID | Edge case | Example | Expected behavior | Phase |
|----|-----------|---------|-------------------|-------|
| IB-01 | UPI with numeric ref only | `UPI/123456789012/SWIGGY` | Extract merchant after last segment | 1 |
| IB-02 | UPI collect request | `UPI-REV-MPAY` | Preserve raw; clean to best-effort label | 1 |
| IB-03 | NEFT salary credit | `NEFT CR-SALARY ACME CORP` | Category `Salary` | 1 |
| IB-04 | IMPS transfer to self | `IMPS/SELF/FUND TRANSFER` | `Other` or transfer handling | 2 |
| IB-05 | Autopay / NACH debit | `NACH-DR-HOME LOAN` | Category `EMI`; recurring candidate | 2 |
| IB-06 | SIP mutual fund | `BSE SIP ZERODHA` | Category `Investments`; recurring | 2 |
| IB-07 | Credit card bill payment | `CC PAYMENT HDFC` | Category `Bills`; not double-counted if CC stmt separate | 2 |
| IB-08 | Cashback credit | Small credit from merchant | Keep as credit; `Other` or match merchant category | 2 |
| IB-09 | Fuel surcharge reversal | Paired debit + credit | Keep both rows | 1 |
| IB-10 | Mixed Hindi/English description | `भुगतान SWIGGY` | UTF-8 handling; merchant extraction on Latin portion | 1 |
| IB-11 | PhonePe / GPay wrapper | `PHONEPE-SWIGGY` | Map to underlying merchant | 1 |
| IB-12 | Failed transaction row in export | Zero amount or "FAILED" status | Skip from metrics | 1 |

---

## 13. Needs/Wants Classification & Savings Recommendations

| ID | Edge case | Expected behavior | Phase | Priority |
|----|-----------|-------------------|-------|----------|
| RW-01 | No salary credit in statement | Skip threshold comparison; return breakdown with note "Set your salary for personalised recommendations" | 2.5 | P0 |
| RW-02 | Multiple salary credits (multiple employers or arrears) | Sum all `Salary` credits for the period; or use largest single credit as monthly proxy | 2.5 | P1 |
| RW-03 | Salary varies month to month | Use average of `Salary` credits across statement period | 2.5 | P1 |
| RW-04 | Wants spend exactly equals budget | Emit positive summary; no recommendations | 2.5 | P0 |
| RW-05 | Wants spend marginally over budget (< 5%) | Emit recommendations with low-urgency tone | 2.5 | P2 |
| RW-06 | All spend in needs categories | No want categories to flag; show "Great — 100% of spend is in needs" | 2.5 | P0 |
| RW-07 | All spend in want categories (no rent/EMI/bills) | Needs = 0; wants = total; recommendations still valid | 2.5 | P1 |
| RW-08 | `wants_budget_pct` set to 0 | Treat as "not set"; skip threshold; avoid division-by-zero | 2.5 | P0 |
| RW-09 | `wants_budget_pct` set to 100 | Always under budget; no recommendations generated | 2.5 | P2 |
| RW-10 | Food category mixed (groceries + delivery) | Split by sub-type: grocery → need, delivery → want; apply correct amounts to each bucket | 2.5 | P1 |
| RW-11 | Unknown food merchant (no rule match, no LLM) | Default food → want (conservative); user can override category | 2.5 | P1 |
| RW-12 | User overrides transaction category after recommendations | Trigger recommendation recompute if `needs_wants` classification changes | 2.5 | P1 |
| RW-13 | LLM unavailable for suggestion text | Fall back to template: "Consider reducing {category} from ₹{actual} to ₹{cap} to save ₹{saving}/month." | 2.5 | P0 |
| RW-14 | LLM returns suggestion without ₹ amounts | Validate; reject; use template fallback | 2.5 | P1 |
| RW-15 | Statement covers multiple months; salary set for single month | Normalize want spend to monthly average before comparison | 2.5 | P1 |
| RW-16 | Needs alone exceed income (salary very low) | Surface negative savings rate; note that needs exceed income | 2.5 | P1 |
| RW-17 | PATCH settings `wants_budget_pct` < 0 or > 100 | HTTP 422 validation error | 2.5 | P0 |
| RW-18 | PATCH settings with negative salary | HTTP 422 validation error | 2.5 | P0 |
| RW-19 | Recommendations panel with no over-budget categories | Show green "within budget" card; hide ranked suggestion list | 2.5 | P0 |
| RW-20 | Tie in potential savings between two want categories | Break tie alphabetically for consistent ordering | 2.5 | P2 |

---

## 14. Test Fixture Matrix

Map edge cases to recommended test fixtures in `backend/tests/fixtures/` and `sample-data/`.

| Fixture file | Edge cases covered |
|--------------|-------------------|
| `hdfc_sample.csv` | CL-01, CL-06, CL-09, CT-01, IB-01, IB-03 (baseline happy path) |
| `hdfc_messy_dates.csv` | CL-02, CL-03, CL-04, PR-12 |
| `hdfc_duplicates.csv` | CL-06, CL-07 |
| `hdfc_income_only.csv` | MT-02, IN-02, RW-06 |
| `hdfc_expense_only.csv` | MT-01, MT-04, RW-01 |
| `hdfc_recurring.csv` | RC-01, RC-02, RC-06, RC-08 |
| `hdfc_single_row.csv` | PR-14, IN-01 |
| `hdfc_needs_wants.csv` | RW-01, RW-06, RW-07, RW-10, RW-11 (mixed food merchants, no salary) |
| `hdfc_over_budget.csv` | RW-04, RW-05, RW-12, RW-15 (wants > 30% salary) |
| `generic_unknown_bank.csv` | PR-01, PR-17 |
| `invalid_empty.csv` | UP-01, UP-11 |
| `invalid_corrupt.csv` | UP-06, PR-12 |
| `large_2000_rows.csv` | PF-01, UX-08 |

---

## 15. Priority Summary for Demo Readiness

### P0 — Must handle before evaluation demo

- All **UP-01, UP-02, UP-03, UP-06, UP-11** (upload validation)
- All **PR-03, PR-05, PR-07, PR-08, PR-10, PR-12** (core parsing)
- All **CL-01, CL-02, CL-04, CL-06, CL-09, CL-11** (cleaning)
- All **CT-01, CT-02, CT-11, CT-12, CT-13** (categorization + LLM degrade)
- All **RC-01, RC-02, RC-06, RC-07, RC-08, RC-15** (recurring basics)
- All **MT-01 through MT-05, MT-12** (metrics edge math)
- All **IN-01, IN-03, IN-04, IN-06** (insights minimum)
- All **AP-01 through AP-04, AP-07, AP-08** (API errors)
- All **UX-01, UX-02, UX-04, UX-11** (frontend errors)
- All **PV-01, PV-02, PV-03, PV-04** (privacy)
- All **RW-01, RW-04, RW-06, RW-08, RW-13, RW-17, RW-18, RW-19** (recommendations core)

### P1 — Should handle for quality demo

- Remaining parsing, cleaning, and categorization cases marked P1
- Recurring tolerance and fuzzy matching
- Pagination, filters, chart edge cases
- Session TTL and DELETE

### P2 — Post-demo / stretch

- PDF parsing edge cases
- Weekly/yearly recurring cadences
- Advanced performance optimization

---

## 16. Edge Case → Component Quick Reference

```
Upload (UP-)          → api/routes/upload, FileUpload.tsx
Parse (PR-)           → parsers/*, registry.py
Clean (CL-)           → pipeline/cleaner.py
Categorize (CT-)      → pipeline/categorizer.py, services/llm.py
Recurring (RC-)       → pipeline/recurring.py
Metrics (MT-)         → pipeline/metrics.py
Insights (IN-)        → pipeline/insights.py
Needs/Wants (RW-)     → pipeline/recommendations.py, config/needs_wants.py,
                         api/routes/recommendations.py, RecommendationsPanel.tsx
API (AP-)             → api/routes/*
UX (UX-)              → frontend/components/*
Privacy (PV-)         → services/ttl.py, upload handler, llm.py
Performance (PF-)     → orchestrator.py, pagination
India-specific (IB-)  → cleaner.py, categorizer.py, fixtures
```

---

## Source

Derived from [`docs/architecture.md`](architecture.md) and [`docs/implementation-plan.md`](implementation-plan.md).
