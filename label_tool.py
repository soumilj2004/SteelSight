"""
SteelSight Annotation Studio
Run: python label_tool.py
Open: http://localhost:9000
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json, os, glob, urllib.parse

PROCESSED_DIR = "data/processed"
OUTPUT_FILE   = "data/labels/annotations.json"

def get_all_images():
    images = []
    for path in sorted(glob.glob(f"{PROCESSED_DIR}/**/*_combined.png", recursive=True)):
        path = path.replace("\\", "/")
        parts = path.split("/")
        mill_id = parts[-2]
        stem = parts[-1].replace("_combined.png", "")
        year, month = stem[:4], stem[5:7]
        images.append({"path": path, "mill_id": mill_id, "date": stem,
                        "year": year, "month": month, "id": f"{mill_id}_{stem}"})
    return images

def load_annotations():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f: return json.load(f)
    return {}

def save_annotations(a):
    os.makedirs("data/labels", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f: json.dump(a, f, indent=2)

IMAGES = get_all_images()
ANNOTATIONS = load_annotations()

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SteelSight — Annotation Studio</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg:        #080a0c;
  --surface:   #0e1215;
  --panel:     #131820;
  --border:    #1c2530;
  --border2:   #243040;
  --text:      #c8d8e8;
  --muted:     #4a6070;
  --dim:       #2a3a4a;
  --active:    #00d48a;
  --active-bg: #00d48a18;
  --idle:      #ff4060;
  --idle-bg:   #ff406018;
  --skip:      #4a6070;
  --skip-bg:   #4a607018;
  --accent:    #3a8fff;
  --mono:      'IBM Plex Mono', monospace;
  --sans:      'IBM Plex Sans', sans-serif;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; background: var(--bg); color: var(--text); font-family: var(--sans); }

/* ── Layout ── */
#app { display: grid; grid-template-rows: 48px 1fr; height: 100vh; }

/* ── Topbar ── */
#topbar {
  display: grid;
  grid-template-columns: 260px 1fr 260px;
  align-items: center;
  padding: 0 20px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  gap: 20px;
}
#logo { display: flex; align-items: center; gap: 10px; }
#logo-mark {
  width: 24px; height: 24px;
  border: 1.5px solid var(--accent);
  display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 2px; padding: 3px;
}
#logo-mark span { background: var(--accent); border-radius: 1px; }
#logo-mark span:nth-child(2) { background: var(--active); }
#logo-mark span:nth-child(3) { background: transparent; border: 1px solid var(--dim); }
#logo-text { font-family: var(--mono); font-size: 13px; font-weight: 600; letter-spacing: 2px; color: var(--text); }
#logo-sub { font-size: 10px; color: var(--muted); letter-spacing: 1px; font-family: var(--mono); }

#progress-wrap { display: flex; flex-direction: column; gap: 5px; }
#progress-track { height: 2px; background: var(--border); border-radius: 1px; overflow: hidden; }
#progress-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--active)); border-radius: 1px; transition: width 0.4s cubic-bezier(.4,0,.2,1); width: 0%; }
#progress-labels { display: flex; justify-content: space-between; font-family: var(--mono); font-size: 10px; color: var(--muted); }
#prog-count { color: var(--text); font-weight: 500; }

#nav-controls { display: flex; align-items: center; justify-content: flex-end; gap: 8px; }
.nav-btn {
  padding: 6px 14px; background: var(--panel); border: 1px solid var(--border2);
  color: var(--muted); font-family: var(--mono); font-size: 11px; cursor: pointer;
  border-radius: 3px; transition: all 0.15s; letter-spacing: 0.5px;
}
.nav-btn:hover { border-color: var(--accent); color: var(--text); }
#idx-display { font-family: var(--mono); font-size: 11px; color: var(--muted); padding: 0 8px; }

/* ── Main content ── */
#content { display: grid; grid-template-columns: 1fr 260px; overflow: hidden; }

/* ── Image area ── */
#image-wrap {
  position: relative; display: flex; align-items: center; justify-content: center;
  background: var(--bg); overflow: hidden; padding: 24px;
}
#image-wrap::before {
  content: '';
  position: absolute; inset: 0;
  background: 
    linear-gradient(rgba(58,143,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(58,143,255,0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
}
#img {
  max-width: 100%; max-height: 100%; object-fit: contain;
  border-radius: 2px;
  box-shadow: 0 0 0 1px var(--border), 0 20px 60px rgba(0,0,0,0.6);
  transition: opacity 0.2s;
}
#img.loading { opacity: 0.3; }

/* image label overlay */
#img-labels {
  position: absolute; bottom: 32px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 2px;
  background: var(--surface); border: 1px solid var(--border); border-radius: 3px;
  padding: 4px 10px; font-family: var(--mono); font-size: 10px; color: var(--muted);
  pointer-events: none;
}
#img-labels span { color: var(--dim); margin: 0 6px; }

/* current label badge */
#label-badge {
  position: absolute; top: 32px; right: 32px;
  font-family: var(--mono); font-size: 11px; font-weight: 600; letter-spacing: 2px;
  padding: 5px 12px; border-radius: 2px; border: 1px solid;
  transition: all 0.2s;
  opacity: 0;
}
#label-badge.show { opacity: 1; }
#label-badge.ACTIVE { background: var(--active-bg); border-color: var(--active); color: var(--active); }
#label-badge.IDLE   { background: var(--idle-bg);   border-color: var(--idle);   color: var(--idle); }
#label-badge.SKIP   { background: var(--skip-bg);   border-color: var(--skip);   color: var(--skip); }

/* ── Sidebar ── */
#sidebar {
  background: var(--surface); border-left: 1px solid var(--border);
  display: flex; flex-direction: column; overflow-y: auto;
}

.sidebar-section {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}
.section-label {
  font-family: var(--mono); font-size: 9px; font-weight: 600;
  letter-spacing: 2.5px; color: var(--muted); text-transform: uppercase;
  margin-bottom: 12px;
}

/* metadata */
#meta-grid { display: flex; flex-direction: column; gap: 8px; }
.meta-row { display: flex; justify-content: space-between; align-items: baseline; }
.meta-key { font-family: var(--mono); font-size: 10px; color: var(--muted); letter-spacing: 0.5px; }
.meta-val { font-family: var(--mono); font-size: 11px; color: var(--text); font-weight: 500; }

/* action buttons */
#actions { display: flex; flex-direction: column; gap: 6px; }
.action-btn {
  width: 100%; padding: 11px 16px;
  background: var(--panel); border: 1px solid var(--border2);
  color: var(--text); font-family: var(--mono); font-size: 11px; font-weight: 600;
  cursor: pointer; border-radius: 3px; text-align: left;
  display: flex; justify-content: space-between; align-items: center;
  transition: all 0.15s; letter-spacing: 1px;
}
.action-btn .key { 
  font-size: 9px; padding: 2px 6px; border-radius: 2px;
  background: var(--border); color: var(--muted); letter-spacing: 1px;
}
.action-btn:hover { transform: translateX(2px); }
#btn-active { border-left: 2px solid var(--active); }
#btn-active:hover { background: var(--active-bg); border-color: var(--active); color: var(--active); }
#btn-active:hover .key { background: var(--active-bg); color: var(--active); }
#btn-idle { border-left: 2px solid var(--idle); }
#btn-idle:hover { background: var(--idle-bg); border-color: var(--idle); color: var(--idle); }
#btn-idle:hover .key { background: var(--idle-bg); color: var(--idle); }
#btn-skip { border-left: 2px solid var(--dim); }
#btn-skip:hover { background: var(--skip-bg); border-color: var(--skip); color: var(--skip); }

.action-btn.selected-active { background: var(--active-bg); border-color: var(--active); color: var(--active); }
.action-btn.selected-idle   { background: var(--idle-bg);   border-color: var(--idle);   color: var(--idle); }
.action-btn.selected-skip   { background: var(--skip-bg);   border-color: var(--skip);   color: var(--skip); }

/* stats */
#stats-grid { display: flex; flex-direction: column; gap: 10px; }
.stat-row { display: flex; flex-direction: column; gap: 4px; }
.stat-header { display: flex; justify-content: space-between; }
.stat-label { font-family: var(--mono); font-size: 10px; color: var(--muted); }
.stat-val { font-family: var(--mono); font-size: 10px; font-weight: 600; }
.stat-val.active { color: var(--active); }
.stat-val.idle   { color: var(--idle); }
.stat-val.skip   { color: var(--muted); }
.stat-bar { height: 2px; background: var(--border); border-radius: 1px; overflow: hidden; }
.stat-bar-fill { height: 100%; border-radius: 1px; transition: width 0.4s; }
.fill-active { background: var(--active); }
.fill-idle   { background: var(--idle); }
.fill-skip   { background: var(--dim); }

/* guide */
#guide { flex: 1; padding: 16px 20px; }
.guide-label { font-family: var(--mono); font-size: 9px; font-weight: 600; letter-spacing: 2.5px; color: var(--muted); text-transform: uppercase; margin-bottom: 10px; }
.guide-item { display: flex; gap: 8px; margin-bottom: 10px; align-items: flex-start; }
.guide-dot { width: 6px; height: 6px; border-radius: 50%; margin-top: 4px; flex-shrink: 0; }
.guide-dot.a { background: var(--active); }
.guide-dot.i { background: var(--idle); }
.guide-text { font-size: 11px; color: var(--muted); line-height: 1.6; }

/* save flash */
#save-flash {
  position: fixed; bottom: 20px; right: 20px;
  font-family: var(--mono); font-size: 10px; letter-spacing: 1px;
  padding: 8px 16px; background: var(--surface); border: 1px solid var(--active);
  color: var(--active); border-radius: 2px;
  opacity: 0; transition: opacity 0.3s; pointer-events: none;
}
#save-flash.show { opacity: 1; }

/* scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
</style>
</head>
<body>
<div id="app">

  <!-- Topbar -->
  <div id="topbar">
    <div id="logo">
      <div id="logo-mark">
        <span></span><span></span><span></span><span></span>
      </div>
      <div>
        <div id="logo-text">STEELSIGHT</div>
        <div id="logo-sub">ANNOTATION STUDIO</div>
      </div>
    </div>
    <div id="progress-wrap">
      <div id="progress-labels">
        <span>ANNOTATION PROGRESS</span>
        <span id="prog-count">0 / 250</span>
      </div>
      <div id="progress-track"><div id="progress-fill"></div></div>
    </div>
    <div id="nav-controls">
      <button class="nav-btn" onclick="go(-1)">PREV</button>
      <span id="idx-display">— / —</span>
      <button class="nav-btn" onclick="go(1)">NEXT</button>
    </div>
  </div>

  <!-- Main -->
  <div id="content">
    <div id="image-wrap">
      <img id="img" src="" alt=""/>
      <div id="img-labels">RGB TRUE COLOR <span>|</span> SWIR HEAT/SMOKE</div>
      <div id="label-badge"></div>
    </div>

    <div id="sidebar">

      <!-- Meta -->
      <div class="sidebar-section">
        <div class="section-label">Image Metadata</div>
        <div id="meta-grid">
          <div class="meta-row">
            <span class="meta-key">FACILITY ID</span>
            <span class="meta-val" id="m-mill">—</span>
          </div>
          <div class="meta-row">
            <span class="meta-key">PERIOD</span>
            <span class="meta-val" id="m-date">—</span>
          </div>
          <div class="meta-row">
            <span class="meta-key">SOURCE</span>
            <span class="meta-val">SENTINEL-2 SR</span>
          </div>
          <div class="meta-row">
            <span class="meta-key">RESOLUTION</span>
            <span class="meta-val">10 m/px</span>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="sidebar-section">
        <div class="section-label">Classification</div>
        <div id="actions">
          <button class="action-btn" id="btn-active" onclick="label('ACTIVE')">
            ACTIVE <span class="key">A</span>
          </button>
          <button class="action-btn" id="btn-idle" onclick="label('IDLE')">
            IDLE <span class="key">I</span>
          </button>
          <button class="action-btn" id="btn-skip" onclick="label('SKIP')">
            SKIP CLOUDY <span class="key">S</span>
          </button>
        </div>
      </div>

      <!-- Stats -->
      <div class="sidebar-section">
        <div class="section-label">Session Statistics</div>
        <div id="stats-grid">
          <div class="stat-row">
            <div class="stat-header">
              <span class="stat-label">ACTIVE</span>
              <span class="stat-val active" id="s-active">0</span>
            </div>
            <div class="stat-bar"><div class="stat-bar-fill fill-active" id="bar-active" style="width:0%"></div></div>
          </div>
          <div class="stat-row">
            <div class="stat-header">
              <span class="stat-label">IDLE</span>
              <span class="stat-val idle" id="s-idle">0</span>
            </div>
            <div class="stat-bar"><div class="stat-bar-fill fill-idle" id="bar-idle" style="width:0%"></div></div>
          </div>
          <div class="stat-row">
            <div class="stat-header">
              <span class="stat-label">SKIPPED</span>
              <span class="stat-val skip" id="s-skip">0</span>
            </div>
            <div class="stat-bar"><div class="stat-bar-fill fill-skip" id="bar-skip" style="width:0%"></div></div>
          </div>
        </div>
      </div>

      <!-- Guide -->
      <div id="guide">
        <div class="guide-label">Labeling Guide</div>
        <div class="guide-item">
          <div class="guide-dot a"></div>
          <div class="guide-text">ACTIVE — visible smoke plume or orange/red heat signature in SWIR panel</div>
        </div>
        <div class="guide-item">
          <div class="guide-dot i"></div>
          <div class="guide-text">IDLE — clean chimneys, no smoke, cold/dark in SWIR panel</div>
        </div>
        <div class="guide-item">
          <div class="guide-dot" style="background:var(--dim)"></div>
          <div class="guide-text">SKIP — significant cloud cover obscures the facility</div>
        </div>
      </div>

    </div>
  </div>
</div>

<div id="save-flash">SAVED</div>

<script>
let images = [], annotations = {}, idx = 0;

async function init() {
  const r = await fetch('/api/images');
  const d = await r.json();
  images = d.images;
  annotations = d.annotations;
  for (let i = 0; i < images.length; i++) {
    if (!annotations[images[i].id]) { idx = i; break; }
  }
  render();
}

function render() {
  if (!images.length) return;
  const img = images[idx];
  const el = document.getElementById('img');
  el.classList.add('loading');
  el.onload = () => el.classList.remove('loading');
  el.src = '/image?path=' + encodeURIComponent(img.path);

  document.getElementById('m-mill').textContent = 'MILL-' + String(img.mill_id).padStart(2,'0');
  document.getElementById('m-date').textContent = img.year + ' / ' + img.month;
  document.getElementById('idx-display').textContent = (idx+1) + ' / ' + images.length;

  // badge
  const lbl = annotations[img.id];
  const badge = document.getElementById('label-badge');
  badge.className = lbl ? 'show ' + lbl : '';
  badge.textContent = lbl || '';

  // button states
  ['active','idle','skip'].forEach(k => {
    document.getElementById('btn-'+k).className = 'action-btn' +
      (lbl === k.toUpperCase() ? ' selected-'+k : '');
  });

  updateStats();
}

function updateStats() {
  const vals = Object.values(annotations);
  const na = vals.filter(v=>v==='ACTIVE').length;
  const ni = vals.filter(v=>v==='IDLE').length;
  const ns = vals.filter(v=>v==='SKIP').length;
  const total = na + ni + ns || 1;
  const labeled = na + ni;

  document.getElementById('s-active').textContent = na;
  document.getElementById('s-idle').textContent = ni;
  document.getElementById('s-skip').textContent = ns;
  document.getElementById('bar-active').style.width = (na/total*100)+'%';
  document.getElementById('bar-idle').style.width = (ni/total*100)+'%';
  document.getElementById('bar-skip').style.width = (ns/total*100)+'%';

  const pct = Math.min(100, labeled/250*100);
  document.getElementById('progress-fill').style.width = pct+'%';
  document.getElementById('prog-count').textContent = labeled + ' / 250';
}

async function label(val) {
  const img = images[idx];
  annotations[img.id] = val;
  await fetch('/api/label', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({id:img.id, label:val, path:img.path, mill_id:img.mill_id, date:img.date})
  });
  flash();
  render();
  setTimeout(() => go(1), 250);
}

function go(dir) {
  idx = Math.max(0, Math.min(images.length-1, idx+dir));
  render();
}

function flash() {
  const el = document.getElementById('save-flash');
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 900);
}

document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  if (e.key==='a'||e.key==='A') label('ACTIVE');
  else if (e.key==='i'||e.key==='I') label('IDLE');
  else if (e.key==='s'||e.key==='S') label('SKIP');
  else if (e.key==='ArrowRight') go(1);
  else if (e.key==='ArrowLeft') go(-1);
});

init();
</script>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/':
            self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers()
            self.wfile.write(HTML.encode())
        elif parsed.path == '/api/images':
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers()
            self.wfile.write(json.dumps({"images":IMAGES,"annotations":ANNOTATIONS}).encode())
        elif parsed.path == '/image':
            params = urllib.parse.parse_qs(parsed.query)
            path = params.get('path',[''])[0]
            if os.path.exists(path):
                self.send_response(200); self.send_header('Content-Type','image/png')
                self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                with open(path,'rb') as f: self.wfile.write(f.read())
            else:
                self.send_response(404); self.end_headers()
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path == '/api/label':
            length = int(self.headers['Content-Length'])
            body = json.loads(self.rfile.read(length))
            ANNOTATIONS[body['id']] = body['label']
            save_annotations(ANNOTATIONS)
            self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers()
            self.wfile.write(b'{"ok":true}')

if __name__ == '__main__':
    print(f"SteelSight Annotation Studio")
    print(f"Loaded {len(IMAGES)} images | {len(ANNOTATIONS)} existing annotations")
    print(f"\nOpen: http://localhost:9000\n")
    HTTPServer(('localhost',9000),Handler).serve_forever()
