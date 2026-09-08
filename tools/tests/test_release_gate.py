# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import tempfile
import unittest
import json
from pathlib import Path
from tools.release_gate import REQUIRED, blockers


class ReleaseTests(unittest.TestCase):
    def test_missing_reports_and_manifest_cannot_release(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertGreaterEqual(len(blockers(Path(d))), 3)

    def test_missing_qualification_cannot_release(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "hardware").mkdir()
            manifest = {"schema": 1, "checks": [
                {"id": key, "owner": "test", "evidence": None} for key in REQUIRED]}
            (root / "hardware/release-readiness.json").write_text(json.dumps(manifest))
            self.assertEqual(sum("qualification evidence" in p for p in blockers(root)),
                             len(REQUIRED))
