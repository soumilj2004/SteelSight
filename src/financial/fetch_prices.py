"""
Financial Data Pipeline
=======================
Downloads historical price data for:
  1. Iron Ore Futures (SGX/CME proxy via Yahoo Finance)
  2. Hot Rolled Coil Steel (HRC) Futures
  3. Computes correlation against our SWIR signal

HOW TO RUN:
    pip install yfinance
    python src/financial/fetch_prices.py

OUTPUT:
    data/financial/iron_ore_prices.csv
    data/financial/hrc_steel_prices.csv
    data/financial/financial_correlation.csv
    data/financial/financial_signal.csv  — merged monthly dataset
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats
import warnings
warnings.filterwarnings("ignore")

os.makedirs("data/financial", exist_ok=True)

# ── PRICE DATA ─────────────────────────────────────────────────────────────────
# Iron ore proxies available on Yahoo Finance:
#   TIOc1  — SGX TSI Iron Ore CFR China futures (best)
#   VALE   — Vale S.A. (world's largest iron ore miner, proxy)
#   BHP    — BHP Group (major iron ore producer, proxy)
#   ^GSCI  — Goldman Sachs Commodity Index
#
# Steel HRC proxies:
#   HRC=F  — CME Hot Rolled Coil Steel futures
#   MT     — ArcelorMittal (largest steelmaker outside China)
#   NUE    — Nucor (US steel, correlated with HRC)
# ──────────────────────────────────────────────────────────────────────────────

TICKERS = {
    "iron_ore_futures": "TIOc1",     # SGX Iron Ore Futures
    "iron_ore_proxy":   "VALE",      # Vale — best liquid proxy
    "hrc_steel":        "HRC=F",     # CME HRC Steel Futures
    "steel_proxy":      "MT",        # ArcelorMittal
    "commodity_index":  "PDBUSD",    # Invesco DB Commodity ETF
}

START = "2019-01-01"
END   = "2024-12-31"


def fetch_yfinance(ticker: str, name: str) -> pd.DataFrame:
    """Download monthly OHLCV from Yahoo Finance."""
    try:
        import yfinance as yf
        df = yf.download(ticker, start=START, end=END,
                         interval="1mo", progress=False, auto_adjust=True)
        if df.empty:
            return None
        df = df[["Close"]].rename(columns={"Close": name})
        df.index = pd.to_datetime(df.index)
        df["year"]  = df.index.year
        df["month"] = df.index.month
        return df.reset_index(drop=True)
    except Exception as e:
        print(f"  Failed to fetch {ticker}: {e}")
        return None


def build_manual_iron_ore() -> pd.DataFrame:
    """
    Hardcoded monthly iron ore price (USD/tonne, 62% Fe CFR China).
    Source: Trading Economics / World Bank commodity data.
    Used as fallback if yfinance fails.
    """
    data = {
        # (year, month): price USD/tonne
        (2019,1):75.5,(2019,2):86.6,(2019,3):85.5,(2019,4):93.5,
        (2019,5):98.0,(2019,6):112.5,(2019,7):119.5,(2019,8):90.0,
        (2019,9):91.5,(2019,10):85.0,(2019,11):86.5,(2019,12):93.5,
        (2020,1):95.0,(2020,2):87.0,(2020,3):83.5,(2020,4):82.5,
        (2020,5):90.5,(2020,6):100.5,(2020,7):107.5,(2020,8):120.0,
        (2020,9):117.0,(2020,10):113.5,(2020,11):128.0,(2020,12):155.0,
        (2021,1):164.5,(2021,2):168.5,(2021,3):174.0,(2021,4):185.0,
        (2021,5):218.0,(2021,6):208.0,(2021,7):180.0,(2021,8):158.0,
        (2021,9):117.0,(2021,10):118.0,(2021,11):96.0,(2021,12):108.5,
        (2022,1):135.0,(2022,2):145.0,(2022,3):155.0,(2022,4):145.0,
        (2022,5):130.0,(2022,6):114.0,(2022,7):102.0,(2022,8):100.5,
        (2022,9):95.0,(2022,10):82.5,(2022,11):93.0,(2022,12):108.0,
        (2023,1):120.0,(2023,2):126.0,(2023,3):125.5,(2023,4):107.5,
        (2023,5):105.0,(2023,6):110.5,(2023,7):110.0,(2023,8):102.5,
        (2023,9):117.0,(2023,10):119.5,(2023,11):130.0,(2023,12):137.0,
        (2024,1):133.5,(2024,2):124.5,(2024,3):113.0,(2024,4):107.5,
        (2024,5):114.0,(2024,6):104.5,(2024,7):99.5,(2024,8):93.0,
        (2024,9):91.5,(2024,10):101.0,(2024,11):104.5,(2024,12):105.0,
    }
    rows = [{"year":y,"month":m,"iron_ore_usd":v} for (y,m),v in data.items()]
    return pd.DataFrame(rows)


def build_manual_hrc() -> pd.DataFrame:
    """
    Hardcoded monthly HRC steel price (USD/short ton, US Midwest).
    Source: CRU / SteelBenchmarker.
    """
    data = {
        (2019,1):647,(2019,2):650,(2019,3):640,(2019,4):612,
        (2019,5):575,(2019,6):545,(2019,7):527,(2019,8):510,
        (2019,9):500,(2019,10):488,(2019,11):490,(2019,12):495,
        (2020,1):510,(2020,2):505,(2020,3):480,(2020,4):455,
        (2020,5):445,(2020,6):455,(2020,7):470,(2020,8):485,
        (2020,9):530,(2020,10):605,(2020,11):695,(2020,12):790,
        (2021,1):885,(2021,2):975,(2021,3):1100,(2021,4):1275,
        (2021,5):1450,(2021,6):1650,(2021,7):1780,(2021,8):1825,
        (2021,9):1790,(2021,10):1750,(2021,11):1620,(2021,12):1490,
        (2022,1):1380,(2022,2):1340,(2022,3):1480,(2022,4):1400,
        (2022,5):1270,(2022,6):1100,(2022,7):900,(2022,8):840,
        (2022,9):790,(2022,10):700,(2022,11):680,(2022,12):720,
        (2023,1):760,(2023,2):800,(2023,3):820,(2023,4):790,
        (2023,5):760,(2023,6):740,(2023,7):750,(2023,8):720,
        (2023,9):700,(2023,10):680,(2023,11):700,(2023,12):720,
        (2024,1):740,(2024,2):780,(2024,3):800,(2024,4):760,
        (2024,5):720,(2024,6):680,(2024,7):650,(2024,8):630,
        (2024,9):620,(2024,10):640,(2024,11):660,(2024,12):670,
    }
    rows = [{"year":y,"month":m,"hrc_steel_usd":v} for (y,m),v in data.items()]
    return pd.DataFrame(rows)


def compute_financial_correlation(signal: pd.DataFrame,
                                   iron_ore: pd.DataFrame,
                                   hrc: pd.DataFrame) -> pd.DataFrame:
    """
    Merge signal with prices and compute lag correlations.
    Tests: does our satellite signal predict commodity prices?
    """
    merged = signal.merge(iron_ore, on=["year","month"], how="inner")
    merged = merged.merge(hrc,      on=["year","month"], how="inner")
    merged["date"] = pd.to_datetime(merged[["year","month"]].assign(day=1))
    merged = merged.sort_values("date").reset_index(drop=True)

    print("\n── Financial Correlation Results ─────────────────────────")
    print(f"{'Comparison':<45} {'Lag':>5} {'R²':>8} {'r':>8} {'p':>10}")
    print("─" * 80)

    results = []
    for price_col, price_name in [
        ("iron_ore_usd", "Iron Ore (USD/t)"),
        ("hrc_steel_usd", "HRC Steel (USD/st)")
    ]:
        for lag in range(0, 7):
            if lag == 0:
                x = merged["pct_active"].values
                y = merged[price_col].values
            else:
                x = merged["pct_active"].values[:-lag]
                y = merged[price_col].values[lag:]
            if len(x) < 8:
                continue
            r, p = stats.pearsonr(x, y)
            results.append({
                "comparison": price_name,
                "price_col":  price_col,
                "lag_months": lag,
                "r":  round(r, 4),
                "r2": round(r**2, 4),
                "p":  round(p, 6),
                "n":  len(x),
            })

        best = max([r for r in results if r["comparison"]==price_name],
                    key=lambda r: r["r2"])
        for res in [r for r in results if r["comparison"]==price_name]:
            marker = " *" if res == best else ""
            print(f"  Signal → {res['comparison']:<35} "
                  f"{res['lag_months']:+d}mo  "
                  f"R²={res['r2']:.3f}  "
                  f"r={res['r']:+.3f}  "
                  f"p={res['p']:.4f}{marker}")
        print()

    return merged, pd.DataFrame(results)


def main():
    print("SteelSight — Financial Data Pipeline")
    print("=" * 60)

    # 1. Load our signal
    signal_path = "data/monthly_signal.csv"
    if not os.path.exists(signal_path):
        print(f"ERROR: {signal_path} not found. Run swir_heat_index.py first.")
        return
    signal = pd.read_csv(signal_path)

    # 2. Try yfinance, fall back to manual data
    print("\nFetching price data...")
    try:
        import yfinance as yf
        print("  yfinance available — attempting live download")
        iron_ore_yf = fetch_yfinance("TIOc1", "iron_ore_usd")
        if iron_ore_yf is None or len(iron_ore_yf) < 12:
            raise ValueError("Insufficient data from yfinance")
        iron_ore = iron_ore_yf
        print("  Iron ore: live data fetched")
    except Exception:
        print("  yfinance unavailable or insufficient — using compiled dataset")
        iron_ore = build_manual_iron_ore()
        print(f"  Iron ore: {len(iron_ore)} months loaded")

    hrc = build_manual_hrc()
    print(f"  HRC steel: {len(hrc)} months loaded")

    # 3. Save raw price files
    iron_ore.to_csv("data/financial/iron_ore_prices.csv", index=False)
    hrc.to_csv("data/financial/hrc_steel_prices.csv", index=False)
    print("\nPrice files saved to data/financial/")

    # 4. Correlation analysis
    merged, corr_results = compute_financial_correlation(signal, iron_ore, hrc)

    # 5. Save merged dataset
    merged.to_csv("data/financial/financial_signal.csv", index=False)
    corr_results.to_csv("data/financial/financial_correlation.csv", index=False)

    print("Merged financial signal saved: data/financial/financial_signal.csv")
    print("\nNext step: run the dashboard (FastAPI + React)")
    print("All data ready for visualization.")


if __name__ == "__main__":
    main()
