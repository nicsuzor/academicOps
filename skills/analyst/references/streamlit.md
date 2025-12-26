---
title: Streamlit
type: reference
permalink: skills-analyst-streamlit
description: Best practices and design patterns for building Streamlit dashboards for research data analysis
tags: [streamlit, dashboard, visualization, reference]
---

# Streamlit Patterns Reference

Best practices for building Streamlit dashboards in academicOps research projects.

## Standard App Structure

### Basic Template

```python
import streamlit as st
import duckdb
import plotly.express as px
import pandas as pd

# Page configuration (must be first Streamlit command)
st.set_page_config(
    page_title="Project Analysis",
    page_icon="📊",
    layout="wide",  # or "centered"
    initial_sidebar_state="expanded",
)


# Data loading with caching
@st.cache_data
def load_data():
    """Load data from dbt warehouse"""
    conn = duckdb.connect("data/warehouse.db")
    return conn.execute("SELECT * FROM fct_cases").df()


# Helper functions
@st.cache_data
def compute_metrics(df):
    """Compute summary metrics"""
    return {
        "total": len(df),
        "avg_processing": df["processing_days"].mean(),
        "completion_rate": (df["status"] == "published").mean(),
    }


# Main application
def main():
    st.title("Case Analysis Dashboard")
    st.markdown("Exploring case processing patterns and outcomes")

    # Load data
    df = load_data()

    # Sidebar filters
    with st.sidebar:
        st.header("Filters")
        status_filter = st.multiselect(
            "Status", options=df["status"].unique(), default=df["status"].unique()
        )
        date_range = st.date_input(
            "Date Range",
            value=(df["submission_date"].min(), df["submission_date"].max()),
        )

    # Apply filters
    filtered_df = df[
        (df["status"].isin(status_filter))
        & (df["submission_date"].between(date_range[0], date_range[1]))
    ]

    # Metrics
    st.header("Overview Metrics")
    col1, col2, col3 = st.columns(3)
    metrics = compute_metrics(filtered_df)
    col1.metric("Total Cases", f"{metrics['total']:,}")
    col2.metric("Avg Processing Days", f"{metrics['avg_processing']:.1f}")
    col3.metric("Completion Rate", f"{metrics['completion_rate']:.1%}")

    # Visualizations
    st.header("Analysis")

    # Chart 1
    fig = px.histogram(
        filtered_df, x="processing_days", title="Processing Time Distribution", nbins=30
    )
    st.plotly_chart(fig, use_container_width=True)

    # Chart 2
    fig2 = px.box(
        filtered_df, x="status", y="processing_days", title="Processing Days by Status"
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Data table
    with st.expander("View Raw Data"):
        st.dataframe(filtered_df, use_container_width=True)


if __name__ == "__main__":
    main()
```

## Data Loading and Caching

### DuckDB Connection

```python
import duckdb


@st.cache_data
def load_data():
    """Load data from dbt warehouse"""
    conn = duckdb.connect("data/warehouse.db", read_only=True)
    query = """
        SELECT
            case_id,
            submission_date,
            decision_date,
            status,
            processing_days
        FROM fct_case_decisions
    """
    return conn.execute(query).df()
```

**Key points:**

- Use `@st.cache_data` to avoid reloading on every interaction
- Use `read_only=True` for safety
- Query dbt marts, never upstream sources
- Return pandas DataFrame for compatibility

### Multiple Data Sources

```python
@st.cache_data
def load_cases():
    conn = duckdb.connect("data/warehouse.db", read_only=True)
    return conn.execute("SELECT * FROM fct_case_decisions").df()


@st.cache_data
def load_jurisdictions():
    conn = duckdb.connect("data/warehouse.db", read_only=True)
    return conn.execute("SELECT * FROM dim_jurisdictions").df()


# In main():
cases = load_cases()
jurisdictions = load_jurisdictions()
merged = cases.merge(jurisdictions, on="jurisdiction_id")
```

