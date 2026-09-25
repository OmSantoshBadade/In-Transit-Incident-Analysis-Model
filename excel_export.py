"""
excel_export.py
Builds a Book1-style .xlsx: one sheet per category, real data + a native
openpyxl chart object (not an image), matching Book1's own chart types
(LineChart, BarChart, BarChart3D, PieChart3D).
"""

import io
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import LineChart, BarChart, BarChart3D, PieChart, PieChart3D, Reference
from openpyxl.styles import Font
from openpyxl.utils.dataframe import dataframe_to_rows

import charts as ch


def _write_table(ws, df: pd.DataFrame, start_row=1):
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)
    return start_row, start_row + len(df)  # header_row, last_data_row


def _add_bar_chart(ws, title, min_col, max_col, min_row, max_row, cats_col, threeD=False):
    chart = BarChart3D() if threeD else BarChart()
    chart.title = title
    chart.type = "col"
    data = Reference(ws, min_col=min_col, max_col=max_col, min_row=min_row, max_row=max_row)
    cats = Reference(ws, min_col=cats_col, min_row=min_row + 1, max_row=max_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.height, chart.width = 9, 18
    return chart


def _add_line_chart(ws, title, min_col, max_col, min_row, max_row, cats_col):
    chart = LineChart()
    chart.title = title
    data = Reference(ws, min_col=min_col, max_col=max_col, min_row=min_row, max_row=max_row)
    cats = Reference(ws, min_col=cats_col, min_row=min_row + 1, max_row=max_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.height, chart.width = 9, 18
    return chart


def _add_pie_chart(ws, title, label_col, val_col, min_row, max_row, threeD=True):
    chart = PieChart3D() if threeD else PieChart()
    chart.title = title
    data = Reference(ws, min_col=val_col, min_row=min_row, max_row=max_row)
    cats = Reference(ws, min_col=label_col, min_row=min_row + 1, max_row=max_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.height, chart.width = 9, 12
    return chart


def build_workbook(df: pd.DataFrame) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)

    # ---- Summary sheet ----
    ws = wb.create_sheet("Summary")
    ws["A1"] = "Dashboard Summary"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A3"] = "Total incidents"
    ws["B3"] = len(df)
    ws["A4"] = "Financial years covered"
    ws["B4"] = ", ".join(sorted(df["FINANCIAL_YEAR"].dropna().unique().tolist())) if not df.empty else "No data"
    ws["A5"] = "Regions"
    ws["B5"] = ", ".join(sorted(df["REGION"].dropna().astype(str).unique().tolist())) if not df.empty else "No data"
    ws["A7"] = "Notes"
    ws["A8"] = "This workbook contains the data tables and native Excel charts shown in the dashboard."

    # ---- Historic Trend ----
    tbl = ch.historic_trend(df)
    if not tbl.empty:
        ws = wb.create_sheet("Historic Trend")
        _write_table(ws, tbl)
        chart = _add_line_chart(ws, "Historical Trend of LPG CP Accidents",
                                 min_col=2, max_col=len(tbl.columns), min_row=1,
                                 max_row=len(tbl) + 1, cats_col=1)
        ws.add_chart(chart, "F2")

    # ---- Region Wise ----
    ws = wb.create_sheet("Region Wise")
    row_cursor = 1
    for metric, label in [("IS_INCIDENT", "Incidents"), ("FATALITIES_TOTAL", "Fatalities"),
                           ("INJURIES_TOTAL", "Injuries")]:
        tbl = ch.region_wise(df, metric)
        if tbl.empty:
            continue
        hdr, last = _write_table(ws, tbl, start_row=row_cursor)
        chart = _add_bar_chart(ws, f"Region wise breakup of LPG CP {label}",
                                min_col=2, max_col=len(tbl.columns), min_row=hdr, max_row=last,
                                cats_col=1)
        ws.add_chart(chart, f"H{row_cursor}")
        row_cursor = last + 2

    combo_tbl = df.groupby("REGION").agg(
        Incidents=("IS_INCIDENT", "sum"), Fatalities=("FATALITIES_TOTAL", "sum"),
        Injuries=("INJURIES_TOTAL", "sum")).reset_index()
    if not combo_tbl.empty:
        hdr, last = _write_table(ws, combo_tbl, start_row=row_cursor)
        chart = _add_bar_chart(ws, "Region wise breakup of Incidents, Fatalities and Injuries",
                                min_col=2, max_col=len(combo_tbl.columns), min_row=hdr, max_row=last,
                                cats_col=1, threeD=True)
        ws.add_chart(chart, f"H{row_cursor}")

    # ---- State Wise ----
    ws = wb.create_sheet("State Wise")
    row_cursor = 1
    for metric, label in [("IS_INCIDENT", "Incidents"), ("FATALITIES_TOTAL", "Fatalities"),
                           ("INJURIES_TOTAL", "Injuries")]:
        tbl = ch.state_wise(df, metric)
        if tbl.empty:
            continue
        hdr, last = _write_table(ws, tbl, start_row=row_cursor)
        chart = _add_bar_chart(ws, f"State wise breakup of LPG CP {label}",
                                min_col=3, max_col=len(tbl.columns), min_row=hdr, max_row=last,
                                cats_col=2)
        ws.add_chart(chart, f"K{row_cursor}")
        row_cursor = last + 2

    # ---- Territory wise graphs (per region x per metric) ----
    ws = wb.create_sheet("Territory wise graphs")
    row_cursor = 1
    for region in sorted(df["REGION"].dropna().unique()):
        for metric, label in [("IS_INCIDENT", "Incidents"), ("FATALITIES_TOTAL", "Fatalities"),
                               ("INJURIES_TOTAL", "Injuries")]:
            tbl = ch.territory_wise(df, region, metric)
            if tbl.empty:
                continue
            hdr, last = _write_table(ws, tbl, start_row=row_cursor)
            chart = _add_bar_chart(ws, f"{region} - Territory wise {label}",
                                    min_col=2, max_col=len(tbl.columns), min_row=hdr, max_row=last,
                                    cats_col=1)
            ws.add_chart(chart, f"H{row_cursor}")
            row_cursor = last + 2

    # ---- Monthly Breakup ----
    tbl = ch.monthly_breakup(df)
    if not tbl.empty:
        ws = wb.create_sheet("Monthly Breakup")
        hdr, last = _write_table(ws, tbl)
        chart = _add_bar_chart(ws, "Monthly Breakup of LPG CP Incidents",
                                min_col=2, max_col=len(tbl.columns), min_row=hdr, max_row=last, cats_col=1)
        ws.add_chart(chart, "I2")

    # ---- Week Days ----
    tbl = ch.week_days(df)
    if not tbl.empty:
        ws = wb.create_sheet("Week Days")
        hdr, last = _write_table(ws, tbl)
        chart = _add_line_chart(ws, "Week Day-wise Breakup of Incidents",
                                 min_col=2, max_col=len(tbl.columns), min_row=hdr, max_row=last, cats_col=1)
        ws.add_chart(chart, "J2")

    # ---- Date wise ----
    tbl = ch.date_wise(df)
    if not tbl.empty:
        ws = wb.create_sheet("Date wise")
        hdr, last = _write_table(ws, tbl)
        chart = _add_line_chart(ws, "Analysis Based on Date",
                                 min_col=2, max_col=len(tbl.columns), min_row=hdr, max_row=last, cats_col=1)
        ws.add_chart(chart, "J2")

    # ---- Time wise ----
    tbl = ch.time_wise(df)
    if not tbl.empty:
        ws = wb.create_sheet("Time wise")
        hdr, last = _write_table(ws, tbl)
        chart = _add_bar_chart(ws, "Time Wise Breakup of LPG CP Incidents",
                                min_col=2, max_col=len(tbl.columns), min_row=hdr, max_row=last, cats_col=1)
        ws.add_chart(chart, "J2")

    # ---- Type of Consumer (may be empty for this dataset) ----
    tbl = ch.type_of_consumer(df)
    ws = wb.create_sheet("Type of Consumer")
    if not tbl.empty:
        hdr, last = _write_table(ws, tbl)
        chart = _add_bar_chart(ws, "Analysis Based on Type of Consumer",
                                min_col=2, max_col=len(tbl.columns), min_row=hdr, max_row=last, cats_col=1)
        ws.add_chart(chart, "I2")
    else:
        ws["A1"] = "No CONSUMER TYPE data present in this dataset (in-transit accidents don't carry a consumer record)."

    # ---- Zone wise (may be empty for this dataset) ----
    tbl = ch.zone_wise(df)
    ws = wb.create_sheet("Zone wise classification")
    if not tbl.empty:
        hdr, last = _write_table(ws, tbl)
        chart = _add_bar_chart(ws, "Zone Wise Classification of LPG CP Incidents",
                                min_col=2, max_col=len(tbl.columns), min_row=hdr, max_row=last, cats_col=1)
        ws.add_chart(chart, "I2")
    else:
        ws["A1"] = "No ZONE column present in this dataset."

    # ---- FIR, DIR Status ----
    ws = wb.create_sheet("FIR, DIR Status")
    fir_tbl = ch.fir_status(df)
    dir_tbl = ch.dir_status(df)
    hdr, last = _write_table(ws, fir_tbl, start_row=1)
    chart1 = _add_pie_chart(ws, "FIR Filing", label_col=1, val_col=2, min_row=hdr, max_row=last)
    ws.add_chart(chart1, "E1")
    if not dir_tbl.empty:
        hdr2, last2 = _write_table(ws, dir_tbl, start_row=last + 2)
        chart2 = _add_pie_chart(ws, "DIR Status", label_col=1, val_col=2, min_row=hdr2, max_row=last2)
        ws.add_chart(chart2, "E17")

    # ---- Root Cause Analysis (one pie per FY) ----
    ws = wb.create_sheet("Root Cause Analysis")
    row_cursor = 1
    for fy in sorted(df["FINANCIAL_YEAR"].dropna().unique()):
        tbl = ch.root_cause(df, fy)
        if tbl.empty:
            continue
        hdr, last = _write_table(ws, tbl, start_row=row_cursor)
        chart = _add_pie_chart(ws, f"Root Cause Analysis of Incidents {fy}",
                                label_col=1, val_col=2, min_row=hdr, max_row=last)
        ws.add_chart(chart, f"E{row_cursor}")
        row_cursor = last + 15

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
