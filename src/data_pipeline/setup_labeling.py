"""
Label Studio Setup for Steel Mill Activity Labeling

HOW TO RUN:
    1. pip install label-studio
    2. python setup_labeling.py   ← generates the import JSON
    3. label-studio start         ← opens browser at localhost:8080
    4. Follow instructions below

LABELING INSTRUCTIONS (your job):
─────────────────────────────────
For each image you will see two panels side by side:
  LEFT  → RGB true color (what you'd see normally)
  RIGHT → SWIR false color (heat/smoke highlighted)

Label each image as ONE of:
  ✅ ACTIVE  — mill is running
     Signs: smoke plume visible, orange/red glow in SWIR view,
            steam clouds, dark exhaust from multiple chimneys
  ❌ IDLE    — mill is not running (or running very low)
     Signs: no smoke, clean chimneys, no heat signature in SWIR,
            facility looks cold/grey

WHEN IN DOUBT:
  - If you see ANY smoke → ACTIVE
  - If you see heat glow in SWIR but no visible smoke → ACTIVE
  - If it's completely clean → IDLE
  - If cloud covers the whole image → SKIP (delete it)

TARGET: Label at least 250 images (125 active, 125 idle ideally)
TIME:   ~3-4 hours, do it in 2 sessions
"""

import os
import json
from pathlib import Path

PROCESSED_DIR = "data/processed"
OUTPUT_JSON   = "data/labels/label_studio_import.json"


def generate_import_json():
    """
    Generates a JSON file to bulk-import all combined images
    into Label Studio as unlabeled tasks.
    """
    os.makedirs("data/labels", exist_ok=True)

    tasks = []
    combined_images = sorted(Path(PROCESSED_DIR).rglob("*_combined.png"))

    for img_path in combined_images:
        # Label Studio needs a URL or local path
        # When running locally, use the absolute path
        abs_path = str(img_path.resolve())
        parts    = img_path.parts

        # Extract mill_id and date from path
        mill_id = parts[-2]
        stem    = img_path.stem  # e.g. "2022_04_combined"
        date    = stem.replace("_combined", "")  # "2022_04"

        tasks.append({
            "data": {
                "image": f"file://{abs_path}",
                "mill_id": mill_id,
                "date": date,
                "source_path": abs_path
            }
        })

    with open(OUTPUT_JSON, "w") as f:
        json.dump(tasks, f, indent=2)

    print(f"Generated {len(tasks)} tasks → {OUTPUT_JSON}")
    return len(tasks)


# Label Studio project config (XML format)
LABEL_CONFIG = """
<View>
  <Header value="Steel Mill Activity Labeling"/>
  <Text name="info" value="Mill: $mill_id | Date: $date"/>
  
  <Image name="image" value="$image" zoom="true" zoomControl="true"/>
  
  <Choices name="activity" toName="image" choice="single" showInLine="true">
    <Choice value="ACTIVE" 
            style="background-color: #22c55e; color: white; font-weight: bold;"
            hotkey="a"/>
    <Choice value="IDLE"   
            style="background-color: #ef4444; color: white; font-weight: bold;"
            hotkey="i"/>
    <Choice value="SKIP_CLOUDY" 
            style="background-color: #94a3b8; color: white;"
            hotkey="s"/>
  </Choices>
</View>
"""


def print_label_studio_steps():
    print("""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LABEL STUDIO SETUP — FOLLOW THESE STEPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Install and start Label Studio
    pip install label-studio
    label-studio start

Step 2: Create new project
    Name: "Steel Mill Activity"
    
Step 3: Set labeling interface
    Go to Settings → Labeling Interface → Code
    Paste this XML:

""")
    print(LABEL_CONFIG)
    print("""
Step 4: Import tasks
    Go to Import → Upload Files
    Upload: data/labels/label_studio_import.json

Step 5: Start labeling!
    Keyboard shortcuts:
      A → ACTIVE
      I → IDLE  
      S → SKIP (cloudy image)
      
Step 6: Export when done
    Export → JSON → save as data/labels/annotations.json
    Tell me when exported — I'll run the next script.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


if __name__ == "__main__":
    print("Generating Label Studio import file...")
    count = generate_import_json()
    print(f"Total images to label: {count}")
    print(f"You only need to label ~250 of them.\n")
    print_label_studio_steps()
