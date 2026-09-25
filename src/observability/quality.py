from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _json_result(result: Any) -> Any:
    if hasattr(result, "to_json_dict"):
        return result.to_json_dict()
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the required GX 1.x expectations and persist a compact report."""
    import great_expectations as gx

    context = gx.get_context(mode="ephemeral")
    source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
    asset = source.add_dataframe_asset(name=f"papers_asset_{report_name}")
    batch_definition = asset.add_batch_definition_whole_dataframe(f"papers_batch_{report_name}")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})
    suite = gx.ExpectationSuite(name=f"papers_quality_{report_name}")
    expectations = [
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30, max_value=100000),
    ]
    for expectation in expectations:
        suite.add_expectation(expectation)
    validation = batch.validate(suite)
    freshness = build_freshness_report(df, settings, settings.paths.quality_dir / f"{report_name}_freshness.json")
    payload = {
        "success": bool(validation.success),
        "report_name": report_name,
        "row_count": int(len(df)),
        "expectations": _json_result(validation),
        "freshness": freshness,
    }
    report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    write_json(report_path, payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize publication freshness against the configured 25% SLA."""
    dates = pd.to_datetime(df.get("published", pd.Series(dtype=str)), errors="coerce", utc=True).dropna()
    total_rows = len(df)
    stale_rows = int((pd.to_numeric(df.get("age_days", 0), errors="coerce") > settings.freshness_threshold_days).sum())
    payload = {
        "latest_published": dates.max().date().isoformat() if not dates.empty else None,
        "oldest_published": dates.min().date().isoformat() if not dates.empty else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_rows / total_rows if total_rows else 1.0,
        "threshold_days": settings.freshness_threshold_days,
        "is_fresh": bool(total_rows and stale_rows / total_rows <= 0.25),
    }
    write_json(report_path, payload)
    return payload
