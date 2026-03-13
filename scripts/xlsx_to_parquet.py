#!/usr/bin/env python3
"""
Convert an Excel (.xlsx) file to Parquet.
Requires: pip install pandas openpyxl pyarrow

Usage:
  python scripts/xlsx_to_parquet.py input.xlsx output.parquet
  python scripts/xlsx_to_parquet.py input.xlsx                    # writes input.parquet
  python scripts/xlsx_to_parquet.py input.xlsx --sheet 1          # use second sheet
"""
import argparse
import sys

import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Convert XLSX to Parquet")
    parser.add_argument("input", help="Path to .xlsx file")
    parser.add_argument("output", nargs="?", default=None, help="Path to .parquet file (default: input.parquet)")
    parser.add_argument("--sheet", type=int, default=0, help="Sheet index (0-based) or name (default: 0)")
    args = parser.parse_args()

    input_path = args.input
    if not input_path.lower().endswith((".xlsx", ".xls")):
        print("Warning: input does not look like .xlsx or .xls", file=sys.stderr)

    output_path = args.output
    if output_path is None:
        output_path = input_path.rsplit(".", 1)[0] + ".parquet"

    print(f"Reading {input_path}...")
    df = pd.read_excel(input_path, sheet_name=args.sheet, engine="openpyxl")
    print(f"Rows: {len(df)}, Columns: {len(df.columns)}")

    print(f"Writing {output_path}...")
    df.to_parquet(output_path, index=False)
    print(f"Done. Parquet saved to {output_path}")


if __name__ == "__main__":
    main()
