\set ON_ERROR_STOP on
\timing on
SET enable_nestloop = off;

CREATE TEMP TABLE tmp_lsir AS
SELECT btrim(lsir_no) AS lsir_no,
       hash_case_no,
       assessment_date,
       CASE WHEN split_part(btrim(create_stamp), '*', 1) ~ '^[0-9]+$'
            THEN date '1967-12-31' + split_part(btrim(create_stamp), '*', 1)::int
       END AS created_date,
       total_score, score, no_score_flag, percentile,
       btrim(cls)             AS cls,
       btrim(referral_source) AS referral_source,
       btrim(referral_reason) AS referral_reason,
       btrim(override_flg)    AS override_flg,
       ans_1,  ans_2,  ans_3,  ans_4,  ans_5,  ans_6,  ans_7,  ans_8,  ans_9,  ans_10,
       ans_11, ans_12, ans_13, ans_14, ans_15, ans_16, ans_17, ans_18, ans_19, ans_20,
       ans_21, ans_22, ans_23, ans_24, ans_25, ans_26, ans_27, ans_28, ans_29, ans_30,
       ans_31, ans_32, ans_33, ans_34, ans_35, ans_36, ans_37, ans_38, ans_39, ans_40,
       ans_41, ans_42, ans_43, ans_44, ans_45, ans_46, ans_47, ans_48, ans_49, ans_50,
       ans_51, ans_52, ans_53, ans_54
FROM cleaned.jocojimslsirdata;

CREATE TEMP TABLE tmp_cases AS
SELECT hash_case_no, MIN(mni_no) AS mni_no, COUNT(DISTINCT mni_no) AS n_mni
FROM cleaned.jocojimscasedata
WHERE hash_case_no IS NOT NULL
GROUP BY hash_case_no;

DROP TABLE IF EXISTS semantic.lsir;
CREATE TABLE semantic.lsir AS
SELECT x.entity_id,
       (c.hash_case_no IS NOT NULL) AS case_found,
       c.mni_no,
       COALESCE(l.assessment_date, l.created_date) AS event_date,
       l.*
FROM tmp_lsir l
LEFT JOIN tmp_cases c USING (hash_case_no)
LEFT JOIN semantic.person_xwalk x
       ON x.source = 'jocoJIMSNameIndex.MNI_NO_0'
      AND x.source_id = lpad(c.mni_no::text, 9, '0');

CREATE INDEX ON semantic.lsir (entity_id, event_date);
ANALYZE semantic.lsir;
ALTER TABLE semantic.lsir OWNER TO jail_mh2;
