DROP TABLE IF EXISTS marts.kpi_yoy;

CREATE TABLE marts.kpi_yoy AS

WITH group_monthly AS (
    SELECT
        period,
        strptime(period || '-01', '%Y-%m-%d')::DATE
            AS month_start,

        'GROUP' AS grouping_level,
        'GROUP' AS grouping_value,

        CASE
            WHEN count(total_tco2e) = count(*)
            THEN sum(total_tco2e)
            ELSE NULL
        END AS total_tco2e

    FROM marts.kpi_emissions

    GROUP BY
        period
),

business_unit_monthly AS (
    SELECT
        period,
        strptime(period || '-01', '%Y-%m-%d')::DATE
            AS month_start,

        'BUSINESS_UNIT' AS grouping_level,
        business_unit AS grouping_value,

        CASE
            WHEN count(total_tco2e) = count(*)
            THEN sum(total_tco2e)
            ELSE NULL
        END AS total_tco2e

    FROM marts.kpi_emissions

    GROUP BY
        period,
        business_unit
),

all_groupings AS (
    SELECT
        period,
        month_start,
        grouping_level,
        grouping_value,
        total_tco2e

    FROM group_monthly

    UNION ALL

    SELECT
        period,
        month_start,
        grouping_level,
        grouping_value,
        total_tco2e

    FROM business_unit_monthly
),

with_last_year AS (
    SELECT
        current_period.period,
        current_period.month_start,
        current_period.grouping_level,
        current_period.grouping_value,
        current_period.total_tco2e,

        previous_period.total_tco2e
            AS total_tco2e_ly

    FROM all_groupings AS current_period

    LEFT JOIN all_groupings AS previous_period
        ON previous_period.grouping_level
            = current_period.grouping_level

       AND previous_period.grouping_value
            = current_period.grouping_value

       AND previous_period.month_start
            = current_period.month_start
              - interval '1 year'
)

SELECT
    period,
    grouping_level,
    grouping_value,
    total_tco2e,
    total_tco2e_ly,

    CASE
        WHEN total_tco2e IS NULL
          OR total_tco2e_ly IS NULL
        THEN NULL

        ELSE
            total_tco2e
            - total_tco2e_ly
    END AS yoy_abs,

    CASE
        WHEN total_tco2e IS NULL
          OR total_tco2e_ly IS NULL
          OR total_tco2e_ly = 0
        THEN NULL

        ELSE
            (
                total_tco2e
                - total_tco2e_ly
            )
            / total_tco2e_ly
    END AS yoy_pct

FROM with_last_year

ORDER BY
    period,
    grouping_level,
    grouping_value;