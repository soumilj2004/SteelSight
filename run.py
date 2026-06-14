"""
SteelSight — One-click launcher
Starts backend, frontend, and opens the browser automatically.

HOW TO RUN:
    python run.py

STOPS with Ctrl+C — kills everything cleanly.
"""

import subprocess
import sys
import os
import time
import webbrowser
import threading
import signal

ROOT     = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(ROOT, "frontend")
NPM      = "npm.cmd" if sys.platform == "win32" else "npm"

CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

procs = []

def log(color, tag, msg):
    print(f"{color}{BOLD}[{tag}]{RESET} {msg}")

def kill_all():
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    log(RED, "STOP", "All processes terminated.")

def signal_handler(sig, frame):
    print()
    kill_all()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def check_requirements():
    log(CYAN, "CHECK", "Verifying requirements...")

    # Check node/npm
    try:
        subprocess.run([NPM, "--version"], capture_output=True, check=True)
        log(GREEN, "CHECK", "npm found")
    except Exception:
        log(RED, "ERROR", "npm not found. Install Node.js from https://nodejs.org")
        sys.exit(1)

    # Check uvicorn
    try:
        subprocess.run([sys.executable, "-m", "uvicorn", "--version"],
                       capture_output=True, check=True)
        log(GREEN, "CHECK", "uvicorn found")
    except Exception:
        log(YELLOW, "INSTALL", "Installing uvicorn...")
        subprocess.run([sys.executable, "-m", "pip", "install", "uvicorn", "fastapi"],
                       check=True)

    # Check if frontend node_modules exists
    nm = os.path.join(FRONTEND, "node_modules")
    if not os.path.exists(nm):
        log(YELLOW, "SETUP", "Installing frontend dependencies (first time only)...")
        subprocess.run([NPM, "install"], cwd=FRONTEND, check=True)
        log(GREEN, "SETUP", "Frontend dependencies installed")
    else:
        log(GREEN, "CHECK", "Frontend dependencies found")

    # Check if recharts is installed
    rc = os.path.join(FRONTEND, "node_modules", "recharts")
    if not os.path.exists(rc):
        log(YELLOW, "SETUP", "Installing recharts...")
        subprocess.run([NPM, "install", "recharts"], cwd=FRONTEND, check=True)

    log(GREEN, "CHECK", "All requirements satisfied")


def check_data():
    log(CYAN, "DATA", "Checking data files...")
    required = [
        ("data/activity_scores.csv",  "Run: python src/inference/swir_heat_index.py"),
        ("data/monthly_signal.csv",   "Run: python src/inference/swir_heat_index.py"),
        ("data/wsa_steel_output.csv", "Ensure wsa_steel_output.csv is in data/"),
    ]
    all_ok = True
    for path, fix in required:
        full = os.path.join(ROOT, path)
        if os.path.exists(full):
            log(GREEN, "DATA", f"Found: {path}")
        else:
            log(YELLOW, "WARN", f"Missing: {path} — {fix}")
            all_ok = False

    fin_signal = os.path.join(ROOT, "data/financial/financial_signal.csv")
    if not os.path.exists(fin_signal):
        log(YELLOW, "DATA", "Financial data not found — running fetch_prices.py...")
        result = subprocess.run(
            [sys.executable, "src/financial/fetch_prices.py"],
            cwd=ROOT, capture_output=True, text=True
        )
        if result.returncode == 0:
            log(GREEN, "DATA", "Financial data fetched successfully")
        else:
            log(YELLOW, "WARN", "Financial data fetch failed — dashboard will show partial data")
    else:
        log(GREEN, "DATA", "Financial data found")

    return all_ok


def start_backend():
    log(CYAN, "BACKEND", "Starting FastAPI on http://localhost:8000 ...")
    p = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.api:app",
         "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    procs.append(p)

    # Stream backend logs with tag
    def stream():
        for line in p.stdout:
            line = line.rstrip()
            if line:
                print(f"{CYAN}[API]{RESET} {line}")
    threading.Thread(target=stream, daemon=True).start()
    return p


def start_frontend():
    log(CYAN, "FRONTEND", "Starting React on http://localhost:5173 ...")
    p = subprocess.Popen(
        [NPM, "run", "dev"],
        cwd=FRONTEND,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=(sys.platform == "win32"),
    )
    procs.append(p)

    def stream():
        for line in p.stdout:
            line = line.rstrip()
            if line:
                print(f"{GREEN}[UI]{RESET} {line}")
    threading.Thread(target=stream, daemon=True).start()
    return p

    def stream():
        for line in p.stdout:
            line = line.rstrip()
            if line:
                print(f"{GREEN}[UI]{RESET} {line}")
    threading.Thread(target=stream, daemon=True).start()
    return p


def open_browser():
    time.sleep(4)
    log(GREEN, "BROWSER", "Opening http://localhost:5173 ...")
    webbrowser.open("http://localhost:5173")


def wait_for_processes(backend, frontend):
    log(GREEN, "READY", "SteelSight is running.")
    log(GREEN, "READY", f"Dashboard  →  http://localhost:5173")
    log(GREEN, "READY", f"API        →  http://localhost:8000")
    log(GREEN, "READY", f"API Docs   →  http://localhost:8000/docs")
    log(YELLOW, "STOP", "Press Ctrl+C to stop everything.\n")

    while True:
        if backend.poll() is not None:
            log(RED, "ERROR", "Backend crashed. Check logs above.")
            kill_all()
            sys.exit(1)
        if frontend.poll() is not None:
            log(RED, "ERROR", "Frontend crashed. Check logs above.")
            kill_all()
            sys.exit(1)
        time.sleep(1)


def main():
    print(r"""
 ███████╗████████╗███████╗███████╗██╗     ███████╗██╗ ██████╗ ██╗  ██╗████████╗
 ██╔════╝╚══██╔══╝██╔════╝██╔════╝██║     ██╔════╝██║██╔════╝ ██║  ██║╚══██╔══╝
 ███████╗   ██║   █████╗  █████╗  ██║     ███████╗██║██║  ███╗███████║   ██║
 ╚════██║   ██║   ██╔══╝  ██╔══╝  ██║     ╚════██║██║██║   ██║██╔══██║   ██║
 ███████║   ██║   ███████╗███████╗███████╗███████║██║╚██████╔╝██║  ██║   ██║
 ╚══════╝   ╚═╝   ╚══════╝╚══════╝╚══════╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝

      Satellite Commodity Intelligence • SWIR Analytics • AI Powered
""")

    os.chdir(ROOT)

    check_requirements()
    print()
    check_data()
    print()

    backend  = start_backend()
    time.sleep(2)
    frontend = start_frontend()

    threading.Thread(target=open_browser, daemon=True).start()
    print()

    wait_for_processes(backend, frontend)


if __name__ == "__main__":
    main()
