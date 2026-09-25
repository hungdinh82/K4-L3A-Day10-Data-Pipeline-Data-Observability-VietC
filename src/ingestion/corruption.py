from __future__ import annotations

from datetime import date
import json
from pathlib import Path

import pandas as pd


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """TODO(student): simulate nhieu dang data corruption.

    Pseudo-code:
    1. Drop mot so latest records.
    2. Blank summary o mot so dong.
    3. Inject noise vao text.
    4. Lam title bi truncate.
    5. Lam published date cu di.
    6. Add duplicate rows.
    7. Rebuild `text_for_embedding`.
    8. Ghi corruption log vao output_log_path.
    """
    if df.empty:
        raise ValueError("Cannot corrupt an empty clean dataframe.")

    corrupted = df.copy(deep=True).sort_values("published", ascending=False).reset_index(drop=True)
    original_count = len(corrupted)
    affected_count = max(1, int(original_count * 0.2))
    log: list[dict[str, object]] = []

    dropped_ids = corrupted.head(affected_count)["paper_id"].tolist()
    corrupted = corrupted.iloc[affected_count:].copy()
    log.append(
        {
            "scenario": "drop_latest_records",
            "description": "Dropped the newest records to simulate loss of fresh data.",
            "count": len(dropped_ids),
            "paper_ids": dropped_ids,
        }
    )

    blank_positions = list(corrupted.index[: min(2, len(corrupted))])
    blank_ids = corrupted.loc[blank_positions, "paper_id"].tolist()
    corrupted.loc[blank_positions, "summary"] = ""
    log.append(
        {
            "scenario": "blank_summary",
            "description": "Blanked summaries to simulate incomplete source records.",
            "count": len(blank_ids),
            "paper_ids": blank_ids,
        }
    )

    noise_positions = list(corrupted.index[2 : min(4, len(corrupted))])
    noise_ids = corrupted.loc[noise_positions, "paper_id"].tolist()
    noise = " [NOISE_X9Q !@# CORRUPTED_TOKEN]"
    corrupted.loc[noise_positions, "text_for_embedding"] = corrupted.loc[noise_positions, "text_for_embedding"] + noise
    log.append(
        {
            "scenario": "inject_text_noise",
            "description": "Injected meaningless tokens into embedding text.",
            "count": len(noise_ids),
            "paper_ids": noise_ids,
            "noise": noise.strip(),
        }
    )

    title_positions = list(corrupted.index[4 : min(6, len(corrupted))])
    title_ids = corrupted.loc[title_positions, "paper_id"].tolist()
    corrupted.loc[title_positions, "title"] = corrupted.loc[title_positions, "title"].astype(str).str[:8]
    log.append(
        {
            "scenario": "truncate_title",
            "description": "Truncated titles below ten characters.",
            "count": len(title_ids),
            "paper_ids": title_ids,
            "max_title_length": 8,
        }
    )

    stale_positions = list(corrupted.index[6 : min(8, len(corrupted))])
    stale_ids = corrupted.loc[stale_positions, "paper_id"].tolist()
    today = date.today()
    stale_day = today.replace(year=today.year - 5)
    corrupted.loc[stale_positions, "published"] = stale_day.isoformat()
    corrupted.loc[stale_positions, "age_days"] = (today - stale_day).days
    log.append(
        {
            "scenario": "stale_date",
            "description": "Moved publication dates five years into the past.",
            "count": len(stale_ids),
            "paper_ids": stale_ids,
            "published": stale_day.isoformat(),
        }
    )

    duplicate_count = min(affected_count, len(corrupted))
    duplicate_rows = corrupted.head(duplicate_count).copy()
    duplicated_ids = duplicate_rows["paper_id"].tolist()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)
    log.append(
        {
            "scenario": "duplicate_rows",
            "description": "Duplicated rows to simulate repeated ingestion.",
            "count": duplicate_count,
            "paper_ids": duplicated_ids,
        }
    )

    # Rebuild derived fields after the title, summary, date, and duplicate mutations.
    corrupted["summary_chars"] = corrupted["summary"].fillna("").astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(
        lambda row: (
            f"Title: {row['title']}\nAuthors: {row['authors_joined']}\nPublished: {row['published']}\n"
            f"Categories: {row['categories_joined']}\nSummary: {row['summary']}"
        ),
        axis=1,
    )
    for position in noise_positions:
        if position < len(corrupted):
            corrupted.loc[position, "text_for_embedding"] += noise

    output_path = Path(output_log_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "original_rows": original_count,
                "corrupted_rows": len(corrupted),
                "scenarios": log,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return corrupted.reset_index(drop=True)
