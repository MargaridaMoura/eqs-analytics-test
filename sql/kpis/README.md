# sql/kpis

Your KPI layer goes here, one file per KPI. Each must create a table or view in the `marts`
schema named exactly as listed in `KPI_CONTRACT` (see `src/eqs_analytics/kpis.py`), with
exactly those columns in that order. They are exported to `reports/<name>.csv` for you.

    01_emissions.sql          -> marts.kpi_emissions
    02_energy_intensity.sql   -> marts.kpi_energy_intensity
    03_trir.sql               -> marts.kpi_trir
    04_yoy.sql                -> marts.kpi_yoy
