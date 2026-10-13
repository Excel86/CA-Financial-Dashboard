# Prompt Library — Vibe-Coded Financial Dashboard

Use these prompts in ChatGPT or Claude. For code changes, provide the current `streamlit_app.py` as an attachment or paste the relevant section. Never accept code without testing it.

## Prompt 1 — Plan before coding
You are a senior Python developer and a CA-firm workflow consultant. Help me build a local Streamlit dashboard using an Excel workbook. The required columns are Month, BusinessUnit, Revenue, COGS, OperatingExpenses, Receivables, Payables, CashBalance. The dashboard should show revenue, gross profit, operating profit, margins, monthly trends, business-unit filters and rule-based exceptions. First provide a concise implementation plan, assumptions, data validations and test cases. Do not write code until the plan is complete.

## Prompt 2 — Generate a first prototype
Build a complete, beginner-friendly Streamlit app for a CA workshop using Python, Pandas, NumPy and openpyxl. The app must read an uploaded `.xlsx` workbook, validate required columns and numeric/date fields, calculate GrossProfit = Revenue - COGS and OperatingProfit = GrossProfit - OperatingExpenses, display KPI cards and monthly charts, support date and business-unit filters, and allow Excel export. Use clear error messages. Do not invent missing values. Include comments and a requirements.txt. This is a training prototype using synthetic data, not a production accounting system.

## Prompt 3 — Debug without rewriting everything
Review the attached Python file and the exact error below. Identify the likely root cause, explain it in plain English, and propose the smallest safe change. Preserve existing working features. Return the corrected code block and a short test plan. Error: [paste exact traceback]. Do not claim the fix works until it has been run and tested.

## Prompt 4 — Add a KPI safely
Modify the current dashboard to add [KPI NAME]. Before coding, define its accounting formula, required columns, treatment of zero or missing denominators, period logic and at least three test cases. Then make the smallest code change and show how to verify the result against a hand calculation. If the source data is insufficient, explain what is missing instead of inventing it.

## Prompt 5 — Improve the exception report
Add configurable screening rules for [e.g., month-on-month revenue decline]. Show the formula, threshold, rows flagged, and a suggested investigation step. Clearly label the results as review flags, not proof of fraud, error or non-compliance. Include a test where no flag is triggered and a test where a flag should trigger.

## Prompt 6 — Create a test dataset
Generate a synthetic Excel dataset with at least 12 months and 3 business units. Include realistic variation and deliberately seeded examples of a revenue decline, an operating loss, a missing value and a duplicate key for validation training. Label it as synthetic. Provide expected results for each seeded test. Do not use any real client data.

## Prompt 7 — Review before professional use
Act as a skeptical reviewer, not a cheerleader. Inspect the dashboard logic for aggregation errors, stock-versus-flow mistakes, date filtering problems, division-by-zero errors, duplicate records, missing values, misleading charts, confidentiality risks and unsupported conclusions. Classify each issue as Critical, High, Medium or Low. Suggest a test for each material issue. Do not state that the app is audit-ready or production-ready without evidence.

## Prompt 8 — Explain to CA participants
Explain this section of Python code to a Chartered Accountant who understands Excel formulas but is new to Python. Map each calculation to an Excel equivalent where possible. Use a small numeric example, identify assumptions, and explain how the result should be verified.
