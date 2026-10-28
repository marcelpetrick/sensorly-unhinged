# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import tempfile
import unittest
import zipfile
import hashlib
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from tools.package_release import (build_archive, manufacturing_paths, source_commit,
                                   variant_for_tag, verify_tag_commit)
from tools.release_gate import REQUIRED


class PackageReleaseTests(unittest.TestCase):
    def test_source_provenance_rejects_wrong_commit_and_dirty_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(["git", *args], cwd=root, text=True,
                                               stderr=subprocess.DEVNULL).strip()
            git("init")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "fixture")
            head = git("rev-parse", "HEAD")
            self.assertEqual(source_commit(root, None), head)
            with self.assertRaisesRegex(ValueError, "does not match HEAD"):
                source_commit(root, "deadbeef")
            (root / "unreviewed.kicad_pcb").write_text("changed source\n")
            with self.assertRaisesRegex(ValueError, "clean committed"):
                source_commit(root, head)

    def test_direct_cli_stops_when_live_export_gate_fails(self):
        from tools import package_release
        with patch("sys.argv", ["package_release", "--tag", "hw-a1"]), \
                patch.object(package_release, "source_commit", return_value="abc"), \
                patch.object(package_release, "verify_tag_commit"), \
                patch.object(package_release.subprocess, "run",
                             side_effect=subprocess.CalledProcessError(2, "make")) as run, \
                patch.object(package_release, "build_archive") as archive, \
                patch("sys.stderr"):
            with self.assertRaises(SystemExit) as error:
                package_release.main()
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(run.call_args.args[0],
                             ["make", "release", "mech", "REQUIRE_OPENSCAD=1",
                              "RELEASE_TAG=hw-a1"])
            archive.assert_not_called()

    def qualified_inputs(self, root):
        def git(*args):
            return subprocess.check_output(["git", *args], cwd=root, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        git("init")
        git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "fixture")
        commit = git("rev-parse", "HEAD")
        git("tag", "hw-a1", commit)
        paths = [
            "LICENSE", "README.md", "docs/30-electrical-design-spec.md",
            "docs/51-power-safety-qualification.md",
            "docs/63-assembly-qualification.md",
            "hardware/outputs/bom.csv", "hardware/outputs/netlist.txt",
            "mechanical/case-a-base.stl", "mechanical/case-a-lid.stl",
            "hardware/outputs/rev-a/RELEASE.txt",
        ] + manufacturing_paths("a")
        paths += [f"measurements/{key}/review.md" for key in sorted(REQUIRED)]
        for name in paths:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic test input\n")
        manifest = {"schema": 1, "checks": [
            {"id": key, "owner": "test", "evidence": f"measurements/{key}/review.md"}
            for key in sorted(REQUIRED)]}
        (root / "hardware/release-readiness.json").write_text(json.dumps(manifest))
        for variant in ("a", "b"):
            report = root / f"_build/{variant}/drc.json"
            report.parent.mkdir(parents=True)
            report.write_text(json.dumps(dict(
                violations=[], unconnected_items=[], schematic_parity=[],
                included_severities=["error", "warning"], ignored_checks=[],
                source=f"env-sensor-{variant}.kicad_pcb")))
        return commit

    def test_tag_must_exist_in_tag_namespace_and_point_to_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(["git", *args], cwd=root, text=True,
                                               stderr=subprocess.DEVNULL).strip()
            git("init")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "first")
            first = git("rev-parse", "HEAD")
            git("branch", "hw-a1", first)
            with self.assertRaisesRegex(ValueError, "does not exist"):
                verify_tag_commit(root, "hw-a1", first)
            git("tag", "hw-a1", first)
            verify_tag_commit(root, "hw-a1", first)
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "second")
            second = git("rev-parse", "HEAD")
            with self.assertRaisesRegex(ValueError, "does not point"):
                verify_tag_commit(root, "hw-a1", second)
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "tag", "-a", "hw-b1", "-m", "annotated", second)
            verify_tag_commit(root, "hw-b1", second)

    def test_tag_must_match_revision_printed_on_board(self):
        self.assertEqual(variant_for_tag("hw-a1"), "a")
        self.assertEqual(variant_for_tag("hw-b1"), "b")
        for bad in ("a1", "hw-a0", "hw-a2", "hw-c1", "HW-A1"):
            with self.subTest(tag=bad), self.assertRaises(ValueError):
                variant_for_tag(bad)

    def test_missing_manufacturing_inputs_cannot_be_packaged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit = self.qualified_inputs(root)
            for name in manufacturing_paths("a"):
                path = root / name
                original = path.read_bytes()
                path.unlink()
                with self.subTest(path=name), self.assertRaisesRegex(
                        ValueError, "release inputs are missing"):
                    build_archive("hw-a1", commit, root / "out", root)
                path.write_bytes(original)
            self.assertFalse((root / "out").exists())

    def test_archive_carries_evidence_and_valid_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit = self.qualified_inputs(root)
            archive, checksum = build_archive(
                "hw-a1", commit, root / "out", root)
            self.assertTrue(checksum.is_file())
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
            self.assertIn(
                "sensorly-unhinged-hw-a1/hardware/outputs/rev-a/RELEASE.txt",
                names)
            self.assertFalse(any(name.endswith("/DRAFT.txt") for name in names))
            for key in REQUIRED:
                self.assertIn(f"sensorly-unhinged-hw-a1/measurements/{key}/review.md", names)
            self.assertEqual(checksum.read_text().split()[0],
                             hashlib.sha256(archive.read_bytes()).hexdigest())

    def test_archive_rejects_missing_or_wrong_hardware_tag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit = self.qualified_inputs(root)
            subprocess.run(["git", "tag", "-d", "hw-a1"], cwd=root,
                           check=True, capture_output=True)
            with self.assertRaisesRegex(ValueError, "does not exist"):
                build_archive("hw-a1", commit, root / "out", root)
            subprocess.run(["git", "tag", "hw-a1", commit], cwd=root,
                           check=True, capture_output=True)
            with self.assertRaisesRegex(ValueError, "does not point"):
                build_archive("hw-a1", "0" * 40, root / "out", root)
            self.assertFalse((root / "out").exists())

    def test_marker_does_not_replace_qualification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit = self.qualified_inputs(root)
            (root / "measurements/battery/review.md").unlink()
            with self.assertRaisesRegex(ValueError, "qualification failed"):
                build_archive("hw-a1", commit, root / "out", root)
            self.assertFalse((root / "out").exists())

    def test_mixed_draft_and_release_exports_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit = self.qualified_inputs(root)
            (root / "hardware/outputs/rev-a/DRAFT.txt").write_text("incomplete\n")
            with self.assertRaisesRegex(ValueError, "draft outputs"):
                build_archive("hw-a1", commit, root / "out", root)
