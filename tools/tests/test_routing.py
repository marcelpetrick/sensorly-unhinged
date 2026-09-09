# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import unittest
from tools.boardgen.route import Track, Via, center_track_ends, validate_neck_crossings
from tools.boardgen.variants import VARIANTS


class RoutingTests(unittest.TestCase):
    def test_exactly_four_neck_conductors(self):
        tracks = [Track(net, .15, "F.Cu", [(13 + i*.5, 33), (13 + i*.5, 43)])
                  for i, net in enumerate(("SDA", "SCL", "GND", "+3V0"))]
        validate_neck_crossings(VARIANTS["b"], tracks)
        tracks.append(Track("GND", .15, "F.Cu", [(15.2, 33), (15.2, 43)]))
        with self.assertRaisesRegex(ValueError, "four thin"):
            validate_neck_crossings(VARIANTS["b"], tracks)

    def test_collinear_overshoot_is_trimmed(self):
        track = Track("CHG_N", .2, "B.Cu", [(11.5, 23.3), (11.5, 24.6)])
        result = center_track_ends([track], [Via("CHG_N", 11.5, 24.5)])
        self.assertEqual(result[0].pts, [(11.5, 23.3), (11.5, 24.5)])
        self.assertEqual(track.pts[-1], (11.5, 24.6))

    def test_other_net_is_unchanged(self):
        track = Track("X", .2, "F.Cu", [(0, 0), (1, 0)])
        self.assertEqual(
            center_track_ends([track], [Via("Y", .9, 0)])[0].pts, track.pts)

    def test_noncollinear_endpoint_is_centered(self):
        track = Track("X", .2, "F.Cu", [(0, 0), (1, 0)])
        result = center_track_ends([track], [Via("X", 1, .1)])
        self.assertEqual(result[0].pts, [(0, 0), (1, .1)])

    def test_interior_corner_connects_at_via_centre(self):
        track = Track("X", .2, "F.Cu", [(0, 0), (1, 0), (1, 1), (2, 1)])
        result = center_track_ends([track], [Via("X", 1, .9)])
        self.assertEqual(
            result[0].pts, [(0, 0), (1, 0), (1, .9), (1, 1), (2, 1)])
