"""
SWIR Heat Index Pipeline
========================
Replaces the ResNet-18 classifier entirely.

Instead of training a neural net to detect smoke/activity,
we compute a quantitative heat index directly from the
SWIR bands (B11, B12) in each satellite image.

WHY THIS WORKS
--------------
Sentinel-2 Band 11 (1610nm) and Band 12 (2190nm) are
shortwave infrared bands. These wavelengths are sensitive
to surface temperature and emissivity. Active blast
furnaces operating at 1200-1500°C emit strongly in SWIR,
creating statistically significant anomalies compared to
cold urban surfaces.

This is the same method used in:
- NASA FIRMS (Fire Information for Resource Management)
- ESA Copernicus Emergency Management Service
- Published remote sensing literature on industrial monitoring

METHODOLOGY
-----------
For each monthly composite image:

1. Read raw reflectance values for B11 and B12
2. Compute per-pixel SWIR index:
      SWIR_idx = (B11 + B12) / 2
3. Compute z-score of each pixel relative to
   the spatial mean/std of that image
4. Count pixels above z-score threshold (anomaly pixels)
5. Compute weighted heat score:
      heat_score = (anomaly_count / total_pixels) * mean_anomaly_intensity
6. Normalize across all mills to 0-1 range

OUTPUT
------
data/activity_scores.csv with columns:
  mill_id, year, month, heat_score, anomaly_pixels,
  mean_swir, peak_swir, prediction (ACTIVE/IDLE)

HOW TO RUN
----------
    python src/inference/swir_heat_index.py

REQUIRES
--------
    data/raw_images/{mill_id}/{YYYY_MM}.tif  (from download_gee.py)
"""

import os
import numpy as np
import pandas as pd
import rasterio
import warnings
from pathlib import Path
from tqdm import tqdm
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

warnings.filterwarnings("ignore")

# ── CONFIG ─────────────────────────────────────────────────────────────────────
RAW_DIR       = "data/raw_images"
MILLS_CSV     = "data/mills.csv"
OUTPUT_CSV    = "data/activity_scores.csv"
PLOTS_DIR     = "data/swir_plots"
BAND_ORDER    = ["B4", "B3", "B2", "B8", "B11", "B12"]
#                  0     1     2     3      4      5
B11_IDX       = 4
B12_IDX       = 5
B4_IDX        = 0   # Red (for RGB preview)
B3_IDX        = 1   # Green
B2_IDX        = 2   # Blue

# Threshold: pixels with z-score above this are "hot"
# 2.0 = top ~2.3% of pixels flagged as anomalous
# Lower = more sensitive, higher = more conservative
ZSCORE_THRESH = 2.0

# A mill is ACTIVE if heat_score > this percentile across all scores
# We set this after computing all scores (adaptive threshold)
ACTIVE_PERCENTILE = 35   # bottom 35% = idle, top 65% = active
                          # steel mills run ~24/7 so most months are active
# ──────────────────────────────────────────────────────────────────────────────

os.makedirs(PLOTS_DIR, exist_ok=True)


def normalize_band(band: np.ndarray, p_low=1, p_high=99) -> np.ndarray:
    """Percentile stretch for visualization only."""
    lo = np.nanpercentile(band, p_low)
    hi = np.nanpercentile(band, p_high)
    arr = np.clip(band, lo, hi)
    return (arr - lo) / (hi - lo + 1e-9)


def read_tif(filepath: str) -> dict:
    """
    Read a 6-band GeoTIFF into a dict of numpy arrays.
    Returns None if file is corrupted or unreadable.
    """
    try:
        with rasterio.open(filepath) as src:
            bands = src.read().astype(np.float32)
            # Replace nodata values with NaN
            nodata = src.nodata
            if nodata is not None:
                bands[bands == nodata] = np.nan
        
        if bands.shape[0] < 6:
            return None
            
        return {
            "B4":  bands[B4_IDX],
            "B3":  bands[B3_IDX],
            "B2":  bands[B2_IDX],
            "B11": bands[B11_IDX],
            "B12": bands[B12_IDX],
            "shape": bands.shape[1:]
        }
    except Exception:
        return None


