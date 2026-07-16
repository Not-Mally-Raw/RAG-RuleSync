"""Inspect the BucketList examples workbook structure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


DEFAULT_WORKBOOK_PATH = Path(r"C:\Users\patle\Downloads\HCL\BucketList Examples (2) (1).xlsx")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook_path", nargs="?", default=str(DEFAULT_WORKBOOK_PATH))
    parser.add_argument("--sample-rows", type=int, default=3)
    args = parser.parse_args()

    workbook_path = Path(args.workbook_path)
    excel = pd.ExcelFile(workbook_path)
    summary = []
    for sheet_name in excel.sheet_names:
        frame = pd.read_excel(workbook_path, sheet_name=sheet_name)
        summary.append(
            {
                "sheet": sheet_name,
                "rows": int(frame.shape[0]),
                "columns": list(map(str, frame.columns)),
                "sample": frame.head(args.sample_rows).fillna("").to_dict(orient="records"),
            }
        )
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
