"""HTML report generator — GET /api/v1/sessions/{id}/report"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.models.db import AnalysisResult, RecurringGroup, SavingsRecommendation, UploadSession
from app.services.database import get_db
from app.services import session as session_svc

router = APIRouter(tags=["report"])


@router.get("/sessions/{session_id}/report", response_class=HTMLResponse)
def get_report(session_id: str, db: Session = Depends(get_db)):
    s = session_svc.get_session(db, session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    analysis = db.query(AnalysisResult).filter(AnalysisResult.session_id == session_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not ready")

    recurring = (
        db.query(RecurringGroup)
        .filter(RecurringGroup.session_id == session_id)
        .order_by(RecurringGroup.amount)
        .all()
    )
    rec = db.query(SavingsRecommendation).filter(
        SavingsRecommendation.session_id == session_id
    ).first()

    m = analysis.metrics
    html = _build_html(s, m, analysis.insights or [], recurring, rec)

    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": f'attachment; filename="rupeeradar-report.html"'},
    )


def _fmt(amount: float) -> str:
    return f"₹{abs(amount):,.0f}"


def _build_html(
    session: UploadSession,
    m: dict,
    insights: list[str],
    recurring: list[RecurringGroup],
    rec: SavingsRecommendation | None,
) -> str:
    period = ""
    if m.get("period_start") and m.get("period_end"):
        period = f"{m['period_start']} to {m['period_end']}"

    top_cats_rows = "".join(
        f"<tr><td>{c['category']}</td><td>{_fmt(c['total'])}</td><td>{c['count']}</td></tr>"
        for c in m.get("top_categories", [])
    )

    monthly_rows = "".join(
        f"<tr><td>{mb['month']}</td><td>{_fmt(mb['income'])}</td><td>{_fmt(mb['spend'])}</td></tr>"
        for mb in m.get("monthly_breakdown", [])
    )

    insight_items = "".join(f"<li>{i}</li>" for i in insights)

    recurring_rows = ""
    if recurring:
        recurring_rows = "".join(
            f"<tr><td>{g.label}</td><td>{g.category}</td>"
            f"<td>{_fmt(g.amount)}/month</td><td>{g.frequency}</td><td>{g.last_seen}</td></tr>"
            for g in recurring
        )
        recurring_section = f"""
        <h2>Recurring Payments</h2>
        <table>
          <thead><tr><th>Description</th><th>Category</th><th>Amount</th><th>Frequency</th><th>Last Seen</th></tr></thead>
          <tbody>{recurring_rows}</tbody>
        </table>"""
    else:
        recurring_section = ""

    rec_section = ""
    if rec and rec.recommendations:
        rec_rows = "".join(
            f"<tr><td>{r['category']}</td><td>{_fmt(r['amount_spent'])}</td>"
            f"<td>{_fmt(r['suggested_cap'])}</td><td>{_fmt(r['potential_saving'])}</td>"
            f"<td>{r['suggestion_text']}</td></tr>"
            for r in rec.recommendations
        )
        rec_section = f"""
        <h2>Savings Recommendations</h2>
        <p class="meta">Wants budget: {rec.wants_budget_pct:.0f}% of salary
        {f'(₹{rec.wants_budget:,.0f})' if rec.wants_budget else ''}.
        Status: {'<span class="over">Over budget</span>' if rec.is_over_budget else '<span class="ok">Within budget</span>'}.</p>
        <table>
          <thead><tr><th>Category</th><th>Spent</th><th>Suggested Cap</th><th>Potential Saving</th><th>Suggestion</th></tr></thead>
          <tbody>{rec_rows}</tbody>
        </table>"""

    savings_rate = m.get("savings_rate")
    savings_rate_str = f" ({savings_rate}% rate)" if savings_rate is not None else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RupeeRadar Report — {session.filename}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 14px; color: #1e293b; background: #f8fafc; padding: 24px; }}
  .container {{ max-width: 860px; margin: 0 auto; background: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 8px rgba(0,0,0,.08); }}
  header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 28px; padding-bottom: 20px; border-bottom: 2px solid #e2e8f0; }}
  .logo {{ width: 40px; height: 40px; background: #4f46e5; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: white; font-size: 18px; font-weight: 700; flex-shrink: 0; }}
  h1 {{ font-size: 20px; font-weight: 700; color: #0f172a; }}
  .meta {{ font-size: 12px; color: #64748b; margin-top: 2px; }}
  h2 {{ font-size: 15px; font-weight: 600; color: #0f172a; margin: 24px 0 10px; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 8px; }}
  .card {{ background: #f1f5f9; border-radius: 8px; padding: 14px; }}
  .card-label {{ font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .04em; }}
  .card-value {{ font-size: 20px; font-weight: 700; color: #0f172a; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 10px; background: #f1f5f9; font-weight: 600; color: #334155; border-bottom: 1px solid #e2e8f0; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #f1f5f9; color: #334155; }}
  tr:last-child td {{ border-bottom: none; }}
  ul {{ padding-left: 20px; }}
  li {{ padding: 4px 0; color: #334155; line-height: 1.5; }}
  .over {{ color: #dc2626; font-weight: 600; }}
  .ok {{ color: #16a34a; font-weight: 600; }}
  footer {{ margin-top: 28px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; }}
  @media print {{
    body {{ background: white; padding: 0; }}
    .container {{ box-shadow: none; border-radius: 0; }}
  }}
</style>
</head>
<body>
<div class="container">
  <header>
    <div class="logo">₹</div>
    <div>
      <h1>RupeeRadar — Financial Report</h1>
      <p class="meta">{session.filename}{f' &nbsp;·&nbsp; {period}' if period else ''}</p>
    </div>
  </header>

  <h2>Summary</h2>
  <div class="summary-grid">
    <div class="card"><div class="card-label">Total Income</div><div class="card-value">{_fmt(m.get('total_income', 0))}</div></div>
    <div class="card"><div class="card-label">Total Spend</div><div class="card-value">{_fmt(m.get('total_spend', 0))}</div></div>
    <div class="card"><div class="card-label">Savings</div><div class="card-value">{_fmt(m.get('savings', 0))}{savings_rate_str}</div></div>
  </div>

  <h2>Spending by Category</h2>
  <table>
    <thead><tr><th>Category</th><th>Total</th><th>Transactions</th></tr></thead>
    <tbody>{top_cats_rows}</tbody>
  </table>

  {f'<h2>Monthly Breakdown</h2><table><thead><tr><th>Month</th><th>Income</th><th>Spend</th></tr></thead><tbody>{monthly_rows}</tbody></table>' if monthly_rows else ''}

  {recurring_section}

  <h2>Insights</h2>
  <ul>{insight_items}</ul>

  {rec_section}

  <footer>Generated by RupeeRadar &nbsp;·&nbsp; Your data is processed privately and never shared.</footer>
</div>
</body>
</html>"""
