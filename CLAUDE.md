# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a modern Streamlit-based web dashboard for LPG CP (Compressed Petroleum) in-transit incidents. The project was rebuilt from scratch to replace three overlapping prior attempts with a clean, single project that explicitly reproduces every chart category from Book1.xlsx.

## Project Structure

- **`app.py`**: Main Flask entrypoint for Vercel deployment, with a separate Streamlit rendering function for local development
- **`data_loader.py`**: Single source of truth for parsing raw Excel data, cleaning placeholder tokens, parsing dates/times, and deriving all needed fields
- **`database.py`**: Persistent SQLite storage keyed by "FIR NUMBER" for multi-year history accumulation
- **`charts.py`**: One aggregation function + one Plotly figure per Book1 chart category with clear column mapping
- **`excel_export.py`**: Builds downloadable Excel with native openpyxl charts matching Book1's chart types (Line, Bar, Bar3D, Pie3D)
- **`tests/`**: pytest-based test suite covering dashboard export and database operations
- **`Demo_Retail_Intransit_Dataset_2015_2025.xlsx`**: Source data file
- **`incident_data.db`**: Persistent SQLite database (included in .gitignore)

## Development Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Development Workflow

**Local Development (Streamlit)**:
```bash
streamlit run app.py
```

**Testing**:
```bash
pytest tests/
```

**Vercel Deployment**:
```bash
# When deploying to Vercel, the Flask app in app.py handles requests automatically
```

### 3. Running Tests
```bash
pytest
```

All tests are in `tests/test_dashboard_export_and_database.py`:
- `test_app_exports_a_vercel_compatible_wsgi_app`: Tests the Flask/Werkzeug test client
- `test_delete_all_data_removes_saved_records`: Tests data persistence
- `test_summary_stats_handles_missing_nested_db_directory`: Tests error handling for missing directories
- `test_excel_report_has_summary_and_chart_tables`: Tests Excel report generation
- `test_custom_chart_data_supports_metric_and_grouping`: Tests custom chart functionality

## Key Features

1. **Multi-year Data Accumulation**: Database stores data by FIR NUMBER, adding to history instead of overwriting
2. **Real-time Upload**: Upload Excel files via sidebar to populate the dashboard
3. **13 Chart Categories**: Covers all Book1 chart types plus custom chart builder
4. **Dual Mode**: Works as Vercel-compatible Flask app OR local Streamlit dashboard
5. **Native Excel Export**: Downloads Excel with actual openpyxl chart objects
6. **Clean Data Architecture**: Single source of truth in `data_loader.py` for all raw Excel parsing

## Architecture Decisions

### Data Flow
1. **Raw Upload** → `load_and_clean()` in `data_loader.py` (single source of truth for Excel layout)
2. **Database Storage** → `upsert_dataframe()` in `database.py` (deduplicates by FIR NUMBER)
3. **Dashboard Display** → `render_dashboard()` in `app.py` (Streamlit mode) OR `_dashboard_html()` (Vercel)
4. **Excel Export** → `build_workbook()` in `excel_export.py` (uses same chart data as dashboard)

### Chart Generation Strategy
- Each chart category has exactly one aggregation function (returns pandas DataFrame) + one visualization function
- `charts.py` contains 13 chart modules, each with consistent naming: `chart_function_name()` returns figure
- `excel_export.py` imports the same aggregation functions to build native Excel charts, ensuring data consistency
- Custom chart builder allows users to create ad-hoc charts with any metric and grouping

### Dual-Mode Architecture
- `app.py` uses Flask for Vercel compatibility
- `render_dashboard()` is called only in local development (`__name__ == "__main__"` and not in Vercel)
- This ensures both deployment environments work without modification

## Development Best Practices

### File Organization
- Each major module (`data_loader.py`, `database.py`, `charts.py`, `excel_export.py`) has a single responsibility
- `charts.py` enforces consistency: one aggregation function per chart + visualization function
- Use `import module as <alias>` for circular import avoidance (e.g., `import charts as ch`)

### Data Consistency
- All charts in `charts.py` and `excel_export.py` use the same aggregation functions
- This guarantees dashboard and Excel export always show the same data
- No data duplication: Streamlit app reads from database, Excel builder reads from same data

### Error Handling
- Graceful degradation: Missing data results in clear warnings/messages, not crashes
- Database errors: Silent fallback to empty state (e.g., missing database creates empty DataFrame)
- Upload errors: Display user-friendly error messages in Streamlit interface

