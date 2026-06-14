"""
Steel Mill Satellite Image Downloader
Uses Google Earth Engine directly (no geemap dependency).

HOW TO RUN:
    python src/data_pipeline/download_gee.py

OUTPUT:
    data/raw_images/{mill_id}/{YYYY_MM}.tif
"""

import ee
import pandas as pd
import os
import math
import time
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ── CONFIG ─────────────────────────────────────────────────────────────────────
PROJECT_ID    = "neon-polymer-463809-j6"
MILLS_CSV     = "data/mills.csv"
OUTPUT_DIR    = "data/raw_images"
START_DATE    = "2019-01-01"
END_DATE      = "2024-12-31"
CHIP_SIZE_KM  = 3
CLOUD_THRESH  = 20
SCALE         = 10
BANDS         = ["B4", "B3", "B2", "B8", "B11", "B12"]
# ──────────────────────────────────────────────────────────────────────────────


def init_gee():
    ee.Initialize(project=PROJECT_ID)
    print("GEE initialized ✓")


def make_bbox(lat, lon, km):
    delta_lat = km / 111.0
    delta_lon = km / (111.0 * math.cos(math.radians(lat)))
    return ee.Geometry.Rectangle([
        lon - delta_lon, lat - delta_lat,
        lon + delta_lon, lat + delta_lat
    ])


def get_monthly_composite(bbox, year, month):
    start = f"{year}-{month:02d}-01"
    next_month = datetime(year, month, 1) + relativedelta(months=1)
    end = next_month.strftime("%Y-%m-%d")

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(bbox)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", CLOUD_THRESH))
        .select(BANDS)
    )

    count = collection.size().getInfo()
    if count == 0:
        return None

    return collection.median().clip(bbox)


def download_image(image, bbox, filepath):
    """
    Download a GEE image directly using the getDownloadURL method.
    No geemap needed.
    """
    url = image.getDownloadURL({
        "scale":  SCALE,
        "region": bbox,
        "format": "GEO_TIFF",
        "bands":  BANDS,
    })

    response = requests.get(url, stream=True, timeout=300)
    response.raise_for_status()

    with open(filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


def download_mill(mill):
    mill_id  = int(mill["mill_id"])
    mill_dir = os.path.join(OUTPUT_DIR, str(mill_id))
    os.makedirs(mill_dir, exist_ok=True)

    bbox    = make_bbox(mill["lat"], mill["lon"], CHIP_SIZE_KM)
    current = datetime.strptime(START_DATE, "%Y-%m-%d")
    end     = datetime.strptime(END_DATE,   "%Y-%m-%d")

    while current <= end:
        year, month = current.year, current.month
        filename = f"{year}_{month:02d}.tif"
        filepath = os.path.join(mill_dir, filename)

        if os.path.exists(filepath):
            print(f"  [{mill_id}] {filename} already exists, skipping")
            current += relativedelta(months=1)
            continue

        try:
            image = get_monthly_composite(bbox, year, month)
            if image is None:
                print(f"  [{mill_id}] {filename} — no clear images, skipping")
                current += relativedelta(months=1)
                continue

            print(f"  [{mill_id}] Downloading {filename}...", end=" ", flush=True)
            download_image(image, bbox, filepath)
            size_kb = os.path.getsize(filepath) / 1024
            print(f"✓ ({size_kb:.0f} KB)")

        except Exception as e:
            print(f"FAILED: {e}")
            time.sleep(2)  # brief pause before next attempt

        current += relativedelta(months=1)


def main():
    init_gee()
    mills = pd.read_csv(MILLS_CSV)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\nDownloading imagery for {len(mills)} mills")
    print(f"Date range: {START_DATE} → {END_DATE}")
    print(f"Bands: {BANDS}\n")
    print("─" * 50)

    for _, mill in mills.iterrows():
        print(f"\nMill {int(mill['mill_id'])}: {mill['name']} ({mill['province']})")
        download_mill(mill)

    print("\n✓ All downloads complete")
    print(f"Images saved to: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()