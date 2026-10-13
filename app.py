import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="CA Financial Dashboard", page_icon="📊", layout="wide")

REQUIRED = [
    "Month", "BusinessUnit", "Revenue", "COGS", "OperatingExpenses",
    "Receivables", "Payables", "CashBalance"
]
NUMERIC = ["Revenue", "COGS", "OperatingExpenses", "Receivables", "Payables", "CashBalance"]

def sample_data():
    # Fallback demo data is used only if the Excel file is not uploaded.
    months = pd.date_range("2025-04-01", periods=12, freq="MS")
    units = {
        "Trading": (850000, .72, 105000, .25, .18, .35),
        "Services": (520000, .38, 175000, .18, .12, .22),
        "Manufacturing": (1100000, .64, 210000, .22, .24, .30),
    }
    rows = []
    for i, month in enumerate(months):
        season = 1 + .07 * np.sin(i * 2 * np.pi / 12)
        for unit, (base, cogs_pct, opex_base, ar_pct, ap_pct, cash_pct) in units.items():
            revenue = base * season * (1 + .012*i)
            if month == pd.Timestamp("2025-09-01") and unit == "Trading":
                revenue *= .70
            cogs = revenue * cogs_pct
            opex = opex_base * (2.25 if month == pd.Timestamp("2025-12-01") and unit == "Services" else 1)
            rows.append({
                "Month": month, "BusinessUnit": unit, "Revenue": round(revenue, 2),
                "COGS": round(cogs, 2), "OperatingExpenses": round(opex, 2),
                "Receivables": round(revenue*ar_pct, 2), "Payables": round(cogs*ap_pct, 2),
                "CashBalance": round(max(50000, revenue*cash_pct), 2)
            })
    return pd.DataFrame(rows)

def validate_and_prepare(raw):
    df = raw.copy()
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError("Missing required column(s): " + ", ".join(missing))
    df = df[REQUIRED].copy()
    df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["BusinessUnit"] = df["BusinessUnit"].astype("string").str.strip()
    issues = []
    if df["Month"].isna().any():
        issues.append(f"{int(df['Month'].isna().sum())} row(s) have an invalid or blank Month.")
    if df["BusinessUnit"].isna().any() or (df["BusinessUnit"] == "").any():
        issues.append("Some rows have a blank BusinessUnit.")
    for col in NUMERIC:
        if df[col].isna().any():
            issues.append(f"{int(df[col].isna().sum())} row(s) have missing/non-numeric values in {col}.")
        if (df[col] < 0).any():
            issues.append(f"{col} contains negative values; confirm whether these are valid adjustments.")
    if df.duplicated(["Month", "BusinessUnit"]).any():
        issues.append("Duplicate Month + BusinessUnit combinations detected. Confirm whether rows should be aggregated.")
    if (df["COGS"] > df["Revenue"]).any():
        issues.append("COGS exceeds Revenue in one or more rows; review the source or confirm the business context.")
    if issues:
        return df, issues
    df["GrossProfit"] = df["Revenue"] - df["COGS"]
    df["OperatingProfit"] = df["GrossProfit"] - df["OperatingExpenses"]
    df["GrossMarginPct"] = np.where(df["Revenue"] != 0, df["GrossProfit"] / df["Revenue"] * 100, np.nan)
    df["OperatingMarginPct"] = np.where(df["Revenue"] != 0, df["OperatingProfit"] / df["Revenue"] * 100, np.nan)
    return df, []

def fmt_inr(value):
    return f"₹{value:,.0f}"

st.title("📊 CA Financial Performance Dashboard")
st.caption("Workshop prototype • Synthetic data • Review all figures before professional use")

with st.sidebar:
    st.header("Data")
    upload = st.file_uploader("Upload an Excel workbook (.xlsx)", type=["xlsx"])
    st.caption("Expected sheet: first worksheet, with the required columns listed below.")
    st.divider()
    st.header("Required columns")
    st.code(", ".join(REQUIRED), language="text")

