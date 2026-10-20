# Jail MH 2 — v2 changes on branch `jail-mh2-fixes`

This document records the changes we're making on `jail-mh2-fixes` in response
to the professor's feedback on Update 2. **Nothing on the submitted branches
`jail-mh2-update1` and `jail-mh2-update2` is modified.** The frozen branches
still reproduce the slide numbers for those submissions.

The v2 changes land in a parallel schema, `semantic_v2`, so the team can
compare before/after and decide when to swap it into `semantic`.

Changes are grouped by the professor's point. Each entry says what he said,
where the issue lived, what we did, and what remains open.

---

## 1. Silent dropping of linked ids — fixed

**Professor's point:** The v1 crosswalk filtered to source ids with exactly
one matched person and set `entity_id` to NULL for the rest. Downstream event
tables that joined on `entity_id` therefore silently removed the people
behind those ids. He asked us to keep every id and flag the ones that look
wrong instead of dropping them.

**Where it lived:** `step1_build_data/01_person_xwalk.sql`
(the `CASE WHEN n_entity_ids = 1 THEN entity_id END` branch), carried into
every event table through the `LEFT JOIN semantic.person_xwalk` pattern.

**Scale of the drop (from the Update 1 Phase 2 checks, not re-measured):**
JCMHC services about 559,145 of 4,609,027 rows and 2,820 patient ids;
crisis calls about 46,939 rows; diagnoses about 40,208 rows; police arrests
about 593 rows and 128 ids; state corrections tied to 1 id. Jail
ids showed zero ambiguous links.

**What `semantic_v2` does:** `semantic_v2.person_xwalk` keeps every
`(source, source_id)` row from `raw.jocojococlient`. For each id it stores
`entity_id = MIN(joid)`, `n_entity_ids = COUNT(DISTINCT joid)`, and a boolean
`check_linkage = (n_entity_ids > 1)`. Every event table in `semantic_v2`
left-joins to this table so every source row survives and inherits
`check_linkage`. Downstream analyses can filter, split, or run sensitivity on
the flagged rows; no silent exclusion.

**Open:** `MIN(joid)` is still an arbitrary pick when `check_linkage` is
true. The flag makes that visible rather than hiding it. Alternative
treatments (duplicate the event per candidate person, keep as separate
people) are a sensitivity run, not a semantic-layer change.

## 2. Semantic crosswalk duplicating `raw.jocojococlient` — kept as a thin wrapper, documented

**Professor's point:** `semantic.person_xwalk` was questioned as redundant,
since `raw.jocojococlient` already has these fields. He suggested joining
directly to the raw table on source and MNI.

**What `semantic_v2` does:** We chose a thin wrapper rather than deleting
the table. The wrapper adds exactly three things to the raw rows:
`entity_id` as `MIN(joid)`, `n_entity_ids`, and `check_linkage`. These are
what the event tables need to join once and inherit the flag without each
event build re-reading `raw.jocojococlient`. The file header in
`01_person_xwalk_v2.sql` documents this decision in full.

**Open (team decision):** if the group prefers the direct-join form, each
event build would compute `check_linkage` inline against the raw table.
Equivalent, slightly simpler for a TA to read, slightly slower per build.

## 3. Zero-padding of the jail MNI — unchanged, documented

**Professor's point:** The MNI stored as integer in `cleaned.jocojimsinmatedata`
has no leading zeros; `raw.jocojococlient.sourceid` for JIMS is 9 characters
with leading zeros. A direct comparison returns zero rows silently.

**What `semantic_v2` does:** `02_bookings_v2.sql` continues to call
`lpad(mni_no::text, 9, '0')` before matching the crosswalk. The crosswalk
`btrim`s the `sourceid` value so later joins don't have to worry about
whitespace. The rationale is in the file header.

## 4. Seven-day information lag — removed

## 4. Seven-day information lag — removed

**Professor's point:** The 7 days was an arbitrary number with no empirical
basis ("why seven days, why not three minutes, why not three months"). He
asked us to delete the filter entirely, not comment it out, and treat the
90-day and 12-month windows as the only cohort/label windows that remain
parameters.

