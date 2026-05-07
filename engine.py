"""
Translation engine: audio capture → Whisper STT → Google Translate → Edge TTS
VERSION: 4 - NO third-party imports at top level.
All numpy/whisper/sounddevice/pygame imports are INSIDE functions only.
"""
import asyncio
import os
import tempfile
import threading
import time


class TranslatorEngine:
    def __init__(self):
        self.model = None
        self.translator = None
        self._running = False
        self._paused = False
        self._thread = None
        self._loop = None
        self._pygame_ready = False

        # Settings
        self.device_index = None
        self.tts_voice = "ru-RU-SvetlanaNeural"
        self.tts_rate = "+0%"
        self.tts_volume = "+0%"
        self.chunk_seconds = 4
        self.sample_rate = 16000

        # Callbacks (set by UI)
        self.on_translation = None   # fn(en: str, ru: str)
        self.on_volume = None         # fn(level: float 0..1)
        self.on_status = None         # fn(status: str)
        self.on_error = None          # fn(msg: str)

    # ── Model loading ──────────────────────────────────────────────────────────

    def load_model(self, model_name: str, progress_cb=None):
        """Load Whisper model and translator. Blocking — run in thread."""
        import numpy as np  # noqa — ensure available
        import whisper
        from deep_translator import GoogleTranslator

        if progress_cb:
            progress_cb(f"Загрузка модели '{model_name}'…")
        self.model = whisper.load_model(model_name)
        self.translator = GoogleTranslator(source="en", target="ru")
        if progress_cb:
            progress_cb("✅ Модель загружена")

    # ── Playback / TTS ─────────────────────────────────────────────────────────

    def _ensure_pygame(self):
        if not self._pygame_ready:
            try:
                import pygame
                pygame.mixer.init()
                self._pygame_ready = True
            except ImportError:
                if self.on_error:
                    self.on_error("pygame не установлен. Аудиовоспроизведение недоступно.")
                return False
        return True

    async def _speak_async(self, text: str):
        try:
            import edge_tts
            import pygame
        except ImportError as e:
            if self.on_error:
                self.on_error(f"Required package missing: {e}")
            return
        
        if not self._ensure_pygame():
            if self.on_error:
                self.on_error("Cannot initialize audio playback")
            return
        
        communicate = edge_tts.Communicate(
            text,
            voice=self.tts_voice,
            rate=self.tts_rate,
            volume=self.tts_volume,
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            tmp = f.name
        await communicate.save(tmp)
        try:
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)
        except Exception as e:
            if self.on_error:
                self.on_error(f"Audio playback error: {e}")
        finally:
            try:
                os.unlink(tmp)
            except Exception:
                pass

    # ── Listening loop ─────────────────────────────────────────────────────────

    def start(self, device_index=None):
        if self._running:
            return
        if device_index is not None:
            self.device_index = device_index
        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._loop_fn, daemon=True)
        self._thread.start()

    def pause(self):
        self._paused = True
        if self.on_status:
            self.on_status("paused")
        if self.on_volume:
            self.on_volume(0.0)

    def resume(self):
        self._paused = False
        if self.on_status:
            self.on_status("listening")

    def stop(self):
        self._running = False
        self._paused = False
        if self.on_volume:
            self.on_volume(0.0)
        if self.on_status:
            self.on_status("idle")

    def _loop_fn(self):
        import numpy as np
        import sounddevice as sd

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ensure_pygame()

        if self.on_status:
            self.on_status("listening")

        while self._running:
            if self._paused:
                time.sleep(0.2)
                continue
            try:
                audio = sd.rec(
                    int(self.chunk_seconds * self.sample_rate),
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype="float32",
                    device=self.device_index if self.device_index != "" else None,
                )
                sd.wait()

                if self._paused or not self._running:
                    continue

                chunk = audio.flatten()
                vol = float(np.abs(chunk).mean())
                if self.on_volume:
                    self.on_volume(min(vol * 220, 1.0))

                if vol < 0.003:
                    continue

                # STT
                if self.on_status:
                    self.on_status("processing")
                result = self.model.transcribe(chunk, language="en", fp16=False)
                text = result["text"].strip()

                if len(text) < 3:
                    if self.on_status:
                        self.on_status("listening")
                    continue

                # Translate
                ru = self.translator.translate(text)

                if self.on_translation:
                    self.on_translation(text, ru)
                if self.on_status:
                    self.on_status("speaking")

                # TTS
                self._loop.run_until_complete(self._speak_async(ru))

                if self._running and not self._paused:
                    if self.on_status:
                        self.on_status("listening")

            except Exception as exc:
                if self._running:
                    if self.on_error:
                        self.on_error(str(exc))
                    if self.on_status:
                        self.on_status("listening")
                time.sleep(0.5)

        if self.on_volume:
            self.on_volume(0.0)

    # ── Audio device test ───────────────────────────────────────────────────────

    def test_device(self, device_index, duration=3.0, volume_cb=None):
        """Record from device for `duration` seconds, report peak volume. Blocking."""
        import numpy as np
        import sounddevice as sd
        samples = int(self.sample_rate * duration)
        try:
            audio = sd.rec(
                samples,
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=device_index if device_index != "" else None,
            )
            steps = int(duration / 0.1)
            for _ in range(steps):
                if volume_cb:
                    partial = audio[: _ * int(self.sample_rate * 0.1)]
                    if len(partial) > 0:
                        vol = float(np.abs(partial).mean())
                        volume_cb(min(vol * 220, 1.0))
                time.sleep(0.1)
            sd.wait()
            chunk = audio.flatten()
            peak = float(np.abs(chunk).mean())
            if volume_cb:
                volume_cb(0.0)
            return peak
        except Exception as exc:
            if volume_cb:
                volume_cb(0.0)
            return 0.0


# ── Package installer helper ────────────────────────────────────────────────────

REQUIRED_PACKAGES = [
    ("openai-whisper", "whisper"),
    ("sounddevice", "sounddevice"),
    ("numpy", "numpy"),
    ("deep-translator", "deep_translator"),
    ("edge-tts", "edge_tts"),
    ("pygame", "pygame"),
]


def install_packages(progress_cb=None):
    """Install all required packages. progress_cb(msg, ok: bool|None)."""
    import subprocess, sys
    all_ok = True
    for pkg_name, import_name in REQUIRED_PACKAGES:
        if progress_cb:
            progress_cb(f"Устанавливаю {pkg_name}…", None)
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg_name, "--quiet"],
            capture_output=True,
            text=True,
        )
        ok = result.returncode == 0
        if not ok:
            all_ok = False
        if progress_cb:
            progress_cb(
                f"{'✅' if ok else '❌'}  {pkg_name}",
                ok,
            )
    return all_ok


def list_input_devices():
    """Return list of (index, name, is_cable) for input devices."""
    try:
        import sounddevice as sd
        devices = []
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                name = d["name"]
                is_cable = "CABLE" in name.upper() or "VB-AUDIO" in name.upper()
                devices.append((i, name, is_cable))
        return devices
    except Exception:
        return []
