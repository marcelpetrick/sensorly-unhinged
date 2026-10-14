# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Topology controls for failed maze construction and cached grids."""
import unittest
from tools.boardgen.autoroute import Board, _BASE_GRIDS, _prune_dead_branches
from tools.boardgen.route import Track, Via
from tools.boardgen.variants import VARIANTS

class CleanupTests(unittest.TestCase):
    def test_dead_branch_removed_without_removing_connected_trunk(self):
        trunk = Track("TEST", .15, "F.Cu", [(0,0),(1,0),(2,0)])
        branch = Track("TEST", .15, "F.Cu", [(1,0),(1,1),(1,2)])
        anchors = [Track("TEST", .15, "F.Cu", [(0,-1),(0,1)]),
                   Track("TEST", .15, "F.Cu", [(2,-1),(2,1)])]
        tracks, vias = _prune_dead_branches([], {}, [trunk,branch], [], anchors)
        self.assertEqual([t.pts for t in tracks], [[(0,0),(1,0),(2,0)]])
        self.assertEqual(vias, [])

    def test_abandoned_single_layer_via_and_stub_removed(self):
        tracks, vias = _prune_dead_branches([], {},
            [Track("TEST", .15, "F.Cu", [(0,0),(1,0)])],
            [Via("TEST",1,0)])
        self.assertEqual((tracks,vias),([],[]))

    def test_grid_cache_is_independent_and_identical_to_fresh(self):
        _BASE_GRIDS.clear()
        first = Board(VARIANTS["a"], [])
        expected = [bytes(layer) for layer in first.blocked]
        second = Board(VARIANTS["a"], [])
        first.block(0,10,20,11,21)
        self.assertEqual([bytes(layer) for layer in second.blocked],expected)
        _BASE_GRIDS.clear()
        fresh = Board(VARIANTS["a"], [])
        self.assertEqual([bytes(layer) for layer in fresh.blocked],expected)
