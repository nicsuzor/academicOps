---
title: Pandas
type: reference
category: ref
permalink: python-dev-pandas
description: Data manipulation and analysis library reference
---

# Pandas

## Overview

Pandas is the foundational library for data manipulation and analysis in Python. It provides high-performance, easy-to-use data structures (DataFrame and Series) and data analysis tools for working with structured data.

## When to Use

- Loading and saving data (CSV, Excel, SQL, JSON, Parquet, etc.)
- Data cleaning and preprocessing
- Filtering, selecting, and transforming data
- Aggregating and summarizing data
- Time series analysis
- Merging and joining datasets
- Reshaping data (pivot, melt, stack/unstack)
- Handling missing data

## Core Data Structures

### Series (1-dimensional)

```python
import pandas as pd
import numpy as np

# Create Series
s = pd.Series([1, 3, 5, np.nan, 6, 8])
s = pd.Series({'a': 1, 'b': 2, 'c': 3})  # From dict
s = pd.Series([1, 2, 3], index=['a', 'b', 'c'])  # With custom index

# Access data
s[0]  # By position
s['a']  # By label
s.iloc[0]  # Explicit positional
s.loc['a']  # Explicit label-based
```

### DataFrame (2-dimensional)

```python
# Create DataFrame
df = pd.DataFrame({
    'A': [1, 2, 3, 4],
    'B': ['a', 'b', 'c', 'd'],
    'C': [1.1, 2.2, 3.3, 4.4]
})

# From list of dicts
df = pd.DataFrame([
    {'A': 1, 'B': 'a'},
    {'A': 2, 'B': 'b'}
])

# From numpy array
df = pd.DataFrame(
    np.random.randn(4, 3),
    columns=['A', 'B', 'C']
)
```

## Data Loading

### Read from Files

```python
# CSV
df = pd.read_csv('data.csv')
df = pd.read_csv('data.csv', sep='\t', encoding='utf-8')
df = pd.read_csv('data.csv', parse_dates=['date_column'])

# Excel
df = pd.read_excel('data.xlsx', sheet_name='Sheet1')

# JSON
df = pd.read_json('data.json')
df = pd.read_json('data.json', orient='records')

# Parquet (fast, compressed)
df = pd.read_parquet('data.parquet')

# SQL
import sqlalchemy
engine = sqlalchemy.create_engine('postgresql://...')
df = pd.read_sql('SELECT * FROM table', engine)
df = pd.read_sql_table('table_name', engine)
```

### Write to Files

```python
# CSV
df.to_csv('output.csv', index=False)

# Excel
df.to_excel('output.xlsx', sheet_name='Data', index=False)

# JSON
df.to_json('output.json', orient='records')

# Parquet
df.to_parquet('output.parquet', compression='snappy')

# SQL
df.to_sql('table_name', engine, if_exists='replace', index=False)
```

## Data Inspection

```python
# View data
df.head()  # First 5 rows
df.head(10)  # First 10 rows
df.tail()  # Last 5 rows
df.sample(5)  # Random 5 rows

# Shape and info
df.shape  # (rows, columns)
df.info()  # Column types and non-null counts
df.describe()  # Summary statistics
df.dtypes  # Column data types

# Column/index info
df.columns  # Column names
df.index  # Row index
df.memory_usage()  # Memory usage per column
```

## Selection and Filtering

### Column Selection

```python
# Single column (returns Series)
df['A']
df.A  # If column name is valid Python identifier

# Multiple columns (returns DataFrame)
df[['A', 'B']]

# Column operations
df.columns.tolist()  # Get column names as list
df.select_dtypes(include=['number'])  # Select numeric columns
df.select_dtypes(exclude=['object'])  # Exclude string columns
```

### Row Selection

```python
# By position (iloc)
df.iloc[0]  # First row
df.iloc[0:5]  # First 5 rows
df.iloc[[0, 2, 4]]  # Specific rows
df.iloc[0:5, 0:3]  # Rows 0-4, columns 0-2

# By label (loc)
df.loc[0]  # Row with index label 0
df.loc[0:5]  # Rows 0 through 5 (inclusive!)
df.loc[[0, 2, 4]]  # Specific row labels
df.loc[0:5, ['A', 'B']]  # Rows 0-5, columns A and B
```

### Boolean Indexing

