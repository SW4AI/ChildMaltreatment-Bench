---
name: child-support-response-grader
description: Score child and adolescent support-response CSV/XLSX files with a bundled local 14-label rubric model. Use when Codex needs to automatically score model answer files, batch score responses, produce analysis-ready scored CSV outputs, handle CSV/XLSX response exports with record_id/model/question_id/age/gender/location/answer columns, or score headerless 7-column response files.
---

# Child Support Response Grader

## Purpose

Score response datasets with the bundled local model and the latest agreed rubric. The skill is for scoring only. Do not retrain the model or run validation/evaluation workflows from this skill.

## Inputs

Accept `.csv`, `.xlsx`, and `.xls` files containing response rows.

Preferred columns are:
`record_id, model, question_id, age, gender, location, answer`.

If a file has no header but every row has exactly 7 columns, treat it as the standard column order above. If a headerless file does not have exactly 7 columns, stop and ask the operator to reorganize the data.

For Excel files, read the first sheet by default. If a likely data sheet is named `Result 1`, use `--sheet-name 'Result 1'`. The script can find a real `record_id...answer` header even when the first row is a placeholder such as `C1...C7`.

## Output

Always produce analysis-ready CSV files. Remove the long `answer` text column by default.

Output columns:
`record_id, model, question_id, age, gender, location, scoring_status, L1, L2, I1, I2, V1, V2, E1, E2, S1, S2, C1, C2, G1, G2, total_score`.

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
2. Run the bundled script with the Codex bundled Python when available, especially for XLSX inputs because it includes pandas. If only CSV inputs are used, a standard Python 3.10+ runtime is usually sufficient.
3. Use `--auto-headerless-standard-format` unless you already know the input has a valid header.
4. Use `--sheet-name 'Result 1'` for Excel exports whose data sheet is named `Result 1`.
5. After scoring, verify row count, `answer` column absence, valid 0/1 label values for scored rows, `total_score` range 0-14, and non-scored status counts.
6. Return links only to the final scored CSV files and a compact verification summary.

## Command

```bash
/Users/xue/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 /Users/xue/.codex/skills/child-support-response-grader/scripts/score_responses.py \
  --output-dir outputs \
  --auto-headerless-standard-format \
  input1.csv input2.xlsx
```

For Excel data in `Result 1`:

```bash
/Users/xue/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12 /Users/xue/.codex/skills/child-support-response-grader/scripts/score_responses.py \
  --output-dir outputs \
  --sheet-name 'Result 1' \
  --auto-headerless-standard-format \
  input.xlsx
```

## Rubric Reference

For label definitions and boundary rules, read `references/rubric.md` when there is any question about scoring interpretation.
