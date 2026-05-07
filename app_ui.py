"""
Main translator window.
Features: start/pause, animated volume bars, TTS settings, subtitle log.
"""
import threading
import time
import tkinter as tk
from datetime import datetime

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG      = "#0b0f14"
BG2     = "#111822"
BG3     = "#18222e"
BORDER  = "#1e2d3d"
ACCENT  = "#38bdf8"
GREEN   = "#22c55e"
ORANGE  = "#f97316"
RED     = "#ef4444"
YELLOW  = "#eab308"
TEXT    = "#e2e8f0"
TEXT2   = "#64748b"
TEXT3   = "#1e293b"

STATUS_LABELS = {
    "idle":       ("⏸  Остановлен",    TEXT2),
    "loading":    ("⏳  Загрузка…",     YELLOW),
    "listening":  ("🎧  Слушаю…",       GREEN),
    "processing": ("⚙  Распознаю…",    ACCENT),
    "speaking":   ("🔊  Озвучиваю…",   ORANGE),
    "paused":     ("⏸  Пауза",          TEXT2),
    "error":      ("⚠  Ошибка",         RED),
}

VOICES = [
    ("ru-RU-SvetlanaNeural", "Светлана (жен.)"),
    ("ru-RU-DmitryNeural",   "Дмитрий (муж.)"),
]


class VolumeBars(tk.Canvas):
    """Animated equalizer-style volume indicator."""
    BARS = 16

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG3, highlightthickness=0, **kw)
        self._heights = [0.03] * self.BARS
        self._target  = 0.0
        self._running = True
        self._animate()

    def set_volume(self, v: float):
        self._target = max(0.0, min(1.0, v))

    def stop(self):
        self._running = False

    def _animate(self):
        if not self._running:
            return
        import random
        w = self.winfo_width()  or 1
        h = self.winfo_height() or 1
        self.delete("all")

        bw  = w / (self.BARS * 1.55)
        gap = bw * 0.55

        for i in range(self.BARS):
            jitter = random.uniform(0.25, 1.0) if self._target > 0.04 else random.uniform(0, 0.06)
            target_h = self._target * jitter
            self._heights[i] += (target_h - self._heights[i]) * 0.38
            self._heights[i] = max(0.018, min(1.0, self._heights[i]))

            bh   = max(3, self._heights[i] * (h - 6))
            x    = i * (bw + gap) + gap
            ytop = h - bh - 3

            lvl = self._heights[i]
            color = GREEN if lvl < 0.45 else ORANGE if lvl < 0.78 else RED

            # Bar body
            self.create_rectangle(x, ytop, x + bw, h - 3, fill=color, outline="")
            # Glow top pixel
            self.create_rectangle(x, ytop, x + bw, ytop + 2,
                                  fill="white", outline="", stipple="gray25")

        self.after(45, self._animate)


class SubtitleLog(ctk.CTkScrollableFrame):
    """Scrollable log of EN→RU subtitle pairs."""

    MAX_ENTRIES = 80

    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=BG, **kw)
        self._entries = []
        self._empty_lbl = ctk.CTkLabel(
            self, text="Переводы появятся здесь…",
            font=("Courier New", 11), text_color=TEXT2,
        )
        self._empty_lbl.pack(pady=40)

    def add(self, en: str, ru: str):
        if self._empty_lbl.winfo_exists():
            try:
                self._empty_lbl.destroy()
            except Exception:
                pass

        ts = datetime.now().strftime("%H:%M:%S")

        frm = ctk.CTkFrame(self, fg_color=BG2, corner_radius=8,
                            border_color=BORDER, border_width=1)
        frm.pack(fill="x", padx=4, pady=3, anchor="n")
        frm.grid_columnconfigure(0, weight=1)

        # Timestamp row
        ctk.CTkLabel(frm, text=ts, font=("Courier New", 9),
                     text_color=TEXT2).grid(row=0, column=0, sticky="w",
                                            padx=10, pady=(6, 2))

        # EN line
        en_frm = ctk.CTkFrame(frm, fg_color="transparent")
        en_frm.grid(row=1, column=0, sticky="ew", padx=10, pady=1)
        ctk.CTkLabel(en_frm, text="EN", width=26,
                     font=("Courier New", 9, "bold"), text_color=BG,
                     fg_color=ORANGE, corner_radius=4).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(en_frm, text=en, font=("Courier New", 11),
                     text_color=TEXT2, anchor="w", justify="left",
                     wraplength=480).pack(side="left", fill="x", expand=True)

        # RU line
        ru_frm = ctk.CTkFrame(frm, fg_color="transparent")
        ru_frm.grid(row=2, column=0, sticky="ew", padx=10, pady=(1, 8))
        ctk.CTkLabel(ru_frm, text="RU", width=26,
                     font=("Courier New", 9, "bold"), text_color=BG,
                     fg_color=GREEN, corner_radius=4).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(ru_frm, text=ru, font=("Courier New", 12, "bold"),
                     text_color=TEXT, anchor="w", justify="left",
                     wraplength=480).pack(side="left", fill="x", expand=True)

        self._entries.append(frm)

        # Trim old entries
        if len(self._entries) > self.MAX_ENTRIES:
            oldest = self._entries.pop(0)
            oldest.destroy()

        # Scroll to top (newest first in reverse)
        self.after(50, lambda: self._parent_canvas.yview_moveto(0))

    def clear(self):
        for w in self._entries:
            try:
                w.destroy()
            except Exception:
                pass
        self._entries.clear()
        self._empty_lbl = ctk.CTkLabel(
            self, text="Переводы появятся здесь…",
            font=("Courier New", 11), text_color=TEXT2,
        )
        self._empty_lbl.pack(pady=40)


