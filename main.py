"""
VoiceBridge - main entry point.
Called by bootstrap.py after all packages are verified installed.
"""
import json
import os
import sys
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
LOG_FILE = os.path.join(APP_DIR, "voicebridge.log")

def log(msg, level="INFO"):
    """Log message to both console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] [{level}] {msg}"
    print(log_msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    except Exception as e:
        print(f"[WARNING] Could not write to log: {e}")

DEFAULT_CONFIG = {
    "setup_complete": False,
    "device_index": None,
    "device_name": "",
    "model": "small",
    "tts_voice": "ru-RU-SvetlanaNeural",
    "tts_rate": 0,
    "tts_volume": 0,
    "chunk_seconds": 4,
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = {**DEFAULT_CONFIG, **json.load(f)}
                log(f"Config loaded from: {CONFIG_PATH}")
                return cfg
        except Exception as e:
            log(f"Error loading config: {e}", "ERROR")
    log("Using default config")
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def check_deps_or_abort():
    """If critical packages missing, show stdlib error and re-run bootstrap."""
    missing = []
    for pkg in ["customtkinter", "numpy", "whisper"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if not missing:
        log("All dependencies check passed")
        return  # all good

    log(f"Missing dependencies: {', '.join(missing)}", "ERROR")
    # Show error using stdlib tkinter (always available)
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(
        "VoiceBridge - Missing packages",
        f"Required packages not installed:\n  {', '.join(missing)}\n\n"
        "Please run START.bat again to auto-install them.\n\n"
        "If problem persists, open CMD and run:\n"
        f"  python -m pip install {' '.join(missing)}"
    )
    root.destroy()

    # Try to re-run bootstrap
    bootstrap = os.path.join(APP_DIR, "bootstrap.py")
    if os.path.exists(bootstrap):
        import subprocess
        log("Re-running bootstrap.py")
        subprocess.run([sys.executable, bootstrap, sys.executable])
    sys.exit(1)


if __name__ == "__main__":
    log("===== VoiceBridge Main Started =====")
    log(f"Python: {sys.version}")
    log(f"App directory: {APP_DIR}")
    
    # Safety net: check packages before importing UI modules
    check_deps_or_abort()

    cfg = load_config()
    force_setup = "--setup" in sys.argv or not cfg.get("setup_complete", False)

    if force_setup:
        log("Launching setup window")
        from setup_ui import SetupWindow
        win = SetupWindow(cfg, save_config)
        win.mainloop()
    else:
        log("Launching app window")
        from app_ui import AppWindow
        win = AppWindow(cfg, save_config)
        win.mainloop()
    
    log("===== VoiceBridge Main Closed =====")
