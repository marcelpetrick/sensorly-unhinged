# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.check_generated import check


class GeneratedCheckTests(unittest.TestCase):
    def fixture(self, root):
        def git(*args):
            subprocess.run(['git', *args], cwd=root, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        git('init', '-q')
        git('config', 'user.email', 'synthetic@example.invalid')
        git('config', 'user.name', 'Synthetic fixture')
        (root / 'model').write_text('original\n')
        (root / 'board').write_text('original\n')
        (root / 'Makefile').write_text('.PHONY: gen thermal bom cost mech\n'
            'gen:\n\tcp model board\nthermal bom cost mech:\n\t@true\n')
        git('add', '.')
        git('commit', '-qm', 'synthetic fixture')
        return git

    def test_matching_generated_inputs_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root)
            check(root, ('board',))

    def test_clean_commit_with_stale_board_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            git = self.fixture(root)
            (root / 'model').write_text('changed model\n')
            git('add', 'model')
            git('commit', '-qm', 'change model without regeneration')
            with self.assertRaisesRegex(ValueError, 'differ from committed'):
                check(root, ('board',))

    def test_existing_edits_are_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root)
            (root / 'board').write_text('manual edits\n')
            with self.assertRaisesRegex(ValueError, 'uncommitted'):
                check(root, ('board',))
            self.assertEqual((root / 'board').read_text(), 'manual edits\n')

    def test_untracked_generated_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.fixture(root)
            (root / 'new-board').write_text('unreviewed\n')
            with self.assertRaisesRegex(ValueError, 'uncommitted'):
                check(root, ('board', 'new-board'))
