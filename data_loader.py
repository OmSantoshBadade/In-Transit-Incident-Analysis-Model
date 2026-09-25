"""
data_loader.py
Loads the raw Retail In-Transit incident Excel export and turns it into a
clean, analysis-ready DataFrame. This is the ONLY place that should know
about the raw column layout of the source Excel file.
"""

import pandas as pd
import numpy as np

# Columns that hold small counts of people (fatalities/injuries by person type)
FATALITY_COLS = ["FATALITY_BPCL_STAFF", "FATALITY_BPCL_PCVO_CREW",
                  "FATALITY_CONTRACT_WORKMEN", "FATALITY_THIRD_PARTY"]
INJURY_COLS = ["INJURY_BPCL_STAFF", "INJURY_BPCL_PCVO_CREW",
               "INJURY_CONTRACT_WORKMEN", "INJURY_THIRD_PARTY"]

# Placeholder tokens the source data uses in place of a real blank
NULL_TOKENS = {"-", "--", "NOT APPLICABLE", "N/A", "NA", "", "NONE", "NIL"}

TIME_BUCKETS = [
    (5, 10, "05:01 to 10:00"),
    (10, 16, "10:01 to 16:00"),
    (16, 23, "16:01 to 23:00"),
    (23, 29, "23:01 to 05:00"),  # wraps past midnight, handled specially
]


def _clean_str_series(s: pd.Series) -> pd.Series:
    s = s.astype(object)
    s = s.map(lambda v: str(v).strip() if v is not None else v)
    is_null = s.map(
        lambda v: (v is None) or (str(v).strip().upper() in NULL_TOKENS)
        or str(v).strip() == ""
    )
    s = s.mask(is_null, np.nan)
    return s


def _financial_year_label(dt: pd.Timestamp):
    """India FY: April 1 -> March 31. Returns e.g. 'FY 2024-25'."""
    if pd.isna(dt):
        return np.nan
    year = dt.year
    if dt.month >= 4:
        start, end = year, year + 1
    else:
        start, end = year - 1, year
    return f"FY {start}-{str(end)[2:]}"


def _time_bucket(t: pd.Timestamp):
    if pd.isna(t):
        return np.nan
    hour = t.hour
    if 5 <= hour < 10 or (hour == 10 and t.minute == 0 and False):
        return "05:01 to 10:00"
    if 10 <= hour < 16:
        return "10:01 to 16:00"
    if 16 <= hour < 23:
        return "16:01 to 23:00"
    return "23:01 to 05:00"  # 23:00-04:59


def load_raw_excel(file) -> pd.DataFrame:
    """Read the two-row-header source workbook. Row 1 = merged group
    labels (ignored), row 2 = the real field names, data starts row 3."""
    df = pd.read_excel(file, header=1)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def clean_and_normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Produce a tidy, typed DataFrame with derived helper columns used by
    every chart in charts.py. Never mutates the caller's frame."""
    df = df.copy()

    # ---- rename the duplicate FATALITIES/INJURIES person-type columns ----
    # These arrive as 8 columns with duplicate names (BPCL STAFF appears
    # twice etc: cols 36-39 = fatalities by person type, 40-43 = injuries).
    cols = list(df.columns)
    # Locate by position since names collide. We know the layout from the
    # source: 36-39 = fatalities by person type, 40-43 = injuries by person type.
    person_cols = ["BPCL STAFF", "BPCL PCVO CREW", "CONTRACT WORKMEN", "THIRD PARTY"]
    fat_positions = [i for i, c in enumerate(cols) if c in person_cols][:4]
    inj_positions = [i for i, c in enumerate(cols) if c in person_cols][4:8]

    new_cols = cols.copy()
    for pos, base in zip(fat_positions, person_cols):
        new_cols[pos] = f"FATALITY_{base.replace(' ', '_')}"
    for pos, base in zip(inj_positions, person_cols):
        new_cols[pos] = f"INJURY_{base.replace(' ', '_')}"
    df.columns = new_cols

    # ---- clean obvious placeholder/blank tokens across text columns ----
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    for c in text_cols:
        df[c] = _clean_str_series(df[c])

    # ---- parse dates & times ----
    df["INCIDENT_DATE_PARSED"] = pd.to_datetime(
        df.get("INCIDENT DATE"), format="%d-%m-%Y", errors="coerce"
    )
    df["INCIDENT_TIME_PARSED"] = pd.to_datetime(
        df.get("INCIDENT TIME"), format="%H:%M", errors="coerce"
    )
    df["FIR_SUBMITTED_PARSED"] = pd.to_datetime(
        df.get("FIR SUBMITTED TIME"), format="%d-%m-%Y %H:%M:%S", errors="coerce"
    )

    # ---- derived dimensions used across charts ----
    df["FINANCIAL_YEAR"] = df["INCIDENT_DATE_PARSED"].apply(_financial_year_label)
    df["MONTH_NAME"] = df["INCIDENT_DATE_PARSED"].dt.month_name()
    df["WEEKDAY_NAME"] = df["INCIDENT_DATE_PARSED"].dt.day_name()
    df["DAY_OF_MONTH"] = df["INCIDENT_DATE_PARSED"].dt.day
    df["TIME_BUCKET"] = df["INCIDENT_TIME_PARSED"].apply(_time_bucket)
    df["FIR_TURNAROUND_DAYS"] = (
        df["FIR_SUBMITTED_PARSED"] - df["INCIDENT_DATE_PARSED"]
    ).dt.total_seconds() / 86400.0

    # ---- numeric fatality/injury totals ----
    for c in FATALITY_COLS + INJURY_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        else:
            df[c] = 0
    df["FATALITIES_TOTAL"] = df[FATALITY_COLS].sum(axis=1)
    df["INJURIES_TOTAL"] = df[INJURY_COLS].sum(axis=1)
    df["IS_INCIDENT"] = 1  # every row is one incident, for count-based charts

    # ---- normalize a few known-messy categorical fields ----
    for c in ["REGION", "STATE", "TERRITORY", "LOCATION", "CONSUMER TYPE",
              "DIR STATUS", "FIR STATUS"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().str.upper().replace("NAN", np.nan)

    # Root causes (up to 3 per row) -> long format handled in charts.py
    for c in ["ROOT CAUSE-1", "ROOT-CAUSE-2", "ROOT-CAUSE-3"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().replace("nan", np.nan)

    # Stable unique key for de-dup / upsert into the database
    if "FIR NUMBER" not in df.columns:
        raise ValueError("Expected column 'FIR NUMBER' not found in uploaded file.")
    df["FIR NUMBER"] = df["FIR NUMBER"].astype(str).str.strip()

    return df


def load_and_clean(file) -> pd.DataFrame:
    """Convenience wrapper: raw upload -> clean, analysis-ready DataFrame."""
    raw = load_raw_excel(file)
    return clean_and_normalize(raw)
