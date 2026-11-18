-- Illustrative no-context query (valid SQL, wrong business metric):
SELECT SUM(booking_amount) AS answer FROM public.bookings WHERE booking_date >= '2025-01-01' AND booking_date < '2026-01-01';
-- Context-enabled answer to recognized subscription revenue:
SELECT SUM(recognized_amount) AS answer FROM public.revenue_schedule WHERE recognition_month >= '2025-01-01' AND recognition_month < '2026-01-01' AND recognition_status='posted';
-- Illustrative no-context gross sales query (wrong for net sales):
SELECT SUM(amount) AS answer FROM public.transactions WHERE transaction_date >= '2025-01-01' AND transaction_date < '2026-01-01' AND transaction_type='sale' AND status='posted';
-- Context-enabled net sales query:
SELECT SUM(amount) AS answer FROM public.transactions WHERE transaction_date >= '2025-01-01' AND transaction_date < '2026-01-01' AND transaction_type IN ('sale','refund','credit') AND status='posted';
