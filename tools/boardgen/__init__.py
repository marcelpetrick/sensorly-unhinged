# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Parametric board generator for the ENV sensor.

One electrical model (design.py) + two geometries (variants.py) -> two KiCad
boards, two SVG previews and one set of checks.  Nothing here is variant
specific except variants.py, which is the point.
"""
__version__ = "0.1.0"
