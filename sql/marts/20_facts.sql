
DROP TABLE IF EXISTS marts.fact_eqs_monthly;

CREATE TABLE marts.fact_eqs_monthly AS

WITH monthly_submissions AS (
    SELECT
        reading_id,
        site_id,
        period_start AS reporting_month,
        metric_code,
        canonical_value AS metric_value,
        canonical_uom,
        source_system,
        submitted_at,
        is_restatement,
        FALSE AS is_estimated

    FROM staging.stg_readings

    WHERE period_type = 'M'
),

quarterly_submissions AS (
    SELECT
        r.reading_id,
        r.site_id,

        (
            r.period_start
            - generated_month.month_offset * interval '1 month'
        )::DATE AS reporting_month,

        r.metric_code,

        r.canonical_value / 3.0 AS metric_value,

        r.canonical_uom,
        r.source_system,
        r.submitted_at,
        r.is_restatement,
        TRUE AS is_estimated

    FROM staging.stg_readings AS r

    CROSS JOIN range(0, 3)
        AS generated_month(month_offset)

    WHERE r.period_type = 'Q'
),

all_monthly_values AS (
    SELECT * FROM monthly_submissions

    UNION ALL

    SELECT * FROM quarterly_submissions
)

SELECT
    s.site_key,
    d.date_key,
    m.metric_key,

    v.reading_id,
    v.metric_value AS value,
    v.canonical_uom AS uom,
    v.source_system,
    v.submitted_at,
    v.is_restatement,
    v.is_estimated

FROM all_monthly_values AS v

INNER JOIN marts.dim_site AS s
    ON s.site_id = v.site_id
   AND v.reporting_month >= date_trunc(
        'month',
        s.valid_from
   )
   AND v.reporting_month <= date_trunc(
        'month',
        coalesce(
            s.valid_to,
            date '9999-12-31'
        )
   )

INNER JOIN marts.dim_date AS d
    ON d.month_start = v.reporting_month

INNER JOIN marts.dim_metric AS m
    ON m.metric_code = v.metric_code;




DROP TABLE IF EXISTS marts.fact_incident;

CREATE TABLE marts.fact_incident AS
SELECT
    i.incident_id,
    s.site_key,
    d.date_key,

    i.incident_date,
    i.incident_type,
    i.severity,
    i.is_recordable,
    i.lost_days,
    i.reported_by

FROM staging.stg_incidents AS i

INNER JOIN marts.dim_site AS s
    ON s.site_id = i.site_id
   AND i.incident_date >= s.valid_from
   AND i.incident_date <= coalesce(
        s.valid_to,
        date '9999-12-31'
   )

INNER JOIN marts.dim_date AS d
    ON d.month_start = date_trunc(
        'month',
        i.incident_date
    );