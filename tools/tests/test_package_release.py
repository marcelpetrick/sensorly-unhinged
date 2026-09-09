# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.package_release import build_archive, variant_for_tag


class PackageReleaseTests(unittest.TestCase):
    def test_tag_must_match_revision_printed_on_board(self):
        self.assertEqual(variant_for_tag("hw-a1"), "a")
        self.assertEqual(variant_for_tag("hw-b1"), "b")
        for bad in ("a1", "hw-a0", "hw-a2", "hw-c1", "HW-A1"):
            with self.subTest(tag=bad), self.assertRaises(ValueError):
                variant_for_tag(bad)

    def test_missing_manufacturing_inputs_cannot_be_packaged(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "release inputs are missing"):
                build_archive("hw-a1", "deadbeef", Path(directory) / "out",
                              Path(directory))

    def test_archive_has_release_marker_and_excludes_draft_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [
                "LICENSE", "README.md", "docs/30-electrical-design-spec.md",
                "docs/51-power-safety-qualification.md",
                "docs/63-assembly-qualification.md",
                "hardware/release-readiness.json", "hardware/outputs/bom.csv",
                "hardware/outputs/netlist.txt", "mechanical/case-a-base.stl",
                "mechanical/case-a-lid.stl", "hardware/schematic/design.kicad_sch",
                "hardware/variant-a/design.kicad_pcb", "hardware/lib/lib.txt",
                "hardware/outputs/rev-a/RELEASE.txt",
                "hardware/outputs/rev-a/DRAFT.txt",
                "hardware/outputs/schematic/design.pdf",
            ]
            for name in paths:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("test\n")
            archive, checksum = build_archive(
                "hw-a1", "deadbeef", root / "out", root)
            self.assertTrue(checksum.is_file())
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
            self.assertIn(
                "sensorly-unhinged-hw-a1/hardware/outputs/rev-a/RELEASE.txt",
                names)
            self.assertFalse(any(name.endswith("/DRAFT.txt") for name in names))