if upload is not None:
    try:
        raw_df = pd.read_excel(upload)
        data_source = f"Uploaded file: {upload.name}"
    except Exception as exc:
        st.error(f"Could not read this workbook: {exc}")
        st.stop()
else:
    raw_df = sample_data()
    data_source = "Built-in synthetic demo data"

st.caption(data_source)
df, validation_issues = validate_and_prepare(raw_df)

if validation_issues:
    st.error("Data validation needs attention before calculations are shown.")
    for issue in validation_issues:
        st.warning(issue)
    st.info("Correct the source workbook and upload it again. The app intentionally stops short of presenting potentially misleading KPIs.")
    st.subheader("Preview of uploaded data")
    st.dataframe(raw_df.head(20), use_container_width=True)
    st.stop()

with st.sidebar:
    all_units = sorted(df["BusinessUnit"].dropna().unique().tolist())
    selected_units = st.multiselect("Business unit", all_units, default=all_units)
    min_month = df["Month"].min().date()
    max_month = df["Month"].max().date()
    date_range = st.date_input("Reporting period", value=(min_month, max_month), min_value=min_month, max_value=max_month)

if not selected_units:
    st.warning("Select at least one business unit.")
    st.stop()
if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Select both a start date and an end date.")
    st.stop()

start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
f = df[
    df["BusinessUnit"].isin(selected_units)
    & (df["Month"] >= start_date)
    & (df["Month"] <= end_date)
].copy()

if f.empty:
    st.warning("No rows match the selected filters.")
    st.stop()

revenue = f["Revenue"].sum()
cogs = f["COGS"].sum()
gross_profit = revenue - cogs
opex = f["OperatingExpenses"].sum()
operating_profit = gross_profit - opex
gross_margin = gross_profit / revenue * 100 if revenue else 0
operating_margin = operating_profit / revenue * 100 if revenue else 0
receivables = f.groupby(["Month", "BusinessUnit"])["Receivables"].last().groupby("BusinessUnit").sum().sum()
payables = f.groupby(["Month", "BusinessUnit"])["Payables"].last().groupby("BusinessUnit").sum().sum()
latest_per_unit = f.sort_values("Month").groupby("BusinessUnit", as_index=False).tail(1)
cash = latest_per_unit["CashBalance"].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue", fmt_inr(revenue))
c2.metric("Gross profit", fmt_inr(gross_profit), f"{gross_margin:.1f}% gross margin")
c3.metric("Operating profit", fmt_inr(operating_profit), f"{operating_margin:.1f}% operating margin")
c4.metric("Cash balance*", fmt_inr(cash))

st.caption("*Cash balance KPI uses the latest available row per selected business unit in the filtered period. Trend charts show monthly balances. Define period-end balance logic explicitly before adapting this prototype for client reporting.")

monthly = f.groupby("Month", as_index=False).agg(
    Revenue=("Revenue", "sum"),
    COGS=("COGS", "sum"),
    OperatingExpenses=("OperatingExpenses", "sum"),
    GrossProfit=("GrossProfit", "sum"),
    OperatingProfit=("OperatingProfit", "sum"),
    Receivables=("Receivables", "sum"),
    Payables=("Payables", "sum"),
    CashBalance=("CashBalance", "sum"),
)
monthly["GrossMarginPct"] = np.where(monthly["Revenue"] != 0, monthly["GrossProfit"] / monthly["Revenue"] * 100, np.nan)
monthly["OperatingMarginPct"] = np.where(monthly["Revenue"] != 0, monthly["OperatingProfit"] / monthly["Revenue"] * 100, np.nan)
monthly["RevenueChangePct"] = monthly["Revenue"].pct_change() * 100

