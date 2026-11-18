SCENARIOS = {
    "bookings_vs_revenue": {
        "question": "What was our recognized subscription revenue in 2025?",
        "metric_id": "recognized_subscription_revenue",
        "policy_ids": ["POL-001", "POL-002", "POL-004"],
        "expected_without": "12800000.00", "expected_with": "10400000.00",
        "description": "Bookings vs. recognized subscription revenue",
    },
    "gross_vs_net": {
        "question": "What were our net sales in 2025 after refunds and credits?",
        "metric_id": "net_sales",
        "policy_ids": ["POL-003", "POL-004"],
        "expected_without": "8600000.00", "expected_with": "7900000.00",
        "description": "Gross vs. net sales",
    },
}
FINANCIAL_TABLES = frozenset({"customers", "contracts", "contract_lines", "bookings", "revenue_schedule", "transactions"})
