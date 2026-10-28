# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build one revision-tagged, checksummed hardware release archive."""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import zipfile
from pathlib import Path

from .boardgen.variants import VARIANTS
from .boardgen.design import PARTS
from .release_gate import blockers, qualification_paths

ROOT = Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"^hw-([ab])([1-9][0-9]*)$")


def manufacturing_paths(variant: str) -> list[str]:
    """Files required even if an export tree or old release marker exists."""
    board = f"env-sensor-{variant}"
    prefix = f"hardware/outputs/rev-{variant}"
    layers = ("F_Cu", "In1_Cu", "In2_Cu", "B_Cu", "F_Mask", "B_Mask",
              "F_Paste", "B_Paste", "F_Silkscreen", "B_Silkscreen", "Edge_Cuts")
    return [f"{prefix}/gerber/{board}-{layer}.gbr" for layer in layers] + [
        f"{prefix}/drill/{board}.drl",
        f"{prefix}/assembly/cpl-{variant}.csv",
        f"{prefix}/assembly/assembly-top-{variant}.pdf",
        f"{prefix}/step/{board}.step",
        "hardware/outputs/schematic/env-sensor.pdf",
        "hardware/outputs/schematic/env-sensor.net",
        "hardware/schematic/env-sensor.kicad_sch",
        f"hardware/variant-{variant}/{board}.kicad_pcb",
        f"hardware/variant-{variant}/{board}.kicad_pro",
        f"hardware/variant-{variant}/{board}.kicad_dru",
        "hardware/lib/sensorly.kicad_sym",
    ] + sorted({f"hardware/lib/sensorly.pretty/{part.footprint.split(':')[-1]}.kicad_mod"
                for part in PARTS})


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


def source_commit(root: Path, requested: str | None) -> str:
    """Do not label uncommitted inputs with an unrelated source commit."""
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if requested is not None and requested != head:
        raise ValueError("source commit does not match HEAD")
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root, text=True)
    if dirty:
        raise ValueError("release requires a clean committed source tree")
    return head


def verify_tag_commit(root: Path, tag: str, commit: str) -> None:
    """Require the exact hardware tag to identify the packaged commit.

    Peeling accepts annotated as well as lightweight tags. Resolve only the
    tags namespace so a same-named branch cannot impersonate the revision.
    """
    variant_for_tag(tag)
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"],
        cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise ValueError(f"hardware tag {tag} does not exist or does not point to a commit")
    if result.stdout.strip() != commit:
        raise ValueError(f"hardware tag {tag} does not point to source commit {commit}")


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
    fixed.extend(root / path for path in manufacturing_paths(variant))
    fixed.extend(qualification_paths(root))
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
    if (root / f"hardware/outputs/rev-{variant}/DRAFT.txt").exists():
        raise ValueError("draft outputs cannot be packaged as a release")
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
    problems = blockers(root)
    if problems:
        raise ValueError("release qualification failed: " + "; ".join(problems))
    verify_tag_commit(root, tag, commit)
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
    parser.add_argument("--commit", help="full source commit; must equal clean HEAD")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "_build/release")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        variant = variant_for_tag(args.tag)
        if args.validate_only:
            print(f"{args.tag} matches {VARIANTS[variant].revision}")
            return 0
        commit = source_commit(ROOT, args.commit)
        verify_tag_commit(ROOT, args.tag, commit)
        # The module is also a public entry point: re-run live rules and exports
        # instead of trusting reports/markers from an earlier successful build.
        subprocess.run(["make", "release", "mech", "REQUIRE_OPENSCAD=1",
                        f"RELEASE_TAG={args.tag}"],
                       cwd=ROOT, check=True)
        source_commit(ROOT, commit)
        verify_tag_commit(ROOT, args.tag, commit)
        archive, checksum = build_archive(args.tag, commit, args.output_dir)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    print(f"wrote {archive}")
    print(f"wrote {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
