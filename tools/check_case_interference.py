# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check seated lid/base and recessed USB cable access against the case/pack."""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    bad = False
    with tempfile.TemporaryDirectory(prefix="sensorly-interference-") as d:
        for v in ("a", "b"):
            for mode in ("interference", "cable_interference"):
                output = Path(d) / f"{v}-{mode}.stl"
                r = subprocess.run(["openscad", "-D", f'part="{mode}"', "-o",
                                    str(output), str(ROOT / f"mechanical/case-{v}.scad")],
                                   capture_output=True, text=True, timeout=120)
                log = r.stdout + r.stderr
                ok = (r.returncode == 1 and not output.exists() and
                      "Current top level object is empty." in log and "ERROR:" not in log)
                label = "seated lid/base" if mode == "interference" else "USB cable/case+pack"
                print(f"variant {v}: {label} intersection {'empty' if ok else 'FAILED'}")
                if not ok:
                    print(log)
                    bad = True
    return int(bad)


if __name__ == "__main__":
    raise SystemExit(main())
