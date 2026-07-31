# Decisions & Reconciliation Note

*Replace this template with your own content. One page maximum. Write it for the Group
Sustainability Reporting lead — assume they read financial reports, not SQL.*

---

## 1. What I would sign off on

*Which figures are you confident enough to put in front of an auditor, and which are not?
Be specific about the metric and the period.*

| Figure | Confidence | Why |
|---|---|---|
| | | |


! Scope 1 & Scope 2 emissions for valid sites and reporting periods | High | Readings passed the data quality checks, units were standardised, duplicate submissions were resolved by keeping the latest version and only data within the Group reporting boundary was included.|

|Energy intensity where monthly energy and hours worked are available |	Medium | The calculation is reliable where complete monthly data exists. Sites reporting quarterly hours required an even monthly allocation, so these values should be treated as estimates.|

|TRIR for rolling 12-month periods with a complete reporting window | Medium	| The calculation is reliable once twelve months of hours worked are available. Earlier periods or months with missing hours should not be used for reporting.|

| Months with missing submissions or unknown sites | Low | These figures were intentionally left as missing rather than estimated to avoid understating or overstating performance.|

---

## 2. Data quality issues found, ranked by materiality

*Ranked by impact on the reported numbers, not by how annoying they were to fix. State the
size of the effect where you can.*

| # | Issue | Effect on reported figures | How I handled it |
|---|---|---|---|
| 1 | Readings outside the site consolidation period (54 records) | Would incorrectly include data from sites before acquisition or after disposal, affecting Group totals. | Excluded from reporting by quarantining the records.|
| 2 | Multiple submissions for the same site, month and metric (19 records) | Risk of double counting or using outdated values.| Kept only the latest submission based on the submission timestamp. |
| 3 | Missing monthly submissions | Produces incomplete KPIs and affects trend analysis. | Left values as missing rather than replacing them with zero.|
| 4 | Unknown sites (4 records) | Cannot be assigned to a reporting entity or business unit. | Quarantined until the site master data is corrected.|
| 5 | Invalid values (3 non-numeric values and 1 negative value) | Prevents reliable calculations. | Quarantined before loading into the reporting model.|
---

## 3. Modelling decisions and trade-offs

*Grain of the fact table. SCD approach for sites. Anything you handled in SQL that could
equally have gone into DAX, and why you chose where you did. Which DQ rules block the load
versus only warn, and why.*

---

The monthly reporting fact table was built at site × month × metric level because this is the lowest level required by all requested KPIs.

The site dimension is designed to preserve historical information if site attributes change in the future. This ensures that historical reports continue to reflect the organisational structure that was valid at the time of reporting.

Business calculations such as emissions, energy intensity, TRIR and year-over-year comparisons were implemented in SQL rather than DAX. This keeps the reporting layer simple and ensures that all reporting tools use the same validated calculations.

Data quality rules that indicate invalid or unreliable data (for example unknown sites, invalid values or readings outside the reporting boundary) quarantine the affected records. Rules that identify situations requiring review, such as multiple submissions, generate warnings but do not stop the reporting process because a valid latest submission can still be selected.

## 4. What I would ask site controllers to fix at source

*Problems that should not be solved downstream at all.*

Submit data only for sites that are within the current reporting boundary.
Report hours worked monthly instead of quarterly where possible.
Use valid site identifiers and approved reporting units.
Investigate and correct invalid or negative values before submission.
Provide a reason and version history whenever a previously submitted value is corrected.

---

## 5. What I'd do next, and what I left out

*Given the time box — what's missing, and what would you do first with another day?*

With more time, I would improve the data validation process, add automatic alerts for missing data and create a simple approval workflow for submitted data.

Due to the time available, I focused on delivering the requested data quality checks, data model and KPIs. Additional reporting features and process improvements were left for future work.