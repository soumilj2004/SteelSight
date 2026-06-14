"""
Batch Inference — Classify all mill images → monthly activity scores

Runs the trained ResNet-18 on every image in data/processed/
Outputs a CSV: mill_id, year, month, activity_score (0.0 to 1.0)

HOW TO RUN:
    python inference.py

REQUIRES:
    models/weights/best_model.pt   ← from training step

OUTPUT:
    data/activity_scores.csv
"""

import os
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from torchvision import models, transforms
from PIL import Image
from pathlib import Path
from tqdm import tqdm

WEIGHTS_PATH  = "models/weights/best_model.pt"
PROCESSED_DIR = "data/processed"
OUTPUT_CSV    = "data/activity_scores.csv"
MILLS_CSV     = "data/mills.csv"
IMG_SIZE      = 224
DEVICE        = "cuda" if torch.cuda.is_available() else "cpu"
BATCH_SIZE    = 64


def load_model(weights_path: str) -> nn.Module:
    model = models.resnet18(weights=None)
    model.fc = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(512, 2)
    )
    model.load_state_dict(torch.load(weights_path, map_location=DEVICE))
    model.eval()
    model.to(DEVICE)
    print(f"Model loaded from {weights_path}")
    return model


transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])


def predict_batch(model, image_paths: list) -> np.ndarray:
    """
    Returns probability of ACTIVE (class 1) for each image.
    Shape: (N,)
    """
    tensors = []
    valid_paths = []
    for path in image_paths:
        try:
            img = Image.open(path).convert("RGB")
            tensors.append(transform(img))
            valid_paths.append(path)
        except Exception as e:
            print(f"  Failed to load {path}: {e}")

    if not tensors:
        return np.array([])

    batch = torch.stack(tensors).to(DEVICE)
    with torch.no_grad():
        logits = model(batch)
        probs  = torch.softmax(logits, dim=1)[:, 1]  # P(ACTIVE)
    return probs.cpu().numpy()


def main():
    model = load_model(WEIGHTS_PATH)
    mills = pd.read_csv(MILLS_CSV)

    records = []
    mill_dirs = sorted([d for d in Path(PROCESSED_DIR).iterdir() if d.is_dir()])

    print(f"\nRunning inference on {len(mill_dirs)} mills...")

    for mill_dir in tqdm(mill_dirs):
        mill_id = int(mill_dir.name)

        # Get all combined images for this mill
        combined_imgs = sorted(mill_dir.glob("*_combined.png"))
        if not combined_imgs:
            continue

        for img_path in combined_imgs:
            stem = img_path.stem.replace("_combined", "")  # "2022_04"
            try:
                year, month = int(stem[:4]), int(stem[5:7])
            except Exception:
                continue

            probs = predict_batch(model, [str(img_path)])
            if len(probs) == 0:
                continue

            activity_score = float(probs[0])
            records.append({
                "mill_id":        mill_id,
                "year":           year,
                "month":          month,
                "activity_score": activity_score,
                "prediction":     "ACTIVE" if activity_score > 0.5 else "IDLE"
            })

    df = pd.DataFrame(records)
    df = df.sort_values(["mill_id", "year", "month"]).reset_index(drop=True)
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"\n✓ Inference complete")
    print(f"Results saved: {OUTPUT_CSV}")
    print(f"\nSample output:")
    print(df.head(10).to_string(index=False))

    # Summary stats
    print(f"\n{'─'*40}")
    print(f"Total records: {len(df)}")
    print(f"Active predictions: {(df.prediction == 'ACTIVE').sum()}")
    print(f"Idle predictions:   {(df.prediction == 'IDLE').sum()}")
    print(f"Date range: {df.year.min()}-{df.month.min():02d} → {df.year.max()}-{df.month.max():02d}")


if __name__ == "__main__":
    main()
