DROP TABLE IF EXISTS marts.kpi_emissions;

CREATE TABLE marts.kpi_emissions AS

WITH active_site_months AS (
    SELECT
        d.date_key,
        d.month_start,
        d.period,

        s.site_key,
        s.site_id,
        s.site_name,
        s.business_unit,
        s.region

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

monthly_emissions AS (
    SELECT
        f.site_key,
        f.date_key,

        max(
            CASE
                WHEN m.metric_code = 'SCOPE1_GHG'
                THEN f.value
            END
        ) AS scope1_tco2e,

        max(
            CASE
                WHEN m.metric_code = 'SCOPE2_GHG'
                THEN f.value
            END
        ) AS scope2_tco2e

    FROM marts.fact_eqs_monthly AS f

    INNER JOIN marts.dim_metric AS m
        ON m.metric_key = f.metric_key

    WHERE m.metric_code IN (
        'SCOPE1_GHG',
        'SCOPE2_GHG'
    )

    GROUP BY
        f.site_key,
        f.date_key
)

SELECT
    sm.period,
    sm.site_id,
    sm.site_name,
    sm.business_unit,
    sm.region,

    e.scope1_tco2e,
    e.scope2_tco2e,

    CASE
        WHEN e.scope1_tco2e IS NULL
          OR e.scope2_tco2e IS NULL
        THEN NULL

        ELSE
            e.scope1_tco2e
            + e.scope2_tco2e
    END AS total_tco2e

FROM active_site_months AS sm

LEFT JOIN monthly_emissions AS e
    ON e.site_key = sm.site_key
   AND e.date_key = sm.date_key

ORDER BY
    sm.period,
    sm.site_id;