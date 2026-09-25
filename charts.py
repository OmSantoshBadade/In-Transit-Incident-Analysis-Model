"""
charts.py
One aggregation function + one Plotly figure per Book1 chart category.
Each aggregator returns a tidy pandas DataFrame; excel_export.py reuses the
same tidy tables to build native openpyxl charts, so the numbers shown in
the app and the numbers exported to Excel can never drift apart.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

FY_SORT_KEY = lambda fy: fy  # 'FY 2019-20' sorts correctly as a string

MONTH_ORDER = ["April", "May", "June", "July", "August", "September",
               "October", "November", "December", "January", "February", "March"]
WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TIME_BUCKET_ORDER = ["05:01 to 10:00", "10:01 to 16:00", "16:01 to 23:00", "23:01 to 05:00"]


def _sorted_fys(df):
    return sorted(df["FINANCIAL_YEAR"].dropna().unique())


# ---------------------------------------------------------------- Historic Trend
def historic_trend(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("FINANCIAL_YEAR").agg(
        Incidents=("IS_INCIDENT", "sum"),
        Fatalities=("FATALITIES_TOTAL", "sum"),
    ).reindex(_sorted_fys(df))
    g["IFR"] = (g["Fatalities"] / g["Incidents"].replace(0, pd.NA) * 100).round(2)
    return g.reset_index().rename(columns={"FINANCIAL_YEAR": "Year"})


def fig_historic_trend(tbl: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tbl["Year"], y=tbl["Incidents"], mode="lines+markers", name="Incidents"))
    fig.add_trace(go.Scatter(x=tbl["Year"], y=tbl["Fatalities"], mode="lines+markers", name="Fatalities"))
    fig.update_layout(title="Historical Trend of LPG CP Accidents", xaxis_title="Year")
    return fig


# ---------------------------------------------------------------- Region Wise
def region_wise(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """metric: 'IS_INCIDENT' | 'FATALITIES_TOTAL' | 'INJURIES_TOTAL'"""
    pivot = df.pivot_table(index="REGION", columns="FINANCIAL_YEAR", values=metric,
                            aggfunc="sum", fill_value=0)
    return pivot.reindex(columns=_sorted_fys(df), fill_value=0).reset_index()


def fig_region_wise(tbl: pd.DataFrame, title: str):
    fy_cols = [c for c in tbl.columns if c != "REGION"]
    fig = px.bar(tbl, x="REGION", y=fy_cols, barmode="group", title=title)
    return fig


def fig_region_wise_combo(df: pd.DataFrame):
    """3D-style combined Incidents/Fatalities/Injuries by region (current data)."""
    g = df.groupby("REGION").agg(
        Incidents=("IS_INCIDENT", "sum"),
        Fatalities=("FATALITIES_TOTAL", "sum"),
        Injuries=("INJURIES_TOTAL", "sum"),
    ).reset_index()
    fig = px.bar(g, x="REGION", y=["Incidents", "Fatalities", "Injuries"], barmode="group",
                 title="Region wise breakup of Incidents, Fatalities and Injuries")
    return fig, g


# ---------------------------------------------------------------- State Wise
def state_wise(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    pivot = df.pivot_table(index=["REGION", "STATE"], columns="FINANCIAL_YEAR",
                            values=metric, aggfunc="sum", fill_value=0)
    return pivot.reindex(columns=_sorted_fys(df), fill_value=0).reset_index()


def fig_state_wise(tbl: pd.DataFrame, title: str):
    fy_cols = [c for c in tbl.columns if c not in ("REGION", "STATE")]
    fig = px.bar(tbl, x="STATE", y=fy_cols, barmode="group", title=title, color="REGION")
    return fig


# ---------------------------------------------------------------- Territory wise
def territory_wise(df: pd.DataFrame, region: str, metric: str) -> pd.DataFrame:
    sub = df[df["REGION"] == region]
    pivot = sub.pivot_table(index="TERRITORY", columns="FINANCIAL_YEAR",
                             values=metric, aggfunc="sum", fill_value=0)
    return pivot.reindex(columns=_sorted_fys(df), fill_value=0).reset_index()


def fig_territory_wise(tbl: pd.DataFrame, title: str):
    fy_cols = [c for c in tbl.columns if c != "TERRITORY"]
    fig = px.bar(tbl, x="TERRITORY", y=fy_cols, barmode="group", title=title)
    return fig


# ---------------------------------------------------------------- Monthly Breakup
def monthly_breakup(df: pd.DataFrame) -> pd.DataFrame:
    pivot = df.pivot_table(index="MONTH_NAME", columns="FINANCIAL_YEAR",
                            values="IS_INCIDENT", aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(MONTH_ORDER, fill_value=0)
    return pivot.reindex(columns=_sorted_fys(df), fill_value=0).reset_index().rename(
        columns={"MONTH_NAME": "Month"})


def fig_monthly_breakup(tbl: pd.DataFrame):
    fy_cols = [c for c in tbl.columns if c != "Month"]
    return px.bar(tbl, x="Month", y=fy_cols, barmode="group",
                   title="Monthly Breakup of LPG CP Incidents")


# ---------------------------------------------------------------- Week Days
def week_days(df: pd.DataFrame) -> pd.DataFrame:
    pivot = df.pivot_table(index="WEEKDAY_NAME", columns="FINANCIAL_YEAR",
                            values="IS_INCIDENT", aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(WEEKDAY_ORDER, fill_value=0)
    tbl = pivot.reindex(columns=_sorted_fys(df), fill_value=0).reset_index().rename(
        columns={"WEEKDAY_NAME": "Days"})
    fy_cols = [c for c in tbl.columns if c != "Days"]
    tbl["Cumulative"] = tbl[fy_cols].sum(axis=1)
    return tbl


def fig_week_days(tbl: pd.DataFrame):
    fy_cols = [c for c in tbl.columns if c not in ("Days", "Cumulative")]
    fig = go.Figure()
    for c in fy_cols:
        fig.add_trace(go.Scatter(x=tbl["Days"], y=tbl[c], mode="lines+markers", name=c))
    fig.update_layout(title="Week Day-wise Breakup of Incidents")
    return fig


# ---------------------------------------------------------------- Date wise
def date_wise(df: pd.DataFrame) -> pd.DataFrame:
    pivot = df.pivot_table(index="DAY_OF_MONTH", columns="FINANCIAL_YEAR",
                            values="IS_INCIDENT", aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(range(1, 32), fill_value=0)
    tbl = pivot.reindex(columns=_sorted_fys(df), fill_value=0).reset_index().rename(
        columns={"DAY_OF_MONTH": "Date"})
    fy_cols = [c for c in tbl.columns if c != "Date"]
    tbl["Cumulative"] = tbl[fy_cols].sum(axis=1)
    return tbl


def fig_date_wise(tbl: pd.DataFrame):
    fy_cols = [c for c in tbl.columns if c not in ("Date", "Cumulative")]
    fig = go.Figure()
    for c in fy_cols:
        fig.add_trace(go.Scatter(x=tbl["Date"], y=tbl[c], mode="lines", name=c))
    fig.update_layout(title="Analysis Based on Date")
    return fig


# ---------------------------------------------------------------- Time wise
def time_wise(df: pd.DataFrame) -> pd.DataFrame:
    pivot = df.pivot_table(index="TIME_BUCKET", columns="FINANCIAL_YEAR",
                            values="IS_INCIDENT", aggfunc="sum", fill_value=0)
    pivot = pivot.reindex(TIME_BUCKET_ORDER, fill_value=0)
    tbl = pivot.reindex(columns=_sorted_fys(df), fill_value=0).reset_index().rename(
        columns={"TIME_BUCKET": "Time"})
    fy_cols = [c for c in tbl.columns if c != "Time"]
    tbl["Total"] = tbl[fy_cols].sum(axis=1)
    return tbl


def fig_time_wise(tbl: pd.DataFrame):
    fy_cols = [c for c in tbl.columns if c not in ("Time", "Total")]
    return px.bar(tbl, x="Time", y=fy_cols, barmode="group",
                   title="Time Wise Breakup of LPG CP Incidents")


# ---------------------------------------------------------------- Type of Consumer
def type_of_consumer(df: pd.DataFrame) -> pd.DataFrame:
    if "CONSUMER TYPE" not in df.columns or df["CONSUMER TYPE"].dropna().empty:
        return pd.DataFrame()
    pivot = df.pivot_table(index="CONSUMER TYPE", columns="FINANCIAL_YEAR",
                            values="IS_INCIDENT", aggfunc="sum", fill_value=0)
    return pivot.reindex(columns=_sorted_fys(df), fill_value=0).reset_index()


def fig_type_of_consumer(tbl: pd.DataFrame):
    fy_cols = [c for c in tbl.columns if c != "CONSUMER TYPE"]
    return px.bar(tbl, x="CONSUMER TYPE", y=fy_cols, barmode="group",
                   title="Analysis Based on Type of Consumer")


# ---------------------------------------------------------------- Zone wise
def zone_wise(df: pd.DataFrame) -> pd.DataFrame:
    if "ZONE" not in df.columns or df["ZONE"].dropna().empty:
        return pd.DataFrame()  # not present in this dataset
    pivot = df.pivot_table(index="ZONE", columns="FINANCIAL_YEAR",
                            values="IS_INCIDENT", aggfunc="sum", fill_value=0)
    return pivot.reindex(columns=_sorted_fys(df), fill_value=0).reset_index()


def fig_zone_wise(tbl: pd.DataFrame):
    fy_cols = [c for c in tbl.columns if c != "ZONE"]
    return px.bar(tbl, x="ZONE", y=fy_cols, barmode="group",
                   title="Zone Wise Classification of LPG CP Incidents")


# ---------------------------------------------------------------- FIR / DIR Status
def fir_status(df: pd.DataFrame) -> pd.DataFrame:
    within = (df["FIR_TURNAROUND_DAYS"] <= 7).sum()
    beyond = (df["FIR_TURNAROUND_DAYS"] > 7).sum()
    return pd.DataFrame({"Bucket": ["<1 Week", ">1 Week"], "Count": [within, beyond]})


def dir_status(df: pd.DataFrame) -> pd.DataFrame:
    if "DIR STATUS" not in df.columns:
        return pd.DataFrame()
    counts = df["DIR STATUS"].value_counts(dropna=True)
    return counts.rename_axis("Status").reset_index(name="Count")


def fig_fir_dir_status(fir_tbl: pd.DataFrame, dir_tbl: pd.DataFrame):
    fig = go.Figure()
    fig.add_trace(go.Pie(labels=fir_tbl["Bucket"], values=fir_tbl["Count"],
                          name="FIR Filing", domain=dict(x=[0, 0.48]), title="FIR Filing"))
    if not dir_tbl.empty:
        fig.add_trace(go.Pie(labels=dir_tbl["Status"], values=dir_tbl["Count"],
                              name="DIR Status", domain=dict(x=[0.52, 1.0]), title="DIR Status"))
    fig.update_layout(title="FIR / DIR Status")
    return fig


# ---------------------------------------------------------------- Root Cause Analysis
def root_cause(df: pd.DataFrame, fy: str = None) -> pd.DataFrame:
    sub = df if fy is None else df[df["FINANCIAL_YEAR"] == fy]
    causes = pd.concat([
        sub[c] for c in ["ROOT CAUSE-1", "ROOT-CAUSE-2", "ROOT-CAUSE-3"] if c in sub.columns
    ]).dropna()
    causes = causes[causes.str.strip() != ""]
    if causes.empty:
        return pd.DataFrame()
    counts = causes.value_counts().rename_axis("Root Cause").reset_index(name="No of Incidents")
    return counts


def fig_root_cause(tbl: pd.DataFrame, title: str):
    return px.pie(tbl, names="Root Cause", values="No of Incidents", title=title)


# ---------------------------------------------------------------- Custom Chart Builder

def build_custom_chart_data(df: pd.DataFrame, group_by: str, metric: str, fy: str = "All") -> pd.DataFrame:
    """Build a grouped table for a user-defined chart.

    group_by: a categorical column such as REGION, STATE, MONTH_NAME, etc.
    metric: numeric field such as IS_INCIDENT, FATALITIES_TOTAL, INJURIES_TOTAL
    fy: optional FY filter, or 'All' for all years.
    """
    if group_by not in df.columns:
        raise ValueError(f"Column '{group_by}' not found in the dataset.")
    if metric not in df.columns:
        raise ValueError(f"Metric '{metric}' not found in the dataset.")

    sub = df.copy()
    if fy != "All":
        sub = sub[sub["FINANCIAL_YEAR"] == fy]

    tbl = sub.groupby(group_by, dropna=False)[metric].sum().reset_index(name="value")
    tbl = tbl.sort_values("value", ascending=False)
    return tbl.rename(columns={group_by: group_by})


def build_custom_chart(tbl: pd.DataFrame, group_col: str, metric: str, chart_type: str = "bar"):
    """Create a Plotly chart from a prebuilt custom dataset."""
    chart_type = (chart_type or "bar").lower()
    if chart_type == "bar":
        return px.bar(tbl, x=group_col, y="value", title=f"{metric} by {group_col}")
    if chart_type == "line":
        return px.line(tbl, x=group_col, y="value", title=f"{metric} by {group_col}")
    if chart_type == "pie":
        return px.pie(tbl, names=group_col, values="value", title=f"{metric} by {group_col}")
    if chart_type == "scatter":
        return px.scatter(tbl, x=group_col, y="value", title=f"{metric} by {group_col}")
    raise ValueError(f"Unsupported chart type: {chart_type}")
