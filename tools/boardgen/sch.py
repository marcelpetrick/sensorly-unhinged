# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Emit the shared KiCad schematic from the same model as the boards.

One schematic, both variants: A and B differ only in geometry, so a second
schematic would be a second thing to keep in sync and a second thing to get
wrong.

Style is deliberately net-label driven rather than drawn wires: every pin gets a
short stub and a global label carrying its net name. On a 41-part design that is
*more* reviewable than a rat's nest - you read a block, you read the labels, you
compare them with the electrical design spec - and it is the only style a
generator can produce reliably. Blocks follow the sheet split the vision
document asked for; they are laid out as titled regions on one A2 sheet instead
of eight sub-sheets, because eight sheets of five parts each is bookkeeping, not
clarity.
"""
from __future__ import annotations

import math
import re
import uuid as _uuid
from pathlib import Path

from .design import NETS, PART_BY_REF, PARTS

LIB = Path(__file__).resolve().parents[2] / "hardware" / "lib" / "sensorly.kicad_sym"
PROJECT = "env-sensor"
STUB = 3.81            # mm, pin stub length (3 x 1.27 grid)
GRID = 1.27

# ref -> symbol in hardware/lib/sensorly.kicad_sym
SYMBOL = {
    "U1": "ESP32-C6-MINI-1", "U2": "SHT4x", "U3": "TPS62840DLC",
    "U4": "BQ24074RGT", "U5": "USBLC6-2SC6",
    "J1": "USB_C_Receptacle_USB2.0_16P", "J2": "Conn_01x02_MountingPin",
    "L1": "L", "D1": "LED", "SW1": "SW_Push",
}

# Blocks follow the sheet split the vision document asked for. Each is a titled
# region; they are flowed into three columns so that adding a part cannot
# silently make two blocks overlap.
# (title, column, refs, columns-of-parts)
BLOCK_DEFS = [
    ("01  ESP32-C6 module", 0, ["U1", "C1", "C2", "C3", "R1", "C4"], 3),
    ("05  USB-C", 0, ["J1", "U5", "R16", "R17", "C14"], 3),
    ("08  Test / programming pads", 0, [f"TP{i}" for i in range(1, 18)], 6),
    ("02  Environmental sensor", 1, ["U2", "C6", "R3", "R4"], 4),
    ("04  Battery charger + power path", 1,
     ["U4", "R7", "R8", "R9", "R10", "R11", "R12", "R13",
      "C9", "C10", "C11", "C12"], 6),
    ("06  Battery + measurement", 1, ["J2", "R14", "R15", "C13"], 4),
    ("03  System regulator  3.30 V baseline", 2,
     ["U3", "L1", "C7", "C8", "R5", "R6"], 3),
    ("07  Button + status LED", 2, ["SW1", "C5", "D1", "R2"], 4),
]

LABEL_ALLOW = 21.59    # 17 x 1.27, room for a stub plus the longest net name
PART_GAP = 6.35        # 5 x 1.27
TITLE_GAP = 30.48      # 24 x 1.27, title baseline to the first row's centre
BLOCK_GAP = 20.32
BAND_W = 228.6         # usable width of one column band
COLUMN_X = (25.4, 279.4, 533.4)
COLUMN_Y0 = 33.02


def _extent(lib, name):
    """Half-width and half-height a placed symbol needs, stubs and labels in."""
    pins = lib.pins(name)
    if not pins:
        return 6.35, 6.35
    xs = [p[0] for p in pins.values()]
    ys = [p[1] for p in pins.values()]
    return (max(abs(min(xs)), abs(max(xs))) + STUB + LABEL_ALLOW,
            max(abs(min(ys)), abs(max(ys))) + STUB + 7.62)


def layout(lib):
    """(blocks, placements, flag_origin).

    Parts are packed into rows sized by the tallest symbol in the row, so a
    tall part such as the module cannot overlap the row beneath it - which is
    exactly the bug a fixed row pitch produced.
    """
    y = {c: COLUMN_Y0 for c in range(len(COLUMN_X))}
    blocks, placements = [], {}
    for title, col, refs, _cols in BLOCK_DEFS:
        bx, by = COLUMN_X[col], y[col]
        blocks.append((title, bx, by))
        cy = by + TITLE_GAP
        row, cx, row_h = [], bx, 0.0
        def flush(cy, row, row_h):
            for ref, px, hw in row:
                placements[ref] = (_snap(px + hw), _snap(cy + row_h))
            return cy + 2 * row_h + PART_GAP
        for ref in refs:
            hw, hh = _extent(lib, _symbol_for(ref))
            if row and cx + 2 * hw > bx + BAND_W:
                cy = flush(cy, row, row_h)
                row, cx, row_h = [], bx, 0.0
            row.append((ref, cx, hw))
            cx += 2 * hw + PART_GAP
            row_h = max(row_h, hh)
        if row:
            cy = flush(cy, row, row_h)
        y[col] = _snap(cy + BLOCK_GAP)
    # Put the flags in whichever column has room left, so the sheet does not
    # grow a ninth block hanging off the bottom edge.
    fcol = min(y, key=lambda c: y[c])
    flag_y = _snap(y[fcol])
    blocks.append(("09  Power-flag drivers (ERC only, no physical parts)",
                   COLUMN_X[fcol], flag_y))
    return blocks, placements, (COLUMN_X[fcol], _snap(flag_y + TITLE_GAP))


def _u(seed: str) -> str:
    return str(_uuid.uuid5(_uuid.NAMESPACE_URL, "sensorly-sch:" + seed))


def _blocks(text: str, head: str):
    i = 0
    tok = "(" + head
    while True:
        i = text.find(tok, i)
        if i < 0:
            return
        j, depth = i, 0
        while j < len(text):
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        yield text[i:j + 1]
        i = j + 1


class Library:
    def __init__(self, path: Path):
        self.text = path.read_text()
        self.symbols: dict[str, str] = {}
        for b in _blocks(self.text, 'symbol "'):
            name = re.match(r'\(symbol "([^"]+)"', b).group(1)
            if "_" in name and name.rsplit("_", 2)[0] in self.symbols:
                continue                      # a sub-unit of one we already have
            self.symbols.setdefault(name, b)

    def pins(self, name: str) -> dict[str, tuple[float, float, float]]:
        out: dict[str, tuple[float, float, float]] = {}
        for p in _blocks(self.symbols[name], "pin "):
            at = re.search(r"\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)", p)
            num = re.search(r'\(number "([^"]*)"', p)
            if at and num:
                out[num.group(1)] = (float(at.group(1)), float(at.group(2)),
                                     float(at.group(3) or 0))
        return out


def unconnected_nets() -> dict[tuple[str, str], str]:
    """KiCad names every no-connect pad `unconnected-(REF-PINNAME-PadNUM)`.

    The board has to use the same names or `--schematic-parity` reports every
    one of them as a missing net. Generating both sides from one function is the
    only way to keep them identical.
    """
    lib = Library(LIB)
    padnet = _pad_net_map()
    out: dict[tuple[str, str], str] = {}
    for p in PARTS:
        name = _symbol_for(p.ref)
        body = lib.symbols[name]
        for blk in _blocks(body, "pin "):
            num = re.search(r'\(number "([^"]*)"', blk)
            pname = re.search(r'\(name "([^"]*)"', blk)
            if not num:
                continue
            key = (p.ref, num.group(1))
            if key in padnet:
                continue
            out[key] = (f"unconnected-({p.ref}-"
                        f"{(pname.group(1) if pname else 'x').replace('~', '')}"
                        f"-Pad{num.group(1)})")
    return out


def _pad_net_map():
    out = {}
    for net, conns in NETS.items():
        for ref, pad in conns:
            out[(ref, pad)] = net
    return out


def _snap(v: float) -> float:
    return round(round(v / GRID) * GRID, 4)


def emit() -> str:
    lib = Library(LIB)
    padnet = _pad_net_map()
    sheet_uuid = _u("sheet/root")

    blocks, placements, flag_origin = layout(lib)

    out = ["(kicad_sch", "\t(version 20260101)",
           '\t(generator "sensorly-boardgen")', '\t(generator_version "10.0")',
           f'\t(uuid "{sheet_uuid}")', '\t(paper "A1")',
           '\t(title_block',
           '\t\t(title "ENV Sensor - shared schematic (Variant A and B)")',
           '\t\t(rev "Rev 1")', '\t\t(company "sensorly-unhinged")',
           '\t\t(comment 1 "SPDX-FileCopyrightText: 2026 Marcel Petrick '
           '<mail@marcelpetrick.it>")',
           '\t\t(comment 2 "SPDX-License-Identifier: GPL-3.0-or-later")',
           '\t\t(comment 3 "Generated by tools/boardgen - edit the model, not this file")',
           '\t\t(comment 4 "Values and pin assignment: docs/30-electrical-design-spec.md")',
           "\t)"]

    used = sorted({_symbol_for(p.ref) for p in PARTS}
                  | {"GND", "+3V0", "VBUS", "PWR_FLAG"})
    out.append("\t(lib_symbols")
    for name in used:
        body = lib.symbols[name]
        body = body.replace(f'(symbol "{name}"', f'(symbol "sensorly:{name}"', 1)
        out.append("\t\t" + body.replace("\n", "\n\t\t"))
    out.append("\t)")

    wires: list[str] = []
    nocs: list[str] = []
    labels: list[str] = []
    symbols: list[str] = []
    texts: list[str] = []

    for title, bx, by in blocks:
        texts.append(_text(title, bx, by, 3.0, _u("blk/" + title)))

    for p in PARTS:
        ref = p.ref
        name = _symbol_for(ref)
        x, y = placements[ref]
        symbols.append(_symbol(name, ref, p.value, p.footprint, x, y, lib,
                               sheet_uuid, in_bom=not p.exclude_from_bom))
        for num, (px, py, ang) in sorted(lib.pins(name).items()):
            ax, ay = _snap(x + px), _snap(y - py)
            net = padnet.get((ref, num))
            if net is None:
                # Deliberately unconnected. IO8 and IO15 are latched strapping
                # pins (EDS S2.1) and the rest are spares; a no-connect flag
                # says "we meant this" instead of leaving ERC to guess.
                nocs.append(_noconnect(ax, ay, _u(f"nc/{ref}/{num}")))
                continue
            # A KiCad pin's (at x y angle) is its *connection* point, and the
            # angle is the direction the pin body runs - towards the symbol.
            # The stub must therefore go the other way, or every stub crosses
            # the symbol and shorts the whole block together.
            dx = -math.cos(math.radians(ang))
            dy = math.sin(math.radians(ang))
            ex, ey = _snap(ax + STUB * dx), _snap(ay + STUB * dy)
            wires.append(_wire(ax, ay, ex, ey, _u(f"w/{ref}/{num}")))
            labels.append(_label(net, ex, ey, (ang + 180) % 360,
                                 _u(f"l/{ref}/{num}")))

    # Power flags: ERC needs one driver per power net, and this design gets its
    # power from connectors and a module, not from a symbol marked "power out".
    # Only nets with no power-output pin of their own need a flag. VSYS and
    # VBAT are driven by the charger's OUT and BAT pins; flagging them as well
    # would be two power outputs on one net, which is an ERC error and, on a
    # real board, a fight.
    for i, net in enumerate(["GND", "+3V0", "VBUS"]):
        fx, fy = _snap(flag_origin[0] + i * 25.4), flag_origin[1]
        symbols.append(_symbol("PWR_FLAG", f"#FLG{i + 1}", "PWR_FLAG", "", fx, fy,
                               lib, sheet_uuid, hide_ref=True))
        wires.append(_wire(fx, fy, fx, _snap(fy + 6.35), _u(f"pf/w/{i}")))
        labels.append(_label(net, fx, _snap(fy + 6.35), 270, _u(f"pf/l/{i}")))

    out += texts + symbols + wires + labels + nocs
    out.append('\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)')
    out.append("\t(embedded_fonts no)")
    out.append(")")
    return "\n".join(out) + "\n"


def _symbol_for(ref: str) -> str:
    if ref in SYMBOL:
        return SYMBOL[ref]
    if ref.startswith("TP"):
        return "TestPoint"
    return {"R": "R", "C": "C", "L": "L", "D": "LED"}[ref[0]]


def _wire(x1, y1, x2, y2, uid) -> str:
    return (f"\t(wire\n\t\t(pts\n\t\t\t(xy {x1} {y1}) (xy {x2} {y2})\n\t\t)\n"
            f"\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n"
            f'\t\t(uuid "{uid}")\n\t)')


def _label(net, x, y, ang, uid) -> str:
    just = "right" if 90 < ang < 270 else "left"
    return (f'\t(global_label "{net}"\n\t\t(shape bidirectional)\n'
            f"\t\t(at {x} {y} {ang})\n\t\t(fields_autoplaced yes)\n"
            f"\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n"
            f"\t\t\t(justify {just})\n\t\t)\n"
            f'\t\t(uuid "{uid}")\n\t)')


def _noconnect(x, y, uid) -> str:
    return f'\t(no_connect\n\t\t(at {x} {y})\n\t\t(uuid "{uid}")\n\t)'


def _text(s, x, y, size, uid) -> str:
    return (f'\t(text "{s}"\n\t\t(exclude_from_sim yes)\n'
            f"\t\t(at {x} {y} 0)\n\t\t(effects\n\t\t\t(font\n"
            f"\t\t\t\t(size {size} {size})\n\t\t\t\t(bold yes)\n\t\t\t)\n"
            f"\t\t\t(justify left bottom)\n\t\t)\n"
            f'\t\t(uuid "{uid}")\n\t)')


def _symbol(name, ref, value, footprint, x, y, lib, sheet_uuid,
            hide_ref=False, in_bom=True) -> str:
    hide = "\n\t\t\t(hide yes)" if hide_ref else ""
    pins = "".join(
        f'\t\t(pin "{n}"\n\t\t\t(uuid "{_u(f"p/{ref}/{n}")}")\n\t\t)\n'
        for n in sorted(lib.pins(name)))
    return (f'\t(symbol\n\t\t(lib_id "sensorly:{name}")\n'
            f"\t\t(at {x} {y} 0)\n\t\t(unit 1)\n\t\t(body_style 1)\n"
            f"\t\t(exclude_from_sim no)\n\t\t(in_bom {'yes' if in_bom else 'no'})\n"
            f"\t\t(on_board yes)\n"
            f"\t\t(dnp no)\n"
            f'\t\t(uuid "{_u("sym/" + ref)}")\n'
            f'\t\t(property "Reference" "{ref}"\n\t\t\t(at {x} {_snap(y - 12.7)} 0){hide}\n'
            f"\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n"
            f'\t\t(property "Value" "{value}"\n\t\t\t(at {x} {_snap(y + 12.7)} 0)\n'
            f"\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n"
            f'\t\t(property "Footprint" "{footprint}"\n\t\t\t(at {x} {y} 0)\n\t\t\t(hide yes)\n'
            f"\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n"
            + pins +
            f'\t\t(instances\n\t\t\t(project "{PROJECT}"\n'
            f'\t\t\t\t(path "/{sheet_uuid}"\n\t\t\t\t\t(reference "{ref}")\n'
            f"\t\t\t\t\t(unit 1)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n\t)")


PROJECT_FILE = """{
  "meta": { "filename": "env-sensor.kicad_pro", "version": 3 },
  "schematic": {
    "annotate_start_num": 0,
    "legacy_lib_dir": "",
    "legacy_lib_list": []
  },
  "sheets": [],
  "text_variables": {}
}
"""

SYM_LIB_TABLE = """(sym_lib_table
  (version 7)
  (lib (name "sensorly")(type "KiCad")(uri "${KIPRJMOD}/../lib/sensorly.kicad_sym")(options "")(descr "ENV sensor project symbols - vendored, see hardware/lib/README.md"))
)
"""


def write(root: Path):
    d = root / "hardware" / "schematic"
    d.mkdir(parents=True, exist_ok=True)
    (d / "env-sensor.kicad_sch").write_text(emit())
    (d / "sym-lib-table").write_text(SYM_LIB_TABLE)
    (d / "env-sensor.kicad_pro").write_text(PROJECT_FILE)
    (d / "fp-lib-table").write_text(
        '(fp_lib_table\n  (version 7)\n  (lib (name "sensorly")(type "KiCad")'
        '(uri "${KIPRJMOD}/../lib/sensorly.pretty")(options "")(descr ""))\n)\n')
