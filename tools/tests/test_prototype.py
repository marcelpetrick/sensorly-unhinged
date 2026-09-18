# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from tools import package_prototype
from tools.prototype_gate import REQUIRED, blockers


class PrototypeTests(unittest.TestCase):
    def fixture(self, root):
        (root / "hardware").mkdir()
        rows = []
        for key in sorted(REQUIRED):
            path = root / f"review-{key}.md"
            path.write_text("SYNTHETIC TEST FIXTURE, NOT QUALIFICATION\n")
            rows.append(dict(id=key, owner="test", evidence=path.name))
        (root / "hardware/prototype-readiness.json").write_text(json.dumps(dict(
            schema=1, purpose="controlled-5-plus-5-engineering-prototypes", checks=rows)))
        for v in ("a", "b"):
            p = root / f"_build/{v}/drc.json"; p.parent.mkdir(parents=True)
            p.write_text(json.dumps(dict(source=f"env-sensor-{v}.kicad_pcb",
                                        included_severities=["error", "warning"], ignored_checks=[],
                                        violations=[], unconnected_items=[], schematic_parity=[])))

    def test_absence_is_not_approval(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertGreaterEqual(len(blockers(Path(d))), 3)

    def test_physical_product_measurements_are_not_needed_for_prototype_review(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.fixture(root)
            self.assertEqual(blockers(root), [])
            (root / "review-electrical.md").unlink()
            self.assertTrue(any("electrical" in p for p in blockers(root)))

    def test_layout_failure_cannot_be_waived_by_prototype_reviews(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.fixture(root)
            p = root / "_build/b/drc.json"; report = json.loads(p.read_text())
            report["unconnected_items"] = [{"type": "unconnected_items"}]
            p.write_text(json.dumps(report))
            self.assertTrue(any("b: 1 unconnected" in p for p in blockers(root)))

    def test_duplicate_reviews_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.fixture(root)
            p = root / "hardware/prototype-readiness.json"; manifest = json.loads(p.read_text())
            manifest["checks"][-1] = manifest["checks"][0]
            p.write_text(json.dumps(manifest))
            self.assertTrue(any("invalid prototype" in p for p in blockers(root)))

    def test_direct_cli_requires_live_gate(self):
        with patch.object(package_prototype, "source_commit", return_value="a" * 40), \
                patch.object(package_prototype.subprocess, "run", side_effect=subprocess.CalledProcessError(2, "make")), \
                patch.object(package_prototype, "build_archive") as archive, patch("sys.stderr"):
            with self.assertRaises(SystemExit):
                package_prototype.main(["--variant", "a"])
            archive.assert_not_called()

    def test_package_is_complete_checksums_and_carries_prototype_disposition(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.fixture(root)
            # Populate missing required files, then verify a deliberate deletion
            # is caught. Fixture creation follows diagnostics; never used in repo.
            for _ in range(100):
                try:
                    archive, sidecar = package_prototype.build_archive("a", "a" * 40, root / "out", root)
                    break
                except ValueError as exc:
                    prefix = "missing/empty/external prototype input: "
                    self.assertTrue(str(exc).startswith(prefix), str(exc))
                    path = Path(str(exc)[len(prefix):]); path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("SYNTHETIC TEST INPUT\n")
            else:
                self.fail("Fixture did not converge")
            self.assertEqual(sidecar.read_text().split()[0], hashlib.sha256(archive.read_bytes()).hexdigest())
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
                self.assertTrue(any(n.endswith("/PROTOTYPE.txt") for n in names))
                self.assertFalse(any(n.endswith("/RELEASE.txt") or n.endswith("/DRAFT.txt") for n in names))
                self.assertTrue(any(n.endswith("review-electrical.md") for n in names))
            (root / "hardware/outputs/rev-a/drill/env-sensor-a.drl").unlink()
            with self.assertRaisesRegex(ValueError, "missing/empty"):
                package_prototype.build_archive("a", "a" * 40, root / "out", root)
