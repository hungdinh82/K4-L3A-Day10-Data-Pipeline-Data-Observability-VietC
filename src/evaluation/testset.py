from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
   """Create a deterministic ten-question benchmark over representative papers."""
   if len(df) < 4:
      raise ValueError("At least four cleaned papers are required to build the evaluation set.")
   selected = df.sort_values(["published", "paper_id"], ascending=[False, True]).head(10)
   questions: list[dict[str, Any]] = []
   layouts = [
      ("summary", "What is the summary of the paper '{title}'?", lambda row: first_sentence(row["summary"])),
      ("authors", "Who authored the paper '{title}'?", lambda row: row["authors_joined"]),
      ("date", "When was the paper '{title}' published?", lambda row: row["published"]),
      ("categories", "What categories describe the paper '{title}'?", lambda row: row["categories_joined"]),
   ]
   for index, (question_type, template, answer) in enumerate(layouts):
      row = selected.iloc[index % len(selected)]
      questions.append({
         "id": f"eval_{index + 1:03d}",
         "question_type": question_type,
         "question": template.format(title=row["title"]),
         "ground_truth": str(answer(row)),
         "ground_truth_doc_ids": [row["paper_id"]],
      })
   for index in range(4, 10):
      row = selected.iloc[index % len(selected)]
      question_type, template, answer = layouts[index % len(layouts)]
      questions.append({
         "id": f"eval_{index + 1:03d}",
         "question_type": question_type,
         "question": template.format(title=row["title"]),
         "ground_truth": str(answer(row)),
         "ground_truth_doc_ids": [row["paper_id"]],
      })
   write_json(output_path, questions)
   return questions
