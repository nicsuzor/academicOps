---
title: Google BigQuery
type: reference
permalink: python-dev-bigquery
description: Python client reference for Google BigQuery data warehouse operations
---

# Google BigQuery

## Overview

Google BigQuery is a serverless, highly scalable data warehouse with built-in ML capabilities. The Python client library provides programmatic access for querying, loading, and managing data.

## Installation

```bash
uv add google-cloud-bigquery google-cloud-bigquery-storage pandas db-dtypes
```

## Authentication

```python
from google.cloud import bigquery
from google.oauth2 import service_account

# Option 1: Use application default credentials
client = bigquery.Client()

# Option 2: Use service account key
credentials = service_account.Credentials.from_service_account_file(
    'path/to/service-account-key.json'
)
client = bigquery.Client(credentials=credentials, project='project-id')
```

## Querying Data

```python
# Basic query
query = """
    SELECT name, COUNT(*) as count
    FROM `project.dataset.table`
    WHERE date >= '2024-01-01'
    GROUP BY name
    ORDER BY count DESC
    LIMIT 10
"""

query_job = client.query(query)
results = query_job.result()  # Wait for completion

for row in results:
    print(f"{row.name}: {row.count}")

# Query to DataFrame
import pandas as pd

df = query_job.to_dataframe()
```

## Parameterized Queries

```python
from google.cloud.bigquery import ScalarQueryParameter

query = """
    SELECT *
    FROM `project.dataset.table`
    WHERE date = @target_date
    AND category = @category
"""

job_config = bigquery.QueryJobConfig(
    query_parameters=[
        ScalarQueryParameter("target_date", "DATE", "2024-01-01"),
        ScalarQueryParameter("category", "STRING", "sales")
    ]
)

query_job = client.query(query, job_config=job_config)
df = query_job.to_dataframe()
```

## Loading Data

```python
# From DataFrame
table_id = "project.dataset.table"

job = client.load_table_from_dataframe(df, table_id)
job.result()  # Wait for completion

# From CSV
job_config = bigquery.LoadJobConfig(
    source_format=bigquery.SourceFormat.CSV,
    skip_leading_rows=1,
    autodetect=True,
)

with open("data.csv", "rb") as source_file:
    job = client.load_table_from_file(source_file, table_id, job_config=job_config)

job.result()

# From JSON
job_config = bigquery.LoadJobConfig(
    source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    autodetect=True,
)

with open("data.jsonl", "rb") as source_file:
    job = client.load_table_from_file(source_file, table_id, job_config=job_config)
```

## Table Management

```python
from google.cloud.bigquery import Table, SchemaField

# Create table
schema = [
    SchemaField("name", "STRING", mode="REQUIRED"),
    SchemaField("age", "INTEGER", mode="NULLABLE"),
    SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
]

table = bigquery.Table(table_id, schema=schema)
table = client.create_table(table)

# Get table
table = client.get_table(table_id)
print(f"Table {table.table_id} has {table.num_rows} rows")

# Delete table
client.delete_table(table_id)

# List tables
tables = client.list_tables("project.dataset")
for table in tables:
    print(table.table_id)
```

## Best Practices

```python
# ✅ Use batch queries for multiple operations
query_job = client.query(
    query,
    job_config=bigquery.QueryJobConfig(
        write_disposition="WRITE_TRUNCATE",  # Overwrite
        create_disposition="CREATE_IF_NEEDED"
    )
)

# ✅ Use partitioned tables for large datasets
job_config = bigquery.LoadJobConfig(
    time_partitioning=bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field="date",
    )
)

# ✅ Use clustering for query optimization
job_config = bigquery.LoadJobConfig(
    clustering_fields=["category", "region"]
)

# ✅ Estimate costs before running
job_config = bigquery.QueryJobConfig(dry_run=True)
query_job = client.query(query, job_config=job_config)
print(f"This query will process {query_job.total_bytes_processed} bytes")
```

## Resources

- Docs: https://cloud.google.com/bigquery/docs
- Python Client: https://cloud.google.com/python/docs/reference/bigquery/latest
