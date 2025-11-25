#!/usr/bin/env python3

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Callable, Dict, List


class KaoriosToolkit:
    """Self-contained subset of the original FrameworkUnpacker."""

    target_jars = [
        "framework.jar",
        "services.jar",
        "miui-framework.jar",
        "miui-services.jar",
    ]

    unpack_dirs = {
        "framework.jar": "framework_unpacked",
        "services.jar": "services_unpacked",
        "miui-framework.jar": "miui_framework_unpacked",
        "miui-services.jar": "miui_services_unpacked",
    }

    def __init__(self) -> None:
        self.current_dir = Path.cwd()
        self.smali_jar = self.current_dir / "smali.jar"
        self.baksmali_jar = self.current_dir / "baksmali.jar"
        self.usagi_dir = self.current_dir / "USAGI"
        self.module_dir = self.current_dir / "module"

        # Friendly console theme on Windows
        if os.name == "nt":
            try:
                os.system("color 0A")
            except Exception:  # pragma: no cover - cosmetic
                pass

    # ------------------------------------------------------------------ helpers
    def check_tools(self) -> bool:
        if not self.smali_jar.exists():
            print("❌ smali.jar không tồn tại.")
            return False
        if not self.baksmali_jar.exists():
            print("❌ baksmali.jar không tồn tại.")
            return False
        return True

    def check_target_files(self) -> List[str]:
        existing_files: List[str] = []
        for jar in self.target_jars:
            jar_path = self.current_dir / jar
            if jar_path.exists():
                existing_files.append(jar)
                print(f"✅ {jar} đã tìm thấy")
            else:
                print(f"❌ {jar} không tồn tại")
        return existing_files

    # ---------------------------------------------------------------- unpacking
    def unpack_all(self, existing_files: List[str]) -> None:
        if not existing_files:
            print("❌ Không có file JAR để giải nén.")
            return

        print(f"\n🚀 Bắt đầu giải nén {len(existing_files)} file JAR...")
        success = 0
        for jar_file in existing_files:
            if self.unpack_jar(jar_file):
                success += 1
        print(f"\n🎉 Hoàn tất! {success}/{len(existing_files)} file OK.")

    def unpack_jar(self, jar_file: str) -> bool:
        jar_path = self.current_dir / jar_file
        out_dir = self.current_dir / self.unpack_dirs[jar_file]

        print(f"\n📦 Đang giải nén {jar_file}...")
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(jar_path, "r") as zip_ref:
                zip_ref.extractall(out_dir)
            print(f"✅ Đã giải nén vào {out_dir}")
            self.unpack_dex_files(out_dir, jar_file)
            return True
        except Exception as exc:
            print(f"❌ Lỗi khi giải nén {jar_file}: {exc}")
            return False

    def unpack_dex_files(self, jar_dir: Path, jar_name: str) -> None:
        dex_files = list(jar_dir.rglob("*.dex"))
        if not dex_files:
            print("ℹ️  Không tìm thấy file DEX.")
            return

        print(f"🔍 Tìm thấy {len(dex_files)} file DEX trong {jar_name}")
        for dex_file in dex_files:
            self.unpack_dex(dex_file, jar_name)

    def unpack_dex(self, dex_path: Path, jar_name: str) -> None:
        dex_name = dex_path.stem
        jar_unpack_dir = self.current_dir / self.unpack_dirs[jar_name]
        smali_dir = jar_unpack_dir / f"smali_{dex_name}"

        if smali_dir.exists():
            shutil.rmtree(smali_dir)
        smali_dir.mkdir(parents=True, exist_ok=True)

        print(f"📱 Đang decompile {dex_path.name}...")
        cmd = [
            "java",
            "-jar",
            str(self.baksmali_jar),
            "d",
            str(dex_path),
            "-o",
            str(smali_dir),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"✅ {dex_path.name} → {smali_dir}")
        except subprocess.CalledProcessError as exc:
            print(f"❌ Lỗi decompile {dex_path.name}: {exc.stderr}")

    # ----------------------------------------------------------- bootloop fix
    def fix_bootloop_a15(self) -> None:
        print("\n🔧 Fix bootloop (A15)...")
        target_files: Dict[str, List[str]] = {
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

        fixed = 0
        for rel_dir, rel_files in target_files.items():
            dir_path = self.current_dir / rel_dir
            if not dir_path.exists():
                print(f"❌ Thư mục {rel_dir} không tồn tại.")
                continue

            print(f"\n📁 Xử lý: {rel_dir}")
            for rel_file in rel_files:
                file_path = dir_path.joinpath(*rel_file.split("/"))
                if not file_path.exists():
                    print(f"  ⚠️  Không có: {rel_file}")
                    continue
                if self.fix_specific_smali_file(file_path):
                    print(f"  ✅ Đã sửa {rel_file}")
                    fixed += 1
                else:
                    print(f"  ℹ️  Không cần sửa {rel_file}")

        print(f"\n🎉 Hoàn tất fix bootloop. Tổng file sửa: {fixed}")
        input("Nhấn Enter để tiếp tục...")

    def apk_protection(self) -> None:
        print("\n🛡️ Apk Protection...")
        target = (
            self.current_dir
            / "framework_unpacked"
            / "smali_classes4"
            / "android"
            / "util"
            / "apk"
            / "ApkSignatureVerifier.smali"
        )

        if not target.exists():
            print("❌ Không tìm thấy ApkSignatureVerifier.smali.")
            input("Nhấn Enter để tiếp tục...")
            return

        if self.patch_apk_signature_verifier(target):
            print("✅ Đã vá ApkSignatureVerifier.smali.")
        else:
            print("ℹ️ Không cần thay đổi hoặc lỗi khi vá.")
        input("Nhấn Enter để tiếp tục...")

    def patch_apk_signature_verifier(self, file_path: Path) -> bool:
        method_key = "getMinimumSignatureSchemeVersionForTargetSdk"
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines(True)
            new_lines: List[str] = []
            in_target_method = False
            replaced = False
            indent = "    "

            i = 0
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()

                if stripped.startswith(".method") and method_key in stripped:
                    in_target_method = True
                    replaced = True
                    method_indent = re.match(r"^(\s*)", line)
                    indent = method_indent.group(1) + "    " if method_indent else "    "
                    new_lines.append(line)
                    new_lines.append(f"{indent}.registers 1\n")
                    new_lines.append("\n")
                    new_lines.append(f"{indent}const/4 v0, 0x0\n")
                    new_lines.append("\n")
                    new_lines.append(f"{indent}return v0\n")
                    new_lines.append("\n")
                    # Skip existing body until .end method
                    i += 1
                    while i < len(lines) and not lines[i].strip().startswith(".end method"):
                        i += 1
                    if i < len(lines):
                        new_lines.append(lines[i])
                    in_target_method = False
                    i += 1
                    continue

                if in_target_method:
                    if stripped.startswith(".end method"):
                        new_lines.append(line)
                        in_target_method = False
                    i += 1
                    continue

                new_lines.append(line)
                i += 1

            if replaced:
                file_path.write_text("".join(new_lines), encoding="utf-8")
            return replaced
        except Exception as exc:
            print(f"    ❌ Lỗi sửa {file_path.name}: {exc}")
            return False

    def fix_specific_smali_file(self, smali_file: Path) -> bool:
        try:
            lines = smali_file.read_text(encoding="utf-8", errors="ignore").splitlines(True)
            new_lines: List[str] = []
            in_method = False
            method_lines: List[str] = []
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
                        new_lines.append(method_lines[0])
                        if "equals" in method_name:
                            new_lines.extend(
                                [
                                    "    .registers 2\n",
                                    "    const/4 v0, 0x0\n",
                                    "    return v0\n",
                                ]
                            )
                        elif "hashCode" in method_name:
                            new_lines.extend(
                                [
                                    "    .registers 1\n",
                                    "    const/4 v0, 0x0\n",
                                    "    return v0\n",
                                ]
                            )
                        elif "toString" in method_name:
                            new_lines.extend(
                                [
                                    "    .registers 1\n",
                                    "    const/4 v0, 0x0\n",
                                    "    return-object v0\n",
                                ]
                            )
                        else:
                            new_lines.extend(method_lines[1:])
                        new_lines.append(line)
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
        except Exception as exc:
            print(f"    ❌ Lỗi xử lý {smali_file.name}: {exc}")
            return False

    # --------------------------------------------------------------- kaori kit
    def kaori_toolbox(self) -> None:
        print("\n🎨 Usagi mod...")
        operations = 0

        if self.copy_kaorios_folder():
            operations += 1
            print("    ✅ Copy kaorios hoàn tất")

        app_pkg_mgr = self.current_dir / "framework_unpacked" / "smali_classes" / "android" / "app" / "ApplicationPackageManager.smali"
        if app_pkg_mgr.exists() and self.modify_application_package_manager_kaori(app_pkg_mgr):
            operations += 1
            print("    ✅ ApplicationPackageManager OK")

        instrumentation = self.current_dir / "framework_unpacked" / "smali_classes" / "android" / "app" / "Instrumentation.smali"
        if instrumentation.exists() and self.modify_instrumentation_kaori(instrumentation):
            operations += 1
            print("    ✅ Instrumentation OK")

        keystore2 = self.current_dir / "framework_unpacked" / "smali_classes3" / "android" / "security" / "KeyStore2.smali"
        if keystore2.exists() and self.modify_keystore2_kaori(keystore2):
            operations += 1
            print("    ✅ KeyStore2 OK")

        android_keystore_spi = (
            self.current_dir
            / "framework_unpacked"
            / "smali_classes3"
            / "android"
            / "security"
            / "keystore2"
            / "AndroidKeyStoreSpi.smali"
        )
        if android_keystore_spi.exists() and self.modify_android_keystore_spi_kaori(android_keystore_spi):
            operations += 1
            print("    ✅ AndroidKeyStoreSpi OK")

        print(f"\n🎉 Hoàn tất Usagi mod ({operations} thao tác).")
        input("Nhấn Enter để tiếp tục...")

    def copy_kaorios_folder(self) -> bool:
        try:
            source = self.usagi_dir / "kaorios"
            target = (
                self.current_dir
                / "framework_unpacked"
                / "smali_classes5"
                / "com"
                / "android"
                / "internal"
                / "util"
                / "kaorios"
            )
            if not source.exists():
                print(f"    ❌ Không có thư mục nguồn {source}")
                return False

            if target.exists():
                shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target)
            return True
        except Exception as exc:
            print(f"    ❌ Lỗi copy kaorios: {exc}")
            return False

    def modify_application_package_manager_kaori(self, file_path: Path) -> bool:
        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.readlines()

            new_lines: List[str] = []
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

                if stripped == "# static fields" and not modifications["field_added"]:
                    new_lines.append(line)
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        new_lines.append(lines[j])
                        j += 1
                    indent = re.match(r"^(\s*)", lines[j])[1] if j < len(lines) else ""
                    new_lines.append(f"{indent}.field private final mContext:Landroid/content/Context;\n")
                    new_lines.append("\n")
                    modifications["field_added"] = True
                    i = j
                    continue

                if stripped == "# direct methods" and not modifications["constructor_added"]:
                    new_lines.append(line)
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        new_lines.append(lines[j])
                        j += 1
                    indent = re.match(r"^(\s*)", lines[j])[1] if j < len(lines) else ""
                    constructor = [
                        f"{indent}.method public constructor <init>(Landroid/content/Context;)V\n",
                        f"{indent}    .registers 2\n",
                        "\n",
                        f"{indent}    invoke-direct {{p0}}, Ljava/lang/Object;-><init>()V\n",
                        "\n",
                        f"{indent}    iput-object p1, p0, Landroid/app/ApplicationPackageManager;->mContext:Landroid/content/Context;\n",
                        "\n",
                        f"{indent}    return-void\n",
                        "\n",
                        f"{indent}.end method\n",
                        "\n",
                    ]
                    new_lines.extend(constructor)
                    modifications["constructor_added"] = True
                    i = j
                    continue

                if stripped.startswith(".method") and "hasSystemFeature(Ljava/lang/String;)Z" in stripped and not modifications["method1_replaced"]:
                    replacement = [
                        ".method public hasSystemFeature(Ljava/lang/String;)Z\n",
                        "    .registers 3\n",
                        "\n",
                        "    const/4 v0, 0x0\n",
                        "\n",
                        "    invoke-virtual {p0, p1, v0}, Landroid/app/ApplicationPackageManager;->hasSystemFeature(Ljava/lang/String;I)Z\n",
                        "\n",
                        "    move-result p0\n",
                        "\n",
                        "    invoke-static {p0, p1}, Lcom/android/internal/util/kaorios/ToolboxUtils;->KaoriosAttestationBL(ZLjava/lang/String;)Z\n",
                        "\n",
                        "    move-result p0\n",
                        "\n",
                        "    return p0\n",
                        "\n",
                        ".end method\n",
                    ]
                    new_lines.extend(replacement)
                    i += 1
                    while i < len(lines) and not lines[i].strip().startswith(".end method"):
                        i += 1
                    i += 1
                    modifications["method1_replaced"] = True
                    continue

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
                            new_lines.append(
                                "    invoke-static {}, Landroid/app/ActivityThread;->currentPackageName()Ljava/lang/String;\n"
                                "\n"
                                "    move-result-object v0\n"
                                "\n"
                                "    iget-object v1, p0, Landroid/app/ApplicationPackageManager;->mContext:Landroid/content/Context;\n"
                                "\n"
                                "    invoke-static {}, Lcom/android/internal/util/kaorios/KaoriFeaturesUtils;->getAppLog()Ljava/lang/String;\n"
                                "\n"
                                "    move-result-object v2\n"
                                "\n"
                                "    const/4 v3, 0x1\n"
                                "\n"
                                "    invoke-static {v1, v2, v3}, Lcom/android/internal/util/kaorios/SettingsHelper;->isToggleEnabled(Landroid/content/Context;Ljava/lang/String;Z)Z\n"
                                "\n"
                                "    move-result v1\n"
                                "\n"
                                "    invoke-static {}, Lcom/android/internal/util/kaorios/KaoriFeaturesUtils;->getFeaturesPixel()[Ljava/lang/String;\n"
                                "\n"
                                "    move-result-object v2\n"
                                "\n"
                                "    invoke-static {}, Lcom/android/internal/util/kaorios/KaoriFeaturesUtils;->getFeaturesPixelOthers()[Ljava/lang/String;\n"
                                "\n"
                                "    move-result-object v4\n"
                                "\n"
                                "    invoke-static {}, Lcom/android/internal/util/kaorios/KaoriFeaturesUtils;->getFeaturesTensor()[Ljava/lang/String;\n"
                                "\n"
                                "    move-result-object v5\n"
                                "\n"
                                "    invoke-static {}, Lcom/android/internal/util/kaorios/KaoriFeaturesUtils;->getFeaturesNexus()[Ljava/lang/String;\n"
                                "\n"
                                "    move-result-object v6\n"
                                "\n"
                            )
                        new_lines.append(current_line)
                        i += 1
                    if i < len(lines):
                        new_lines.append(lines[i])
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
            print(f"    ❌ Lỗi sửa {file_path.name}: {exc}")
            return False

    def modify_instrumentation_kaori(self, file_path: Path) -> bool:
        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.readlines()

            new_lines: List[str] = []
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
                    indent = re.match(r"^(\s*)", line)[1]
                    new_lines.append(f"{indent}invoke-static {{p1}}, Lcom/android/internal/util/kaorios/ToolboxUtils;->KaoriosProps(Landroid/content/Context;)V\n")
                    method1_patched = True
                if in_method2 and stripped == "return-object v0" and not method2_patched:
                    indent = re.match(r"^(\s*)", line)[1]
                    new_lines.append(f"{indent}invoke-static {{p3}}, Lcom/android/internal/util/kaorios/ToolboxUtils;->KaoriosProps(Landroid/content/Context;)V\n")
                    method2_patched = True

                new_lines.append(line)

            if method1_patched or method2_patched:
                file_path.write_text("".join(new_lines), encoding="utf-8")
                return True
            return False
        except Exception as exc:
            print(f"    ❌ Lỗi sửa {file_path.name}: {exc}")
            return False

    def modify_keystore2_kaori(self, file_path: Path) -> bool:
        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.readlines()

            new_lines: List[str] = []
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
                    indent = re.match(r"^(\s*)", line)[1]
                    new_lines.append(f"{indent}invoke-static {{v0}}, Lcom/android/internal/util/kaorios/ToolboxUtils;->KaoriosKeybox(Landroid/system/keystore2/KeyEntryResponse;)Landroid/system/keystore2/KeyEntryResponse;\n")
                    new_lines.append(f"{indent}move-result-object v0\n")
                    patched = True

                new_lines.append(line)

            if patched:
                file_path.write_text("".join(new_lines), encoding="utf-8")
                return True
            return False
        except Exception as exc:
            print(f"    ❌ Lỗi sửa {file_path.name}: {exc}")
            return False

    def modify_android_keystore_spi_kaori(self, file_path: Path) -> bool:
        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as handle:
                lines = handle.readlines()

            new_lines: List[str] = []
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
                    indent = re.match(r"^(\s*)", line)[1]
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
            print(f"    ❌ Lỗi sửa {file_path.name}: {exc}")
            return False

    # -------------------------------------------------------------- repack ops
    def repack_all_classes(self) -> None:
        print("\n=== REPACK ALL CLASSES ===")
        smali_dirs: List[Path] = []
        for folder in [
            "framework_unpacked",
            "services_unpacked",
            "miui_framework_unpacked",
            "miui_services_unpacked",
        ]:
            base = self.current_dir / folder
            if base.exists():
                for child in base.iterdir():
                    if child.is_dir() and child.name.startswith("smali_classes"):
                        smali_dirs.append(child)

        if not smali_dirs:
            print("❌ Không tìm thấy thư mục smali.")
            return

        for directory in smali_dirs:
            dex_name = directory.name.replace("smali_", "") + ".dex"
            output = directory.parent / dex_name
            cmd = [
                "java",
                "-jar",
                str(self.smali_jar),
                "a",
                str(directory),
                "-o",
                str(output),
                "--api",
                "33",
            ]
            print(f"\n🔄 Đang repack {directory.name} → {dex_name}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print("    ✅ Thành công")
                shutil.rmtree(directory)
            else:
                print(f"    ❌ Lỗi: {result.stderr}")

        print("\n🎉 Repack classes hoàn tất.")

    def repack_all_jar_files(self) -> None:
        print("\n=== REPACK ALL JAR FILES ===")
        candidates = [
            ("framework.jar", "framework_unpacked"),
            ("services.jar", "services_unpacked"),
            ("miui-framework.jar", "miui_framework_unpacked"),
            ("miui-services.jar", "miui_services_unpacked"),
        ]

        any_repacked = False
        for jar_name, directory in candidates:
            dir_path = self.current_dir / directory
            if not dir_path.exists():
                continue

            print(f"\n🔄 Đang repack {directory} → {jar_name}")
            cmd = f'jar cfM "{jar_name}" -C "{dir_path}" .'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print("    ✅ Thành công")
                shutil.rmtree(dir_path)
                any_repacked = True
            else:
                print(f"    ❌ Lỗi: {result.stderr}")

        if not any_repacked:
            print("❌ Không có thư mục unpacked để repack.")
        else:
            print("\n🎉 Repack JAR hoàn tất.")

    # -------------------------------------------------------------- module zip
    def create_test_module(self) -> None:
        print("\n📦 Tạo Test Module...")
        module_root = self.module_dir
        framework_dir = module_root / "system" / "framework"
        system_ext_dir = module_root / "system" / "system_ext" / "framework"
        framework_dir.mkdir(parents=True, exist_ok=True)
        system_ext_dir.mkdir(parents=True, exist_ok=True)

        copies = [
            (self.current_dir / "framework.jar", framework_dir / "framework.jar"),
            (self.current_dir / "services.jar", framework_dir / "services.jar"),
            (self.current_dir / "miui-framework.jar", system_ext_dir / "miui-framework.jar"),
            (self.current_dir / "miui-services.jar", system_ext_dir / "miui-services.jar"),
        ]

        for src, dst in copies:
            if src.exists():
                shutil.copy2(src, dst)
                print(f"   ✅ Copy {src.name}")
            else:
                print(f"   ⚠️  Thiếu {src.name}")

        zip_path = self.current_dir / "Module-framework-test.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(module_root):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(module_root)
                    zipf.write(file_path, arcname)
                    print(f"   ➕ {arcname}")

        for _, dst in copies:
            if dst.exists():
                dst.unlink()

        print("🎉 Đã tạo Module-framework-test.zip thành công.")


# ==============================================================================
# CLI
# ==============================================================================

class KaoriosCLI:
    def __init__(self) -> None:
        self.toolkit = KaoriosToolkit()

    def run(self) -> None:
        if not self.toolkit.check_tools():
            print("\n❌ Thiếu smali/baksmali. Thoát Usagi mod.")
            return

        while True:
            self._print_menu()
            try:
                choice = input("Chọn chức năng (1-7): ").strip()
            except KeyboardInterrupt:
                print("\n👋 Thoát Usagi mod.")
                return

            actions: Dict[str, Callable[[], None]] = {
                "1": self._unpack_all_jars,
                "2": self.toolkit.fix_bootloop_a15,
                "3": self.toolkit.apk_protection,
                "4": self.toolkit.kaori_toolbox,
                "5": self.toolkit.repack_all_classes,
                "6": self.toolkit.repack_all_jar_files,
                "7": self.toolkit.create_test_module,
                "8": self._exit_cli,
            }

            action = actions.get(choice)
            if not action:
                print("❌ Lựa chọn không hợp lệ.")
                continue
            action()

    def _unpack_all_jars(self) -> None:
        files = self.toolkit.check_target_files()
        self.toolkit.unpack_all(files)

    def _exit_cli(self) -> None:
        print("👋 Tạm biệt!")
        sys.exit(0)

    def _print_menu(self) -> None:
        print("\n" + "=" * 50)
        print("                USAGI MOD")
        print("=" * 50)
        print("1. Giải nén tất cả file JAR có sẵn")
        print("2. Fix Bootloop (A15)")
        print("3. Apk Protection")
        print("4. Kaori Toolbox")
        print("5. Repack All Classes")
        print("6. Repack All Jar File")
        print("7. Create Test Module")
        print("8. Thoát")
        print()


def main() -> None:
    KaoriosCLI().run()


if __name__ == "__main__":
    main()

