-- Three layers, one schema each:
--   staging : raw CSV columns we use, typed; plus cleaned/aggregated helper tables
--   dw      : star schema (dimensions + facts) with PK / FK / CHECK constraints
--   mart    : read-only views for KPIs, dashboard and DSS (no data copied)
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS dw;
CREATE SCHEMA IF NOT EXISTS mart;