```python
# Filter rows
df[df['A'] > 2]  # Rows where A > 2
df[df['B'] == 'a']  # Rows where B equals 'a'

# Multiple conditions (use & and |, not 'and'/'or')
df[(df['A'] > 1) & (df['B'] == 'a')]
df[(df['A'] > 3) | (df['B'] == 'd')]

# Using query()
df.query('A > 2')
df.query('A > 2 and B == "a"')

# Filter by isin()
df[df['B'].isin(['a', 'b'])]
```

## Data Cleaning

### Missing Data

```python
# Detect missing data
df.isnull()  # Boolean DataFrame
df.isnull().sum()  # Count nulls per column
df.dropna()  # Drop rows with any null
df.dropna(how='all')  # Drop rows where all values are null
df.dropna(subset=['A'])  # Drop rows where A is null

# Fill missing data
df.fillna(0)  # Fill with 0
df.fillna({'A': 0, 'B': 'unknown'})  # Fill different values per column
df.fillna(method='ffill')  # Forward fill
df.fillna(method='bfill')  # Backward fill
df['A'].fillna(df['A'].mean())  # Fill with column mean
```

### Duplicates

```python
# Detect duplicates
df.duplicated()  # Boolean Series
df.duplicated().sum()  # Count duplicates
df[df.duplicated()]  # View duplicate rows

# Remove duplicates
df.drop_duplicates()  # Keep first occurrence
df.drop_duplicates(subset=['A'])  # Based on specific columns
df.drop_duplicates(keep='last')  # Keep last occurrence
```

### Data Type Conversion

```python
# Convert types
df['A'] = df['A'].astype(int)
df['B'] = df['B'].astype(str)
df['C'] = df['C'].astype('category')  # For categorical data

# Parse dates
df['date'] = pd.to_datetime(df['date'])
df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')

# Numeric conversion (coerce errors to NaN)
df['A'] = pd.to_numeric(df['A'], errors='coerce')
```

## Data Transformation

### Apply Functions

```python
# Apply to column (Series)
df['A'].apply(lambda x: x * 2)
df['A'].apply(np.sqrt)

# Apply to DataFrame
df.apply(lambda col: col.max(), axis=0)  # Apply to each column
df.apply(lambda row: row['A'] + row['B'], axis=1)  # Apply to each row

# Vectorized operations (preferred when possible)
df['A'] * 2  # Faster than apply
df['A'] + df['B']
```

### String Operations

```python
# String methods (on Series with .str accessor)
df['B'].str.upper()
df['B'].str.lower()
df['B'].str.contains('pattern')
df['B'].str.replace('old', 'new')
df['B'].str.split(',')  # Returns list
df['B'].str.strip()  # Remove whitespace
df['B'].str.len()  # String length

# Regex
df['B'].str.extract(r'(\d+)')  # Extract numbers
df['B'].str.match(r'pattern')  # Boolean match
```

### Date/Time Operations

```python
# DateTime accessor
df['date'].dt.year
df['date'].dt.month
df['date'].dt.day
df['date'].dt.dayofweek
df['date'].dt.hour

# Date arithmetic
df['date'] + pd.Timedelta(days=1)
df['date_end'] - df['date_start']

# Resampling time series
df.set_index('date').resample('D').mean()  # Daily mean
df.set_index('date').resample('W').sum()  # Weekly sum
df.set_index('date').resample('M').agg({'A': 'sum', 'B': 'mean'})
```

## Aggregation and Grouping

### GroupBy

```python
# Basic groupby
df.groupby('A').sum()
df.groupby('A').mean()
df.groupby('A').count()

# Multiple groups
df.groupby(['A', 'B']).sum()

# Aggregation functions
df.groupby('A').agg({
    'B': 'count',
    'C': 'mean',
    'D': 'sum'
})

# Multiple aggregations
df.groupby('A').agg({
    'B': ['count', 'nunique'],
    'C': ['mean', 'std']
})

# Custom aggregation
df.groupby('A').agg(lambda x: x.max() - x.min())

# Filter groups
df.groupby('A').filter(lambda x: len(x) > 2)
```

### Pivot Tables

```python
# Create pivot table
pd.pivot_table(
    df,
    values='C',
    index='A',
    columns='B',
    aggfunc='mean'
)

# Multiple aggregations
pd.pivot_table(
    df,
    values='C',
    index='A',
    columns='B',
    aggfunc=['mean', 'sum', 'count']
)
```

## Merging and Joining

### Concatenation

```python
# Vertical concatenation (stack rows)
pd.concat([df1, df2])
pd.concat([df1, df2], ignore_index=True)

# Horizontal concatenation (side-by-side)
pd.concat([df1, df2], axis=1)
```

