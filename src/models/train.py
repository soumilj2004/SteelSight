"""
Steel Mill Activity Classifier — ResNet-18 Training Script

Binary classification: ACTIVE (1) vs IDLE (0)

HOW TO RUN (on Kaggle — free GPU):
    1. Upload this file + data/processed/ + data/labels/annotations.json to Kaggle
    2. Enable GPU: Settings → Accelerator → GPU T4 x2
    3. Run: python train.py
    4. Download: models/weights/best_model.pt

EXPECTED TRAINING TIME: ~20 minutes on Kaggle GPU
EXPECTED ACCURACY: 85-92% (we'll see)
"""

import os
import json
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
from pathlib import Path

# ── CONFIG ─────────────────────────────────────────────────────────────────────
ANNOTATIONS_JSON = "data/labels/annotations.json"
PROCESSED_DIR    = "data/processed"
WEIGHTS_DIR      = "models/weights"
BATCH_SIZE       = 32
EPOCHS           = 25
LR               = 1e-4
IMG_SIZE         = 224      # ResNet input size
DEVICE           = "cuda" if torch.cuda.is_available() else "cpu"
SEED             = 42
# ──────────────────────────────────────────────────────────────────────────────

torch.manual_seed(SEED)
np.random.seed(SEED)
os.makedirs(WEIGHTS_DIR, exist_ok=True)

LABEL_MAP = {"ACTIVE": 1, "IDLE": 0}


# ── DATASET ────────────────────────────────────────────────────────────────────
class MillDataset(Dataset):
    def __init__(self, samples: list, transform=None):
        """
        samples: list of (image_path, label_int) tuples
        """
        self.samples   = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, torch.tensor(label, dtype=torch.long)


def parse_annotations(json_path: str) -> list:
    """
    Parse Label Studio export JSON into (image_path, label) pairs.
    Skips SKIP_CLOUDY images.
    """
    with open(json_path) as f:
        data = json.load(f)

    samples = []
    for item in data:
        # Get annotation result
        annotations = item.get("annotations", [])
        if not annotations:
            continue

        result = annotations[0].get("result", [])
        if not result:
            continue

        label_str = result[0]["value"]["choices"][0]
        if label_str == "SKIP_CLOUDY":
            continue
        if label_str not in LABEL_MAP:
            continue

        # Get image path
        source_path = item["data"].get("source_path", "")
        if not os.path.exists(source_path):
            # Try relative path
            source_path = source_path.replace("file://", "")
        if not os.path.exists(source_path):
            continue

        samples.append((source_path, LABEL_MAP[label_str]))

    print(f"Loaded {len(samples)} labeled samples")
    active = sum(1 for _, l in samples if l == 1)
    idle   = sum(1 for _, l in samples if l == 0)
    print(f"  ACTIVE: {active} | IDLE: {idle}")
    return samples


# ── TRANSFORMS ─────────────────────────────────────────────────────────────────
train_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],   # ImageNet mean
                         [0.229, 0.224, 0.225]),   # ImageNet std
])

val_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])


# ── MODEL ──────────────────────────────────────────────────────────────────────
def build_model() -> nn.Module:
    """
    ResNet-18 pretrained on ImageNet, final layer replaced with binary output.
    
    Why ResNet-18?
    - Pretrained weights already understand edges, textures, shapes
    - We're just fine-tuning it to recognise smoke plumes specifically
    - Lightweight enough to run on CPU at inference time
    """
    model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)

    # Freeze all layers except the last block + classifier
    # This speeds up training significantly and prevents overfitting on small data
    for name, param in model.named_parameters():
        if "layer4" not in name and "fc" not in name:
            param.requires_grad = False

    # Replace final layer: 512 features → 2 classes (IDLE, ACTIVE)
    model.fc = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(512, 2)
    )
    return model


