"""
Preprocess raw GeoTIFF images into PNG chips ready for labeling.

- Reads multi-band GeoTIFF (B4, B3, B2, B8, B11, B12)
- Exports:
    1. RGB visible image (B4/B3/B2) → for human labeling
    2. SWIR composite (B11/B12/B8) → highlights heat signatures
    3. Merged side-by-side view    → what you'll actually label in Label Studio

HOW TO RUN:
    python preprocess.py

OUTPUT:
    data/processed/{mill_id}/{YYYY_MM}_rgb.png
    data/processed/{mill_id}/{YYYY_MM}_swir.png
    data/processed/{mill_id}/{YYYY_MM}_combined.png
"""

import os
import numpy as np
import rasterio
import cv2
from pathlib import Path
import pandas as pd

RAW_DIR   = "data/raw_images"
OUT_DIR   = "data/processed"
MILLS_CSV = "data/mills.csv"


def normalize_band(band: np.ndarray, p_low=2, p_high=98) -> np.ndarray:
    """
    Percentile stretch normalization.
    Cuts the bottom 2% and top 2% of values, then scales to 0-255.
    Makes dark satellite images visually clear.
    """
    lo = np.percentile(band, p_low)
    hi = np.percentile(band, p_high)
    band = np.clip(band, lo, hi)
    band = (band - lo) / (hi - lo + 1e-8)
    return (band * 255).astype(np.uint8)


def read_tif(filepath: str):
    """
    Read a multi-band GeoTIFF.
    Returns dict of band arrays: {"B4": arr, "B3": arr, ...}
    Band order in file matches BANDS list in download_gee.py:
    index 0=B4, 1=B3, 2=B2, 3=B8, 4=B11, 5=B12
    """
    with rasterio.open(filepath) as src:
        bands = src.read()  # shape: (6, H, W)

    return {
        "B4":  bands[0],   # Red
        "B3":  bands[1],   # Green
        "B2":  bands[2],   # Blue
        "B8":  bands[3],   # NIR
        "B11": bands[4],   # SWIR1 — heat sensitive
        "B12": bands[5],   # SWIR2 — heat sensitive
    }


def make_rgb(bands: dict) -> np.ndarray:
    """True color RGB image (what a human sees from space)."""
    r = normalize_band(bands["B4"])
    g = normalize_band(bands["B3"])
    b = normalize_band(bands["B2"])
    return cv2.merge([b, g, r])  # OpenCV uses BGR


def make_swir(bands: dict) -> np.ndarray:
    """
    SWIR false color composite.
    Maps SWIR1→R, SWIR2→G, NIR→B.
    Active furnaces glow bright red/orange in this view.
    Smoke plumes show as white/grey streaks.
    """
    r = normalize_band(bands["B11"])
    g = normalize_band(bands["B12"])
    b = normalize_band(bands["B8"])
    return cv2.merge([b, g, r])


def make_combined(rgb: np.ndarray, swir: np.ndarray, label: str = "") -> np.ndarray:
    """
    Side-by-side: RGB | SWIR with a label bar at top.
    This is what you'll see in Label Studio.
    """
    h, w = rgb.shape[:2]
    combined = np.zeros((h + 30, w * 2 + 10, 3), dtype=np.uint8)
    combined[30:, :w] = rgb
    combined[30:, w+10:] = swir

    # header bar
    combined[:30] = (40, 40, 40)
    cv2.putText(combined, "RGB (True Color)", (5, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    cv2.putText(combined, "SWIR (Heat/Smoke)", (w + 15, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    if label:
        cv2.putText(combined, label, (w - 60, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 100), 1)
    return combined


def resize_to_square(img: np.ndarray, size=512) -> np.ndarray:
    """Resize to fixed size for consistent model input."""
    return cv2.resize(img, (size, size), interpolation=cv2.INTER_LANCZOS4)


def process_mill(mill_id: int, mill_name: str):
    raw_mill_dir = os.path.join(RAW_DIR, str(mill_id))
    out_mill_dir = os.path.join(OUT_DIR, str(mill_id))
    os.makedirs(out_mill_dir, exist_ok=True)

    tif_files = sorted(Path(raw_mill_dir).glob("*.tif"))
    if not tif_files:
        print(f"  Mill {mill_id}: no TIF files found, skipping")
        return

    for tif_path in tif_files:
        stem = tif_path.stem  # e.g. "2022_04"
        out_rgb      = os.path.join(out_mill_dir, f"{stem}_rgb.png")
        out_swir     = os.path.join(out_mill_dir, f"{stem}_swir.png")
        out_combined = os.path.join(out_mill_dir, f"{stem}_combined.png")

        if os.path.exists(out_combined):
            continue

        try:
            bands   = read_tif(str(tif_path))
            rgb     = resize_to_square(make_rgb(bands))
            swir    = resize_to_square(make_swir(bands))
            combined = make_combined(rgb, swir, label=f"Mill {mill_id} | {stem}")

            cv2.imwrite(out_rgb, rgb)
            cv2.imwrite(out_swir, swir)
            cv2.imwrite(out_combined, combined)
            print(f"  [{mill_id}] {stem} ✓")

        except Exception as e:
            print(f"  [{mill_id}] {stem} FAILED: {e}")


def main():
    mills = pd.read_csv(MILLS_CSV)
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Processing {len(mills)} mills...\n")
    for _, row in mills.iterrows():
        mill_id = int(row["mill_id"])
        print(f"Mill {mill_id}: {row['name']}")
        process_mill(mill_id, row["name"])

    print("\n✓ Preprocessing complete")
    print(f"Output: {OUT_DIR}/")


if __name__ == "__main__":
    main()
