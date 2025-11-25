#!/usr/bin/env python3
# kaori.py

import os
import shutil
import re
from pathlib import Path
from utils import CURRENT_DIR, USAGI_DIR, log

def copy_kaorios_folder():
    source = USAGI_DIR / "kaorios"
    
    target = (
        CURRENT_DIR / "framework_unpacked" / "smali_classes5" 
        / "com" / "android" / "internal" / "util" / "kaorios"
    )
    
    if not source.exists():
        log(f"Không tìm thấy thư mục nguồn {source.name}", "WARN")
        return False
    
    try:
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
        return True
    except Exception as e:
        log(f"Lỗi copy kaorios: {e}", "ERROR")
        return False

def modify_application_package_manager_kaori(file_path: Path) -> bool:
    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines(True)
        new_lines = []
        modifications = {
            "field_added": False,
            "constructor_added": False,
            "method1_replaced": False,
            "method2_modified": False,
        }

        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 1. Add Field
            if stripped == "# static fields" and not modifications["field_added"]:
                new_lines.append(line)
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    new_lines.append(lines[j])
                    j += 1
                indent = re.match(r"^(\s*)", lines[j])[1] if j < len(lines) else ""
                new_lines.append(f"{indent}.field private final mContext:Landroid/content/Context;\n\n")
                modifications["field_added"] = True
                i = j
                continue

            # 2. Add Constructor
            if stripped == "# direct methods" and not modifications["constructor_added"]:
                new_lines.append(line)
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    new_lines.append(lines[j])
                    j += 1
                indent = re.match(r"^(\s*)", lines[j])[1] if j < len(lines) else ""
                constructor = [
                    f"{indent}.method public constructor <init>(Landroid/content/Context;)V\n",
                    f"{indent}    .registers 2\n\n",
                    f"{indent}    invoke-direct {{p0}}, Ljava/lang/Object;-><init>()V\n\n",
                    f"{indent}    iput-object p1, p0, Landroid/app/ApplicationPackageManager;->mContext:Landroid/content/Context;\n\n",
                    f"{indent}    return-void\n\n",
                    f"{indent}.end method\n\n",
                ]
                new_lines.extend(constructor)
                modifications["constructor_added"] = True
                i = j
                continue

            # 3. Replace hasSystemFeature(String)
            if stripped.startswith(".method") and "hasSystemFeature(Ljava/lang/String;)Z" in stripped and not modifications["method1_replaced"]:
                replacement = [
                    ".method public hasSystemFeature(Ljava/lang/String;)Z\n",
                    "    .registers 3\n\n",
                    "    const/4 v0, 0x0\n\n",
                    "    invoke-virtual {p0, p1, v0}, Landroid/app/ApplicationPackageManager;->hasSystemFeature(Ljava/lang/String;I)Z\n\n",
                    "    move-result p0\n\n",
                    "    invoke-static {p0, p1}, Lcom/android/internal/util/kaorios/ToolboxUtils;->KaoriosAttestationBL(ZLjava/lang/String;)Z\n\n",
                    "    move-result p0\n\n",
                    "    return p0\n\n",
                    ".end method\n",
                ]
                new_lines.extend(replacement)
                # Skip original body
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(".end method"):
                    i += 1
                i += 1 
                modifications["method1_replaced"] = True
                continue

            # 4. Modify hasSystemFeature(String, Int)
            if stripped.startswith(".method") and "hasSystemFeature(Ljava/lang/String;I)Z" in stripped and not modifications["method2_modified"]:
                new_lines.append(line)
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(".end method"):
                    current_line = lines[i]
                    current_stripped = current_line.strip()
                    if current_stripped.startswith(".registers"):
                        new_lines.append("    .registers 12\n")
                        i += 1
                        continue
                    if "mHasSystemFeatureCache" in current_stripped:
                        # Inject Kaori logic block
                        new_lines.append(
                            "    invoke-static {}, Landroid/app/ActivityThread;->currentPackageName()Ljava/lang/String;\n\n"
                            "    move-result-object v0\n\n"
                            "    iget-object v1, p0, Landroid/app/ApplicationPackageManager;->mContext:Landroid/content/Context;\n\n"
                            "    invoke-static {}, Lcom/android/internal/util/kaorios/KaoriFeaturesUtils;->getAppLog()Ljava/lang/String;\n\n"
                            "    move-result-object v2\n\n"
                            "    const/4 v3, 0x1\n\n"
                            "    invoke-static {v1, v2, v3}, Lcom/android/internal/util/kaorios/SettingsHelper;->isToggleEnabled(Landroid/content/Context;Ljava/lang/String;Z)Z\n\n"
                            "    move-result v1\n\n"
                            "    invoke-static {}, Lcom/android/internal/util/kaorios/KaoriFeaturesUtils;->getFeaturesPixel()[Ljava/lang/String;\n\n"
                            "    move-result-object v2\n\n"
                            "    invoke-static {}, Lcom/android/internal/util/kaorios/KaoriFeaturesUtils;->getFeaturesPixelOthers()[Ljava/lang/String;\n\n"
                            "    move-result-object v4\n\n"
                            "    invoke-static {}, Lcom/android/internal/util/kaorios/KaoriFeaturesUtils;->getFeaturesTensor()[Ljava/lang/String;\n\n"
                            "    move-result-object v5\n\n"
                            "    invoke-static {}, Lcom/android/internal/util/kaorios/KaoriFeaturesUtils;->getFeaturesNexus()[Ljava/lang/String;\n\n"
                            "    move-result-object v6\n\n"
                        )
                    new_lines.append(current_line)
                    i += 1
                if i < len(lines):
                    new_lines.append(lines[i]) # .end method
                    i += 1
                modifications["method2_modified"] = True
                continue

            new_lines.append(line)
            i += 1

        if any(modifications.values()):
            file_path.write_text("".join(new_lines), encoding="utf-8")
            return True
        return False
    except Exception as exc:
        log(f"Lỗi sửa {file_path.name}: {exc}", "ERROR")
        return False

