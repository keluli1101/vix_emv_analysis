
# Dynamic Market Volatility Regimes & EMV Analysis

This repository provides an empirical framework for analyzing financial market volatility regimes and their macroeconomic drivers using CBOE Volatility Index (VIX) data and Policy Uncertainty Equity Market Volatility (EMV) trackers. 

The pipeline combines a derivative-free **Genetic Algorithm (GA)** to globally optimize finite **Mixture of Gaussians (MoG)** models on VIX log-returns, alongside **Cross-Validated Regularized Regressions (Elastic Net, LASSO, Ridge)** to extract primary macroeconomic transmission channels while controlling for high-dimensional feature collinearity.

---

## Table of Contents

- [Data Sources](#data-sources)
- [Project Directory Structure](#project-directory-structure)
- [Environment Setup](#environment-setup)
- [Data Conversion Tools](#data-conversion-tools)
- [Usage Guide](#usage-guide)
- [Data Preprocessing & Version Alignment Details](#data-preprocessing--version-alignment-details)

---

## Data Sources

The project relies on two primary open-access datasets:

1. **VIX Daily History Data (1990–Present)**
   - **Description**: Daily OHLC historical prices published by CBOE.
   - **Download Link**: [https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv](https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv)
   - **Local Path**: `data/raw/VIX_History.csv`

2. **Monthly Equity Market Volatility (EMV) Tracker Data**
   - **Description**: Category-specific equity market volatility trackers constructed via text analysis of leading news publications by Baker, Bloom, Davis, and Kost.
   - **Download Link**: [https://www.policyuncertainty.com/media/EMV_Data.xlsx](https://www.policyuncertainty.com/media/EMV_Data.xlsx)
   - **Local Path**: `data/raw/EMV_Data.xlsx`

---

## Project Directory Structure

```text
.
├── data/
│   ├── processed/                # Preprocessed monthly CSV files for modeling
│   │   ├── MEMV.csv              # Processed monthly EMV trackers (43 core predictors)
│   │   ├── MEMV.csv.org          # Original / benchmark processed data copy
│   │   └── MVIX.csv              # Processed monthly VIX level & log-return series
│   └── raw/                      # Download destination for raw source files
│       ├── EMV_Data.csv
│       ├── EMV_Data.xlsx
│       └── VIX_History.csv
├── scripts/                      # Automated download and data cleaning scripts
│   ├── convert_emv.py            # Preprocesses raw EMV Excel files into formatted CSVs
│   └── convert_vix.py            # Aggregates daily OHLC VIX CSVs into monthly series
├── output/
│   └── para_saved/               # Saved model parameters and GA optimization state checkpoints
│       ├── result_para_v1.20.pkl
│       ├── result_para_v2.1.pkl
│       └── result_para_v2.20.pkl
├── genetic_algorithm.py          # Genetic Algorithm (GA) implementation for global MoG optimization
├── vix_emv_analysis.ipynb        # Main Jupyter Notebook for model estimation, selection, and diagnostics
├── Log-returns_and_MoG_pdf.pdf   # Publication-ready visualization of empirical return PDFs vs MoG fits
├── requirements.txt              # Project Python dependencies
└── README.md                     # Project documentation
```

---

## Environment Setup

Ensure you have Python 3.10+ installed. Install the required dependencies using `pip`:

```bash
pip install -r requirements.txt
```

---

## Data Conversion Tools

The `scripts/` directory includes two command-line utilities designed for automated fetching, cleaning, and filtering:

### 1. `convert_vix.py`
Extracts the closing price on the last available trading day of each month from daily VIX data, outputting a standardized monthly dataset (`MVIX.csv`).

### 2. `convert_emv.py`
Converts the raw EMV Excel sheet into a monthly CSV (`MEMV.csv`). It standardizes the leading date column (`DATE` in `MM/DD/YYYY` format), strips accidental header whitespace, drops non-numeric source text footers, and filters out non-standard experiment variables.

---

## Usage Guide

Run the conversion scripts with the `--download` flag to automatically fetch raw data from remote URLs into `data/raw/` before executing preprocessing:

```bash
# 1. Download and preprocess EMV data (Sample Range: 01/01/1990 to 12/31/2025)
python3 scripts/convert_emv.py data/raw/EMV_Data.xlsx data/processed/MEMV.csv 01/01/1990 12/31/2025 --download

# 2. Download and preprocess VIX data (Sample Range: 01/01/1990 to 12/31/2025)
python3 scripts/convert_vix.py data/raw/VIX_History.csv data/processed/MVIX.csv 01/01/1990 12/31/2025 --download
```

Once preprocessed, launch the main Jupyter Notebook to reproduce empirical estimation and figures:

```bash
jupyter notebook vix_emv_analysis.ipynb
```

---

## Data Preprocessing & Version Alignment Details

To maintain exact alignment and comparability with baseline experimental setups, the preprocessing pipeline applies the following explicit data cleaning rules:

1. **Header Whitespace Normalization (`str.strip()`)**
   - Older legacy datasets contained trailing whitespace in column names (e.g., `"National Security Policy EMV Tracker "`), whereas newer official releases removed trailing spaces.
   - The pipeline enforces `df.columns = df.columns.astype(str).str.strip()` across all inputs to prevent key error exceptions during feature matrix indexing.

2. **Predictor Alignment across Dataset Versions**
   - **Newly Added Trackers in Recent Releases**: `Infectious Disease EMV Tracker` and `Petroleum Markets EMV Tracker`.
   - **Alignment Rule**: `convert_emv.py` automatically drops these two recently added columns, ensuring a stable, 43-dimensional predictor space consistent across legacy and updated data versions.

3. **Footer Annotation Stripping & Column Naming**
   - Automatically detects and drops non-numeric footer notes (e.g., source citations at the bottom of `EMV_Data.xlsx`).
   - Guarantees `DATE` as the primary key column name across all generated `.csv` files.
