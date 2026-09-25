"""
app.py
Vercel-compatible entrypoint for deployment, while preserving the local
Streamlit dashboard experience when launched with `streamlit run app.py`.
"""

import os

from flask import Flask

app = Flask(__name__)
application = app


@app.route("/")
def landing_page():
    return (
        "<!doctype html>"
        "<html><head><title>Incident Dashboard</title>"
        "<style>body{font-family:Arial,sans-serif;padding:2rem;line-height:1.6}</style></head>"
        "<body>"
        "<h1>LPG CP In-Transit Incident Dashboard</h1>"
        "<p>This project is configured for Vercel deployment with a top-level WSGI app export.</p>"
        "<p>For the full dashboard UI locally, run:</p>"
        "<pre>streamlit run app.py</pre>"
        "</body></html>",
        200,
    )


def render_dashboard():
    import streamlit as st

    import data_loader as dl
    import database as db
    import charts as ch
    import excel_export as ex

    st.set_page_config(page_title="LPG CP / In-Transit Incident Dashboard", layout="wide")

    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        div[data-testid="stMetricLabel"] { font-size: 0.82rem; }
        div[data-testid="stMetricValue"] { font-size: 1.4rem; }
        .section-header { font-weight: 700; font-size: 1.1rem; margin-top: 0.8rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("LPG CP In-Transit Incident Dashboard")
    st.caption("Operational incident reporting for LPG CP in-transit accidents")

    with st.sidebar:
        st.header("Data Management")
        uploaded = st.file_uploader("Upload Retail_Intransit_Dataset.xlsx", type=["xlsx"], help="The file will be cleaned and stored in the local SQLite database.")
        if uploaded is not None:
            try:
                clean_df = dl.load_and_clean(uploaded)
                n = db.upsert_dataframe(clean_df)
                st.success(f"Loaded and stored {n} incident records.")
            except Exception as e:
                st.error(f"Failed to process file: {e}")

        stats = db.summary_stats()
        st.metric("Total incidents", stats["total_incidents"])
        st.caption("Financial years covered: " + (", ".join(stats["years"]) if stats["years"] else "none yet"))

        if st.session_state.get("confirm_delete", False):
            st.warning("This will permanently delete all stored incident records.")
            if st.button("Confirm delete all data", type="primary", use_container_width=True):
                db.delete_all_data()
                st.session_state.confirm_delete = False
                st.success("All stored data has been deleted.")
                st.rerun()
        else:
            if st.button("Delete all stored data", type="secondary", use_container_width=True):
                st.session_state.confirm_delete = True
                st.rerun()

    df = db.load_all()

    if df.empty:
        st.info("Upload a dataset in the sidebar to get started.")
        st.stop()

    stats = db.summary_stats()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total incidents", stats["total_incidents"])
    with col2:
        st.metric("Financial years", len(stats["years"]))
    with col3:
        st.metric("Regions covered", df["REGION"].dropna().nunique())

    xlsx_bytes = ex.build_workbook(df)
    st.download_button(
        "Download Excel report with charts and tables",
        data=xlsx_bytes,
        file_name="incident_analysis_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    tabs = st.tabs([
        "Custom Chart", "Historic Trend", "Region Wise", "State Wise", "Territory Wise",
        "Monthly Breakup", "Week Days", "Date Wise", "Time Wise",
        "Type of Consumer", "Zone Wise", "FIR / DIR Status", "Root Cause",
    ])

    with tabs[0]:
        st.markdown("<div class='section-header'>Custom chart builder</div>", unsafe_allow_html=True)
        group_options = [
            "REGION", "STATE", "TERRITORY", "MONTH_NAME", "WEEKDAY_NAME",
            "TIME_BUCKET", "DIR STATUS", "FIR STATUS", "ROOT CAUSE-1",
            "ROOT-CAUSE-2", "ROOT-CAUSE-3", "CONSUMER TYPE", "ZONE"
        ]
        metric_options = ["IS_INCIDENT", "FATALITIES_TOTAL", "INJURIES_TOTAL"]
        custom_group = st.selectbox("Group by", [c for c in group_options if c in df.columns])
        custom_metric = st.selectbox("Metric", metric_options)
        custom_fy = st.selectbox("Financial year", ["All"] + sorted(df["FINANCIAL_YEAR"].dropna().unique().tolist()))
        custom_chart_type = st.selectbox("Chart type", ["bar", "line", "pie", "scatter"])

        try:
            custom_tbl = ch.build_custom_chart_data(df, custom_group, custom_metric, custom_fy)
            st.plotly_chart(ch.build_custom_chart(custom_tbl, custom_group, custom_metric, custom_chart_type), use_container_width=True)
            st.dataframe(custom_tbl, use_container_width=True)
        except ValueError as exc:
            st.warning(str(exc))

    with tabs[1]:
        tbl = ch.historic_trend(df)
        st.plotly_chart(ch.fig_historic_trend(tbl), use_container_width=True)
        st.dataframe(tbl, use_container_width=True)

    with tabs[2]:
        for metric, label in [("IS_INCIDENT", "Incidents"), ("FATALITIES_TOTAL", "Fatalities"),
                              ("INJURIES_TOTAL", "Injuries")]:
            tbl = ch.region_wise(df, metric)
            if not tbl.empty:
                st.plotly_chart(ch.fig_region_wise(tbl, f"Region wise breakup of LPG CP {label}"),
                                use_container_width=True)
        combo_fig, combo_tbl = ch.fig_region_wise_combo(df)
        st.plotly_chart(combo_fig, use_container_width=True)
        st.dataframe(combo_tbl, use_container_width=True)

    with tabs[3]:
        for metric, label in [("IS_INCIDENT", "Incidents"), ("FATALITIES_TOTAL", "Fatalities"),
                              ("INJURIES_TOTAL", "Injuries")]:
            tbl = ch.state_wise(df, metric)
            if not tbl.empty:
                st.plotly_chart(ch.fig_state_wise(tbl, f"State wise breakup of LPG CP {label}"),
                                use_container_width=True)
                st.dataframe(tbl, use_container_width=True)

    with tabs[4]:
        region_choice = st.selectbox("Region", sorted(df["REGION"].dropna().unique()))
        for metric, label in [("IS_INCIDENT", "Incidents"), ("FATALITIES_TOTAL", "Fatalities"),
                              ("INJURIES_TOTAL", "Injuries")]:
            tbl = ch.territory_wise(df, region_choice, metric)
            if not tbl.empty:
                st.plotly_chart(ch.fig_territory_wise(tbl, f"{region_choice} — Territory wise {label}"),
                                use_container_width=True)
                st.dataframe(tbl, use_container_width=True)

    with tabs[5]:
        tbl = ch.monthly_breakup(df)
        st.plotly_chart(ch.fig_monthly_breakup(tbl), use_container_width=True)
        st.dataframe(tbl, use_container_width=True)

    with tabs[6]:
        tbl = ch.week_days(df)
        st.plotly_chart(ch.fig_week_days(tbl), use_container_width=True)
        st.dataframe(tbl, use_container_width=True)

    with tabs[7]:
        tbl = ch.date_wise(df)
        st.plotly_chart(ch.fig_date_wise(tbl), use_container_width=True)
        st.dataframe(tbl, use_container_width=True)

    with tabs[8]:
        tbl = ch.time_wise(df)
        st.plotly_chart(ch.fig_time_wise(tbl), use_container_width=True)
        st.dataframe(tbl, use_container_width=True)

    with tabs[9]:
        tbl = ch.type_of_consumer(df)
        if tbl.empty:
            st.warning("No CONSUMER TYPE data in this dataset — in-transit accidents don't carry a consumer record. This chart will populate once a dataset containing that column is uploaded.")
        else:
            st.plotly_chart(ch.fig_type_of_consumer(tbl), use_container_width=True)
            st.dataframe(tbl, use_container_width=True)

    with tabs[10]:
        tbl = ch.zone_wise(df)
        if tbl.empty:
            st.warning("No ZONE column present in this dataset. This chart will populate once a dataset containing that column is uploaded.")
        else:
            st.plotly_chart(ch.fig_zone_wise(tbl), use_container_width=True)
            st.dataframe(tbl, use_container_width=True)

    with tabs[11]:
        fir_tbl = ch.fir_status(df)
        dir_tbl = ch.dir_status(df)
        st.plotly_chart(ch.fig_fir_dir_status(fir_tbl, dir_tbl), use_container_width=True)
        st.dataframe(fir_tbl, use_container_width=True)
        if not dir_tbl.empty:
            st.dataframe(dir_tbl, use_container_width=True)

    with tabs[12]:
        fy_choice = st.selectbox("Financial Year", sorted(df["FINANCIAL_YEAR"].dropna().unique()), key="rootcause_fy")
        tbl = ch.root_cause(df, fy_choice)
        if tbl.empty:
            st.warning("No root cause data for this year.")
        else:
            st.plotly_chart(ch.fig_root_cause(tbl, f"Root Cause Analysis {fy_choice}"), use_container_width=True)
            st.dataframe(tbl, use_container_width=True)


if __name__ == "__main__":
    if os.environ.get("VERCEL") == "1":
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
    else:
        render_dashboard()
