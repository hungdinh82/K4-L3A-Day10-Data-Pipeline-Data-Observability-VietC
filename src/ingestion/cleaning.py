from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw records into a dataframe ready for embedding.

    Pseudo-code:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    columns = [
        "paper_id",
        "title",
        "summary",
        "authors",
        "categories",
        "primary_category",
        "published",
        "updated",
        "abs_url",
        "pdf_url",
        "comment",
        "authors_joined",
        "categories_joined",
        "summary_chars",
        "age_days",
        "text_for_embedding",
    ]

    rows = []
    for record in records:
        authors = list(
            dict.fromkeys(
                value
                for value in (normalize_whitespace(str(item)) for item in record.authors if item)
                if value
            )
        )
        categories = list(
            dict.fromkeys(
                value
                for value in (normalize_whitespace(str(item)) for item in record.categories if item)
                if value
            )
        )
        rows.append(
            {
                "paper_id": normalize_whitespace(record.paper_id).lower(),
                "title": normalize_whitespace(record.title),
                "summary": normalize_whitespace(record.summary),
                "authors": authors,
                "categories": categories,
                "primary_category": normalize_whitespace(record.primary_category)
                or (categories[0] if categories else ""),
                "published": record.published,
                "updated": record.updated,
                "abs_url": normalize_whitespace(record.abs_url),
                "pdf_url": normalize_whitespace(record.pdf_url),
                "comment": normalize_whitespace(record.comment),
            }
        )

    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows)
    df["published"] = pd.to_datetime(df["published"], errors="coerce", utc=True)
    df["updated"] = pd.to_datetime(df["updated"], errors="coerce", utc=True)

    # Records without an identity, useful text, or a valid publication date
    # cannot be embedded or evaluated reliably.
    valid = (
        df["paper_id"].ne("")
        & df["title"].ne("")
        & df["summary"].ne("")
        & df["published"].notna()
    )
    df = df.loc[valid].copy()
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")
    df["age_days"] = (
        run_timestamp.normalize() - df["published"].dt.normalize()
    ).dt.days.astype("int64")

    df["published"] = df["published"].dt.strftime("%Y-%m-%d")
    df["updated"] = df["updated"].dt.strftime("%Y-%m-%d").fillna("")
    df["authors_joined"] = df["authors"].map(compact_join)
    df["categories_joined"] = df["categories"].map(compact_join)
    df["summary_chars"] = df["summary"].str.len()
    df["text_for_embedding"] = df.apply(
        lambda row: (
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Published: {row['published']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Summary: {row['summary']}"
        ),
        axis=1,
    )

    return df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(
        drop=True
    )[columns]
