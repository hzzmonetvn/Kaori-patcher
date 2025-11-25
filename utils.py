#!/usr/bin/env python3
# utils.py

import os
import shutil
import zipfile
from pathlib import Path

# --- Cấu hình đường dẫn ---
CURRENT_DIR = Path.cwd()
SMALI_JAR = CURRENT_DIR / "smali.jar"
BAKSMALI_JAR = CURRENT_DIR / "baksmali.jar"
USAGI_DIR = CURRENT_DIR / "USAGI"
MODULE_DIR = CURRENT_DIR / "module"

TARGET_JARS = [
    "framework.jar",
    "services.jar",
    "miui-framework.jar",
    "miui-services.jar",
]

UNPACK_DIRS = {
    "framework.jar": "framework_unpacked",
    "services.jar": "services_unpacked",
    "miui-framework.jar": "miui_framework_unpacked",
    "miui-services.jar": "miui_services_unpacked",
}

def check_tools():
    """Kiểm tra sự tồn tại của smali/baksmali"""
    if not SMALI_JAR.exists() or not BAKSMALI_JAR.exists():
        print("❌ Lỗi: Thiếu smali.jar hoặc baksmali.jar")
        return False
    return True

def log(msg, level="INFO"):
    icons = {"INFO": "ℹ️", "SUCCESS": "✅", "ERROR": "❌", "WARN": "⚠️", "PROCESS": "📦"}
    print(f"{icons.get(level, '')} {msg}")

def ensure_dir(path: Path):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

def delete_dir(path: Path):
    if path.exists():
        shutil.rmtree(path)
      