class AppWindow(ctk.CTk):
    def __init__(self, config: dict, save_fn):
        super().__init__()
        self.config_data = config
        self.save_fn = save_fn
        self._status = "idle"
        self._is_running = False
        self._translation_count = 0
        self._engine = None
        self._model_loaded = False

        self.title("VoiceBridge  —  EN → RU")
        self.geometry("960x680")
        self.minsize(820, 560)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build()
        self._refresh_devices()
        self._load_model_async()

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)

        # ── Top bar ──────────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0, height=52)
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        top.grid_propagate(False)
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="VOICE BRIDGE",
                     font=("Courier New", 15, "bold"), text_color=ACCENT
                     ).grid(row=0, column=0, padx=18, pady=14)

        self._status_lbl = ctk.CTkLabel(top, text="⏳  Загрузка модели…",
                                         font=("Courier New", 11), text_color=YELLOW)
        self._status_lbl.grid(row=0, column=1, sticky="w", padx=8)

        ctk.CTkLabel(top, text="EN → RU", font=("Courier New", 11),
                     text_color=TEXT2).grid(row=0, column=2, padx=12)

        self._count_lbl = ctk.CTkLabel(top, text="Переведено: 0",
                                        font=("Courier New", 10), text_color=TEXT2)
        self._count_lbl.grid(row=0, column=3, padx=8)

        ctk.CTkButton(top, text="⚙ Установка", width=100, height=28,
                       fg_color=BG3, hover_color=BORDER, text_color=TEXT2,
                       font=("Courier New", 10),
                       command=self._open_setup
                       ).grid(row=0, column=4, padx=12)

        # ── Volume meter ─────────────────────────────────────────────────────
        vol_frame = ctk.CTkFrame(self, fg_color=BG3, corner_radius=10, height=72)
        vol_frame.grid(row=1, column=0, columnspan=2, sticky="ew",
                       padx=12, pady=(10, 0))
        vol_frame.grid_propagate(False)
        vol_frame.grid_columnconfigure(0, weight=1)

        self._vol_bars = VolumeBars(vol_frame)
        self._vol_bars.grid(row=0, column=0, sticky="nsew", padx=10, pady=8)

        # ── Main area ─────────────────────────────────────────────────────────
        # Left: log
        self._log = SubtitleLog(self, label_text="", corner_radius=10)
        self._log.grid(row=2, column=0, sticky="nsew", padx=(12, 6), pady=10)

        # Right: controls panel
        self._panel = ctk.CTkFrame(self, fg_color=BG2, corner_radius=10, width=230)
        self._panel.grid(row=2, column=1, sticky="nsew", padx=(0, 12), pady=10)
        self._panel.grid_propagate(False)
        self._build_panel()

        # ── Bottom bar ────────────────────────────────────────────────────────
        bot = ctk.CTkFrame(self, fg_color=BG2, corner_radius=0, height=62)
        bot.grid(row=3, column=0, columnspan=2, sticky="ew")
        bot.grid_propagate(False)
        bot.grid_columnconfigure(1, weight=1)

        self._main_btn = ctk.CTkButton(
            bot, text="▶  ЗАПУСТИТЬ",
            font=("Courier New", 14, "bold"),
            fg_color=GREEN, hover_color="#16a34a",
            text_color="#000", height=42, width=200,
            command=self._toggle,
        )
        self._main_btn.grid(row=0, column=0, padx=16, pady=10)

        ctk.CTkButton(bot, text="Очистить лог", width=110, height=32,
                       fg_color=BG3, hover_color=BORDER, text_color=TEXT2,
                       font=("Courier New", 10),
                       command=self._clear_log
                       ).grid(row=0, column=2, padx=12)

        self._model_lbl = ctk.CTkLabel(bot, text="", font=("Courier New", 9),
                                        text_color=TEXT2)
        self._model_lbl.grid(row=0, column=3, padx=12)

    def _build_panel(self):
        p = self._panel

        def section(text, row):
            ctk.CTkLabel(p, text=text, font=("Courier New", 9, "bold"),
                         text_color=TEXT2).grid(row=row, column=0, sticky="w",
                                                padx=14, pady=(14, 4))

        # Device
        section("УСТРОЙСТВО ЗАХВАТА", 0)
        self._dev_var = ctk.StringVar(value="Авто")
        self._dev_menu = ctk.CTkOptionMenu(
            p, values=["Авто"], variable=self._dev_var,
            fg_color=BG3, button_color=BORDER, dropdown_fg_color=BG,
            font=("Courier New", 10), width=204,
            command=self._on_device_change,
        )
        self._dev_menu.grid(row=1, column=0, padx=14, pady=(0, 4))

        # Voice
        section("ГОЛОС TTS", 2)
        voice_names = [v[1] for v in VOICES]
        saved_voice = self.config_data.get("tts_voice", "ru-RU-SvetlanaNeural")
        default_v = next((v[1] for v in VOICES if v[0] == saved_voice), voice_names[0])
        self._voice_var = ctk.StringVar(value=default_v)
        ctk.CTkOptionMenu(
            p, values=voice_names, variable=self._voice_var,
            fg_color=BG3, button_color=BORDER, dropdown_fg_color=BG,
            font=("Courier New", 10), width=204,
            command=self._on_voice_change,
        ).grid(row=3, column=0, padx=14, pady=(0, 4))

        # Speed slider
        section("СКОРОСТЬ РЕЧИ", 4)
        self._rate_var = tk.IntVar(value=self.config_data.get("tts_rate", 0))
        self._rate_lbl = ctk.CTkLabel(p, text=self._fmt_rate(self._rate_var.get()),
                                       font=("Courier New", 10), text_color=ACCENT)
        self._rate_lbl.grid(row=4, column=1, sticky="e", padx=14)
        ctk.CTkSlider(p, from_=-50, to=100, variable=self._rate_var,
                       width=204, progress_color=ACCENT, button_color=ACCENT,
                       command=lambda v: (
                           self._rate_lbl.configure(text=self._fmt_rate(int(v))),
                           self._apply_tts_settings(),
                       )).grid(row=5, column=0, padx=14, pady=(0, 4))

        # Volume slider
        section("ГРОМКОСТЬ TTS", 6)
        self._vol_var = tk.IntVar(value=self.config_data.get("tts_volume", 0))
        self._vol_lbl = ctk.CTkLabel(p, text=self._fmt_val(self._vol_var.get()),
                                      font=("Courier New", 10), text_color=ACCENT)
        self._vol_lbl.grid(row=6, column=1, sticky="e", padx=14)
        ctk.CTkSlider(p, from_=-50, to=50, variable=self._vol_var,
                       width=204, progress_color=ACCENT, button_color=ACCENT,
                       command=lambda v: (
                           self._vol_lbl.configure(text=self._fmt_val(int(v))),
                           self._apply_tts_settings(),
                       )).grid(row=7, column=0, padx=14, pady=(0, 4))

        # Chunk seconds
        section("ДЛИНА ФРАГМЕНТА (СЕК)", 8)
        self._chunk_var = tk.IntVar(value=self.config_data.get("chunk_seconds", 4))
        self._chunk_lbl = ctk.CTkLabel(p, text=f"{self._chunk_var.get()} сек",
                                        font=("Courier New", 10), text_color=ACCENT)
        self._chunk_lbl.grid(row=8, column=1, sticky="e", padx=14)
        ctk.CTkSlider(p, from_=2, to=8, variable=self._chunk_var, number_of_steps=6,
                       width=204, progress_color=ACCENT, button_color=ACCENT,
                       command=lambda v: self._chunk_lbl.configure(text=f"{int(v)} сек"),
                       ).grid(row=9, column=0, padx=14, pady=(0, 8))

        p.grid_columnconfigure(0, weight=1)

    @staticmethod
    def _fmt_rate(v): return f"+{v}%" if v >= 0 else f"{v}%"
    @staticmethod
    def _fmt_val(v):  return f"+{v}%" if v >= 0 else f"{v}%"

    # ── Engine setup ──────────────────────────────────────────────────────────

    def _load_model_async(self):
        model_name = self.config_data.get("model", "small")
        self._set_status("loading")
        self._main_btn.configure(state="disabled")

        def worker():
            from engine import TranslatorEngine
            self._engine = TranslatorEngine()
            self._engine.on_translation = self._on_translation
            self._engine.on_volume      = self._on_volume
            self._engine.on_status      = self._on_engine_status
            self._engine.on_error       = self._on_engine_error
            try:
                self._engine.load_model(model_name)
                self._model_loaded = True
                self.after(0, lambda: (
                    self._set_status("idle"),
                    self._main_btn.configure(state="normal"),
                    self._model_lbl.configure(text=f"модель: {model_name}"),
                ))
            except Exception as e:
                self.after(0, lambda: (
                    self._set_status("error"),
                    self._status_lbl.configure(text=f"⚠ Ошибка: {e}"),
                ))

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_devices(self):
        try:
            from engine import list_input_devices
            self._devices = list_input_devices()
            names = ["Авто"] + [
                f"[{idx}] {name}" + ("  ✓ VB-Cable" if is_c else "")
                for idx, name, is_c in self._devices
            ]
            self._dev_menu.configure(values=names)
            # Auto-select VB-Cable
            saved = self.config_data.get("device_index")
            for idx, name, is_c in self._devices:
                if is_c and saved is None:
                    self._dev_var.set(f"[{idx}] {name}  ✓ VB-Cable")
                    break
                if saved is not None and idx == saved:
                    self._dev_var.set(f"[{idx}] {name}" + ("  ✓ VB-Cable" if is_c else ""))
                    break
        except Exception:
            pass

    # ── Control callbacks ─────────────────────────────────────────────────────

    def _toggle(self):
        if not self._model_loaded:
            return
        if not self._is_running:
            self._start()
        else:
            self._pause()

    def _start(self):
        self._is_running = True
        dev = self._get_selected_device()
        if self._engine:
            if self._status == "paused":
                self._engine.resume()
            else:
                self._engine.device_index      = dev
                self._engine.chunk_seconds     = self._chunk_var.get()
                self._apply_tts_settings()
                self._engine.start(device_index=dev)
        self._main_btn.configure(text="⏸  ПАУЗА",
                                  fg_color=ORANGE, hover_color="#c2410c",
                                  text_color="#000")

    def _pause(self):
        self._is_running = False
        if self._engine:
            self._engine.pause()
        self._main_btn.configure(text="▶  ЗАПУСТИТЬ",
                                  fg_color=GREEN, hover_color="#16a34a",
                                  text_color="#000")

    def _get_selected_device(self):
        val = self._dev_var.get()
        if val == "Авто":
            return None
        for idx, name, _ in self._devices:
            if val.startswith(f"[{idx}]"):
                return idx
        return None

    def _on_device_change(self, _=None):
        if self._is_running and self._engine:
            self._engine.device_index = self._get_selected_device()

    def _on_voice_change(self, _=None):
        self._apply_tts_settings()

    def _apply_tts_settings(self):
        if not self._engine:
            return
        voice_name = self._voice_var.get()
        voice_id = next((v[0] for v in VOICES if v[1] == voice_name), VOICES[0][0])
        rate = int(self._rate_var.get())
        vol  = int(self._vol_var.get())
        self._engine.tts_voice   = voice_id
        self._engine.tts_rate    = f"+{rate}%" if rate >= 0 else f"{rate}%"
        self._engine.tts_volume  = f"+{vol}%" if vol >= 0 else f"{vol}%"
        self.config_data["tts_voice"]  = voice_id
        self.config_data["tts_rate"]   = rate
        self.config_data["tts_volume"] = vol

    def _clear_log(self):
        self._log.clear()
        self._translation_count = 0
        self._count_lbl.configure(text="Переведено: 0")

    # ── Engine callbacks (called from bg thread → schedule on UI thread) ───────

    def _on_translation(self, en: str, ru: str):
        self._translation_count += 1
        self.after(0, lambda: (
            self._log.add(en, ru),
            self._count_lbl.configure(text=f"Переведено: {self._translation_count}"),
        ))

    def _on_volume(self, v: float):
        self.after(0, lambda: self._vol_bars.set_volume(v))

    def _on_engine_status(self, s: str):
        self.after(0, lambda: self._set_status(s))

    def _on_engine_error(self, msg: str):
        self.after(0, lambda: self._status_lbl.configure(
            text=f"⚠  {msg[:60]}", text_color=RED))

    def _set_status(self, s: str):
        self._status = s
        text, color = STATUS_LABELS.get(s, (s, TEXT2))
        self._status_lbl.configure(text=text, text_color=color)

    # ── Setup / close ─────────────────────────────────────────────────────────

    def _open_setup(self):
        if self._engine:
            self._engine.stop()
        self.save_fn(self.config_data)
        self.destroy()
        from setup_ui import SetupWindow
        w = SetupWindow(self.config_data, self.save_fn)
        w.mainloop()

    def _on_close(self):
        if self._engine:
            self._engine.stop()
        self._vol_bars.stop()
        self.save_fn(self.config_data)
        self.destroy()
