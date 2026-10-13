# Quick Manual Test Cases

1. Valid file: upload `sample_financial_data.xlsx`; dashboard should load.
2. Missing column: rename `Revenue` to `Sales`; app should stop and name the missing column.
3. Non-numeric value: enter `unknown` in one Revenue cell; app should flag invalid numeric values.
4. Duplicate key: duplicate a Month + BusinessUnit row; app should stop and request review.
5. Filter: select only Trading; KPI totals should change.
6. Date range: select a shorter period; charts and totals should update.
7. Revenue decline: the synthetic sample intentionally contains a Trading revenue dip in September 2025; filter to Trading and include September to see if the chosen threshold flags it.
8. Operating loss: the synthetic sample includes elevated Services operating expenses in December 2025; filter to Services and include December to review the operating-loss flag.
9. Export: download the Excel output and confirm it contains FilteredData and MonthlySummary sheets.
10. Reconciliation: independently calculate Gross Profit and Operating Profit for one row in Excel and compare with app results.