**Where it lived:**
`step3_triage/mcrt_triage_config.yaml` (four `::date - 7` references and
one `::date - 7 - 90`), `step2_update1_baselines/1_baselines_three_dates.sql`
and `2_baselines_18_month_avg.sql` (`\set lag 7` and eight `:lag`
expressions), the root `README.md` data-lag bullet.

**What we did:** All references to the 7-day lag are deleted (not commented
out). Service, screen, pretrial and LSI-R windows now compare the record's
date to `as_of_date` directly. The "not engaged" window is
`[as_of_date - 90 days, as_of_date)`.

**Consequence:** The Update 1 anchor of 4,462 / 1,150 / 3,312 / 0 at
2018-05-01 was computed with the lag and will not reproduce from
`semantic_v2` after this change. The team will record new anchors as part
of the validation checks in section 7. The Update 1 and Update 2 slides
on the frozen branches do not change; the lag figures there document the
submission-time state.


**What we did:** All references to the 7-day lag are deleted (not commented
out). Service, screen, pretrial and LSI-R windows now compare the record's
date to `as_of_date` directly. The "not engaged" window is
`[as_of_date - 90 days, as_of_date)`.

**Consequence:** The Update 1 anchor of 4,462 / 1,150 / 3,312 / 0 at
2018-05-01 was computed with the lag and will not reproduce from
`semantic_v2` after this change. The team will record new anchors as part
of the validation checks in section 7. The Update 1 and Update 2 slides
on the frozen branches do not change; the lag figures there document the
submission-time state.

## 5. Comments annotating filters — applied

**Professor's point:** The cohort query lacked comments mapping filters to
the formulation spec on the slides, and some CTE names
(`jail_mh_flagged`) read like "everyone released and not in jail" rather
than "released + jail-flagged for MH need". Future readers (and the TA)
should be able to verify each line against the spec.

**What we did:**
* Every `*_v2.sql` file in `step1_build_data/` has a file-header block
  describing what the table holds and how it differs from v1.
* `step3_triage/mcrt_triage_config.yaml` now carries a per-filter quote
  from the Update 1 formulation sentence above each CTE, and CTE names
  were expanded (for example, `jail_mh_flagged` →
  `flagged_mh_by_jail_assessment`, with a separate
  `released_in_past_12m_and_not_in_jail` CTE) so each name matches what
  the filter actually enforces.

## 6. Shared output folder — set up on this branch; parameterization deferred

**Professor's point:** The 90-day and 12-month windows should become
command-line parameters so configurations can be varied without
overwriting files, and output logs should live in a shared group
directory, not individual home directories.

**Shared output folder (applied):**
`/class/groups/jail_mh2/triage_runs_v2/` with permissions `drwxrws---`
and group `jail_mh2`. The setgid bit means every subfolder and file
inside inherits the group, so teammates can read each other's run
folders without extra chmod. `step3_triage/run.py` writes there by
default and creates a timestamped per-run subfolder so runs don't
overwrite each other.

The repo's `.gitignore` lists `triage_output/`, `triage_output_jail_mh2/`,
`run_stdout.log` and `triage.log` so no one accidentally commits
person-level matrices or logs.

**Parameterization (deferred):** `--release-lookback`, `--service-days`
and `--label-timespan` CLI flags are not implemented yet. The group
will agree on the flag names and defaults before we add them.

## 7. Validation after the rebuild — to be run by the team

Once `semantic_v2` is built, the team will run the following and record
before/after for each:

1. Row counts and `check_linkage` splits per event table in `semantic_v2`
   versus `semantic`.
2. Count of flagged source ids per source in `semantic_v2.person_xwalk`.
3. Cohort and label counts for 2017-05-01 and 2018-05-01 under the v2
   crosswalk and with the 7-day lag removed. These are new anchors; they
   won't match the Update 1 figure of 4,462 / 1,150 / 3,312 / 0.
4. Cohort filters counted alone (released, not in jail, jail-flagged,
   not engaged) to show how many each step removes.

The team's decision to swap `semantic_v2` into `semantic` depends on
these numbers and on separate review of the policy consequences.

## 8. Branch and schema policy

- Submitted branches `jail-mh2-update1` and `jail-mh2-update2` are frozen.
- All v2 work happens on `jail-mh2-fixes`.
- All v2 tables live in schema `semantic_v2`, owned by role `jail_mh2`.
