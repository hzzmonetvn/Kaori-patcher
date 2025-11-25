#!/usr/bin/env python3
# 2_fix_bootloop.py

from pathlib import Path
from utils import CURRENT_DIR, log

TARGET_FILES = {
    "framework_unpacked/smali_classes2": [
        "android/hardware/input/KeyboardLayoutPreviewDrawable$GlyphDrawable.smali",
        "android/hardware/input/PhysicalKeyLayout$EnterKey.smali",
        "android/hardware/input/PhysicalKeyLayout$LayoutKey.smali",
        "android/media/MediaRouter2$InstanceInvalidatedCallbackRecord.smali",
        "android/media/MediaRouter2$PackageNameUserHandlePair.smali",
    ],
    "services_unpacked/smali_classes": [
        "com/android/server/BinaryTransparencyService$Digest.smali"
    ],
    "services_unpacked/smali_classes2": [
        "com/android/server/inputmethod/AdditionalSubtypeMapRepository$WriteTask.smali",
        "com/android/server/policy/PhoneWindowManager$SwitchKeyboardLayoutMessageObject.smali",
        "com/android/server/policy/SingleKeyGestureDetector$MessageObject.smali",
    ],
    "miui_services_unpacked/smali_classes": [
        "com/android/server/am/BroadcastQueueModernStubImpl$ActionCount.smali",
        "com/android/server/input/InputDfsReportStubImpl$MessageObject.smali",
        "com/android/server/input/InputOneTrackUtil$TrackEventListData.smali",
        "com/android/server/input/InputOneTrackUtil$TrackEventStringData.smali",
        "com/android/server/policy/MiuiScreenOnProximityLock$AcquireMessageObject.smali",
        "com/android/server/policy/MiuiScreenOnProximityLock$ReleaseMessageObject.smali",
    ],
}

def fix_smali_content(smali_file: Path) -> bool:
    try:
        lines = smali_file.read_text(encoding="utf-8", errors="ignore").splitlines(True)
        new_lines = []
        in_method = False
        method_lines = []
        clear_method = False
        method_name = ""
        modified = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(".method"):
                in_method = True
                method_lines = [line]
                clear_method = False
                method_name = stripped.split()[-1]
                continue
            
            if in_method and "invoke-custom" in stripped:
                clear_method = True
            
            if in_method and stripped.startswith(".end method"):
                if clear_method:
                    modified = True
                    new_lines.append(method_lines[0]) # Header
                    # Inject dummy return based on method type
                    if "equals" in method_name:
                        new_lines.extend(["    .registers 2\n", "    const/4 v0, 0x0\n", "    return v0\n"])
                    elif "hashCode" in method_name:
                        new_lines.extend(["    .registers 1\n", "    const/4 v0, 0x0\n", "    return v0\n"])
                    elif "toString" in method_name:
                        new_lines.extend(["    .registers 1\n", "    const/4 v0, 0x0\n", "    return-object v0\n"])
                    else:
                        new_lines.extend(method_lines[1:])
                    new_lines.append(line) # .end method
                else:
                    new_lines.extend(method_lines)
                    new_lines.append(line)
                in_method = False
                method_lines = []
                continue

            if in_method:
                method_lines.append(line)
            else:
                new_lines.append(line)

        if modified:
            smali_file.write_text("".join(new_lines), encoding="utf-8")
        return modified
    except Exception as e:
        log(f"Lỗi file {smali_file.name}: {e}", "ERROR")
        return False

def main():
    log("Bắt đầu Fix Bootloop (A15)...", "PROCESS")
    fixed_count = 0
    
    for rel_dir, files in TARGET_FILES.items():
        dir_path = CURRENT_DIR / rel_dir
        if not dir_path.exists():
            continue
            
        for rel_file in files:
            file_path = dir_path.joinpath(*rel_file.split("/"))
            if file_path.exists():
                if fix_smali_content(file_path):
                    log(f"Fixed: {rel_file}", "SUCCESS")
                    fixed_count += 1
    
    log(f"Hoàn tất. Đã sửa {fixed_count} files.", "SUCCESS")

if __name__ == "__main__":
    main()
  