### Cache Control

```python
# Cache expires after 1 hour
@st.cache_data(ttl=3600)
def load_data(): ...


# Don't cache (for debugging)
# @st.cache_data  # commented out
def load_data(): ...


# Clear cache button
if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()
```

## Layout Patterns

### Columns

```python
# Equal width columns
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Metric 1", value)
with col2:
    st.metric("Metric 2", value)
with col3:
    st.metric("Metric 3", value)

# Custom width ratios
col1, col2 = st.columns([2, 1])  # 2:1 ratio
with col1:
    st.plotly_chart(fig)
with col2:
    st.markdown("Explanation...")
```

### Tabs

```python
tab1, tab2, tab3 = st.tabs(["Overview", "Trends", "Details"])

with tab1:
    st.header("Overview")
    # Overview content

with tab2:
    st.header("Trends")
    # Trends charts

with tab3:
    st.header("Details")
    # Detailed tables
```

### Expanders

```python
with st.expander("View Raw Data"):
    st.dataframe(df)

with st.expander("Methodology"):
    st.markdown("""
    This analysis uses...
    """)
```

### Sidebar

```python
with st.sidebar:
    st.header("Filters")

    # Filters
    status = st.multiselect("Status", options)
    date_range = st.date_input("Date Range", value)

    # Controls
    st.divider()
    if st.button("Reset Filters"):
        st.rerun()
```

## Interactive Components

### Filters

```python
# Multiselect
status_filter = st.multiselect(
    "Status",
    options=df["status"].unique(),
    default=df["status"].unique(),  # All selected by default
    help="Select one or more statuses to filter",
)

# Selectbox (single selection)
jurisdiction = st.selectbox(
    "Jurisdiction",
    options=df["jurisdiction"].unique(),
    index=0,  # Default to first
)

# Slider
processing_days = st.slider(
    "Processing Days",
    min_value=int(df["processing_days"].min()),
    max_value=int(df["processing_days"].max()),
    value=(0, 100),  # Range slider
    step=1,
)

# Date input
date_range = st.date_input(
    "Date Range",
    value=(df["submission_date"].min(), df["submission_date"].max()),
    help="Select start and end dates",
)

# Text input
search = st.text_input("Search decision text", "")
```

### Applying Filters

```python
# Boolean indexing
filtered_df = df[
    (df["status"].isin(status_filter))
    & (df["processing_days"].between(processing_days[0], processing_days[1]))
    & (df["submission_date"].between(date_range[0], date_range[1]))
]

# Text search
if search:
    filtered_df = filtered_df[
        filtered_df["decision_text"].str.contains(search, case=False, na=False)
    ]
```

### Buttons and Actions

```python
# Simple button
if st.button("Run Analysis"):
    result = perform_analysis(df)
    st.write(result)

# Button with state
if "analysis_run" not in st.session_state:
    st.session_state.analysis_run = False

if st.button("Run Analysis"):
    st.session_state.analysis_run = True

if st.session_state.analysis_run:
    st.success("Analysis completed!")
```

### Form (batch inputs)

```python
with st.form("filter_form"):
    st.write("Configure Filters")

    status = st.multiselect("Status", options)
    date_range = st.date_input("Date Range", value)

    submitted = st.form_submit_button("Apply Filters")

    if submitted:
        # Process filters
        filtered_df = apply_filters(df, status, date_range)
        st.write(f"Showing {len(filtered_df)} records")
```

## Visualization Libraries

### Plotly (Recommended)