### Performance Considerations
- Database uses unique index on "FIR NUMBER" for deduplication
- Streamlit session state only stores UI configuration, not data
- Excel generation: Uses pandas DataFrame operations efficiently

## File-Specific Patterns

### data_loader.py
- Single responsibility: Parse raw Excel format into clean DataFrame
- Uses `pd.read_excel(file, header=1)` for two-row headers (row 1 merged groups, row 2 actual column names)
- Handles placeholder tokens: `NULL_TOKENS` for cleaning text columns
- Derives all needed fields: financial year, month, weekday, time bucket, etc.

### charts.py
- Pattern: `function_name(df)` returns DataFrame + `fig_function_name(tbl)` returns Plotly figure
- All aggregation functions use `.groupby()` and `.agg()` with consistent column naming
- Custom chart builder: `build_custom_chart_data()` + `build_custom_chart()` for ad-hoc visualizations

### database.py
- Persistent SQLite with deduplication by "FIR NUMBER"
- Flexible schema: creates table on first insertion if it doesn't exist
- Directory creation on demand via `_resolve_db_path()`

### excel_export.py
- Uses `openpyxl` for native Excel charts (not images)
- Reuses same aggregation functions from `charts.py` to ensure data consistency
- One sheet per chart category, matching Book1's chart types exactly

## Common Development Tasks

### Adding a New Chart Category
1. **Identify chart type**: Determine if it's a new aggregation + visualization pair
2. **Add to charts.py**: Create `function_name(df)` aggregation + `fig_function_name(tbl)` visualization
3. **Update excel_export.py**: Add sheet creation and chart building using same aggregation
4. **Update app.py**: Add tab to the Streamlit UI in `render_dashboard()`

### Fixing Data Issues
- Problem with Excel parsing? Check `load_raw_excel()` and `_clean_str_series()`
- Missing columns in charts? Verify `data_loader.py` creates all necessary derived fields
- Date/time issues? Check `_financial_year_label()` and `_time_bucket()`

### Performance Optimization
- Profile slow operations with Streamlit's built-in profiling
- Consider database indexing for large datasets
- Excel generation can be memory-intensive for large datasets

### Bug Fixes
- Most bugs manifest as "no data shown" or empty charts
- Check: data uploaded successfully → database populated → dashboard fetches data
- Fix upstream first (data loading), then downstream (charts), then UI

## Testing Strategy

### Current Tests
All tests focus on:
- Core functionality verification
- Data persistence across sessions
- Excel export correctness
- Error handling for edge cases

### Testing Recommendations
- Add unit tests for individual functions in `data_loader.py` (parsing, cleaning, derivation)
- Add integration tests for multi-file upload scenarios
- Add performance tests for large dataset handling
- Test both Streamlit and Vercel modes independently

## Technical Details

### Dependencies
- streamlit>=1.30: Web framework
- pandas>=2.0: Data manipulation
- openpyxl>=3.1: Excel generation
- plotly>=5.18: Charting
- Flask>=3.1: Vercel compatibility
- gunicorn>=22.0: Production WSGI server

### Known Data Gaps
The `Retail_Intransit_Dataset.xlsx` only covers tank-lorry-in-transit accidents:
- **Type of Consumer**: No `CONSUMER TYPE` values in this dataset
- **Zone wise classification**: No `ZONE` column at all
- **Multi-year Trends**: Only contains FY 2024-25 data initially

These are data limitations, not bugs. The code handles missing data gracefully.

## Deployment

### Local Development
```bash
streamlit run app.py
```

### Vercel Deployment
```bash
# The Flask app in app.py is already Vercel-compatible
# Deploy the repository to Vercel, it will work out of the box
```

## Future Improvements

1. **Multi-user support**: Add authentication/authorization
2. **Real-time updates**: WebSocket support for live data updates
3. **Advanced analytics**: Time-series analysis, anomaly detection
4. **Mobile app**: Native iOS/Android app
5. **API layer**: RESTful API for programmatic access
6. **More data sources**: Integrate additional incident datasets
7. **Automated reporting**: Scheduled email/SMS reports
8. **Dashboard customization**: User-defined widgets and layouts

## Attribution

When creating git commits and pull requests, end commit messages with:
```
Co-Authored-By: Claude Code <noreply@anthropic.com>
```

End pull request descriptions with:
```
🤖 Generated with [Claude Code](https://claude.com/claude-code)
```