tab1, tab2, tab3 = st.tabs(["Performance", "Exceptions", "Data & Export"])
with tab1:
    st.subheader("Monthly revenue and profit")
    chart_df = monthly.set_index("Month")[["Revenue", "GrossProfit", "OperatingProfit"]]
    st.line_chart(chart_df, use_container_width=True)
    left, right = st.columns(2)
    with left:
        st.subheader("Monthly cost structure")
        st.bar_chart(monthly.set_index("Month")[["COGS", "OperatingExpenses"]], use_container_width=True)
    with right:
        st.subheader("Working capital indicators")
        st.line_chart(monthly.set_index("Month")[["Receivables", "Payables", "CashBalance"]], use_container_width=True)
    st.subheader("Business unit summary")
    unit_summary = f.groupby("BusinessUnit", as_index=False).agg(
        Revenue=("Revenue", "sum"), COGS=("COGS", "sum"),
        OperatingExpenses=("OperatingExpenses", "sum"),
        Receivables=("Receivables", "last"), Payables=("Payables", "last"),
        CashBalance=("CashBalance", "last")
    )
    unit_summary["GrossProfit"] = unit_summary["Revenue"] - unit_summary["COGS"]
    unit_summary["OperatingProfit"] = unit_summary["GrossProfit"] - unit_summary["OperatingExpenses"]
    st.dataframe(unit_summary.style.format({
        c: "₹{:,.0f}" for c in ["Revenue","COGS","OperatingExpenses","Receivables","Payables","CashBalance","GrossProfit","OperatingProfit"]
    }), use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Rule-based items for professional review")
    threshold = st.slider("Flag month-on-month revenue decline greater than (%)", min_value=5, max_value=50, value=15, step=5)
    exceptions = []
    unit_month = f.groupby(["BusinessUnit", "Month"], as_index=False).agg(
        Revenue=("Revenue", "sum"), COGS=("COGS", "sum"),
        OperatingExpenses=("OperatingExpenses", "sum"),
        Receivables=("Receivables", "last"), Payables=("Payables", "last"),
        CashBalance=("CashBalance", "last")
    ).sort_values(["BusinessUnit", "Month"])
    unit_month["OperatingProfit"] = unit_month["Revenue"] - unit_month["COGS"] - unit_month["OperatingExpenses"]
    unit_month["RevenueChangePct"] = unit_month.groupby("BusinessUnit")["Revenue"].pct_change() * 100
    for _, row in unit_month.iterrows():
        period = row["Month"].strftime("%Y-%m")
        unit = row["BusinessUnit"]
        if pd.notna(row["RevenueChangePct"]) and row["RevenueChangePct"] <= -threshold:
            exceptions.append({"Month": period, "BusinessUnit": unit, "Severity": "Review", "Rule": f"Revenue declined {abs(row['RevenueChangePct']):.1f}% month-on-month", "Suggested action": "Compare sales volume, pricing, customer mix and cut-off."})
        if row["OperatingProfit"] < 0:
            exceptions.append({"Month": period, "BusinessUnit": unit, "Severity": "Review", "Rule": "Operating loss for the month", "Suggested action": "Review gross margin, one-off costs, classification and supporting evidence."})
        if row["Revenue"] > 0 and row["Receivables"] / row["Revenue"] > .30:
            exceptions.append({"Month": period, "BusinessUnit": unit, "Severity": "Review", "Rule": "Receivables exceed 30% of monthly revenue", "Suggested action": "Review ageing, subsequent receipts, disputes and credit terms."})
    if exceptions:
        st.dataframe(pd.DataFrame(exceptions), use_container_width=True, hide_index=True)
    else:
        st.success("No exceptions triggered by the selected simple rules. This does not mean the data is error-free.")
    st.caption("These are illustrative screening rules, not audit conclusions, fraud indicators or compliance opinions. Thresholds should be tailored to the business.")

with tab3:
    st.subheader("Validated data")
    st.dataframe(f, use_container_width=True, hide_index=True)
    export = monthly.copy()
    export["Month"] = export["Month"].dt.strftime("%Y-%m-%d")
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        f.to_excel(writer, index=False, sheet_name="FilteredData")
        export.to_excel(writer, index=False, sheet_name="MonthlySummary")
    st.download_button(
        "Download filtered data and monthly summary (Excel)",
        data=output.getvalue(),
        file_name="ca_financial_dashboard_output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.divider()
st.caption("Training prototype only. Confirm accounting definitions, period-end balance treatment, source completeness and all flagged items with the responsible professional.")
