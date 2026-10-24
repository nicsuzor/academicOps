"""Tests for the research pipeline Copier template and lifecycle."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import copier
import duckdb
import pytest

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "research-pipeline"


def test_bigquery_export_parquet_fails_fast_when_no_mart_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BigQuery parquet export raises RuntimeError when no mart tables exist."""
    dest = tmp_path / "bq_no_marts"
    copier.run_copy(
        src_path=str(TEMPLATE_DIR),
        dst_path=str(dest),
        data={
            "project_name": "bq_no_marts_test",
            "project_title": "BQ No Marts Test",
            "sql_engine": "bigquery",
            "bigquery_project": "test-project",
            "bigquery_dataset": "test_dataset",
        },
        defaults=True,
        unsafe=True,
    )

    spec = importlib.util.spec_from_file_location(
        "export_parquet_bq", dest / "scripts" / "export_parquet.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    mock_client = MagicMock()
    mock_query_job = MagicMock()
    mock_query_job.result.return_value = []
    mock_client.query.return_value = mock_query_job

    monkeypatch.setattr("google.cloud.bigquery.Client", lambda **kwargs: mock_client)
    spec.loader.exec_module(module)

    with pytest.raises(
        RuntimeError, match="No mart tables matching 'fct_%' or 'dim_%' found to export."
    ):
        module.export_bigquery_marts()


def test_duckdb_project_dbt_lifecycle_and_parquet_export(tmp_path: Path) -> None:
    """A rendered DuckDB project passes dbt parse, seed, run, test, and exports Parquet."""
    dest = tmp_path / "duckdb_pipeline"
    copier.run_copy(
        src_path=str(TEMPLATE_DIR),
        dst_path=str(dest),
        data={
            "project_name": "lifecycle_test",
            "project_title": "Lifecycle Test",
            "sql_engine": "duckdb",
        },
        defaults=True,
        unsafe=True,
    )

    env = {
        "PATH": sys.executable + ":" + subprocess.os.environ.get("PATH", ""),
        "DBT_PROFILES_DIR": str(dest / "dbt"),
        "DUCKDB_PATH": str(dest / "data" / "local_cache.duckdb"),
    }
    (dest / "data").mkdir(parents=True, exist_ok=True)
    dbt_dir = dest / "dbt"

    # 1. dbt parse
    res_parse = subprocess.run(
        [sys.executable, "-m", "dbt.cli.main", "parse", "--project-dir", str(dbt_dir)],
        cwd=str(dest),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res_parse.returncode == 0, (
        f"dbt parse failed:\nstdout:\n{res_parse.stdout}\nstderr:\n{res_parse.stderr}"
    )

    # 2. dbt seed
    res_seed = subprocess.run(
        [sys.executable, "-m", "dbt.cli.main", "seed", "--project-dir", str(dbt_dir)],
        cwd=str(dest),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res_seed.returncode == 0, (
        f"dbt seed failed:\nstdout:\n{res_seed.stdout}\nstderr:\n{res_seed.stderr}"
    )

    # 3. dbt run
    res_run = subprocess.run(
        [sys.executable, "-m", "dbt.cli.main", "run", "--project-dir", str(dbt_dir)],
        cwd=str(dest),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res_run.returncode == 0, (
        f"dbt run failed:\nstdout:\n{res_run.stdout}\nstderr:\n{res_run.stderr}"
    )

    # 4. dbt test
    res_test = subprocess.run(
        [sys.executable, "-m", "dbt.cli.main", "test", "--project-dir", str(dbt_dir)],
        cwd=str(dest),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res_test.returncode == 0, (
        f"dbt test failed:\nstdout:\n{res_test.stdout}\nstderr:\n{res_test.stderr}"
    )

    # 5. export_parquet.py
    res_export = subprocess.run(
        [sys.executable, str(dest / "scripts" / "export_parquet.py")],
        cwd=str(dest),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res_export.returncode == 0, (
        f"export_parquet failed:\nstdout:\n{res_export.stdout}\nstderr:\n{res_export.stderr}"
    )

    # Verify exported Parquet file
    parquet_file = dest / "data" / "export" / "fct_evaluation_summary.parquet"
    assert parquet_file.is_file(), f"Expected Parquet file {parquet_file} does not exist"

    # Verify Parquet content via duckdb
    conn = duckdb.connect()
    df = conn.execute(f"SELECT * FROM '{parquet_file}'").fetchdf()
    assert len(df) > 0
    assert "model_type" in df.columns
    assert "total_models" in df.columns


def test_bigquery_project_dbt_parse(tmp_path: Path) -> None:
    """A rendered BigQuery project successfully passes dbt parse."""
    dest = tmp_path / "bq_pipeline"
    copier.run_copy(
        src_path=str(TEMPLATE_DIR),
        dst_path=str(dest),
        data={
            "project_name": "bq_parse_test",
            "project_title": "BigQuery Parse Test",
            "sql_engine": "bigquery",
            "bigquery_project": "test-project-123",
            "bigquery_dataset": "test_dataset",
        },
        defaults=True,
        unsafe=True,
    )

    env = {
        "PATH": sys.executable + ":" + subprocess.os.environ.get("PATH", ""),
        "DBT_PROFILES_DIR": str(dest / "dbt"),
        "BIGQUERY_PROJECT": "test-project-123",
        "BIGQUERY_DATASET": "test_dataset",
    }
    dbt_dir = dest / "dbt"

    res_parse = subprocess.run(
        [sys.executable, "-m", "dbt.cli.main", "parse", "--project-dir", str(dbt_dir)],
        cwd=str(dest),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res_parse.returncode == 0, (
        f"BigQuery dbt parse failed:\nstdout:\n{res_parse.stdout}\nstderr:\n{res_parse.stderr}"
    )


def test_duckdb_export_parquet_fails_fast_when_no_mart_tables(tmp_path: Path) -> None:
    """Parquet export halts loudly with an explicit error when no mart tables exist."""
    dest = tmp_path / "duckdb_no_marts"
    copier.run_copy(
        src_path=str(TEMPLATE_DIR),
        dst_path=str(dest),
        data={
            "project_name": "no_marts_test",
            "project_title": "No Marts Test",
            "sql_engine": "duckdb",
        },
        defaults=True,
        unsafe=True,
    )

    env = {
        "PATH": sys.executable + ":" + subprocess.os.environ.get("PATH", ""),
        "DBT_PROFILES_DIR": str(dest / "dbt"),
        "DUCKDB_PATH": str(dest / "data" / "local_cache.duckdb"),
    }
    # Create the duckdb database with only a non-mart table
    (dest / "data").mkdir(parents=True, exist_ok=True)
    db = duckdb.connect(str(dest / "data" / "local_cache.duckdb"))
    db.execute("CREATE TABLE non_mart_table (id INTEGER);")
    db.close()

    res_export = subprocess.run(
        [sys.executable, str(dest / "scripts" / "export_parquet.py")],
        cwd=str(dest),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res_export.returncode != 0
    assert (
        "RuntimeError: No mart tables matching 'fct_%' or 'dim_%' found to export."
        in res_export.stderr
    )
