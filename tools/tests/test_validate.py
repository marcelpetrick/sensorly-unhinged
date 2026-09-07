# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import unittest

from tools.boardgen.design import NETS, PARTS
from tools.boardgen.validate import validate


class ConnectivityTests(unittest.TestCase):
    def test_live_model(self):
        validate()

    def test_duplicate_reference(self):
        with self.assertRaisesRegex(ValueError, "duplicate part"):
            validate(parts=PARTS + [PARTS[0]])

    def test_duplicate_net_assignment(self):
        nets = copy.deepcopy(NETS)
        nets["GND"].append(("U1", "3"))
        with self.assertRaisesRegex(ValueError, "assigned twice"):
            validate(nets=nets)

    def test_missing_pad(self):
        nets = copy.deepcopy(NETS)
        nets["GND"].append(("U1", "999"))
        with self.assertRaisesRegex(ValueError, "unknown footprint pad"):
            validate(nets=nets)

    def test_bypassed_enable_resistor(self):
        nets = copy.deepcopy(NETS)
        nets["VSYS"] += nets.pop("EN_REG")
        with self.assertRaisesRegex(ValueError, "bypassed"):
            validate(nets=nets)
