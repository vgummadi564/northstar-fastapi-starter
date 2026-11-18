import json
from uuid import uuid4, UUID
from decimal import Decimal, InvalidOperation
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .config import Settings
from .db import query
from .ai import generate_sql
from .scenarios import SCENARIOS, FINANCIAL_TABLES
from .sql_guard import validate_sql

settings = Settings()
app = FastAPI(title="Northstar — From Context to Confidence", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

REPLAY_SQL = {
    ("bookings_vs_revenue", "without_context"): "SELECT SUM(booking_amount) AS answer FROM public.bookings WHERE booking_date >= '2025-01-01' AND booking_date < '2026-01-01'",
    ("bookings_vs_revenue", "with_context"): "SELECT SUM(recognized_amount) AS answer FROM public.revenue_schedule WHERE recognition_month >= '2025-01-01' AND recognition_month < '2026-01-01' AND recognition_status = 'posted'",
    ("gross_vs_net", "without_context"): "SELECT SUM(amount) AS answer FROM public.transactions WHERE transaction_date >= '2025-01-01' AND transaction_date < '2026-01-01' AND transaction_type = 'sale' AND status = 'posted'",
    ("gross_vs_net", "with_context"): "SELECT SUM(amount) AS answer FROM public.transactions WHERE transaction_date >= '2025-01-01' AND transaction_date < '2026-01-01' AND transaction_type IN ('sale', 'refund', 'credit') AND status = 'posted'",
}

class AskRequest(BaseModel):
    scenario: str
    question: str = Field(min_length=5, max_length=500)
    mode: str = "without_context"
    execution: str = "live"  # live LLM or explicitly labeled replay

class RecalculateRequest(BaseModel):
    scenario: str
    question: str = Field(min_length=5, max_length=500)
    execution: str = "live"

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "northstar-fastapi"}

@app.get("/api/scenarios")
def scenarios():
    return [{"id": k, "question": v["question"], "description": v["description"]} for k, v in SCENARIOS.items()]

@app.get("/api/tables")
def tables():
    return {"tables": sorted(FINANCIAL_TABLES)}

@app.get("/api/tables/{table_name}")
def table_preview(table_name: str, limit: int = Query(default=10, ge=1, le=50)):
    if table_name not in FINANCIAL_TABLES:
        raise HTTPException(404, "Table unavailable")
    try:
        # Table name is interpolated only after strict allowlist validation.
        return {"table": table_name, "rows": query(settings.database_url_readonly, f"SELECT * FROM public.{table_name} LIMIT %s", (limit,), max_rows=50)}
    except Exception as exc:
        raise HTTPException(503, "Database preview unavailable") from exc


def approved_context(scenario):
    spec = SCENARIOS[scenario]
    # Fetch only approved versions effective during the 2025 reporting period.
    try:
        policies = query(settings.database_url_backend,
            "SELECT policy_id, policy_name, policy_text, version, effective_date, expiration_date, approval_status FROM public.finance_policies WHERE policy_id = ANY(%s) AND approval_status='approved' AND effective_date <= %s AND (expiration_date IS NULL OR expiration_date >= %s) ORDER BY policy_id",
            (spec["policy_ids"], "2025-12-31", "2025-01-01"))
        metrics = query(settings.database_url_backend,
            "SELECT metric_id, metric_name, business_description, calculation_rule, source_tables, required_filters, reporting_date_column, version, approval_status FROM public.metric_definitions WHERE metric_name ILIKE %s AND approval_status='approved' AND effective_date <= %s AND (expiration_date IS NULL OR expiration_date >= %s)",
            ("%Recognized subscription revenue%" if scenario == "bookings_vs_revenue" else "%Net sales%", "2025-12-31", "2025-01-01"))
        if len(policies) != len(spec["policy_ids"]) or len(metrics) != 1:
            raise ValueError("Approved business context is incomplete")
        return {"policies": policies, "metrics": metrics}
    except Exception as exc:
        raise HTTPException(503, "Approved business context unavailable") from exc

@app.get("/api/context/{scenario}")
def get_context(scenario: str):
    if scenario not in SCENARIOS:
        raise HTTPException(404, "Unknown scenario")
    return approved_context(scenario)


def execute(scenario, question, mode, execution):
    if scenario not in SCENARIOS or mode not in ("without_context", "with_context"):
        raise HTTPException(422, "Unknown scenario or mode")
    if execution not in ("live", "replay"):
        raise HTTPException(422, "Execution must be live or replay")
    context = approved_context(scenario) if mode == "with_context" else None
    try:
        if execution == "replay":
            sql = REPLAY_SQL[(scenario, mode)]
            interpretation = "Curated, labeled replay query; executed against the live database."
        else:
            sql, interpretation = generate_sql(settings.openai_api_key, settings.openai_model, question, context)
        safe_sql = validate_sql(sql)
        rows = query(settings.database_url_readonly, safe_sql, max_rows=1)
        if len(rows) != 1 or "answer" not in rows[0]:
            raise ValueError("Query must return one row with an answer column")
        amount = Decimal(str(rows[0]["answer"]))
        expected = Decimal(SCENARIOS[scenario]["expected_with" if mode == "with_context" else "expected_without"])
        validated = amount == expected
        audit_id = str(uuid4())
        evidence = context or {"policies": [], "metrics": []}
        validation = {"matches_demo_target": validated, "expected": str(expected), "actual": str(amount), "note": "A no-context LLM is not guaranteed to choose the demo's incorrect metric."}
        query(settings.database_url_backend,
            "INSERT INTO public.ai_query_audit (audit_id, scenario, execution_mode, user_question, generated_sql, result_json, policy_evidence_json, validation_json) VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb) RETURNING audit_id",
            (audit_id, scenario, mode, question, safe_sql, json.dumps(rows), json.dumps(evidence), json.dumps({**validation, "execution": execution})),
            readonly=False, max_rows=1)
        return {"run_id": audit_id, "scenario": scenario, "mode": mode, "execution": execution,
                "sql": safe_sql, "interpretation": interpretation, "result": rows[0],
                "context": evidence, "validation": validation}
    except HTTPException:
        raise
    except Exception as exc:
        # Do not leak connection strings, keys, model messages or raw database errors.
        raise HTTPException(422, "Execution failed; check server logs and database permissions") from exc

@app.post("/api/ask")
def ask(req: AskRequest):
    return execute(req.scenario, req.question, req.mode, req.execution)

@app.post("/api/recalculate")
def recalculate(req: RecalculateRequest):
    return execute(req.scenario, req.question, "with_context", req.execution)

@app.get("/api/audit/{run_id}")
def audit(run_id: str):
    try:
        parsed = str(UUID(run_id))
    except ValueError as exc:
        raise HTTPException(422, "Invalid run ID") from exc
    try:
        rows = query(settings.database_url_backend,
            "SELECT audit_id, scenario, execution_mode, user_question, generated_sql, result_json, policy_evidence_json, validation_json, created_at FROM public.ai_query_audit WHERE audit_id=%s", (parsed,), max_rows=1)
    except Exception as exc:
        raise HTTPException(503, "Audit unavailable") from exc
    if not rows:
        raise HTTPException(404, "Audit record not found")
    return rows[0]
