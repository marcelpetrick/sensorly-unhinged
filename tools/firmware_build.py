# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the bring-up image with an explicitly pinned, already installed SDK."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SDK_COMMIT = "735507283d5b2f9fb363a1901172dbd9e847945d"  # ESP-IDF v5.5.4


def main():
    sdk = os.environ.get("IDF_PATH")
    if not sdk:
        raise SystemExit("Source ESP-IDF v5.5.4 export.sh first; see docs/72-firmware-bringup.md")
    actual = subprocess.check_output(["git", "-C", sdk, "rev-parse", "HEAD"], text=True).strip()
    if actual != SDK_COMMIT:
        raise SystemExit(f"ESP-IDF must be v5.5.4 commit {SDK_COMMIT}; found {actual}")
    if subprocess.check_output(["git", "-C", sdk, "status", "--porcelain", "--untracked-files=no"], text=True).strip():
        raise SystemExit("ESP-IDF checkout has tracked modifications")
    subprocess.run(["idf.py", "-C", str(ROOT / "firmware"), "-B", str(ROOT / "_build/firmware"),
                    "-D", f"SDKCONFIG={ROOT / '_build/firmware/sdkconfig'}", "build"], check=True)


if __name__ == "__main__":
    main()
