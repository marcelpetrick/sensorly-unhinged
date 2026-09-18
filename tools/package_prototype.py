# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Create a controlled prototype order package only after fresh build/review gates."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import zipfile

from .boardgen.variants import VARIANTS
from .package_release import manufacturing_paths, source_commit
from .prototype_gate import ROOT, blockers, review_paths


def build_archive(variant, commit, output_dir, root=ROOT):
    if variant not in VARIANTS:
        raise ValueError("variant must be a or b")
    problems = blockers(root)
    if problems:
        raise ValueError("prototype qualification failed: " + "; ".join(problems))
    paths = [root / p for p in manufacturing_paths(variant)] + review_paths(root)
    paths += [root / p for p in (
        "LICENSE", "README.md", "hardware/lib/README.md",
        "hardware/schematic/sym-lib-table",
        f"hardware/variant-{variant}/fp-lib-table",
        "hardware/prototype-readiness.json", "hardware/release-readiness.json",
        "hardware/outputs/bom.csv", "hardware/outputs/netlist.txt",
        "docs/30-electrical-design-spec.md", "docs/51-power-safety-qualification.md",
        "docs/63-assembly-qualification.md", "docs/72-firmware-bringup.md",
        "docs/65-prototype-to-production.md",
        f"mechanical/case-{variant}-base.stl", f"mechanical/case-{variant}-lid.stl")]
    for path in paths:
        if not path.is_file() or not path.stat().st_size or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"missing/empty/external prototype input: {path}")
    revision = VARIANTS[variant].revision.lower().replace(" ", "-")
    name = f"sensorly-unhinged-prototype-{revision}-{commit[:12]}"
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{name}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(f"{name}/PROTOTYPE.txt",
                        "CONTROLLED ENGINEERING PROTOTYPES ONLY — NOT A QUALIFIED PRODUCT\n"
                        f"Revision: {VARIANTS[variant].revision}\nSource commit: {commit}\n"
                        "Maximum planned quantity: 5 of this variant, 5 of the other.\n"
                        "Product measurement/qualification gates remain separate and open.\n"
                        "Follow docs/65-prototype-to-production.md before ordering or powering.\n")
        for path in sorted(set(paths)):
            bundle.write(path, f"{name}/{path.relative_to(root).as_posix()}")
    sidecar = archive.with_suffix(".zip.sha256")
    sidecar.write_text(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n")
    return archive, sidecar


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("a", "b"), required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "_build/prototype")
    args = parser.parse_args(argv)
    try:
        commit = source_commit(ROOT, None)
        # Every CLI path builds before packaging; stale success reports cannot
        # authorize different copper. Outputs keep DRAFT markers outside archive.
        subprocess.run(["make", "prototype-check", "outputs", "mech", "REQUIRE_OPENSCAD=1"],
                       cwd=ROOT, check=True)
        source_commit(ROOT, commit)
        archive, sidecar = build_archive(args.variant, commit, args.output_dir)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    print(f"wrote {archive}\nwrote {sidecar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
