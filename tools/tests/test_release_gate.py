# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import tempfile
import unittest
from pathlib import Path
from tools.release_gate import blockers


class ReleaseTests(unittest.TestCase):
    def test_missing_reports_and_manifest_cannot_release(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertGreaterEqual(len(blockers(Path(d))), 3)

    def test_current_unqualified_hardware_cannot_release(self):
        self.assertTrue(any("qualification evidence" in p for p in blockers()))
