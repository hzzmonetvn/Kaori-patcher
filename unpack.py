#!/usr/bin/env python3
# 1_unpack.py

import shutil
import subprocess
import zipfile
import sys
from utils import (
    CURRENT_DIR, TARGET_JARS, UNPACK_DIRS, BAKSMALI_JAR, 
    check_tools, log, delete_dir, ensure_dir
)

def unpack_jar(jar_file):
    jar_path = CURRENT_DIR / jar_file
    out_dir = CURRENT_DIR / UNPACK_DIRS[jar_file]

    log(f"Đang giải nén {jar_file}...", "PROCESS")
    delete_dir(out_dir)
    ensure_dir(out_dir)

    try:
        with zipfile.ZipFile(jar_path, "r") as zip_ref:
            zip_ref.extractall(out_dir)
        
        # Decompile DEX files
        dex_files = list(out_dir.rglob("*.dex"))
        if not dex_files:
            log(f"Không tìm thấy file DEX trong {jar_file}", "WARN")
            return

        for dex_path in dex_files:
            dex_name = dex_path.stem
            smali_dir = out_dir / f"smali_{dex_name}"
            delete_dir(smali_dir)
            ensure_dir(smali_dir)

            cmd = [
                "java", "-jar", str(BAKSMALI_JAR), 
                "d", str(dex_path), "-o", str(smali_dir)
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            log(f"Decompiled {dex_path.name} -> {smali_dir.name}", "SUCCESS")

    except Exception as e:
        log(f"Lỗi giải nén {jar_file}: {e}", "ERROR")
        sys.exit(1)

def main():
    if not check_tools():
        sys.exit(1)

    found_any = False
    for jar in TARGET_JARS:
        if (CURRENT_DIR / jar).exists():
            unpack_jar(jar)
            found_any = True
    
    if not found_any:
        log("Không tìm thấy file JAR nào để giải nén.", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
  