```python
import plotly.express as px
import plotly.graph_objects as go

# Histogram
fig = px.histogram(
    df,
    x="processing_days",
    title="Processing Time Distribution",
    nbins=30,
    color="status",
    marginal="box",  # Show distribution summary
)
st.plotly_chart(fig, use_container_width=True)

# Scatter plot
fig = px.scatter(
    df,
    x="submission_date",
    y="processing_days",
    color="status",
    hover_data=["case_id", "jurisdiction"],
    title="Processing Time Over Time",
)
st.plotly_chart(fig, use_container_width=True)

# Box plot
fig = px.box(
    df,
    x="jurisdiction",
    y="processing_days",
    color="status",
    title="Processing Days by Jurisdiction and Status",
)
fig.update_xaxis(tickangle=45)
st.plotly_chart(fig, use_container_width=True)

# Time series
daily_counts = df.groupby("submission_date").size().reset_index(name="count")
fig = px.line(
    daily_counts, x="submission_date", y="count", title="Daily Case Submissions"
)
st.plotly_chart(fig, use_container_width=True)

# Heatmap
pivot = df.pivot_table(
    values="processing_days", index="jurisdiction", columns="status", aggfunc="mean"
)
fig = px.imshow(
    pivot,
    title="Avg Processing Days by Jurisdiction and Status",
    aspect="auto",
    color_continuous_scale="RdYlGn_r",
)
st.plotly_chart(fig, use_container_width=True)
```

**Plotly advantages:**

- Interactive (zoom, pan, hover)
- Professional appearance
- Wide variety of chart types
- Good mobile support

### Altair

```python
import altair as alt

# Basic chart
chart = (
    alt.Chart(df)
    .mark_bar()
    .encode(x="status", y="count()", color="status")
    .properties(title="Cases by Status")
)
st.altair_chart(chart, use_container_width=True)

# Layered chart
base = alt.Chart(df).encode(x="submission_date:T")
line = base.mark_line().encode(y="mean(processing_days):Q")
points = base.mark_point().encode(y="processing_days:Q")
chart = line + points
st.altair_chart(chart, use_container_width=True)
```

### Matplotlib (for compatibility)

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
ax.hist(df["processing_days"], bins=30)
ax.set_xlabel("Processing Days")
ax.set_ylabel("Count")
ax.set_title("Processing Time Distribution")
st.pyplot(fig)
```

## Metrics Display

### Simple Metrics

```python
st.metric(label="Total Cases", value=f"{len(df):,}", delta=f"+{new_cases} this month")
```

### Metrics in Columns

```python
col1, col2, col3 = st.columns(3)

col1.metric("Total Cases", f"{len(df):,}", help="Total number of cases in dataset")

col2.metric(
    "Avg Processing Days",
    f"{df['processing_days'].mean():.1f}",
    delta=f"{df['processing_days'].mean() - benchmark:.1f} vs benchmark",
)

