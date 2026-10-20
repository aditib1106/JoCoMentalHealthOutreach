\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

-- Fixes schema for Jail MH 2, created on branch jail-mh2-fixes.
-- Mirrors the existing `semantic` schema layout. Nothing in `semantic` is modified.
-- The team decides later whether to swap this into `semantic`.

CREATE SCHEMA IF NOT EXISTS semantic_v2;
ALTER SCHEMA semantic_v2 OWNER TO jail_mh2;
