"""Input and output helpers for bundled response scoring."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .rubric import LABELS

DEFAULT_TEXT_COLUMNS = ("回答", "answer", "response", "text", "文本答案", "答案")
STANDARD_RESPONSE_COLUMNS = (
    "record_id",
    "model",
    "question_id",
    "age",
    "gender",
    "location",
    "answer",
)


def read_csv_rows(
    path: str | Path,
    text_column: str | None = None,
    fieldnames: Iterable[str] | None = None,
) -> tuple[list[dict[str, str]], list[str], str]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, fieldnames=list(fieldnames) if fieldnames else None)
        headers = list(reader.fieldnames or [])
        if not headers:
            raise ValueError("CSV has no header")
        column = text_column or next(
            (candidate for candidate in DEFAULT_TEXT_COLUMNS if candidate in headers), None
        )
        if column is None or column not in headers:
            choices = ", ".join(headers)
            raise ValueError(f"No answer text column found. Use --text-column. Existing columns: {choices}")
        return list(reader), headers, column


def read_input_rows(
    path: str | Path,
    text_column: str | None = None,
    fieldnames: Iterable[str] | None = None,
    sheet_name: str | int = 0,
) -> tuple[list[dict[str, str]], list[str], str]:
    source = Path(path)
    if source.suffix.lower() == ".csv":
        return read_csv_rows(source, text_column, fieldnames)
    if source.suffix.lower() not in (".xlsx", ".xls"):
        raise ValueError(f"Unsupported input format: {source.suffix}")

    import pandas as pd

    frame = pd.read_excel(source, sheet_name=sheet_name, header=None)
    if frame.empty:
        raise ValueError("Excel sheet has no data")
    header_index = None
    headers: list[str]
    for index, row in frame.iterrows():
        values = ["" if pd.isna(value) else str(value).strip() for value in row.tolist()]
        if values and values[0] == "record_id" and "answer" in values:
            header_index = index
            headers = values
            break
    if header_index is None:
        if frame.shape[1] != len(STANDARD_RESPONSE_COLUMNS):
            raise ValueError("Headerless Excel input must have exactly 7 columns")
        headers = list(STANDARD_RESPONSE_COLUMNS)
        data_frame = frame
    else:
        data_frame = frame.iloc[header_index + 1 :]
    data_frame = data_frame.iloc[:, : len(headers)]
    rows = []
    for values in data_frame.itertuples(index=False, name=None):
        cleaned = ["" if pd.isna(value) else str(value) for value in values]
        rows.append(dict(zip(headers, cleaned)))
    column = text_column or next(
        (candidate for candidate in DEFAULT_TEXT_COLUMNS if candidate in headers), None
    )
    if column is None or column not in headers:
        choices = ", ".join(headers)
        raise ValueError(f"No answer text column found. Use --text-column. Existing columns: {choices}")
    return rows, list(headers), column


def text_scoring_status(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "missing_answer"
    if "API调用失败" in stripped or "api调用失败" in stripped.lower():
        return "source_generation_failed"
    return "scored"


def write_scored_csv(
    path: str | Path,
    rows: Iterable[dict[str, str]],
    original_columns: list[str],
    predictions: Iterable[dict[str, int] | None],
    exclude_columns: Iterable[str] = (),
    statuses: Iterable[str] | None = None,
) -> None:
    excluded = set(exclude_columns)
    output_columns = [
        column
        for column in original_columns
        if column not in LABELS and column != "total_score" and column not in excluded
    ]
    if statuses is not None:
        output_columns.append("scoring_status")
    output_columns.extend(LABELS)
    output_columns.append("total_score")
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_columns)
        writer.writeheader()
        row_statuses = iter(statuses) if statuses is not None else None
        for row, scores in zip(rows, predictions):
            output = {column: row.get(column, "") for column in output_columns}
            if row_statuses is not None:
                output["scoring_status"] = next(row_statuses)
            if scores is not None:
                output.update(scores)
                output["total_score"] = sum(scores[label] for label in LABELS)
            else:
                output.update({label: "" for label in LABELS})
                output["total_score"] = ""
            writer.writerow(output)
