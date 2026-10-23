"""Tests for the research pipeline Copier template and lifecycle."""

import subprocess
import sys
from pathlib import Path

import copier
import duckdb

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "research-pipeline"


def test_render_duckdb_project_structure(tmp_path: Path) -> None:
    """The template renders a DuckDB project with required files and configurations."""
    dest = tmp_path / "duckdb_research"
    copier.run_copy(
        src_path=str(TEMPLATE_DIR),
        dst_path=str(dest),
        data={
            "project_name": "tox_duckdb",
            "project_title": "Toxicity Analysis (DuckDB)",
            "sql_engine": "duckdb",
        },
        defaults=True,
        unsafe=True,
    )

    # Core directory and file assertions
    assert (dest / "dbt" / "dbt_project.yml").is_file()
    assert (dest / "dbt" / "profiles.yml").is_file()
    assert (dest / "pyproject.toml").is_file()
    assert (dest / ".env.example").is_file()
    assert (dest / ".github" / "workflows" / "ci.yml").is_file()
    assert (dest / "manuscript" / "_quarto.yml").is_file()
    assert (dest / "manuscript" / "index.qmd").is_file()
    assert (dest / "scripts" / "export_parquet.py").is_file()
    assert (dest / "dbt" / "seeds" / "safety_model_registry.csv").is_file()
    assert (dest / "dbt" / "models" / "marts" / "fct_evaluation_summary.sql").is_file()
    assert (dest / "dbt" / "tests" / "assert_registry_model_count_parity.sql").is_file()

    # Content checks for DuckDB specialization
    profiles_text = (dest / "dbt" / "profiles.yml").read_text()
    assert "type: duckdb" in profiles_text
    assert "DUCKDB_PATH" in profiles_text

    pyproject_text = (dest / "pyproject.toml").read_text()
    assert "dbt-duckdb" in pyproject_text
    assert "tox_duckdb" in pyproject_text


def test_render_bigquery_project_structure(tmp_path: Path) -> None:
    """The template renders a BigQuery project with required files and configurations."""
    dest = tmp_path / "bq_research"
    copier.run_copy(
        src_path=str(TEMPLATE_DIR),
        dst_path=str(dest),
        data={
            "project_name": "tox_bq",
            "project_title": "Toxicity Analysis (BigQuery)",
            "sql_engine": "bigquery",
            "bigquery_project": "test-gcp-project",
            "bigquery_dataset": "test_analytics",
        },
        defaults=True,
        unsafe=True,
    )

    assert (dest / "dbt" / "dbt_project.yml").is_file()
    assert (dest / "dbt" / "profiles.yml").is_file()
    assert (dest / "pyproject.toml").is_file()
    assert (dest / ".env.example").is_file()
    assert (dest / ".github" / "workflows" / "ci.yml").is_file()

    profiles_text = (dest / "dbt" / "profiles.yml").read_text()
    assert "type: bigquery" in profiles_text
    assert "test-gcp-project" in profiles_text
    assert "test_analytics" in profiles_text

    pyproject_text = (dest / "pyproject.toml").read_text()
    assert "dbt-bigquery" in pyproject_text


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

    dbt_dir = dest / "dbt"
    (dest / "data").mkdir(parents=True, exist_ok=True)

    env = {
        "PATH": sys.executable + ":" + subprocess.os.environ.get("PATH", ""),
        "DBT_PROFILES_DIR": str(dest / "dbt"),
        "DUCKDB_PATH": str(dest / "data" / "local_cache.duckdb"),
    }

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
