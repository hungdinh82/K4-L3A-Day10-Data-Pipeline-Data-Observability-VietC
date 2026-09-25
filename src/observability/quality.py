from __future__ import annotations

from typing import Any

import json
import great_expectations as gx
import pandas as pd
from great_expectations.expectations.core import (
    ExpectColumnValueLengthsToBeBetween,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValuesToNotBeNull,
    ExpectTableRowCountToBeBetween,
)

from core.config import Settings


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the data quality checks and freshness gate.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"{report_name}_source")
    data_asset = data_source.add_dataframe_asset(name=f"{report_name}_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe(f"{report_name}_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})
    expectations = [
        ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        *(ExpectColumnValuesToNotBeNull(column=column) for column in ("paper_id", "title", "text_for_embedding")),
        ExpectColumnValuesToBeUnique(column="paper_id"),
        ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]
    results = [batch.validate(expectation) for expectation in expectations]
    freshness = build_freshness_report(df, settings, settings.paths.quality_dir / f"{report_name}_freshness.json")
    payload = {
        "success": all(result.success for result in results) and freshness["is_fresh"],
        "report_name": report_name,
        "row_count": len(df),
        "expectations": [
            {"type": type(expectation).__name__, "success": result.success, "result": result.result}
            for expectation, result in zip(expectations, results, strict=True)
        ],
        "freshness": freshness,
    }
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
    (settings.paths.quality_dir / f"{report_name}_quality_report.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build a freshness summary report.

    Pseudo-code:
    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    threshold = settings.freshness_threshold_days
    dates = pd.to_datetime(df.get("published", pd.Series(dtype=str)), errors="coerce", utc=True)
    age_days = pd.to_numeric(df.get("age_days", pd.Series(dtype=float)), errors="coerce")
    stale_rows = int((age_days > threshold).sum())
    total_rows = int(len(df))
    latest = dates.max()
    oldest = dates.min()
    payload = {
        "latest_published": latest.date().isoformat() if pd.notna(latest) else None,
        "oldest_published": oldest.date().isoformat() if pd.notna(oldest) else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_rows / total_rows if total_rows else 1.0,
        "threshold_days": threshold,
        "is_fresh": bool(total_rows and stale_rows / total_rows <= 0.25),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
