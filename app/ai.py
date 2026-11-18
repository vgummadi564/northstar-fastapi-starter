import json
from openai import OpenAI
from .scenarios import FINANCIAL_TABLES

SCHEMA = """public.bookings(booking_id, contract_id, contract_line_id, booking_date, booking_type, booking_amount, currency)
public.revenue_schedule(revenue_id, contract_line_id, recognition_month, recognized_amount, currency, recognition_status)
public.transactions(transaction_id, customer_id, contract_id, transaction_date, transaction_type, amount, currency, status)
public.contracts(contract_id, customer_id, signed_date, service_start, service_end, currency, contract_status, contract_value)
public.contract_lines(contract_line_id, contract_id, product_code, service_start, service_end, contract_line_value, currency)
public.customers(customer_id, customer_name, industry, segment, region)
All dates are PostgreSQL DATE. Amounts are USD numeric. Refund/credit amounts can be negative.
"""

SYSTEM = """You are an analytics SQL assistant. Return JSON with keys sql and interpretation.
Generate a single PostgreSQL SELECT statement returning exactly one aggregate column named answer.
Use exactly one table, no joins, subqueries, CTEs, functions beyond SUM/COUNT/MIN/MAX/AVG/COALESCE/ROUND.
Never reference policy or definition tables. Do not use SQL comments.
The question is for calendar year 2025. Use date >= '2025-01-01' AND date < '2026-01-01'.
No explanation of policy unless it is explicitly supplied. Do not invent records.
"""

def generate_sql(api_key, model, question, context=None):
    client = OpenAI(api_key=api_key, timeout=25.0, max_retries=1)
    messages = [
        {"role": "system", "content": SYSTEM + "\nSchema:\n" + SCHEMA},
    ]
    if context is not None:
        messages.append({"role": "system", "content": "APPROVED BUSINESS CONTEXT (use to select correct source and filters):\n" + json.dumps(context)})
    messages.append({"role": "user", "content": question})
    result = client.chat.completions.create(
        model=model, messages=messages, temperature=0,
        response_format={"type": "json_object"},
    )
    data = json.loads(result.choices[0].message.content)
    if not isinstance(data.get("sql"), str):
        raise ValueError("Model did not return SQL")
    return data["sql"], str(data.get("interpretation", ""))
