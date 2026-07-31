

-- Clean site master data

DROP TABLE IF EXISTS staging.stg_sites;

CREATE TABLE staging.stg_sites AS
SELECT
    try_cast(site_id AS INTEGER) AS site_id,

    trim(site_name) AS site_name,

    CASE
        WHEN upper(trim(country)) = 'GERMANY' THEN 'DE'
        WHEN upper(trim(country)) = 'USA' THEN 'US'
        ELSE upper(trim(country))
    END AS country,

    upper(trim(region)) AS region,
    trim(business_unit) AS business_unit,
    try_cast(headcount AS INTEGER) AS headcount,
    try_cast(valid_from AS DATE) AS valid_from,
    try_cast(
        nullif(trim(valid_to), '')
        AS DATE
    ) AS valid_to

FROM raw.sites;


-- Clean metric definitions

DROP TABLE IF EXISTS staging.stg_metrics;

CREATE TABLE staging.stg_metrics AS
SELECT
    trim(metric_code) AS metric_code,
    trim(metric_name) AS metric_name,
    trim(category) AS category,
    trim(canonical_uom) AS canonical_uom,

    CASE
        WHEN upper(trim(is_additive)) = 'Y' THEN TRUE
        ELSE FALSE
    END AS is_additive

FROM raw.metric_definitions;


-- Clean unit conversions


DROP TABLE IF EXISTS staging.stg_uom_conversions;

CREATE TABLE staging.stg_uom_conversions AS
SELECT
    trim(from_uom) AS from_uom,
    trim(to_uom) AS to_uom,
    try_cast(factor AS DOUBLE) AS conversion_factor

FROM raw.uom_conversions;


-- Clean, validate and rank readings

DROP TABLE IF EXISTS staging.stg_readings;

CREATE TABLE staging.stg_readings AS

WITH typed_readings AS (
    SELECT
        try_cast(r.reading_id AS BIGINT) AS reading_id,
        try_cast(r.site_id AS INTEGER) AS site_id,
        try_cast(r.period || '-01' AS DATE) AS period_start,
        trim(r.metric_code) AS metric_code,
        try_cast(r.value AS DOUBLE) AS raw_value,
        trim(r.uom) AS source_uom,
        upper(trim(r.period_type)) AS period_type,
        trim(r.source_system) AS source_system,
        try_cast(r.submitted_at AS TIMESTAMP) AS submitted_at

    FROM raw.readings AS r

    WHERE NOT EXISTS (
        SELECT 1
        FROM staging.dq_quarantine AS q
        WHERE q.reading_id = r.reading_id
    )
),

converted_readings AS (
    SELECT
        r.reading_id,
        r.site_id,
        r.period_start,
        r.metric_code,
        r.raw_value,
        r.source_uom,
        m.canonical_uom,

        r.raw_value * c.conversion_factor
            AS canonical_value,

        r.period_type,
        r.source_system,
        r.submitted_at,

        count(*) OVER (
            PARTITION BY
                r.site_id,
                r.period_start,
                r.metric_code
        ) AS submission_count,

        row_number() OVER (
            PARTITION BY
                r.site_id,
                r.period_start,
                r.metric_code
            ORDER BY
                r.submitted_at DESC,
                r.reading_id DESC
        ) AS submission_rank

    FROM typed_readings AS r

    INNER JOIN staging.stg_metrics AS m
        ON m.metric_code = r.metric_code

    INNER JOIN staging.stg_uom_conversions AS c
        ON c.from_uom = r.source_uom
       AND c.to_uom = m.canonical_uom
)

SELECT
    reading_id,
    site_id,
    period_start,
    metric_code,
    raw_value,
    source_uom,
    canonical_value,
    canonical_uom,
    period_type,
    source_system,
    submitted_at,
    submission_count,
    submission_count > 1 AS is_restatement

FROM converted_readings

WHERE submission_rank = 1;


-- Clean and deduplicate incidents

DROP TABLE IF EXISTS staging.stg_incidents;

CREATE TABLE staging.stg_incidents AS

WITH typed_incidents AS (
    SELECT
        try_cast(incident_id AS BIGINT) AS incident_id,
        try_cast(site_id AS INTEGER) AS site_id,
        try_cast(incident_date AS DATE) AS incident_date,
        trim(incident_type) AS incident_type,
        trim(severity) AS severity,

        CASE
            WHEN upper(trim(is_recordable)) = 'Y' THEN TRUE
            ELSE FALSE
        END AS is_recordable,

        try_cast(lost_days AS INTEGER) AS lost_days,
        trim(reported_by) AS reported_by

    FROM raw.incidents
),

ranked_incidents AS (
    SELECT
        *,

        row_number() OVER (
            PARTITION BY incident_id
            ORDER BY
                lost_days DESC,
                CASE
                    WHEN reported_by = 'EHS Officer' THEN 1
                    ELSE 0
                END DESC
        ) AS incident_rank

    FROM typed_incidents
)

SELECT
    incident_id,
    site_id,
    incident_date,
    incident_type,
    severity,
    is_recordable,
    lost_days,
    reported_by

FROM ranked_incidents

WHERE incident_rank = 1;