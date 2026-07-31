DROP TABLE IF EXISTS marts.kpi_trir;

CREATE TABLE marts.kpi_trir AS

WITH active_site_months AS (
    SELECT
        d.date_key,
        d.month_start,
        d.period,

        s.site_key,
        s.site_id,
        s.site_name

    FROM marts.dim_date AS d

    INNER JOIN marts.dim_site AS s
        ON d.month_start >= date_trunc(
            'month',
            s.valid_from
        )
       AND d.month_start <= date_trunc(
            'month',
            coalesce(
                s.valid_to,
                date '9999-12-31'
            )
        )
),

monthly_incidents AS (
    SELECT
        i.site_key,
        i.date_key,

        count(*) FILTER (
            WHERE i.is_recordable = TRUE
        ) AS recordable_incidents

    FROM marts.fact_incident AS i

    GROUP BY
        i.site_key,
        i.date_key
),

monthly_hours AS (
    SELECT
        f.site_key,
        f.date_key,
        f.value AS hours_worked

    FROM marts.fact_eqs_monthly AS f

    INNER JOIN marts.dim_metric AS m
        ON m.metric_key = f.metric_key

    WHERE m.metric_code = 'HOURS_WORKED'
),

monthly_base AS (
    SELECT
        sm.period,
        sm.month_start,
        sm.site_key,
        sm.site_id,
        sm.site_name,

        coalesce(
            mi.recordable_incidents,
            0
        ) AS recordable_incidents,

        mh.hours_worked

    FROM active_site_months AS sm

    LEFT JOIN monthly_incidents AS mi
        ON mi.site_key = sm.site_key
       AND mi.date_key = sm.date_key

    LEFT JOIN monthly_hours AS mh
        ON mh.site_key = sm.site_key
       AND mh.date_key = sm.date_key
),

rolling_values AS (
    SELECT
        period,
        month_start,
        site_key,
        site_id,
        site_name,

        sum(recordable_incidents) OVER (
            PARTITION BY site_key
            ORDER BY month_start
            ROWS BETWEEN 11 PRECEDING
                     AND CURRENT ROW
        ) AS recordable_incidents_r12,

        sum(hours_worked) OVER (
            PARTITION BY site_key
            ORDER BY month_start
            ROWS BETWEEN 11 PRECEDING
                     AND CURRENT ROW
        ) AS hours_worked_r12,

        count(*) OVER (
            PARTITION BY site_key
            ORDER BY month_start
            ROWS BETWEEN 11 PRECEDING
                     AND CURRENT ROW
        ) AS months_in_window,

        count(hours_worked) OVER (
            PARTITION BY site_key
            ORDER BY month_start
            ROWS BETWEEN 11 PRECEDING
                     AND CURRENT ROW
        ) AS months_with_hours

    FROM monthly_base
)

SELECT
    period,
    site_id,
    site_name,

    recordable_incidents_r12,
    hours_worked_r12,

    CASE
        WHEN months_in_window < 12
          OR months_with_hours < 12
          OR hours_worked_r12 IS NULL
          OR hours_worked_r12 = 0
        THEN NULL

        ELSE
            recordable_incidents_r12
            * 200000.0
            / hours_worked_r12
    END AS trir_r12,

    (
        months_in_window = 12
        AND months_with_hours = 12
    ) AS has_full_window

FROM rolling_values

ORDER BY
    period,
    site_id;