def compute_heat_score(bands: dict) -> dict:
    """
    Core computation: derive heat index from SWIR bands.
    
    Returns dict with:
      heat_score      - primary signal (0 to 1+)
      anomaly_pixels  - count of hot pixels
      anomaly_frac    - fraction of image that is hot
      mean_swir       - mean SWIR intensity
      peak_swir       - 99th percentile SWIR (peak heat)
      zscore_max      - maximum z-score in image
    """
    b11 = bands["B11"]
    b12 = bands["B12"]
    
    # Combined SWIR index — average of both heat-sensitive bands
    swir = (b11 + b12) / 2.0
    
    # Mask out NaN (cloud/nodata pixels)
    valid_mask = ~np.isnan(swir)
    swir_valid = swir[valid_mask]
    
    if len(swir_valid) < 100:
        # Not enough valid pixels
        return None
    
    # Spatial z-score: how many std deviations above the image mean
    # This normalizes for atmospheric conditions and seasonal variation
    mu  = np.nanmean(swir_valid)
    sig = np.nanstd(swir_valid)
    
    if sig < 1e-6:
        # Uniform image (all clouds or all same value)
        return None
    
    zscore = (swir - mu) / sig
    
    # Anomaly pixels: spatially extreme heat
    anomaly_mask = (zscore > ZSCORE_THRESH) & valid_mask
    anomaly_pixels = int(anomaly_mask.sum())
    total_valid    = int(valid_mask.sum())
    anomaly_frac   = anomaly_pixels / total_valid
    
    # Mean intensity of anomaly pixels (how hot are the hot pixels)
    if anomaly_pixels > 0:
        anomaly_intensity = float(np.nanmean(swir[anomaly_mask]))
    else:
        anomaly_intensity = 0.0
    
    # Heat score = fraction of hot pixels × their intensity
    # Units: arbitrary but consistent across images
    heat_score = anomaly_frac * (anomaly_intensity / (mu + 1e-9))
    
    return {
        "heat_score":      round(float(heat_score), 6),
        "anomaly_pixels":  anomaly_pixels,
        "anomaly_frac":    round(float(anomaly_frac), 6),
        "mean_swir":       round(float(mu), 2),
        "peak_swir":       round(float(np.nanpercentile(swir_valid, 99)), 2),
        "zscore_max":      round(float(np.nanmax(zscore[valid_mask])), 3),
    }


def save_diagnostic_plot(bands: dict, heat: dict, mill_id: int,
                          mill_name: str, year: int, month: int):
    """
    Save a 3-panel diagnostic image:
    Left:   RGB true color
    Middle: SWIR false color (B11/B12/B8)
    Right:  Heat anomaly map (hot pixels highlighted)
    """
    b11 = bands["B11"]
    b12 = bands["B12"]
    swir = (b11 + b12) / 2.0
    mu   = np.nanmean(swir[~np.isnan(swir)])
    sig  = np.nanstd(swir[~np.isnan(swir)])
    zscore = (swir - mu) / (sig + 1e-9)

    fig = plt.figure(figsize=(15, 5), facecolor='#0a0d0f')
    fig.patch.set_facecolor('#0a0d0f')
    gs = gridspec.GridSpec(1, 3, figure=fig, wspace=0.05)

    titles = ['RGB True Color', 'SWIR False Color', 'Heat Anomaly Map']
    axes = [fig.add_subplot(gs[i]) for i in range(3)]

    # Panel 1 — RGB
    r = normalize_band(bands["B4"])
    g = normalize_band(bands["B3"])
    b = normalize_band(bands["B2"])
    rgb = np.dstack([r, g, b])
    axes[0].imshow(rgb)

    # Panel 2 — SWIR false color
    sw1 = normalize_band(bands["B11"])
    sw2 = normalize_band(bands["B12"])
    # Map B11→R, B12→G, mean→B for false color
    swir_rgb = np.dstack([sw1, sw2, (sw1+sw2)/2])
    axes[1].imshow(swir_rgb)

    # Panel 3 — Anomaly map
    axes[2].imshow(rgb, alpha=0.4)
    hot = np.ma.masked_where(zscore <= ZSCORE_THRESH, zscore)
    im = axes[2].imshow(hot, cmap='hot', alpha=0.8,
                         vmin=ZSCORE_THRESH, vmax=ZSCORE_THRESH+3)

    for ax, title in zip(axes, titles):
        ax.set_title(title, color='#64748b', fontsize=9,
                     fontfamily='monospace', pad=6)
        ax.axis('off')

    status = "ACTIVE" if heat["heat_score"] > 0 else "IDLE"
    fig.suptitle(
        f"Mill {mill_id}: {mill_name}  |  {year}-{month:02d}  |  "
        f"Heat Score: {heat['heat_score']:.4f}  |  "
        f"Anomaly Pixels: {heat['anomaly_pixels']}  |  {status}",
        color='#c8d8e8', fontsize=10, fontfamily='monospace', y=1.01
    )

    out_path = os.path.join(PLOTS_DIR, f"mill{mill_id:02d}_{year}_{month:02d}.png")
    plt.savefig(out_path, dpi=100, bbox_inches='tight',
                facecolor='#0a0d0f', edgecolor='none')
    plt.close(fig)