def modify_instrumentation_kaori(file_path: Path) -> bool:
    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines(True)
        new_lines = []
        in_method1 = False
        in_method2 = False
        method1_patched = False
        method2_patched = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(".method public static whitelist newApplication(Ljava/lang/Class;Landroid/content/Context;)Landroid/app/Application;"):
                in_method1 = True
                new_lines.append(line)
                continue
            if stripped.startswith(".method public whitelist newApplication(Ljava/lang/ClassLoader;Ljava/lang/String;Landroid/content/Context;)Landroid/app/Application;"):
                in_method2 = True
                new_lines.append(line)
                continue
            
            if in_method1 and stripped == ".end method":
                in_method1 = False
            if in_method2 and stripped == ".end method":
                in_method2 = False

            if in_method1 and stripped == "return-object v0" and not method1_patched:
                indent = re.match(r"^(\s*)", line).group(1)
                new_lines.append(f"{indent}invoke-static {{p1}}, Lcom/android/internal/util/kaorios/ToolboxUtils;->KaoriosProps(Landroid/content/Context;)V\n")
                method1_patched = True
            
            if in_method2 and stripped == "return-object v0" and not method2_patched:
                indent = re.match(r"^(\s*)", line).group(1)
                new_lines.append(f"{indent}invoke-static {{p3}}, Lcom/android/internal/util/kaorios/ToolboxUtils;->KaoriosProps(Landroid/content/Context;)V\n")
                method2_patched = True

            new_lines.append(line)

        if method1_patched or method2_patched:
            file_path.write_text("".join(new_lines), encoding="utf-8")
            return True
        return False
    except Exception as exc:
        log(f"Lỗi sửa {file_path.name}: {exc}", "ERROR")
        return False

def modify_keystore2_kaori(file_path: Path) -> bool:
    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines(True)
        new_lines = []
        in_method = False
        patched = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(".method public blacklist getKeyEntry("):
                in_method = True
                new_lines.append(line)
                continue
            if in_method and stripped == ".end method":
                in_method = False

            if in_method and stripped == "return-object v0" and not patched:
                indent = re.match(r"^(\s*)", line).group(1)
                new_lines.append(f"{indent}invoke-static {{v0}}, Lcom/android/internal/util/kaorios/ToolboxUtils;->KaoriosKeybox(Landroid/system/keystore2/KeyEntryResponse;)Landroid/system/keystore2/KeyEntryResponse;\n")
                new_lines.append(f"{indent}move-result-object v0\n")
                patched = True

            new_lines.append(line)

        if patched:
            file_path.write_text("".join(new_lines), encoding="utf-8")
            return True
        return False
    except Exception as exc:
        log(f"Lỗi sửa {file_path.name}: {exc}", "ERROR")
        return False

def modify_android_keystore_spi_kaori(file_path: Path) -> bool:
    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines(True)
        new_lines = []
        in_method = False
        patched = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(".method public whitelist test-api engineGetCertificateChain"):
                in_method = True
                new_lines.append(line)
                continue
            if in_method and stripped == ".end method":
                in_method = False

            if in_method and "registers" in stripped and not patched:
                indent = re.match(r"^(\s*)", line).group(1)
                new_lines.append(line)
                new_lines.append(f"{indent}invoke-static {{}}, Lcom/android/internal/util/kaorios/ToolboxUtils;->KaoriosPropsEngineGetCertificateChain()V\n")
                patched = True
                continue

            new_lines.append(line)

        if patched:
            file_path.write_text("".join(new_lines), encoding="utf-8")
            return True
        return False
    except Exception as exc:
        log(f"Lỗi sửa {file_path.name}: {exc}", "ERROR")
        return False

def main():

    if os.getenv("ENABLE_MOD") == "false":
        log("SKIP: Kaori Features (User disabled)", "WARN")
        return

    log("Bắt đầu Kaori Mod...", "PROCESS")
    
    
    if copy_kaorios_folder():
        log("Đã copy thư mục kaorios", "SUCCESS")
    
    
    
    fw_base = CURRENT_DIR / "framework_unpacked"
    
    targets = [
        (
            fw_base / "smali_classes" / "android" / "app" / "ApplicationPackageManager.smali",
            modify_application_package_manager_kaori
        ),
        (
            fw_base / "smali_classes" / "android" / "app" / "Instrumentation.smali",
            modify_instrumentation_kaori
        ),
        (
            fw_base / "smali_classes3" / "android" / "security" / "KeyStore2.smali",
            modify_keystore2_kaori
        ),
        (
            fw_base / "smali_classes3" / "android" / "security" / "keystore2" / "AndroidKeyStoreSpi.smali",
            modify_android_keystore_spi_kaori
        )
    ]

    count = 0
    for file_path, func in targets:
        if file_path.exists():
            if func(file_path):
                log(f"Đã patch: {file_path.name}", "SUCCESS")
                count += 1
            else:
                log(f"Patch thất bại hoặc không cần thiết: {file_path.name}", "INFO")
        else:
            log(f"Bỏ qua (Không tìm thấy): {file_path.name}", "WARN")

    log(f"Patch successfully ({count} file đã sửa).", "SUCCESS")

if __name__ == "__main__":
    main()
              
