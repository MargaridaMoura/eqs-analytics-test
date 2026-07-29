# sql/marts

Your dimensional model goes here. Files run in **filename order**, so name them for
dependency order:

    00_staging.sql      clean / type / deduplicate into the `staging` schema
    10_dimensions.sql   marts.dim_site, marts.dim_metric, marts.dim_date
    20_facts.sql        marts.fact_eqs_monthly, marts.fact_incident

`src/eqs_analytics/marts.py` checks the required objects exist and fails loudly if not.
