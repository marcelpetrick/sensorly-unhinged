# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build one revision-tagged, checksummed hardware release archive."""
from __future__ import annotations

import argparse
import hashlib
import re
import zipfile
from pathlib import Path

from .boardgen.variants import VARIANTS

ROOT = Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"^hw-([ab])([1-9][0-9]*)$")


def variant_for_tag(tag: str) -> str:
    match = TAG_RE.fullmatch(tag)
    if not match:
        raise ValueError("tag must match hw-aN or hw-bN")
    variant = match.group(1)
    expected = VARIANTS[variant].revision.lower().replace(" ", "-")
    if tag != expected:
        raise ValueError(
            f"tag {tag} does not match the generated {VARIANTS[variant].revision} revision")
    return variant


def release_inputs(root: Path, variant: str) -> list[Path]:
    fixed = [
        root / "LICENSE",
        root / "README.md",
        root / "docs/30-electrical-design-spec.md",
        root / "docs/51-power-safety-qualification.md",
        root / "docs/63-assembly-qualification.md",
        root / "hardware/release-readiness.json",
        root / "hardware/outputs/bom.csv",
        root / "hardware/outputs/netlist.txt",
        root / f"mechanical/case-{variant}-base.stl",
        root / f"mechanical/case-{variant}-lid.stl",
    ]
    trees = [
        root / "hardware/schematic",
        root / f"hardware/variant-{variant}",
        root / "hardware/lib",
        root / f"hardware/outputs/rev-{variant}",
        root / "hardware/outputs/schematic",
    ]
    files = fixed[:]
    for tree in trees:
        if tree.is_dir():
            files.extend(path for path in tree.rglob("*") if path.is_file())
    # A release archive must never inherit the development marker.
    files = [path for path in files if path.name != "DRAFT.txt"]
    missing = [path for path in fixed if not path.is_file() or not path.stat().st_size]
    marker = root / f"hardware/outputs/rev-{variant}/RELEASE.txt"
    if not marker.is_file() or not marker.stat().st_size:
        missing.append(marker)
    if missing:
        names = ", ".join(str(path.relative_to(root)) for path in missing)
        raise ValueError(f"release inputs are missing or empty: {names}")
    return sorted(set(files), key=lambda path: path.relative_to(root).as_posix())


def build_archive(tag: str, commit: str, output_dir: Path,
                  root: Path = ROOT) -> tuple[Path, Path]:
    variant = variant_for_tag(tag)
    files = release_inputs(root, variant)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"sensorly-unhinged-{tag}.zip"
    manifest = (
        "sensorly-unhinged hardware release\n"
        f"tag: {tag}\n"
        f"board revision: {VARIANTS[variant].revision}\n"
        f"source commit: {commit}\n"
        "qualification: hardware/release-readiness.json\n"
    )
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        prefix = f"sensorly-unhinged-{tag}"
        bundle.writestr(f"{prefix}/MANIFEST.txt", manifest)
        for path in files:
            relative = path.relative_to(root)
            bundle.write(path, f"{prefix}/{relative.as_posix()}")
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum_path = archive.with_suffix(".zip.sha256")
    checksum_path.write_text(f"{checksum}  {archive.name}\n")
    return archive, checksum_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--commit", default="unknown")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "_build/release")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        variant = variant_for_tag(args.tag)
        if args.validate_only:
            print(f"{args.tag} matches {VARIANTS[variant].revision}")
            return 0
        archive, checksum = build_archive(args.tag, args.commit, args.output_dir)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"wrote {archive}")
    print(f"wrote {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
