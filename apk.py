#!/usr/bin/env python3
# 3_apk_protection.py

import os
import re
from pathlib import Path
from utils import CURRENT_DIR, log

def patch_verifier(file_path: Path) -> bool:
    """
    Tìm method getMinimumSignatureSchemeVersionForTargetSdk và patch
    để trả về 0 (disable signature check).
    """
    method_key = "getMinimumSignatureSchemeVersionForTargetSdk"
    
    try:
        # Đọc file
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines(True)
        new_lines = []
        in_target_method = False
        replaced = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 1. Tìm thấy đầu method cần patch
            if stripped.startswith(".method") and method_key in stripped:
                in_target_method = True
                replaced = True
                
                # Giữ lại định nghĩa method gốc
                new_lines.append(line)
                
                # Xác định indent (thụt đầu dòng) để code mới thẳng hàng
                match = re.match(r"^(\s*)", line)
                base_indent = match.group(1) if match else ""
                indent = base_indent + "    "
                
                # Chèn code patch (return 0)
                # .registers 1
                # const/4 v0, 0x0
                # return v0
                new_lines.append(f"{indent}.registers 1\n")
                new_lines.append("\n")
                new_lines.append(f"{indent}const/4 v0, 0x0\n")
                new_lines.append("\n")
                new_lines.append(f"{indent}return v0\n")
                new_lines.append("\n")
                
                # Bỏ qua nội dung cũ của method cho đến khi gặp .end method
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(".end method"):
                    i += 1
                
                # Nếu tìm thấy .end method, thêm nó vào
                if i < len(lines):
                    new_lines.append(lines[i])
                
                in_target_method = False
                i += 1
                continue

            # 2. Xử lý các dòng thông thường khác
            new_lines.append(line)
            i += 1

        # Ghi file nếu có thay đổi
        if replaced:
            file_path.write_text("".join(new_lines), encoding="utf-8")
            return True
        
        return False

    except Exception as e:
        log(f"Lỗi khi patch {file_path.name}: {e}", "ERROR")
        return False

def main():
    # 1. Kiểm tra biến môi trường từ GitHub Action
    if os.getenv("ENABLE_MOD") == "false":
        log("SKIP: Apk Protection (User disabled)", "WARN")
        return

    log("Thực hiện APK Protection bypass...", "PROCESS")

    # 2. Đường dẫn file mục tiêu
    # Lưu ý: Class index (smali_classes4) có thể thay đổi tùy ROM/Android Version.
    # Code này sử dụng đường dẫn mặc định như script gốc.
    target_file = (
        CURRENT_DIR 
        / "framework_unpacked" 
        / "smali_classes4" 
        / "android" 
        / "util" 
        / "apk" 
        / "ApkSignatureVerifier.smali"
    )

    # 3. Kiểm tra file tồn tại
    if not target_file.exists():
        log(f"Không tìm thấy file mục tiêu: {target_file}", "WARN")
        # Có thể thêm logic loop tìm trong các smali_classes* khác nếu cần thiết
        return

    # 4. Thực hiện patch
    if patch_verifier(target_file):
        log("Đã vá thành công ApkSignatureVerifier.smali", "SUCCESS")
    else:
        log("Không tìm thấy method cần vá hoặc lỗi khi ghi file.", "INFO")

if __name__ == "__main__":
    main()
