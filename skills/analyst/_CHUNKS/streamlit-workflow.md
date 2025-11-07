# Streamlit Visualization Workflow

Create Streamlit visualizations following single-step collaborative pattern.

## Streamlit Structure

Standard Streamlit app structure for academicOps projects:

```python
import streamlit as st
import duckdb
import plotly.express as px

# Page config
st.set_page_config(page_title="Project Analysis", layout="wide")


# Data loading (cached)
@st.cache_data
def load_data():
    conn = duckdb.connect("data/warehouse.db")
    return conn.execute("SELECT * FROM fct_cases").df()


# Main app
def main():
    st.title("Case Analysis Dashboard")

    df = load_data()

    # Filters in sidebar
    with st.sidebar:
        st.header("Filters")
        status_filter = st.multiselect("Status", df["status"].unique())

    # Apply filters
    if status_filter:
        df = df[df["status"].isin(status_filter)]

    # Visualizations
    st.header("Overview Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Cases", len(df))
    col2.metric("Avg Processing Days", df["processing_days"].mean().round(1))
    col3.metric("Completion Rate", f"{(df['status'] == 'published').mean():.1%}")

    # Chart
    fig = px.histogram(df, x="processing_days", title="Processing Time Distribution")
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
```

## Follow Single-Step Visualization Workflow

**Step 1: Load data from dbt model**

```python
import streamlit as st
import duckdb


@st.cache_data
def load_data():
    conn = duckdb.connect("data/warehouse.db")
    return conn.execute("SELECT * FROM fct_cases").df()


df = load_data()
st.dataframe(df.head())
```

**STOP. Show to user. Confirm data is correct.**

**Step 2: Create single chart** (only after user confirms data)

```python
import plotly.express as px

fig = px.histogram(df, x="processing_days", title="Processing Time Distribution")
st.plotly_chart(fig, use_container_width=True)
```

**STOP. Show to user. Get feedback on chart.**

**Step 3: Add interactivity** (only after user approves chart)

```python
with st.sidebar:
    status_filter = st.multiselect("Status", df["status"].unique())

if status_filter:
    df = df[df["status"].isin(status_filter)]
```

**STOP. Show to user. Confirm filter works as expected.**

**Continue this pattern:** One change at a time, user feedback, then proceed.

## Additional Resources

See `references/streamlit-patterns.md` for comprehensive visualization best practices, including:

- Interactive components (filters, selections)
- Visualization libraries (Plotly, Altair)
- Layout patterns (columns, tabs, expanders)
- Performance optimization
- State management