col3.metric(
    "Completion Rate",
    f"{(df['status'] == 'published').mean():.1%}",
    delta=f"{current_rate - last_month_rate:.1%} vs last month",
)
```

### Custom Metric Cards

```python
def metric_card(title, value, description=""):
    st.markdown(
        f"""
    <div style="padding: 1rem; border-radius: 0.5rem; background-color: #f0f2f6;">
        <h3>{title}</h3>
        <h2>{value}</h2>
        <p style="color: #666;">{description}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


metric_card(
    "Processing Time",
    f"{df['processing_days'].mean():.1f} days",
    "Average across all cases",
)
```

## Data Tables

### Basic DataFrame Display

```python
# Simple display
st.dataframe(df)

# With configuration
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "processing_days": st.column_config.NumberColumn(
            "Processing Days", help="Days from submission to decision", format="%d days"
        ),
        "submission_date": st.column_config.DateColumn(
            "Submission Date", format="YYYY-MM-DD"
        ),
    },
)
```

### Interactive Data Table

```python
# Data editor (allows user editing - use carefully!)
edited_df = st.data_editor(
    df,
    use_container_width=True,
    num_rows="dynamic",  # Allow adding rows
)

if edited_df.equals(df):
    st.info("No changes made")
else:
    st.warning("Data has been modified")
    if st.button("Save Changes"):
        # Save logic here
        st.success("Changes saved!")
```

### Styled DataFrames

```python
def highlight_slow(row):
    """Highlight slow processing times"""
    return [
        "background-color: yellow" if row["processing_days"] > 90 else "" for _ in row
    ]


styled_df = df.style.apply(highlight_slow, axis=1)
st.dataframe(styled_df)
```

## State Management

### Session State

```python
# Initialize state
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None

# Store results
if st.button("Run Analysis"):
    results = perform_analysis(df)
    st.session_state.analysis_results = results

# Use stored results
if st.session_state.analysis_results:
    st.write(st.session_state.analysis_results)
```

### Persistent Filters

```python
# Initialize filter state
if "status_filter" not in st.session_state:
    st.session_state.status_filter = df["status"].unique().tolist()

# Use state in filter
status_filter = st.multiselect(
    "Status",
    options=df["status"].unique(),
    default=st.session_state.status_filter,
    key="status_filter",  # Automatically syncs with session_state
)
```

## Performance Tips

### Caching Strategy

```python
# Cache data loading
@st.cache_data
def load_data(): ...


# Cache expensive computations
@st.cache_data
def compute_statistics(df): ...


# Cache ML models
@st.cache_resource
def load_model(): ...
```

### Lazy Loading

```python
# Load data only when needed
if st.button("Load Full Dataset"):
    with st.spinner("Loading data..."):
        df = load_large_dataset()
        st.session_state.df = df

if "df" in st.session_state:
    st.dataframe(st.session_state.df)
```

### Pagination

```python
# Paginate large datasets
page_size = 100
page_number = st.number_input(
    "Page", min_value=1, max_value=(len(df) // page_size) + 1, value=1
)

start_idx = (page_number - 1) * page_size
end_idx = start_idx + page_size

st.dataframe(df.iloc[start_idx:end_idx])
st.caption(f"Showing {start_idx + 1}-{min(end_idx, len(df))} of {len(df)} rows")
```

## Error Handling

### Graceful Errors

```python
try:
    df = load_data()
    if df.empty:
        st.warning("No data available for selected filters")
        st.stop()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Continue with analysis
st.dataframe(df)
```

### Progress Indicators

```python
with st.spinner("Loading data..."):
    df = load_data()

progress_bar = st.progress(0)
for i, item in enumerate(large_list):
    process(item)
    progress_bar.progress((i + 1) / len(large_list))

st.success("Processing complete!")
```

## Multi-Page Apps

### File Structure

```
streamlit/
├── Home.py              # Main entry point
└── pages/
    ├── 1_📊_Overview.py
    ├── 2_📈_Trends.py
    └── 3_📋_Details.py
```

### Page Navigation

```python
# Home.py
import streamlit as st

st.set_page_config(page_title="Case Analysis", page_icon="📊")

st.title("Case Analysis Dashboard")
st.markdown("Use the sidebar to navigate between pages")

# Each page file (e.g., pages/1_📊_Overview.py)
import streamlit as st

st.title("Overview")
# Page content...
```

## Best Practices

1. **Data Loading:**
   - Always cache data loading
   - Query dbt marts, never upstream sources
   - Use read-only database connections

2. **Layout:**
   - Use wide layout for data-heavy apps
   - Group related controls in sidebar
   - Use columns for metrics
   - Use tabs for different views

3. **Interactivity:**
   - Provide sensible defaults for filters
   - Show loading indicators for slow operations
   - Give user feedback on actions

4. **Performance:**
   - Cache expensive computations
   - Paginate large datasets
   - Use `use_container_width=True` for responsive charts

5. **Accessibility:**
   - Add help text to inputs
   - Use descriptive labels
   - Provide context for metrics
   - Include methodology explanations

6. **Self-Documentation:**
   - Add markdown explanations inline
   - Use expanders for detailed methodology
   - Include data source information
   - Document filter logic

