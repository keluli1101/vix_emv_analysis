#!/usr/bin/env python3

import argparse
import sys
import urllib.request
from pathlib import Path

import pandas as pd


DATE_FORMAT = "%m/%d/%Y"
DEFAULT_VIX_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"


def parse_date(date_string: str) -> pd.Timestamp:
    """Parse a date in MM/DD/YYYY format."""
    try:
        return pd.to_datetime(date_string, format=DATE_FORMAT)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date: {date_string}. Expected format: MM/DD/YYYY"
        )


def download_file(url: str, output_path: Path) -> None:
    """Download raw VIX data from URL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading raw VIX data from {url} ...")
    
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
    download_url: str = DEFAULT_VIX_URL,
) -> None:
    """Convert daily OHLC VIX CSV to monthly VIX CSV."""

    if start_date > end_date:
        raise ValueError("Start date must not be later than end date.")

    input_path = Path(input_file)
    output_path = Path(output_file)

    # ------------------------------------------------------------------
    # 0. Download file if requested or if missing
    # ------------------------------------------------------------------
    if download or not input_path.is_file():
        download_file(download_url, input_path)

    if not input_path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    # ------------------------------------------------------------------
    # 1. Read input CSV
    # ------------------------------------------------------------------
    df = pd.read_csv(input_path)
    df.columns = df.columns.str.strip()

    required_columns = {"DATE", "CLOSE"}
    if not required_columns.issubset(df.columns):
        raise ValueError("Input CSV missing required columns (DATE, CLOSE).")

    df = df[["DATE", "CLOSE"]].copy()
    df["DATE"] = pd.to_datetime(df["DATE"], format=DATE_FORMAT, errors="coerce")
    df["CLOSE"] = pd.to_numeric(df["CLOSE"], errors="coerce")

    if df["DATE"].isna().any() or df["CLOSE"].isna().any():
        raise ValueError("Found invalid DATE or CLOSE values in input CSV.")

    # Sort & Deduplicate
    df = df.sort_values("DATE").drop_duplicates(subset=["DATE"], keep="last")

    # Date range intersection
    input_start, input_end = df["DATE"].min(), df["DATE"].max()
    actual_start = max(start_date, input_start)
    actual_end = min(end_date, input_end)

    if actual_start > actual_end:
        raise ValueError("Requested date range has no intersection with input data.")

    df = df[(df["DATE"] >= actual_start) & (df["DATE"] <= actual_end)].copy()

    # Keep last available trading day per month
    df["YEAR_MONTH"] = df["DATE"].dt.to_period("M")
    df = (
        df.sort_values("DATE")
        .groupby("YEAR_MONTH", as_index=False)
        .tail(1)
        .sort_values("DATE")
        .reset_index(drop=True)
    )

    df = df[["DATE", "CLOSE"]].rename(columns={"CLOSE": "VIX"})
    df["DATE"] = df["DATE"].dt.strftime(DATE_FORMAT)

    # Output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, float_format="%.6f")

    print("Conversion completed successfully.")
    print(f"Output file: {output_path}")
    print(f"Output rows: {len(df)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert daily VIX CSV into monthly VIX CSV with optional download."
    )

    parser.add_argument("input_file", help="Input CSV file path")
    parser.add_argument("output_file", help="Output CSV file path")
    parser.add_argument("start_date", type=parse_date, help="Start date (MM/DD/YYYY)")
    parser.add_argument("end_date", type=parse_date, help="End date (MM/DD/YYYY)")

    parser.add_argument(
        "--download",
        action="store_true",
        help="Download raw VIX data before processing",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_VIX_URL,
        help="Custom URL for raw VIX CSV file",
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
