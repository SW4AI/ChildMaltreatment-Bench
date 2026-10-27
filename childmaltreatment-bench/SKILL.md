---
name: childmaltreatment-bench
description: Score ChildMaltreatment-Bench CSV/XLSX response files using a bundled local 14-label model based on an operationalized WHO LIVES CC framework. Use for batch assessment, analysis-ready scored CSV outputs, and rubric-based practice feedback for child maltreatment responses.
---

# ChildMaltreatment-Bench

## Purpose

Score ChildMaltreatment-Bench response datasets for the Child Maltreatment Response Evaluation Benchmark with the bundled local model and the latest agreed rubric. The assessment system operationalizes seven dimensions adapted from the WHO's LIVES CC framework: Listen, Inquire, Validate, Enhance safety, Support, Child and adolescent friendly environment, and Caregiver support. Each dimension has two binary sub-dimensions, for 14 labels and a total score from 0 to 14.

The skill supports research evaluation, batch model comparison, and structured practice feedback for social workers or other helping professionals. Practice feedback is educational and should not replace professional supervision, safeguarding procedures, clinical assessment, or emergency services. Do not retrain the model or run validation/evaluation workflows from this skill.

## Inputs

Accept `.csv`, `.xlsx`, and `.xls` files containing response rows. The response-text column is the only required input for scoring; age, gender, location, model, question ID, and record ID are optional metadata.

Preferred columns, when available, are:
`record_id, model, question_id, age, gender, location, answer`.

Recognize response-text columns named `answer`, `response`, `text`, `回答`, `文本答案`, or `答案`. Use `--text-column` for another name.

If a file has no header but every row has exactly 7 columns, treat it as the standard column order above. If a headerless file does not have exactly 7 columns, stop and ask the operator to reorganize the data.

For Excel files, read the first sheet by default. If a likely data sheet is named `Result 1`, use `--sheet-name 'Result 1'`. The script can find a real `record_id...answer` header even when the first row is a placeholder such as `C1...C7`.

## Output

Always produce analysis-ready CSV files. Remove the long `answer` text column by default.

Output keeps the supplied metadata columns, adds `scoring_status`, the 14 labels, and `total_score`. Missing metadata columns are not required and are not invented.

Use the naming rule implemented by the script:

- First output: `<input_stem>_scored.csv`
- If that exists: `<input_stem>_scored_2.csv`, then `_3`, etc.

Never overwrite an existing scored output unless the user explicitly asks you to delete or replace files.

## Scoring Status

Use `scoring_status` to preserve rows that cannot be scored:

- `scored`: answer text was scored.
- `missing_answer`: answer text is empty or whitespace.
- `source_generation_failed`: answer text contains an API-generation failure marker.

For non-scored rows, leave all label scores and `total_score` blank.

## Procedure

1. Inspect each input file for extension, row count, columns, likely answer column, missing answers, and source-generation failures.
2. Run the bundled script from the skill/repository root with `python scripts/score_responses.py`. Use any Python 3.10+ runtime with the dependencies in `requirements.txt`; CSV-only scoring uses the standard library, while XLSX input requires `pandas` and `openpyxl`.
3. Use `--auto-headerless-standard-format` unless you already know the input has a valid header.
4. Use `--sheet-name 'Result 1'` for Excel exports whose data sheet is named `Result 1`.
5. After scoring, verify row count, `answer` column absence, valid 0/1 label values for scored rows, `total_score` range 0-14, and non-scored status counts.
6. Return links only to the final scored CSV files and a compact verification summary.

## Command

```bash
python scripts/score_responses.py \
  --output-dir outputs \
  --auto-headerless-standard-format \
  input1.csv input2.xlsx
```

For Excel data in `Result 1`:

```bash
python scripts/score_responses.py \
  --output-dir outputs \
  --sheet-name 'Result 1' \
  --auto-headerless-standard-format \
  input.xlsx
```

## Rubric Reference

For label definitions and boundary rules, read `references/rubric.md` when there is any question about scoring interpretation.
