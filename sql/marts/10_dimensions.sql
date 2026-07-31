

DROP TABLE IF EXISTS marts.dim_site;

CREATE TABLE marts.dim_site AS
SELECT
    row_number() OVER (
        ORDER BY site_id, valid_from
    )::INTEGER AS site_key,

    site_id,
    site_name,
    country,
    region,
    business_unit,
    headcount,
    valid_from,
    valid_to,

    valid_to IS NULL AS is_current

FROM staging.stg_sites;




DROP TABLE IF EXISTS marts.dim_metric;

CREATE TABLE marts.dim_metric AS
SELECT
    row_number() OVER (
        ORDER BY metric_code
    )::INTEGER AS metric_key,

    metric_code,
    metric_name,
    category,
    canonical_uom,
    is_additive

FROM staging.stg_metrics;



DROP TABLE IF EXISTS marts.dim_date;

CREATE TABLE marts.dim_date AS

WITH months AS (
    SELECT
        date '2024-01-01'
        + month_number * interval '1 month'
            AS month_start

    FROM range(0, 24) AS generated_months(month_number)
)

SELECT
    try_cast(
        strftime(month_start, '%Y%m')
        AS INTEGER
    ) AS date_key,

    month_start::DATE AS month_start,

    strftime(month_start, '%Y-%m') AS period,

    year(month_start)::INTEGER AS year,

    quarter(month_start)::INTEGER AS quarter,

    month(month_start)::INTEGER AS month_number,

    strftime(month_start, '%B') AS month_name

FROM months

ORDER BY month_start;