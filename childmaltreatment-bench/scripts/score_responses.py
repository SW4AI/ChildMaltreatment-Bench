#!/usr/bin/env python3
"""Score ChildMaltreatment-Bench responses with the bundled local model."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ai_grader.data import (  # noqa: E402
    STANDARD_RESPONSE_COLUMNS,
    read_input_rows,
    text_scoring_status,
    write_scored_csv,
)
from ai_grader.model import MultiLabelNB  # noqa: E402
from ai_grader.rubric import LABELS  # noqa: E402

DEFAULT_MODEL = SKILL_DIR / "assets" / "grader_model.pkl.gz"


def parse_sheet_name(value: str) -> str | int:
    if value.isdigit():
        return int(value)
    return value


def unique_output_path(input_path: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    base = output_dir / f"{input_path.stem}_scored.csv"
    if not base.exists():
        return base
    index = 2
    while True:
        candidate = output_dir / f"{input_path.stem}_scored_{index}.csv"
        if not candidate.exists():
            return candidate
        index += 1


def detect_headerless(path: Path, sheet_name: str | int) -> bool:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            first = next(csv.reader(handle), None)
        return bool(first and first[:7] != list(STANDARD_RESPONSE_COLUMNS) and len(first) == 7)
    if path.suffix.lower() in (".xlsx", ".xls"):
        try:
            import pandas as pd
        except ImportError:
            return False
        frame = pd.read_excel(path, sheet_name=sheet_name, header=None, nrows=12)
        for _, row in frame.iterrows():
            values = ["" if pd.isna(value) else str(value).strip() for value in row.tolist()]
            if values and values[0] == "record_id" and "answer" in values:
                return False
        return frame.shape[1] == len(STANDARD_RESPONSE_COLUMNS)
    return False


def score_file(
    input_path: Path,
    model: MultiLabelNB,
    output_dir: Path,
    text_column: str | None,
    sheet_name: str | int,
    headerless_standard_format: bool,
) -> dict[str, object]:
    input_fields = STANDARD_RESPONSE_COLUMNS if headerless_standard_format else None
    rows, columns, detected_text_column = read_input_rows(
        input_path, text_column, input_fields, sheet_name
    )
    statuses = [text_scoring_status(row.get(detected_text_column, "")) for row in rows]
    predictions = [
        model.predict_one(row.get(detected_text_column, "")) if status == "scored" else None
        for row, status in zip(rows, statuses)
    ]
    output_path = unique_output_path(input_path, output_dir)
    write_scored_csv(
        output_path,
        rows,
        columns,
        predictions,
        exclude_columns=[detected_text_column],
        statuses=statuses,
    )
    summary = validate_output(output_path)
    summary.update(
        {
            "input": str(input_path),
            "output": str(output_path),
            "text_column": detected_text_column,
            "rows": len(rows),
            "scored_rows": statuses.count("scored"),
            "not_scored_rows": len(rows) - statuses.count("scored"),
            "statuses": {status: statuses.count(status) for status in sorted(set(statuses))},
        }
    )
    return summary


def validate_output(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    has_answer = "answer" in (rows[0].keys() if rows else [])
    invalid_rows = 0
    totals: list[int] = []
    for row in rows:
        if row.get("scoring_status") != "scored":
            continue
        if any(row.get(label) not in {"0", "1"} for label in LABELS):
            invalid_rows += 1
            continue
        try:
            total = int(row.get("total_score", ""))
        except ValueError:
            invalid_rows += 1
            continue
        if total < 0 or total > len(LABELS):
            invalid_rows += 1
        else:
            totals.append(total)
    return {
        "output_rows": len(rows),
        "has_answer_column": has_answer,
        "invalid_scored_rows": invalid_rows,
        "min_total": min(totals) if totals else None,
        "max_total": max(totals) if totals else None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score ChildMaltreatment-Bench CSV/XLSX response files with the bundled rubric model."
    )
    parser.add_argument("inputs", nargs="+", help="CSV/XLSX response files to score")
    parser.add_argument("--output-dir", default="outputs", help="Directory for scored CSV files")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="Model file path")
    parser.add_argument("--text-column", help="Answer text column name when not auto-detected")
    parser.add_argument("--sheet-name", default="0", help="Excel sheet name or index; default 0")
    parser.add_argument(
        "--headerless-standard-format",
        action="store_true",
        help="Treat headerless input as record_id/model/question_id/age/gender/location/answer",
    )
    parser.add_argument(
        "--auto-headerless-standard-format",
        action="store_true",
        help="Automatically use the 7-column standard mapping for headerless inputs",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    model = MultiLabelNB.load(args.model)
    output_dir = Path(args.output_dir)
    sheet_name = parse_sheet_name(str(args.sheet_name))
    summaries = []
    for raw_input in args.inputs:
        input_path = Path(raw_input).expanduser().resolve()
        headerless = args.headerless_standard_format
        if args.auto_headerless_standard_format and not headerless:
            headerless = detect_headerless(input_path, sheet_name)
        try:
            summary = score_file(
                input_path,
                model,
                output_dir,
                args.text_column,
                sheet_name,
                headerless,
            )
        except ValueError as exc:
            print(f"ERROR {input_path}: {exc}", file=sys.stderr)
            return 2
        summaries.append(summary)
        print(
            "SCORED "
            f"input={summary['input']} output={summary['output']} "
            f"rows={summary['rows']} scored={summary['scored_rows']} "
            f"not_scored={summary['not_scored_rows']} "
            f"invalid={summary['invalid_scored_rows']} "
            f"total_range={summary['min_total']}-{summary['max_total']} "
            f"statuses={summary['statuses']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
