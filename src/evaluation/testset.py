from __future__ import annotations

from typing import Any
from dataclasses import dataclass

from core.utils import read_json, write_json

import pandas as pd


@dataclass(frozen=True)
class TestSet:
    samples: list[dict[str, Any]]


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """TODO(student): tao bo evaluation set tu cleaned dataframe.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
    if len(df) < 4:
        raise ValueError("At least four clean papers are required to build the benchmark test set.")

    rows = df.reset_index(drop=True)
    first, second, third, fourth = (rows.iloc[index] for index in range(4))
    samples = [
        {
            "id": "summary-001",
            "type": "summary",
            "question_type": "summary",
            "question": f"What is the main research contribution of '{first['title']}'?",
            "ground_truth": first["summary"],
            "ground_truth_doc_ids": [first["paper_id"]],
        },
        {
            "id": "authors-001",
            "type": "authors",
            "question_type": "authors",
            "question": f"Who authored the study '{second['title']}'?",
            "ground_truth": second["authors_joined"],
            "ground_truth_doc_ids": [second["paper_id"]],
        },
        {
            "id": "date-001",
            "type": "date",
            "question_type": "date",
            "question": f"When was '{third['title']}' published?",
            "ground_truth": third["published"],
            "ground_truth_doc_ids": [third["paper_id"]],
        },
        {
            "id": "category-001",
            "type": "category",
            "question_type": "category",
            "question": f"What categories does '{fourth['title']}' belong to?",
            "ground_truth": fourth["categories_joined"],
            "ground_truth_doc_ids": [fourth["paper_id"]],
        },
        {
            "id": "multi-hop-001",
            "type": "multi_hop",
            "question_type": "multi_hop",
            "question": (
                f"Which authors studied the connection between {first['primary_category']} and "
                f"{second['primary_category']} in the indexed corpus?"
            ),
            "ground_truth": f"{first['authors_joined']}; {second['authors_joined']}",
            "ground_truth_doc_ids": [first["paper_id"], second["paper_id"]],
        },
    ]
    write_json(output_path, samples)
    return samples


def load_or_create_test_set(df: pd.DataFrame, output_path) -> TestSet:
    """Load a stable benchmark, creating it once when refresh is needed."""
    if output_path.exists():
        samples = read_json(output_path)
    else:
        samples = build_test_set(df, output_path)
    return TestSet(samples=samples)
