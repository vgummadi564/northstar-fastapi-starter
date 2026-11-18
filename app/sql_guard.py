"""Conservative starter guard. Combine with a DB-enforced SELECT-only role.
Only simple single-table SELECT aggregates are allowed for LLM-generated SQL.
"""
import sqlglot
from sqlglot import exp
from .scenarios import FINANCIAL_TABLES

ALLOWED_FUNCTIONS = {"SUM", "COUNT", "MIN", "MAX", "AVG", "COALESCE", "ROUND"}
FORBIDDEN = (exp.Subquery, exp.Union, exp.Intersect, exp.Except, exp.Join, exp.With,
             exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter,
             exp.Command, exp.Into, exp.Window, exp.CTE)


def validate_sql(sql: str) -> str:
    if not sql or len(sql) > 4000 or "--" in sql or "/*" in sql or "*/" in sql:
        raise ValueError("SQL rejected: invalid size or comments")
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except Exception as exc:
        raise ValueError("SQL rejected: parse failure") from exc
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise ValueError("Only a single SELECT statement is allowed")
    root = statements[0]
    if any(isinstance(node, FORBIDDEN) for node in root.walk()):
        raise ValueError("SQL construct not permitted")
    tables = list(root.find_all(exp.Table))
    if len(tables) != 1 or tables[0].name.lower() not in FINANCIAL_TABLES:
        raise ValueError("Query must reference exactly one permitted financial table")
    if tables[0].db and tables[0].db.lower() != "public":
        raise ValueError("Only public schema permitted")
    if root.args.get("limit") is not None or root.args.get("offset") is not None:
        raise ValueError("LLM SQL must be a scalar aggregate")
    if root.args.get("group") or root.args.get("order") or root.args.get("having"):
        raise ValueError("Grouped queries not supported in this starter")
    if len(root.expressions) != 1 or root.expressions[0].find(exp.AggFunc) is None:
        raise ValueError("Query must select one aggregate result")
    for node in root.walk():
        if isinstance(node, exp.Func):
            name = node.sql_name().upper()
            if name not in ALLOWED_FUNCTIONS:
                raise ValueError(f"SQL function not allowed: {name}")
    return root.sql(dialect="postgres")
