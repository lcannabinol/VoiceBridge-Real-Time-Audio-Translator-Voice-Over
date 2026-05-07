"""
bootstrap.py - VoiceBridge installer and launcher.
Uses ONLY Python stdlib.
"""
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime

# Setup logging
APP_DIR = os.path.dirname(os.path.abspath(__file__))
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

# Debug: print python info immediately
log(f"Python: {sys.version}")
log(f"Executable: {sys.executable}")
log(f"App directory: {APP_DIR}")
PYTHON = sys.executable

PACKAGES = [
    ("customtkinter",   "customtkinter",   "UI framework", True),
    ("numpy",           "numpy",           "Numeric computing", True),
    ("sounddevice",     "sounddevice",     "Audio capture", True),
    ("openai-whisper",  "whisper",         "Speech recognition", True),
    ("deep-translator", "deep_translator", "Translation", True),
    ("edge-tts",        "edge_tts",        "Text-to-speech", True),
    ("pygame",          "pygame",          "Audio playback (optional for Python 3.14+)", False),
]

# Split into required and optional
REQUIRED_PACKAGES = [p for p in PACKAGES if p[3]]
OPTIONAL_PACKAGES = [p for p in PACKAGES if not p[3]]


def is_installed(name):
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def install(pip_name):
    # pygame needs pre-built wheels, not compilation
    if pip_name.lower() == "pygame":
        cmd = [PYTHON, "-m", "pip", "install", pip_name,
               "--only-binary=:all:",
               "--quiet", "--disable-pip-version-check"]
    else:
        cmd = [PYTHON, "-m", "pip", "install", pip_name,
               "--quiet", "--disable-pip-version-check"]
    
    log(f"Installing: {pip_name}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        log(f"Successfully installed: {pip_name}", "INFO")
    else:
        log(f"Failed to install {pip_name}: {r.stderr.strip()}", "ERROR")
    return r.returncode == 0, r.stderr.strip()


def all_ok():
    """Check if all REQUIRED packages are installed"""
    return all(is_installed(imp) for _, imp, _, _ in REQUIRED_PACKAGES)


def launch_app():
    main_py = os.path.join(APP_DIR, "main.py")
    log(f"Launching: {PYTHON} {main_py}")
    # Use list form - never fails due to spaces
    ret = subprocess.run([PYTHON, main_py])
    if ret.returncode != 0:
        log(f"main.py exited with code {ret.returncode}", "ERROR")


class UI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("VoiceBridge Setup")
        self.root.geometry("540x400")
        self.root.resizable(False, False)
        self.root.configure(bg="#0b0f14")
        self.root.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"540x400+{(sw-540)//2}+{(sh-400)//2}")
        self._done = False
        self._build()

    def _build(self):
        r = self.root
        tk.Label(r, text="VOICE BRIDGE", font=("Courier New", 16, "bold"),
                 fg="#38bdf8", bg="#0b0f14").pack(pady=(18, 2))
        tk.Label(r, text="Installing required packages...",
                 font=("Courier New", 9), fg="#64748b", bg="#0b0f14").pack()
        tk.Frame(r, bg="#1e2d3d", height=1).pack(fill="x", padx=30, pady=10)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("B.Horizontal.TProgressbar",
                        troughcolor="#18222e", background="#38bdf8",
                        bordercolor="#0b0f14")
        self.pb = tk.DoubleVar()
        ttk.Progressbar(r, variable=self.pb, maximum=len(PACKAGES),
                        style="B.Horizontal.TProgressbar",
                        length=480).pack(padx=30)

        self.status = tk.StringVar(value="Checking...")
        tk.Label(r, textvariable=self.status, font=("Courier New", 10),
                 fg="#38bdf8", bg="#0b0f14", anchor="w",
                 width=58).pack(padx=30, pady=(6, 0))

        frm = tk.Frame(r, bg="#0b0f14")
        frm.pack(fill="both", expand=True, padx=30, pady=6)
        self.log = tk.Text(frm, font=("Courier New", 9), bg="#111822",
                           fg="#94a3b8", relief="flat", state="disabled")
        sb = tk.Scrollbar(frm, command=self.log.yview, relief="flat",
                          troughcolor="#111822")
        self.log.configure(yscrollcommand=sb.set)
        self.log.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        tk.Label(r, text=f"Python: {PYTHON}",
                 font=("Courier New", 8), fg="#94a3b8",
                 bg="#0b0f14").pack(pady=(0, 4))

        self.btn = tk.Button(r, text="  Launch VoiceBridge  ",
                             font=("Courier New", 11, "bold"),
                             bg="#22c55e", fg="#000", relief="flat",
                             cursor="hand2", state="disabled",
                             command=self._launch)
        self.btn.pack(pady=(0, 12))

    def write(self, text, color="#94a3b8"):
        self.log.configure(state="normal")
        tag = str(len(self.log.get("1.0", "end")))
        self.log.insert("end", text + "\n", tag)
        self.log.tag_configure(tag, foreground=color)
        self.log.see("end")
        self.log.configure(state="disabled")
        self.root.update_idletasks()
        # Also log to file
        if text.strip():
            log(text)

    def _launch(self):
        self._done = True
        self.root.destroy()

    def run(self):
        threading.Thread(target=self._worker, daemon=True).start()
        self.root.mainloop()
        return self._done

    def _worker(self):
        need = []
        optional_missing = []
        
        for i, (pip, imp, desc, is_required) in enumerate(PACKAGES):
            if is_installed(imp):
                self.write(f"[OK]   {pip}", "#22c55e")
            else:
                if is_required:
                    self.write(f"[---]  {pip}  ({desc})", "#f97316")
                    need.append((pip, imp, desc, is_required))
                else:
                    self.write(f"[OPT]  {pip}  ({desc})", "#94a3b8")
                    optional_missing.append((pip, imp, desc))
            self.root.after(0, lambda v=i + 1: self.pb.set(v))

        if not need:
            self.write("", None)
            self.write("All required packages ready!", "#22c55e")
            if optional_missing:
                self.write(f"Optional packages missing: {', '.join(p[0] for p in optional_missing)}", "#f97316")
            self.root.after(0, lambda: self.status.set("All ready!"))
            self.root.after(0, lambda: self.btn.configure(state="normal"))
            self.root.after(1200, self._launch)
            return

        self.write("", None)
        self.write(f"Installing {len(need)} required package(s)...", "#38bdf8")
        done_count = len(PACKAGES) - len(need)
        errors = []

        for pip, imp, desc, is_required in need:
            self.root.after(0, lambda p=pip: self.status.set(f"Installing {p}..."))
            self.write(f"pip install {pip}...", "#64748b")
            ok, err = install(pip)
            done_count += 1
            self.root.after(0, lambda v=done_count: self.pb.set(v))
            if ok:
                self.write(f"  OK: {pip}", "#22c55e")
            else:
                short = (err.splitlines()[-1][:60] if err else "error")
                self.write(f"  FAIL: {pip}: {short}", "#ef4444")
                errors.append(pip)

        self.write("", None)
        if errors:
            self.write(f"ERROR: {len(errors)} required package(s) failed: {', '.join(errors)}", "#ef4444")
        else:
            self.write("All required packages installed!", "#22c55e")
            if optional_missing:
                self.write(f"Note: Optional packages missing: {', '.join(p[0] for p in optional_missing)}", "#f97316")

        self.root.after(0, lambda: self.status.set("Done!"))
        self.root.after(0, lambda: self.btn.configure(
            state="normal",
            bg="#22c55e" if not errors else "#ef4444"))
        if not errors:
            self.root.after(1500, self._launch)


def main():
    log("===== VoiceBridge Bootstrap Started =====")
    if all_ok():
        log("All packages already installed")
        launch_app()
        return
    log("Starting package installation UI")
    ui = UI()
    if ui.run():
        log("Installation complete, launching app")
        launch_app()
    else:
        log("Installation cancelled by user")


if __name__ == "__main__":
    main()
