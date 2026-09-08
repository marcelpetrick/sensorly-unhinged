# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from tools.boardgen.route import Track, Via, center_track_ends


class RoutingTests(unittest.TestCase):
    def test_collinear_overshoot_is_trimmed(self):
        track = Track("CHG_N", .2, "B.Cu", [(11.5, 23.3), (11.5, 24.6)])
        result = center_track_ends([track], [Via("CHG_N", 11.5, 24.5)])
        self.assertEqual(result[0].pts, [(11.5, 23.3), (11.5, 24.5)])
        self.assertEqual(track.pts[-1], (11.5, 24.6))

    def test_other_net_and_noncollinear_paths_are_unchanged(self):
        track = Track("X", .2, "F.Cu", [(0, 0), (1, 0)])
        for via in (Via("Y", .9, 0), Via("X", 1, .1)):
            self.assertEqual(center_track_ends([track], [via])[0].pts, track.pts)
