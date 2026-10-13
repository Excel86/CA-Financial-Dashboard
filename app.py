import streamlit as st
import pandas as pd
import numpy as np
import asyncio
import base64
import json
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

st.set_page_config(page_title="CA Financial Dashboard", page_icon="📊", layout="wide")

REQUIRED = [
    "Month", "BusinessUnit", "Revenue", "COGS", "OperatingExpenses",
    "Receivables", "Payables", "CashBalance"
]
NUMERIC = ["Revenue", "COGS", "OperatingExpenses", "Receivables", "Payables", "CashBalance"]

def sample_data():
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

def make_pdf_report(filtered, monthly, unit_summary, revenue, gross_profit, operating_profit,
                    gross_margin, operating_margin, cash, report_title="CA Financial Performance Report"):
    """Build a PDF in memory; no temporary report file is written to disk."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4), rightMargin=12*mm, leftMargin=12*mm,
        topMargin=12*mm, bottomMargin=12*mm, title=report_title
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallNote", parent=styles["BodyText"], fontSize=8, leading=10))
    story = [
        Paragraph(report_title, styles["Title"]),
        Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')} (local app time)", styles["SmallNote"]),
        Paragraph(
            f"Period: {filtered['Month'].min():%d %b %Y} to {filtered['Month'].max():%d %b %Y} | "
            f"Business units: {', '.join(sorted(filtered['BusinessUnit'].astype(str).unique()))}",
            styles["BodyText"]
        ),
        Spacer(1, 8),
        Paragraph("Key performance indicators", styles["Heading2"]),
    ]
    kpi_data = [
        ["Revenue", "Gross Profit", "Gross Margin", "Operating Profit", "Operating Margin", "Latest Cash Balance*"],
        [fmt_inr(revenue), fmt_inr(gross_profit), f"{gross_margin:.1f}%",
         fmt_inr(operating_profit), f"{operating_margin:.1f}%", fmt_inr(cash)]
    ]
    kpi_table = Table(kpi_data, repeatRows=1)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#17365D")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), .4, colors.grey),
        ("BACKGROUND", (0,1), (-1,1), colors.HexColor("#EAF0F7")),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story += [kpi_table, Spacer(1, 5), Paragraph(
        "*Cash balance is the sum of the latest available row per selected business unit in the filtered period.",
        styles["SmallNote"]), Spacer(1, 10), Paragraph("Monthly summary", styles["Heading2"])]

    month_cols = ["Month", "Revenue", "COGS", "Operating Expenses", "Gross Profit", "Operating Profit", "Receivables", "Payables", "Cash Balance"]
    month_rows = [month_cols]
    for _, r in monthly.iterrows():
        month_rows.append([
            pd.Timestamp(r["Month"]).strftime("%Y-%m"),
            *[fmt_inr(r[c]) for c in ["Revenue","COGS","OperatingExpenses","GrossProfit","OperatingProfit","Receivables","Payables","CashBalance"]]
        ])
    mt = Table(month_rows, repeatRows=1)
    mt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#17365D")), ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,-1),7),
        ("GRID",(0,0),(-1,-1),.35,colors.grey), ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ALIGN",(1,1),(-1,-1),"RIGHT"), ("TOPPADDING",(0,0),(-1,-1),4), ("BOTTOMPADDING",(0,0),(-1,-1),4)
    ]))
    story += [mt, Spacer(1, 10), Paragraph("Business unit summary", styles["Heading2"])]
    unit_cols = ["Business Unit", "Revenue", "COGS", "Operating Expenses", "Gross Profit", "Operating Profit", "Receivables*", "Payables*", "Cash Balance*"]
    unit_rows = [unit_cols]
    for _, r in unit_summary.iterrows():
        unit_rows.append([str(r["BusinessUnit"])] + [fmt_inr(r[c]) for c in [
            "Revenue","COGS","OperatingExpenses","GrossProfit","OperatingProfit","Receivables","Payables","CashBalance"
        ]])
    ut = Table(unit_rows, repeatRows=1)
    ut.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#17365D")), ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,-1),7),
        ("GRID",(0,0),(-1,-1),.35,colors.grey), ("ALIGN",(1,1),(-1,-1),"RIGHT"),
        ("TOPPADDING",(0,0),(-1,-1),4), ("BOTTOMPADDING",(0,0),(-1,-1),4)
    ]))
    story += [ut, Spacer(1, 5), Paragraph(
        "*Receivables, payables and cash are balances; interpret them using the firm's agreed period-end reporting policy. "
        "This report is an analytical aid and not an audit opinion or compliance conclusion.",
        styles["SmallNote"]
    )]
    doc.build(story)
    return buf.getvalue()

async def _mcp_send_email(server_url, auth_token, tool_name, to_email, subject, message, pdf_bytes, filename):
    """Call an MCP Streamable HTTP server that exposes the documented send-email tool contract."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    async with streamablehttp_client(server_url, headers=headers) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tool_list = await session.list_tools()
            available = {t.name: t for t in tool_list.tools}
            if tool_name not in available:
                names = ", ".join(sorted(available.keys())) or "(no tools advertised)"
                raise RuntimeError(
                    f"MCP tool '{tool_name}' was not found. Tools advertised by the server: {names}. "
                    "Set MCP_SEND_EMAIL_TOOL to the correct tool name in Streamlit secrets."
                )
            tool = available[tool_name]
            required_contract = {"to", "subject", "body", "attachments"}
            advertised = set((tool.inputSchema or {}).get("properties", {}).keys())
            if not required_contract.issubset(advertised):
                raise RuntimeError(
                    f"The MCP tool '{tool_name}' does not expose the expected attachment-capable contract. "
                    f"Advertised argument names: {', '.join(sorted(advertised)) or '(not declared)'}. "
                    "Use an MCP email server/tool that accepts to, subject, body and attachments, or adapt the argument mapping in app.py."
                )
            arguments = {
                "to": to_email,
                "subject": subject,
                "body": message,
                "attachments": [{
                    "filename": filename,
                    "mime_type": "application/pdf",
                    "content_base64": base64.b64encode(pdf_bytes).decode("ascii")
                }]
            }
            result = await session.call_tool(tool_name, arguments=arguments)
            if getattr(result, "isError", False):
                messages = []
                for item in (getattr(result, "content", None) or []):
                    if getattr(item, "text", None):
                        messages.append(item.text)
                raise RuntimeError("MCP email tool returned an error: " + ("; ".join(messages) or "unspecified tool error"))
            messages = []
            for item in (getattr(result, "content", None) or []):
                if getattr(item, "text", None):
                    messages.append(item.text)
            return "; ".join(messages) if messages else "MCP server returned success without a text result."

