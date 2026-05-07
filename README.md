# VoiceBridge-Real-Time-Audio-Translator-Voice-Over
VoiceBridge — это прототип, который перехватывает аудиопоток с ПК, распознаёт речь на выбранном языке, переводит её на лету и тут же озвучивает закадрово на другом языке.   Фактически это дубляж realtime с помощью Python, VB-CABLE и моделей синтетического TTS

## 📌 Описание
VoiceBridge — это прототип, который перехватывает аудиопоток с ПК, распознаёт речь на выбранном языке, переводит её на лету и тут же озвучивает закадрово на другом языке.  
Фактически это **реальное время дубляж** с помощью Python, VB-CABLE и моделей синтетического интеллекта.

---

## ✨ Возможности
- 🎙️ Перехват системного аудио через **VB-CABLE**
- 🧠 Распознавание речи (например, Whisper)
- 🌍 Мгновенный перевод на целевой язык
- 🔊 Закадровая озвучка в реальном времени
- ⚡ Минимальная задержка (зависит от железа/облака)
- 🛠️ Автозапуск через batch‑файл

---

## 🖥️ Требования
- Windows 10/11
- [VB-CABLE](https://vb-audio.com/Cable/) (виртуальный аудиокабель)
- Python 3.11 (желательно) или новее
- Библиотеки Python:
  - `speechrecognition`
  - `transformers`
  - `pyaudio`
  - `sounddevice`
  - `torch` (или `onnxruntime` для облегчённых моделей)

---

## ⚙️ Установка
1. Установите **VB-CABLE** и настройте его как устройство вывода/ввода.
2. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/yourname/voicebridge.git
   cd voicebridge
   Установите зависимости:

bash
pip install -r requirements.txt

Запустите батник:

bash
VoiceBridge.bat

▶️ Пример VoiceBridge.bat
@echo off
title VoiceBridge

echo ==========================================
echo  VOICE BRIDGE - EN to RU Translator  
echo ==========================================
echo.

:: Поиск Python 3.11
set PYTHON_EXE=
set FOUND_PYTHON=0

py -3.11 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_EXE=py -3.11
    set FOUND_PYTHON=1
    goto :found_python
)

set "PYTHON_PATHS=C:\Python311 C:\Program Files\Python311"
for %%P in (%PYTHON_PATHS%) do (
    if exist "%%P\python.exe" (
        set PYTHON_EXE="%%P\python.exe"
        set FOUND_PYTHON=1
        goto :found_python
    )
)

python --version >nul 2>&1 && set PYTHON_EXE=python && set FOUND_PYTHON=1 && goto :found_python
py --version >nul 2>&1 && set PYTHON_EXE=py && set FOUND_PYTHON=1 && goto :found_python

:found_python
if %FOUND_PYTHON% equ 0 (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)

echo [OK] Using: %PYTHON_EXE%
%PYTHON_EXE% "%~dp0bootstrap.py"

🐍 Пример bootstrap.py


import sys
import subprocess

REQUIRED = [
    "speechrecognition",
    "transformers",
    "pyaudio",
    "sounddevice",
    "torch"
]

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

print("[Bootstrap] Checking dependencies...")
for pkg in REQUIRED:
    try:
        __import__(pkg)
        print(f"[OK] {pkg}")
    except ImportError:
        print(f"[Missing] Installing {pkg}...")
        install(pkg)

print("[Bootstrap] Starting VoiceBridge...")
import main  # основной скрипт с логикой перевода



🐍 Пример main.py (минимальный)

import speech_recognition as sr
import sounddevice as sd
import numpy as np
from transformers import pipeline

# Настройки
source_lang = "en"
target_lang = "ru"

# Модель перевода
translator = pipeline("translation", model=f"Helsinki-NLP/opus-mt-{source_lang}-{target_lang}")

# Распознавание речи
recognizer = sr.Recognizer()
mic = sr.Microphone()

print("[VoiceBridge] Ready. Speak...")

while True:
    with mic as source:
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio, language=source_lang)
        print(f"[Input] {text}")
        translated = translator(text)[0]['translation_text']
        print(f"[Translated] {translated}")
        # Озвучка (можно подключить pyttsx3 или gTTS)
    except Exception as e:
        print("[Error]", e)



🚀 Использование
Настройте входной и выходной язык в main.py.
Запустите VoiceBridge.bat.
Всё, что звучит на исходном языке, будет переведено и озвучено на целевом.


⚠️ Disclaimer
Это прототип, собранный за пару часов. Используйте как основу, дорабатывайте под свои задачи и делитесь улучшениями!
