# ChildMaltreatment-Bench

ChildMaltreatment-Bench is a Codex skill and command-line scoring tool for the Child Maltreatment Response Evaluation Benchmark. It processes CSV or XLSX files containing model-generated answers and outputs analysis-ready CSV files with 14 binary rubric scores and a total score.

## Project Name

- Short name: `ChildMaltreatment-Bench`
- Full name: `Child Maltreatment Response Evaluation Benchmark`

## Authors

1. Xuetong Wang
2. Gaoran Chen
3. Yiwei Qiu
4. Guowei Wan

East China Normal University

## What It Scores

The bundled rubric includes 14 labels:

```text
L1, L2, I1, I2, V1, V2, E1, E2, S1, S2, C1, C2, G1, G2
```

These labels cover listening, inquiry, validation, safety, formal support resources, child-friendly communication, mental health or medical support, and non-abusive caregiver support. See [`references/rubric.md`](references/rubric.md) for the full scoring definitions.


## Requirements

- Python 3.10 or later
- CSV input: Python standard library only
- XLSX/XLS input: install `pandas` and `openpyxl`

Install optional spreadsheet dependencies from the repository root:

```bash
pip install -r requirements.txt
```

## Input Format

Preferred input columns:

```text
record_id, model, question_id, age, gender, location, answer
```

Supported files:

- `.csv`
- `.xlsx`
- `.xls`

Headerless files are accepted only when they contain exactly 7 columns in the standard order above. If the column count does not match, the data should be reorganized before scoring.

## Output Format

The skill outputs analysis-ready CSV files. The long `answer` column is removed by default.

Output columns:

```text
record_id, model, question_id, age, gender, location, scoring_status,
L1, L2, I1, I2, V1, V2, E1, E2, S1, S2, C1, C2, G1, G2, total_score
```

`scoring_status` may be:

- `scored`: the answer was scored successfully.
- `missing_answer`: the answer was empty.
- `source_generation_failed`: the answer text indicates an upstream API or generation failure.

For non-scored rows, all score fields are left blank.

## File Naming

The output file name is generated automatically:

```text
<input_stem>_scored.csv
```

If that file already exists, the script uses:

```text
<input_stem>_scored_2.csv
<input_stem>_scored_3.csv
...
```

This avoids overwriting previous results.

## Usage

From the repository or skill root, use the bundled scoring script:

```bash
python scripts/score_responses.py \
  --output-dir outputs \
  --auto-headerless-standard-format \
  input.csv
```

For Excel files where the data sheet is named `Result 1`:

```bash
python scripts/score_responses.py \
  --output-dir outputs \
  --sheet-name "Result 1" \
  --auto-headerless-standard-format \
  input.xlsx
```

## Repository Contents

```text
childmaltreatment-bench/
├── SKILL.md
├── README.md
├── requirements.txt
├── agents/
│   └── openai.yaml
├── assets/
│   └── grader_model.pkl.gz
├── references/
│   └── rubric.md
└── scripts/
    ├── score_responses.py
    └── ai_grader/
        ├── __init__.py
        ├── data.py
        ├── model.py
        └── rubric.py
```

## Notes

The skill uses a bundled local model and does not call external APIs. It is intended for batch scoring and preparing structured outputs for statistical analysis. It does not include training or validation-set evaluation commands. The command-line script is intentionally independent of Codex-specific paths so other coding agents can run it from the repository root.
