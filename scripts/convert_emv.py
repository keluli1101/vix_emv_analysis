#!/usr/bin/env python3

import argparse
import sys
import urllib.request
from pathlib import Path

import pandas as pd


DATE_FORMAT = "%m/%d/%Y"
DEFAULT_EMV_URL = "https://www.policyuncertainty.com/media/EMV_Data.xlsx"


def parse_date(date_string: str) -> pd.Timestamp:
    """Parse a date in MM/DD/YYYY format."""
    try:
        return pd.to_datetime(
            date_string,
            format=DATE_FORMAT,
        )
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date: {date_string}. "
            f"Expected format: MM/DD/YYYY"
        )


def download_file(url: str, output_path: Path) -> None:
    """Download raw file from URL if requested or missing."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading raw data from {url} ...")
    
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req) as response, open(output_path, "wb") as out_file:
        out_file.write(response.read())
    print(f"Successfully saved raw file to {output_path}")


def convert_csv(
    input_file: str,
    output_file: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    download: bool = False,
    download_url: str = DEFAULT_EMV_URL,
) -> None:
    """Convert EMV Excel data to CSV with extra data cleaning."""

    if start_date > end_date:
        raise ValueError("Start date must not be later than end date.")

    input_path = Path(input_file)
    output_path = Path(output_file)

    # ------------------------------------------------------------------
    # 0. Download input file if requested or file does not exist
    # ------------------------------------------------------------------
    if download or not input_path.is_file():
        download_file(download_url, input_path)

    if not input_path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    if input_path.suffix.lower() not in {".xlsx", ".xls"}:
        raise ValueError("Input file must be an Excel file (.xlsx or .xls).")

    # ------------------------------------------------------------------
    # 1. Read Excel file
    # ------------------------------------------------------------------
    df = pd.read_excel(input_path, engine="openpyxl")

    # 清理列名前后空格
    df.columns = df.columns.astype(str).str.strip()

    # 删除全空行
    df = df.dropna(how="all").reset_index(drop=True)

    # ------------------------------------------------------------------
    # 2. Check required columns
    # ------------------------------------------------------------------
    required_columns = {"Year", "Month"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Input Excel file is missing required columns: "
            f"{', '.join(sorted(missing_columns))}"
        )

    # ------------------------------------------------------------------
    # 3. Validate and Clean Year & Month
    # ------------------------------------------------------------------
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Month"] = pd.to_numeric(df["Month"], errors="coerce")

    # 剔除末尾非数值注释行 (如 Source 声明)
    non_numeric_mask = df["Year"].isna() | df["Month"].isna()
    if non_numeric_mask.any():
        dropped_count = non_numeric_mask.sum()
        print(f"Notice: Dropped {dropped_count} non-numeric/footer row(s) (e.g., source notes).")
        df = df[~non_numeric_mask].copy()

    # 检查月份范围
    invalid_month = (df["Month"] < 1) | (df["Month"] > 12)
    if invalid_month.any():
        raise ValueError("Found invalid Month values (outside 1-12 range).")

    df["Year"] = df["Year"].astype(int)
    df["Month"] = df["Month"].astype(int)

    # ------------------------------------------------------------------
    # 4. Create Temp Date column & filter date range
    # ------------------------------------------------------------------
    df["_tmp_date"] = pd.to_datetime(
        {"year": df["Year"], "month": df["Month"], "day": 1},
        errors="coerce",
    )

    input_start = df["_tmp_date"].min()
    input_end = df["_tmp_date"].max()

    actual_start = max(start_date, input_start)
    actual_end = min(end_date, input_end)

    if actual_start > actual_end:
        raise ValueError("Requested date range has no intersection with input data.")

    df = df[(df["_tmp_date"] >= actual_start) & (df["_tmp_date"] <= actual_end)].copy()

    # ------------------------------------------------------------------
    # 5. Format DATE and Filter columns
    # ------------------------------------------------------------------
    # 将日期格式化并赋给首列 DATE
    df["DATE"] = df["_tmp_date"].dt.strftime(DATE_FORMAT)

    excluded_columns = {
        "Year",
        "Month",
        "_tmp_date",
        "DATE",
        "Infectious Disease EMV Tracker",
        "Petroleum Markets EMV Tracker",
    }

    other_columns = [col for col in df.columns if col not in excluded_columns]
    
    # 确保首列名为 DATE
    df = df[["DATE"] + other_columns]

    # ------------------------------------------------------------------
    # 6. Write CSV
    # ------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print("Conversion completed successfully.")
    print(f"Output file: {output_path}")
    print(f"Output rows: {len(df)}, Output columns: {len(df.columns)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert EMV Excel data to CSV with optional auto-downloading."
    )

    parser.add_argument("input_file", help="Input Excel file path (.xlsx)")
    parser.add_argument("output_file", help="Output CSV file path")
    parser.add_argument("start_date", type=parse_date, help="Start date (MM/DD/YYYY)")
    parser.add_argument("end_date", type=parse_date, help="End date (MM/DD/YYYY)")
    
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download raw EMV data before processing",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_EMV_URL,
        help="Custom URL for raw EMV Excel file",
    )

    args = parser.parse_args()

    try:
        convert_csv(
            input_file=args.input_file,
            output_file=args.output_file,
            start_date=args.start_date,
            end_date=args.end_date,
            download=args.download,
            download_url=args.url,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
