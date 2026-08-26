"""Every file we wrote carries its licence; nothing we vendored is relicensed.

A LICENSE file at the root is necessary and not sufficient - files get copied
out of repositories one at a time. SPDX headers travel with them, and they are
machine readable, so this check can enforce them.

    python -m tools.check_license          # verify
    python -m tools.check_license --fix    # add missing headers
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COPYRIGHT = "2026 Marcel Petrick <mail@marcelpetrick.it>"
LICENSE_ID = "GPL-3.0-or-later"

# Authored source. Everything else is vendored, generated with its own header,
# or content rather than code.
PATTERNS = ["tools/**/*.py", "*.sh", "mechanical/env-sensor-case.scad"]
EXPLICIT = ["Makefile"]

# Vendored: keeps its own terms, listed in hardware/lib/README.md and the
# README licence table. Never given our header.
VENDORED = ["hardware/lib/sensorly.pretty/", "hardware/lib/sensorly.kicad_sym"]

COMMENT = {".py": "#", ".sh": "#", ".scad": "//", "": "#"}


def header(comment: str) -> str:
    return (f"{comment} SPDX-FileCopyrightText: {COPYRIGHT}\n"
            f"{comment} SPDX-License-Identifier: {LICENSE_ID}\n")


def targets() -> list[Path]:
    out: list[Path] = []
    for pat in PATTERNS:
        out += sorted(ROOT.glob(pat))
    out += [ROOT / e for e in EXPLICIT]
    return [p for p in out
            if p.is_file() and not any(v in str(p.relative_to(ROOT))
                                       for v in VENDORED)]


def main(argv: list[str]) -> int:
    fix = "--fix" in argv
    missing = []
    for p in targets():
        text = p.read_text()
        if "SPDX-License-Identifier" in text:
            continue
        missing.append(p)
        if not fix:
            continue
        c = COMMENT.get(p.suffix, "#")
        lines = text.splitlines(keepends=True)
        if lines and lines[0].startswith("#!"):
            text = lines[0] + header(c) + "".join(lines[1:])
        else:
            text = header(c) + text
        p.write_text(text)

    if fix:
        print(f"  added a licence header to {len(missing)} file(s)")
        return 0
    if missing:
        for p in missing:
            print(f"    no SPDX header: {p.relative_to(ROOT)}")
        return 1
    print(f"  {len(targets())} authored source file(s) carry "
          f"SPDX-License-Identifier: {LICENSE_ID}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
