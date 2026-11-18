-- REVIEW BEFORE RUNNING. Replace passwords with securely generated secrets.
-- Execute as a database administrator in Supabase SQL Editor.
-- These roles are not a substitute for reviewing RLS and public API exposure.
CREATE ROLE northstar_reader LOGIN PASSWORD 'REPLACE_WITH_STRONG_READER_PASSWORD';
CREATE ROLE northstar_backend LOGIN PASSWORD 'REPLACE_WITH_STRONG_BACKEND_PASSWORD';
GRANT CONNECT ON DATABASE postgres TO northstar_reader, northstar_backend;
GRANT USAGE ON SCHEMA public TO northstar_reader, northstar_backend;
GRANT SELECT ON public.customers, public.contracts, public.contract_lines,
  public.bookings, public.revenue_schedule, public.transactions TO northstar_reader;
GRANT SELECT ON public.metric_definitions, public.finance_policies,
  public.metric_policy_links, public.ai_query_audit TO northstar_backend;
GRANT INSERT ON public.ai_query_audit TO northstar_backend;
-- IMPORTANT: inspect Supabase anon/authenticated PUBLIC grants and RLS separately.