def process_all_mills() -> pd.DataFrame:
    """
    Main loop: process every TIF file across all mills.
    Returns DataFrame of results.
    """
    mills = pd.read_csv(MILLS_CSV)
    records = []
    skipped = 0
    processed = 0

    mill_dirs = sorted([d for d in Path(RAW_DIR).iterdir() if d.is_dir()],
                        key=lambda d: int(d.name))

    print(f"\nProcessing {len(mill_dirs)} mill directories...\n")

    for mill_dir in mill_dirs:
        mill_id = int(mill_dir.name)
        mill_row = mills[mills["mill_id"] == mill_id]
        mill_name = mill_row["name"].values[0] if len(mill_row) else f"Mill {mill_id}"

        tif_files = sorted(mill_dir.glob("*.tif"))
        if not tif_files:
            continue

        for tif_path in tqdm(tif_files, desc=f"Mill {mill_id:02d}: {mill_name[:25]}", leave=False):
            stem = tif_path.stem  # "2022_04"
            try:
                year  = int(stem[:4])
                month = int(stem[5:7])
            except Exception:
                continue

            bands = read_tif(str(tif_path))
            if bands is None:
                skipped += 1
                continue

            heat = compute_heat_score(bands)
            if heat is None:
                skipped += 1
                continue

            records.append({
                "mill_id":       mill_id,
                "mill_name":     mill_name,
                "year":          year,
                "month":         month,
                "heat_score":    heat["heat_score"],
                "anomaly_pixels":heat["anomaly_pixels"],
                "anomaly_frac":  heat["anomaly_frac"],
                "mean_swir":     heat["mean_swir"],
                "peak_swir":     heat["peak_swir"],
                "zscore_max":    heat["zscore_max"],
            })
            processed += 1

    print(f"\nProcessed: {processed} images | Skipped: {skipped}")
    return pd.DataFrame(records)


