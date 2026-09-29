#!/bin/bash
# Reproduces the slide 5 comparisons: outcome window (3/6/9/12 months) and release look-back (12 months/2/3 years).
# Runs update1_baselines.sql with one parameter changed at a time; writes temporary copies to /tmp only.
set -e
cd "$(dirname "$0")"
DB="-h database.mlpolicylab.dssg.io -U ${PGUSER:-$USER} -d johnson_county_ddj_jail_mh2"

for w in 3 6 9 12; do
  sed "s/^\\\\set label_window '12 months'/\\\\set label_window '$w months'/" update1_baselines.sql > /tmp/u1_window_$w.sql
  echo "######## OUTCOME WINDOW = $w months"
  psql $DB -q -f /tmp/u1_window_$w.sql 2>&1 | grep -v NOTICE
done

for lb in "12 months" "2 years" "3 years"; do
  f="/tmp/u1_lookback_${lb// /_}.sql"
  sed "s/^\\\\set lookback '12 months'/\\\\set lookback '$lb'/" update1_baselines.sql > "$f"
  echo "######## LOOK-BACK = $lb"
  psql $DB -q -f "$f" 2>&1 | grep -v NOTICE
done