# ── TRAINING LOOP ──────────────────────────────────────────────────────────────
def train_epoch(model, loader, optimizer, criterion):
    model.train()
    total_loss, correct, total = 0, 0, 0

    for images, labels in loader:
        images, labels = images.to(DEVICE), labels.to(DEVICE)
        optimizer.zero_grad()
        outputs = model(images)
        loss    = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * images.size(0)
        _, predicted = outputs.max(1)
        correct += predicted.eq(labels).sum().item()
        total   += images.size(0)

    return total_loss / total, correct / total


def eval_epoch(model, loader, criterion):
    model.eval()
    total_loss, correct, total = 0, 0, 0
    all_preds, all_labels = [], []

    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = model(images)
            loss    = criterion(outputs, labels)

            total_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            correct += predicted.eq(labels).sum().item()
            total   += images.size(0)

            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    return total_loss / total, correct / total, all_preds, all_labels


def plot_training(train_losses, val_losses, train_accs, val_accs):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    ax1.plot(train_losses, label="Train Loss")
    ax1.plot(val_losses,   label="Val Loss")
    ax1.set_title("Loss")
    ax1.legend()

    ax2.plot(train_accs, label="Train Acc")
    ax2.plot(val_accs,   label="Val Acc")
    ax2.set_title("Accuracy")
    ax2.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(WEIGHTS_DIR, "training_curves.png"))
    plt.close()
    print("Saved training curves → models/weights/training_curves.png")


# ── MAIN ───────────────────────────────────────────────────────────────────────
def main():
    print(f"Device: {DEVICE}")
    print(f"PyTorch: {torch.__version__}\n")

    # Load data
    samples = parse_annotations(ANNOTATIONS_JSON)
    if len(samples) < 50:
        print("ERROR: Need at least 50 labeled samples. Label more images first.")
        return

    # Split 80/20 train/val, stratified
    train_samples, val_samples = train_test_split(
        samples, test_size=0.2, random_state=SEED,
        stratify=[l for _, l in samples]
    )
    print(f"\nTrain: {len(train_samples)} | Val: {len(val_samples)}")

    train_ds = MillDataset(train_samples, train_transform)
    val_ds   = MillDataset(val_samples,   val_transform)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=2)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=2)

    # Model
    model     = build_model().to(DEVICE)
    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()), lr=LR
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss()

    # Train
    best_val_acc = 0
    train_losses, val_losses, train_accs, val_accs = [], [], [], []

    print(f"\nTraining for {EPOCHS} epochs...\n")
    for epoch in range(1, EPOCHS + 1):
        tr_loss, tr_acc                          = train_epoch(model, train_loader, optimizer, criterion)
        vl_loss, vl_acc, vl_preds, vl_labels     = eval_epoch(model, val_loader, criterion)
        scheduler.step()

        train_losses.append(tr_loss); val_losses.append(vl_loss)
        train_accs.append(tr_acc);   val_accs.append(vl_acc)

        print(f"Epoch {epoch:02d}/{EPOCHS} | "
              f"Train Loss: {tr_loss:.4f} Acc: {tr_acc:.3f} | "
              f"Val Loss: {vl_loss:.4f} Acc: {vl_acc:.3f}")

        if vl_acc > best_val_acc:
            best_val_acc = vl_acc
            torch.save(model.state_dict(), os.path.join(WEIGHTS_DIR, "best_model.pt"))
            print(f"  ✓ Saved best model (val acc: {vl_acc:.3f})")

    # Final evaluation
    print(f"\n{'─'*50}")
    print(f"Best Val Accuracy: {best_val_acc:.3f}")
    print("\nClassification Report:")
    print(classification_report(vl_labels, vl_preds, target_names=["IDLE", "ACTIVE"]))

    print("Confusion Matrix:")
    print(confusion_matrix(vl_labels, vl_preds))

    plot_training(train_losses, val_losses, train_accs, val_accs)

    print(f"\n✓ Training complete")
    print(f"Model saved: models/weights/best_model.pt")
    print(f"Download this file and put it in your local models/weights/ folder")


if __name__ == "__main__":
    main()