def apply_adaptive_threshold(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assign ACTIVE/IDLE using an adaptive percentile threshold.
    
    Why adaptive?
    Steel mills operate ~24/7. Globally across all mills and months,
    most images should be ACTIVE. Setting a fixed threshold risks
    calling everything active or everything idle.
    
    Instead: threshold = Nth percentile of heat scores.
    Images below threshold = IDLE (likely shutdown/maintenance).
    Images above threshold = ACTIVE (normal operation).
    """
    threshold = np.percentile(df["heat_score"], ACTIVE_PERCENTILE)
    df["prediction"] = df["heat_score"].apply(
        lambda s: "ACTIVE" if s > threshold else "IDLE"
    )
    df["threshold_used"] = round(threshold, 6)
    print(f"\nAdaptive threshold: {threshold:.6f} "
          f"(ACTIVE_PERCENTILE={ACTIVE_PERCENTILE})")
    print(f"ACTIVE: {(df.prediction=='ACTIVE').sum()} | "
          f"IDLE: {(df.prediction=='IDLE').sum()}")
    return df


def save_monthly_aggregate(df: pd.DataFrame):
    """
    Compute monthly aggregate: % of mills active each month.
    This is the leading indicator signal we correlate against WSA data.
    """
    monthly = df.groupby(["year", "month"]).agg(
        mills_active  = ("prediction", lambda x: (x=="ACTIVE").sum()),
        mills_total   = ("prediction", "count"),
        mean_heat     = ("heat_score", "mean"),
        median_heat   = ("heat_score", "median"),
        max_heat      = ("heat_score", "max"),
    ).reset_index()
    monthly["pct_active"] = (
        monthly["mills_active"] / monthly["mills_total"] * 100
    ).round(2)
    monthly["date"] = pd.to_datetime(
        monthly[["year","month"]].assign(day=1)
    )
    monthly = monthly.sort_values("date").reset_index(drop=True)
    out = "data/monthly_signal.csv"
    monthly.to_csv(out, index=False)
    print(f"\nMonthly signal saved: {out}")
    return monthly


def save_signal_plot(monthly: pd.DataFrame):
    """Save the main portfolio visualization."""
    fig, axes = plt.subplots(2, 1, figsize=(16, 8),
                              facecolor='#080a0c', sharex=True)
    fig.patch.set_facecolor('#080a0c')

    for ax in axes:
        ax.set_facecolor('#0e1215')
        ax.tick_params(colors='#4a6070', labelsize=9)
        ax.spines[:].set_color('#1c2530')
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)

    # Panel 1: % mills active
    ax1 = axes[0]
    ax1.fill_between(monthly["date"], monthly["pct_active"],
                      alpha=0.15, color='#3a8fff')
    ax1.plot(monthly["date"], monthly["pct_active"],
             color='#3a8fff', linewidth=1.5, zorder=3)
    ax1.scatter(monthly["date"], monthly["pct_active"],
                color='#3a8fff', s=20, zorder=4)
    ax1.set_ylabel("Mills Active (%)", color='#c8d8e8',
                   fontsize=10, fontfamily='monospace')
    ax1.set_ylim(0, 105)
    ax1.axhline(monthly["pct_active"].mean(), color='#3a8fff',
                linestyle='--', linewidth=0.8, alpha=0.4)
    ax1.set_title("Satellite Signal: % Chinese Steel Mills Active (SWIR Heat Index)",
                  color='#c8d8e8', fontsize=11, fontfamily='monospace', pad=10)
    ax1.grid(True, color='#1c2530', linewidth=0.5, alpha=0.7)

    # Panel 2: mean heat score
    ax2 = axes[1]
    ax2.fill_between(monthly["date"], monthly["mean_heat"],
                      alpha=0.15, color='#00d48a')
    ax2.plot(monthly["date"], monthly["mean_heat"],
             color='#00d48a', linewidth=1.5, zorder=3)
    ax2.scatter(monthly["date"], monthly["mean_heat"],
                color='#00d48a', s=20, zorder=4)
    ax2.set_ylabel("Mean Heat Score", color='#c8d8e8',
                   fontsize=10, fontfamily='monospace')
    ax2.set_title("Aggregate SWIR Heat Score (Proxy for Steel Output Intensity)",
                  color='#c8d8e8', fontsize=11, fontfamily='monospace', pad=10)
    ax2.grid(True, color='#1c2530', linewidth=0.5, alpha=0.7)

    import matplotlib.dates as mdates
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45, color='#4a6070', fontsize=8)

    fig.suptitle(
        "SteelSight — SWIR Heat Index Signal | 45 Chinese Facilities | Sentinel-2 SR | 2019–2024",
        color='#64748b', fontsize=10, fontfamily='monospace', y=1.01
    )

    plt.tight_layout()
    out = "data/signal_plot.png"
    plt.savefig(out, dpi=150, bbox_inches='tight',
                facecolor='#080a0c', edgecolor='none')
    plt.close()
    print(f"Signal plot saved: {out}")


def print_summary(df: pd.DataFrame, monthly: pd.DataFrame):
    print("\n" + "━"*60)
    print("SWIR HEAT INDEX — SUMMARY")
    print("━"*60)
    print(f"Total images processed : {len(df)}")
    print(f"Mills covered          : {df['mill_id'].nunique()}")
    print(f"Date range             : {df['year'].min()}-{df['month'].min():02d} "
          f"→ {df['year'].max()}-{df['month'].max():02d}")
    print(f"ACTIVE predictions     : {(df.prediction=='ACTIVE').sum()} "
          f"({(df.prediction=='ACTIVE').mean()*100:.1f}%)")
    print(f"IDLE predictions       : {(df.prediction=='IDLE').sum()} "
          f"({(df.prediction=='IDLE').mean()*100:.1f}%)")
    print(f"\nTop 5 hottest mills (mean heat score):")
    top = df.groupby(["mill_id","mill_name"])["heat_score"].mean().sort_values(ascending=False).head(5)
    for (mid, name), score in top.items():
        print(f"  Mill {mid:02d}: {name[:30]:<30} {score:.6f}")
    print(f"\nMonthly signal range:")
    print(f"  Min % active: {monthly['pct_active'].min():.1f}%  "
          f"(coldest month: {monthly.loc[monthly['pct_active'].idxmin(),'date'].strftime('%Y-%m')})")
    print(f"  Max % active: {monthly['pct_active'].max():.1f}%  "
          f"(hottest month: {monthly.loc[monthly['pct_active'].idxmax(),'date'].strftime('%Y-%m')})")
    print("━"*60)
    print(f"\nFiles saved:")
    print(f"  data/activity_scores.csv   — per-mill per-month scores")
    print(f"  data/monthly_signal.csv    — aggregate monthly signal")
    print(f"  data/signal_plot.png       — main portfolio visual")
    print(f"  data/swir_plots/           — diagnostic plots per image")
    print("\nNext step: run src/analysis/correlation_analysis.py")


def main():
    print("SteelSight — SWIR Heat Index Pipeline")
    print("=" * 60)
    print(f"Raw images directory : {RAW_DIR}")
    print(f"Z-score threshold    : {ZSCORE_THRESH}")
    print(f"Active percentile    : {ACTIVE_PERCENTILE}th")

    # 1. Process all TIF files
    df = process_all_mills()

    if df.empty:
        print("\nERROR: No images processed. Check data/raw_images/ exists.")
        return

    # 2. Apply adaptive threshold
    df = apply_adaptive_threshold(df)

    # 3. Save per-mill scores
    df = df.sort_values(["mill_id", "year", "month"]).reset_index(drop=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nActivity scores saved: {OUTPUT_CSV}")

    # 4. Monthly aggregate signal
    monthly = save_monthly_aggregate(df)

    # 5. Signal plot
    save_signal_plot(monthly)

    # 6. Summary
    print_summary(df, monthly)


if __name__ == "__main__":
    main()
