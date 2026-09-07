# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reject corrupt connectivity before dictionaries can silently overwrite it."""
from . import geometry as G
from .design import NETS, PARTS
from .sch import LIB, Library, _symbol_for


def validate(parts=None, nets=None):
    parts = PARTS if parts is None else parts
    nets = NETS if nets is None else nets
    refs = {p.ref: p for p in parts}
    if len(refs) != len(parts):
        raise ValueError("duplicate part reference")
    symbols = Library(LIB)
    assigned = {}
    for net, connections in nets.items():
        if not net or not connections:
            raise ValueError(f"empty net: {net!r}")
        for ref, pad in connections:
            if ref not in refs:
                raise ValueError(f"{net}: unknown reference {ref}")
            if pad not in G.get(refs[ref].footprint).pads:
                raise ValueError(f"{net}: unknown footprint pad {ref}.{pad}")
            if pad not in symbols.pins(_symbol_for(ref)):
                raise ValueError(f"{net}: unknown symbol pin {ref}.{pad}")
            key = (ref, pad)
            if key in assigned:
                raise ValueError(f"{ref}.{pad} assigned twice: {assigned[key]}, {net}")
            assigned[key] = net
    for ref in refs:
        if ref.startswith(("R", "C", "L")):
            a, b = assigned.get((ref, "1")), assigned.get((ref, "2"))
            if a is None or b is None:
                raise ValueError(f"{ref}: two-terminal passive has an unassigned pin")
            if a == b:
                raise ValueError(f"{ref}: passive is bypassed on {a}")

