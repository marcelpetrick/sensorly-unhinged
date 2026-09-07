# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import struct
import tempfile
import unittest
from pathlib import Path
from tools.check_stl import bbox


class MeshTests(unittest.TestCase):
    def read(self, data):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "mesh.stl"
            p.write_bytes(data)
            return bbox(p)

    def test_ascii_and_binary_have_same_dimensions(self):
        ascii_mesh = b"solid test\nvertex 0 0 0\nvertex 2 0 0\nvertex 0 3 4\nendsolid"
        binary = b"solid binary".ljust(80, b"\0") + struct.pack("<I12fH", 1,
                      0, 0, 1, 0, 0, 0, 2, 0, 0, 0, 3, 4, 0)
        self.assertEqual(self.read(ascii_mesh), (2, 3, 4))
        self.assertEqual(self.read(binary), (2, 3, 4))

    def test_nonfinite_vertices_fail(self):
        self.assertIsNone(self.read(b"vertex nan 0 0\nvertex 1 1 1"))

    def test_empty_mesh_fails(self):
        self.assertIsNone(self.read(b"solid empty\nendsolid"))
