# LPG CP In-Transit Incident Dashboard

A clean rebuild that replaces the three overlapping prior attempts
(`backend.zip`, `DEMO_2.zip`, `Incident-Analysis-main.zip`) with one
project that explicitly reproduces every chart category from `Book1.xlsx`.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints, and upload
`Retail_Intransit_Dataset.xlsx` in the sidebar.

## How it works

- `data_loader.py` — parses the raw two-row-header Excel export, cleans
  placeholder tokens (`-`, `NOT APPLICABLE`, etc.), parses dates/times, and
  derives every field the charts need (Indian financial year, weekday,
  time-of-day bucket, fatality/injury totals).
- `database.py` — persists cleaned rows to a local SQLite file keyed by
  `FIR NUMBER`, so uploading a new year's file **adds** to history instead
  of overwriting it. Re-uploading the same file safely dedupes.
- `charts.py` — one aggregation function + one Plotly figure per Book1
  chart category. Explicit column mapping, no keyword-guessing.
- `excel_export.py` — builds a downloadable `.xlsx` with **native**
  openpyxl chart objects (not embedded images), matching Book1's own
  chart types (Line / Bar / Bar3D / Pie3D) sheet-for-sheet.
- `app.py` — the Streamlit UI: upload, persistent stats, one tab per
  category, and the Excel download button.

## Known data gaps (not bugs)

`Retail_Intransit_Dataset.xlsx` covers **tank-lorry-in-transit accidents**
only — a narrower slice than Book1's broader "LPG CP Incidents." Two Book1
categories genuinely have no matching data in this file and will show a
clear "no data" notice instead of being faked:

- **Type of Consumer** — no `CONSUMER TYPE` values in this dataset (transit
  accidents aren't tied to a specific consumer).
- **Zone wise classification** — there is no `ZONE` column in this dataset
  at all.

Both will populate automatically the moment a dataset containing those
columns is uploaded — no code changes needed.

Also note: this dataset only contains **FY 2024-25** data. Multi-year trend
charts (Historic Trend, year-over-year comparisons) will show a single
year/bar until further years are uploaded — the database accumulates them
over time as you add more files.
