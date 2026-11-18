from contextlib import contextmanager
from decimal import Decimal
from datetime import date, datetime
import psycopg
from psycopg.rows import dict_row


def json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    return value

@contextmanager
def connect(dsn, *, readonly=True):
    with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=8) as conn:
        with conn.transaction():
            if readonly:
                conn.execute("SET TRANSACTION READ ONLY")
            conn.execute("SET LOCAL statement_timeout = '5000ms'")
            conn.execute("SET LOCAL search_path = public, pg_catalog")
            yield conn


def query(dsn, sql, params=(), *, readonly=True, max_rows=100):
    with connect(dsn, readonly=readonly) as conn:
        rows = conn.execute(sql, params).fetchmany(max_rows + 1)
        if len(rows) > max_rows:
            raise ValueError("Query returned too many rows")
        return json_safe(rows)
