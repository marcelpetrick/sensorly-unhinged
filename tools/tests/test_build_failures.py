# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class BuildFailureTests(unittest.TestCase):
    def test_release_output_mode_requires_qualification(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run(["make", "-f", str(ROOT / "Makefile"),
                                "-o", "drc", "-o", "bom", "-o", "erc",
                                "outputs", "OUTPUT_CLASS=release", "PY=false",
                                "KICAD_CLI=true"], cwd=d, capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn(b"tools.release_gate", r.stdout)
            self.assertFalse((Path(d) / "hardware/outputs").exists())

    def test_failed_release_export_invalidates_both_old_markers(self):
        with tempfile.TemporaryDirectory() as d:
            for variant in ("a", "b"):
                marker = Path(d) / f"hardware/outputs/rev-{variant}/RELEASE.txt"
                marker.parent.mkdir(parents=True)
                marker.write_text("old export\n")
            r = subprocess.run(["make", "-f", str(ROOT / "Makefile"),
                                "-o", "drc", "-o", "bom", "-o", "release-check",
                                "outputs", "OUTPUT_CLASS=release", "KICAD_CLI=false"],
                               cwd=d, capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual(list(Path(d).rglob("RELEASE.txt")), [])

    def test_first_fab_export_failure_is_not_hidden_by_echo(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run(["make", "-f", str(ROOT / "Makefile"),
                                "-o", "drc", "-o", "bom", "outputs",
                                "KICAD_CLI=false"], cwd=d, capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn(b"wrote hardware/outputs/rev-a", r.stdout)

    def test_openscad_failure_stops_mesh_recipe(self):
        with tempfile.TemporaryDirectory() as d:
            executable = Path(d) / "openscad"
            executable.write_text("#!/bin/sh\nexit 7\n")
            executable.chmod(0o755)
            env = dict(os.environ, PATH=d + os.pathsep + os.environ["PATH"])
            r = subprocess.run(["make", "-f", str(ROOT / "Makefile"),
                                "mech", "PY=true"], cwd=d, env=env, capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertNotIn(b"wrote mechanical/case-a-base.stl", r.stdout)
