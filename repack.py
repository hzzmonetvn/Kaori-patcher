#!/usr/bin/env python3
# 5_repack.py

import subprocess
import shutil
import zipfile
import os
from pathlib import Path
from utils import (
    CURRENT_DIR, SMALI_JAR, MODULE_DIR, 
    log, delete_dir, ensure_dir
)

def repack_classes():
    log("Repack classes (Smali -> Dex)...", "PROCESS")
    smali_dirs = []
    for folder in ["framework_unpacked", "services_unpacked", "miui_framework_unpacked", "miui_services_unpacked"]:
        base = CURRENT_DIR / folder
        if base.exists():
            for child in base.iterdir():
                if child.is_dir() and child.name.startswith("smali_classes"):
                    smali_dirs.append(child)

    for directory in smali_dirs:
        dex_name = directory.name.replace("smali_", "") + ".dex"
        output = directory.parent / dex_name
        cmd = [
            "java", "-jar", str(SMALI_JAR), 
            "a", str(directory), 
            "-o", str(output), "--api", "33"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            log(f"Repacked {directory.name}", "SUCCESS")
            delete_dir(directory)
        else:
            log(f"Lỗi repack {directory.name}: {res.stderr}", "ERROR")

def repack_jars():
    log("Repack JAR files...", "PROCESS")
    candidates = [
        ("framework.jar", "framework_unpacked"),
        ("services.jar", "services_unpacked"),
        ("miui-framework.jar", "miui_framework_unpacked"),
        ("miui-services.jar", "miui_services_unpacked"),
    ]

    for jar_name, directory in candidates:
        dir_path = CURRENT_DIR / directory
        if not dir_path.exists():
            continue
        output_jar = CURRENT_DIR / jar_name
        with zipfile.ZipFile(output_jar, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(dir_path):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(dir_path)
                    zf.write(file_path, arcname)
        
        log(f"Đã tạo {jar_name}", "SUCCESS")
        delete_dir(dir_path)

def create_module():
    log("Tạo Magisk Module...", "PROCESS")
    framework_dir = MODULE_DIR / "system" / "framework"
    system_ext_dir = MODULE_DIR / "system" / "system_ext" / "framework"
    ensure_dir(framework_dir)
    ensure_dir(system_ext_dir)

    copies = [
        (CURRENT_DIR / "framework.jar", framework_dir / "framework.jar"),
        (CURRENT_DIR / "services.jar", framework_dir / "services.jar"),
        (CURRENT_DIR / "miui-framework.jar", system_ext_dir / "miui-framework.jar"),
        (CURRENT_DIR / "miui-services.jar", system_ext_dir / "miui-services.jar"),
    ]

    for src, dst in copies:
        if src.exists():
            shutil.copy2(src, dst)

    zip_path = CURRENT_DIR / "Module-framework-test.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(MODULE_DIR):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(MODULE_DIR)
                zipf.write(file_path, arcname)
    
    log(f"Module saved: {zip_path}", "SUCCESS")

def main():
    repack_classes()
    repack_jars()
    create_module()

if __name__ == "__main__":
    main()
  
