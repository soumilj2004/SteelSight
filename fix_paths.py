import json
import os

with open('data/labels/label_studio_import.json') as f:
    tasks = json.load(f)

for t in tasks:
    p = t['data']['source_path'].replace('\\', '/')
    idx = p.find('processed/')
    rel = p[idx + len('processed/'):]
    # Use Label Studio local file serving format
    t['data']['image'] = '/data/local-files/?d=' + rel

with open('data/labels/label_studio_import.json', 'w') as f:
    json.dump(tasks, f)

print(f'Done — updated {len(tasks)} image paths')
print('Now reimport data/labels/label_studio_import.json in Label Studio')