def send_email_via_mcp(server_url, auth_token, tool_name, to_email, subject, message, pdf_bytes, filename):
    return asyncio.run(_mcp_send_email(
        server_url, auth_token, tool_name, to_email, subject, message, pdf_bytes, filename
    ))

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

unit_summary = f.groupby("BusinessUnit", as_index=False).agg(
    Revenue=("Revenue", "sum"), COGS=("COGS", "sum"),
    OperatingExpenses=("OperatingExpenses", "sum"),
    Receivables=("Receivables", "last"), Payables=("Payables", "last"),
    CashBalance=("CashBalance", "last")
)
unit_summary["GrossProfit"] = unit_summary["Revenue"] - unit_summary["COGS"]
unit_summary["OperatingProfit"] = unit_summary["GrossProfit"] - unit_summary["OperatingExpenses"]

tab1, tab2, tab3, tab4 = st.tabs(["Performance", "Exceptions", "Data & Export", "Mail Report"])
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

with tab4:
    st.subheader("Email the current financial report as a PDF")
    st.write("The PDF will use the currently selected business units and reporting period.")
    with st.form("mail_report_form"):
        recipient = st.text_input("Recipient email address", placeholder="recipient@example.com")
        email_subject = st.text_input(
            "Email subject",
            value=f"Financial Performance Report | {start_date:%d %b %Y} – {end_date:%d %b %Y}"
        )
        email_message = st.text_area(
            "Email message",
            value="Dear Recipient,\n\nPlease find attached the financial performance report for the selected reporting period.\n\nRegards"
        )
        confirm_send = st.checkbox("I confirm that the recipient is authorized to receive this report.")
        send_clicked = st.form_submit_button("Send PDF report via Gmail MCP", type="primary")

    with st.expander("MCP connection status and setup"):
        secrets_ok = bool(st.secrets.get("MCP_SERVER_URL", "")) and bool(st.secrets.get("MCP_SEND_EMAIL_TOOL", "send_email"))
        st.write("MCP server URL configured:", "Yes" if st.secrets.get("MCP_SERVER_URL", "") else "No")
        st.write("MCP bearer token configured:", "Yes" if st.secrets.get("MCP_AUTH_TOKEN", "") else "No")
        st.write("MCP send-email tool:", st.secrets.get("MCP_SEND_EMAIL_TOOL", "send_email"))
        st.caption("The remote MCP server must be authenticated and expose an attachment-capable email tool. See README.md for the required tool contract and secrets.")

    if send_clicked:
        import re
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient.strip()):
            st.error("Enter a valid recipient email address.")
        elif not email_subject.strip():
            st.error("Email subject cannot be blank.")
        elif not email_message.strip():
            st.error("Email message cannot be blank.")
        elif not confirm_send:
            st.error("Please confirm that the recipient is authorized to receive this report.")
        elif not st.secrets.get("MCP_SERVER_URL", ""):
            st.error("MCP_SERVER_URL is not configured. Add the MCP server settings to Streamlit Cloud Secrets.")
        else:
            try:
                pdf_bytes = make_pdf_report(
                    f, monthly, unit_summary, revenue, gross_profit, operating_profit,
                    gross_margin, operating_margin, cash
                )
                server_url = str(st.secrets["MCP_SERVER_URL"]).strip()
                auth_token = str(st.secrets.get("MCP_AUTH_TOKEN", "")).strip()
                tool_name = str(st.secrets.get("MCP_SEND_EMAIL_TOOL", "send_email")).strip()
                with st.spinner("Connecting to the MCP server and sending the PDF report..."):
                    result_message = send_email_via_mcp(
                        server_url, auth_token, tool_name, recipient.strip(),
                        email_subject.strip(), email_message.strip(), pdf_bytes,
                        f"CA_Financial_Report_{start_date:%Y%m%d}_{end_date:%Y%m%d}.pdf"
                    )
                st.success("The MCP email tool reported success.")
                st.info(result_message)
            except Exception as exc:
                st.error(f"Email was not confirmed as sent. Details: {exc}")
                st.warning("Check the MCP server URL, authentication, tool name, attachment contract and server logs. Do not retry repeatedly until you know whether the first request was delivered.")

st.divider()
st.caption("Training prototype only. Confirm accounting definitions, period-end balance treatment, source completeness and all flagged items with the responsible professional.")
