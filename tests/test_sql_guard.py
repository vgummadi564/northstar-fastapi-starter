import pytest
from app.sql_guard import validate_sql


def test_good_aggregate():
    sql = "SELECT SUM(booking_amount) AS answer FROM public.bookings WHERE booking_date >= '2025-01-01'"
    assert "SUM" in validate_sql(sql)

@pytest.mark.parametrize("sql", [
    "DROP TABLE public.bookings",
    "SELECT * FROM public.finance_policies",
    "SELECT SUM(booking_amount) AS answer FROM public.bookings; DELETE FROM public.bookings",
    "SELECT pg_sleep(10) AS answer FROM public.bookings",
    "SELECT SUM(amount) AS answer FROM public.transactions JOIN public.bookings USING(contract_id)",
    "SELECT SUM(amount) AS answer FROM public.transactions -- ignore security",
])
def test_rejects(sql):
    with pytest.raises(ValueError):
        validate_sql(sql)