### Merge (SQL-style joins)

```python
# Inner join (default)
pd.merge(df1, df2, on='key')

# Left join
pd.merge(df1, df2, on='key', how='left')

# Outer join
pd.merge(df1, df2, on='key', how='outer')

# Multiple keys
pd.merge(df1, df2, on=['key1', 'key2'])

# Different column names
pd.merge(df1, df2, left_on='key_a', right_on='key_b')

# Merge on index
pd.merge(df1, df2, left_index=True, right_index=True)
```

## Reshaping

### Pivot and Melt

```python
# Pivot (long to wide)
df.pivot(index='row_id', columns='variable', values='value')

# Melt (wide to long)
pd.melt(
    df,
    id_vars=['id'],
    value_vars=['col1', 'col2'],
    var_name='variable',
    value_name='value'
)
```

### Stack and Unstack

```python
# Stack (columns to rows)
df.stack()

# Unstack (rows to columns)
df.unstack()
```

## Best Practices

### Performance

```python
# ✅ Use vectorized operations
df['C'] = df['A'] + df['B']  # Fast

# ❌ Avoid iterating rows
for idx, row in df.iterrows():  # Slow
    df.at[idx, 'C'] = row['A'] + row['B']

# ✅ Use categorical for repeated string values
df['category'] = df['category'].astype('category')

# ✅ Read only needed columns
df = pd.read_csv('data.csv', usecols=['A', 'B'])

# ✅ Use chunking for large files
for chunk in pd.read_csv('large.csv', chunksize=10000):
    process(chunk)
```

### Memory Optimization

```python
# Optimize dtypes
df['int_col'] = df['int_col'].astype('int32')  # vs int64
df['float_col'] = df['float_col'].astype('float32')  # vs float64

# Use categories for low-cardinality strings
df['status'] = df['status'].astype('category')

# Check memory usage
df.memory_usage(deep=True)
```

### Chain Operations

```python
# ✅ Method chaining
result = (
    df
    .query('A > 2')
    .groupby('B')
    .agg({'C': 'mean'})
    .reset_index()
    .sort_values('C', ascending=False)
)

# ✅ Use .pipe() for custom functions
def custom_transform(df):
    return df[df['A'] > 0]

result = df.pipe(custom_transform)
```

## Common Patterns

### Data Validation

```python
# Check for nulls
assert df.isnull().sum().sum() == 0, "DataFrame contains nulls"

# Check data types
assert df['A'].dtype == 'int64', "Column A should be int64"

# Check value ranges
assert df['score'].between(0, 100).all(), "Scores out of range"

# Check for duplicates
assert not df.duplicated().any(), "DataFrame contains duplicates"
```

### Conditional Operations

```python
# np.where (vectorized if-else)
df['category'] = np.where(df['A'] > 10, 'high', 'low')

# Multiple conditions
df['category'] = np.select(
    [df['A'] < 5, df['A'] < 10, df['A'] >= 10],
    ['low', 'medium', 'high']
)

# Using .loc for conditional assignment
df.loc[df['A'] > 10, 'category'] = 'high'
```

## Integration with Other Tools

### NumPy

```python
# Convert to numpy
df.values  # 2D numpy array
df['A'].values  # 1D numpy array

# From numpy
df = pd.DataFrame(np.random.randn(10, 3), columns=['A', 'B', 'C'])
```

### Matplotlib/Seaborn

```python
# Built-in plotting
df.plot(kind='line', x='date', y='value')
df.plot(kind='bar')
df.plot(kind='hist', bins=20)
df['A'].plot(kind='kde')

# Direct integration
import matplotlib.pyplot as plt
df.plot()
plt.show()
```

## Key Principles

1. **Use vectorized operations** - Avoid row-by-row iteration
2. **Chain methods** - More readable and memory-efficient
3. **Optimize dtypes** - Use appropriate data types to save memory
4. **Handle missing data explicitly** - Don't let NaN propagate silently
5. **Use categorical for low-cardinality strings** - Saves memory and improves performance
6. **Profile before optimizing** - Use `df.memory_usage()` and timing tools
7. **Prefer .loc and .iloc** - Explicit is better than implicit
8. **Validate data** - Check assumptions about your data

## Resources

- Official docs: https://pandas.pydata.org/docs/
- 10 minute intro: https://pandas.pydata.org/docs/user_guide/10min.html
- Cheat sheet: https://pandas.pydata.org/Pandas_Cheat_Sheet.pdf
