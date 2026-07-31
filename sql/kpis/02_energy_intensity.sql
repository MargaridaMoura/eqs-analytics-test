DROP TABLE IF EXISTS marts.kpi_energy_intensity;

CREATE TABLE marts.kpi_energy_intensity AS

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

monthly_values AS (
    SELECT
        f.site_key,
        f.date_key,

        max(
            CASE
                WHEN m.metric_code = 'ENERGY_CONS'
                THEN f.value
            END
        ) AS energy_mwh,

        max(
            CASE
                WHEN m.metric_code = 'HOURS_WORKED'
                THEN f.value
            END
        ) AS hours_worked,

        max(
            CASE
                WHEN m.metric_code = 'HOURS_WORKED'
                THEN f.is_estimated
            END
        ) AS hours_are_estimated

    FROM marts.fact_eqs_monthly AS f

    INNER JOIN marts.dim_metric AS m
        ON m.metric_key = f.metric_key

    WHERE m.metric_code IN (
        'ENERGY_CONS',
        'HOURS_WORKED'
    )

    GROUP BY
        f.site_key,
        f.date_key
)

SELECT
    sm.period,
    sm.site_id,
    sm.site_name,

    mv.energy_mwh,
    mv.hours_worked,

    CASE
        WHEN mv.energy_mwh IS NULL
          OR mv.hours_worked IS NULL
          OR mv.hours_worked = 0
        THEN NULL

        ELSE
            mv.energy_mwh
            * 1000.0
            / mv.hours_worked
    END AS mwh_per_1000_hours,

    coalesce(
        mv.hours_are_estimated,
        FALSE
    ) AS is_estimated

FROM active_site_months AS sm

LEFT JOIN monthly_values AS mv
    ON mv.site_key = sm.site_key
   AND mv.date_key = sm.date_key

ORDER BY
    sm.period,
    sm.site_id;