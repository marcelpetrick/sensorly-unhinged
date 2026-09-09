# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Emit a KiCad 10 .kicad_pcb from the model.

Everything the board needs is written here - stackup, nets, footprints (embedded
from hardware/lib so the file is self-contained), outline, zones, thermal and RF
keep-outs, silkscreen and the routed island nets.
"""
from __future__ import annotations

import re
import uuid as _uuid
from pathlib import Path

from . import geometry as G
from .design import (BOARD_THICKNESS, NETS, PART_BY_REF, STACKUP)
from .place import Placement
from .route import Track, Via
from .sch import unconnected_nets
from .variants import (B_ISLAND_RECT, B_NECK_RECT, Variant, antenna_keepout,
                       sensor_keepout)

ORIGIN = (100.0, 60.0)          # where the board sits on the A4 sheet

LAYER_IDS = [
    (0, "F.Cu", "signal", None), (4, "In1.Cu", "signal", None),
    (6, "In2.Cu", "signal", None), (2, "B.Cu", "signal", None),
    (9, "F.Adhes", "user", "F.Adhesive"), (11, "B.Adhes", "user", "B.Adhesive"),
    (13, "F.Paste", "user", None), (15, "B.Paste", "user", None),
    (5, "F.SilkS", "user", "F.Silkscreen"), (7, "B.SilkS", "user", "B.Silkscreen"),
    (1, "F.Mask", "user", None), (3, "B.Mask", "user", None),
    (17, "Dwgs.User", "user", "User.Drawings"),
    (19, "Cmts.User", "user", "User.Comments"),
    (21, "Eco1.User", "user", "User.Eco1"), (23, "Eco2.User", "user", "User.Eco2"),
    (25, "Edge.Cuts", "user", None), (27, "Margin", "user", None),
    (31, "F.CrtYd", "user", "F.Courtyard"), (29, "B.CrtYd", "user", "B.Courtyard"),
    (35, "F.Fab", "user", None), (33, "B.Fab", "user", None),
]


def _u(seed: str) -> str:
    return str(_uuid.uuid5(_uuid.NAMESPACE_URL, "sensorly:" + seed))


def _xy(x, y):
    return (round(x + ORIGIN[0], 4), round(y + ORIGIN[1], 4))


# --------------------------------------------------------------------------
def _net_index():
    idx = {"": 0}
    names = sorted(set(NETS) | set(unconnected_nets().values()))
    for i, name in enumerate(names, start=1):
        idx[name] = i
    return idx


def _pad_net_map():
    """(ref, pad) -> net name, including the generated unconnected-() names."""
    out = {}
    for net, conns in NETS.items():
        for ref, pad in conns:
            out[(ref, pad)] = net
    out.update(unconnected_nets())
    return out


def _emit_footprint(p: Placement, netidx, padnet) -> str:
    fp = G.get(p.footprint)
    text = fp.text
    part = PART_BY_REF[p.ref]

    text = re.sub(r'^\(footprint "[^"]+"', f'(footprint "{p.footprint}"', text, count=1)
    text = re.sub(r"\n\t\(version \d+\)", "", text, count=1)
    text = re.sub(r'\n\t\(generator "[^"]*"\)', "", text, count=1)
    text = re.sub(r'\n\t\(generator_version "[^"]*"\)', "", text, count=1)

    x, y = _xy(p.x, p.y)
    rot = p.rot % 360
    at = f"\n\t(at {x} {y}{'' if rot == 0 else ' ' + str(rot)})"
    text = re.sub(r'(\n\t\(layer "[BF]\.Cu"\))',
                  rf'\1\n\t(uuid "{_u("fp/" + p.ref)}"){at}', text, count=1)

    text = re.sub(r'\(property "Reference" "[^"]*"',
                  f'(property "Reference" "{p.ref}"', text, count=1)
    text = re.sub(r'\(property "Value" "[^"]*"',
                  f'(property "Value" "{part.value}"', text, count=1)

    # Every footprint instance needs its own UUIDs: the library file's UUIDs are
    # identical across all 20-odd 0402 instances, which KiCad would reject.
    seen: dict[str, str] = {}

    def _reuuid(m):
        old = m.group(1)
        if old not in seen:
            seen[old] = _u(f"{p.ref}/{old}")
        return f'(uuid "{seen[old]}")'

    head, sep, tail = text.partition("(descr")
    tail = re.sub(r'\(uuid "([0-9a-fA-F-]+)"\)', _reuuid, tail)
    text = head + sep + tail

    # Reference designators come off the silkscreen. On a 30 x 34 mm board
    # carrying forty 0402s there is no legible way to silk-print all of them -
    # they collide with each other and with pads, which is exactly what KiCad's
    # silk DRC says. Nothing is lost: every KiCad library footprint already
    # carries an fp_text "${REFERENCE}" on F.Fab, so the assembly drawing keeps
    # every reference. The silkscreen then carries only what a human needs while
    # holding the board: name, revision, battery polarity, USB and pogo labels.
    for block in G._blocks(text, 'property "Reference"'):
        if "(hide yes)" in block:
            break
        i = block.index(")", block.index("(at "))
        text = text.replace(block, block[:i + 1] + "\n\t\t(hide yes)"
                            + block[i + 1:], 1)
        break

    # pads: absolute rotation, and the net they belong to
    pieces, cursor = [], 0
    for block in G._blocks(text, "pad "):
        i = text.index(block, cursor)
        pieces.append(text[cursor:i])
        cursor = i + len(block)
        name = re.search(r'\(pad "([^"]*)"', block).group(1)
        if rot:
            m = re.search(r"\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)", block)
            pang = float(m.group(3) or 0.0)
            block = block.replace(
                m.group(0), f"(at {m.group(1)} {m.group(2)} {(pang + rot) % 360})", 1)
        net = padnet.get((p.ref, name))
        if net:
            block = block.rstrip()[:-1].rstrip() + \
                f'\n\t\t(net {netidx[net]} "{net}")\n\t)'
        pieces.append(block)
    pieces.append(text[cursor:])
    text = "".join(pieces)

    attrs = []
    if part.exclude_from_bom:
        attrs.extend(["exclude_from_bom", "exclude_from_pos_files"])
    if part.dnp:
        attrs.append("dnp")
    if attrs and "(attr " in text:
        text = re.sub(
            r"\(attr ([^)]*)\)",
            lambda m: f"(attr {m.group(1)} "
                      f"{' '.join(a for a in attrs if a not in m.group(1))})",
            text, count=1)

    return "\t" + text.replace("\n", "\n\t").rstrip() + "\n"


# --------------------------------------------------------------------------
def _outline(v: Variant) -> str:
    pts = v.outline
    out = []
    for i, a in enumerate(pts):
        b = pts[(i + 1) % len(pts)]
        ax, ay = _xy(*a)
        bx, by = _xy(*b)
        out.append(
            f"\t(gr_line\n\t\t(start {ax} {ay})\n\t\t(end {bx} {by})\n"
            f"\t\t(stroke\n\t\t\t(width 0.1)\n\t\t\t(type default)\n\t\t)\n"
            f'\t\t(layer "Edge.Cuts")\n\t\t(uuid "{_u(f"edge/{v.key}/{i}")}")\n\t)\n')
    return "".join(out)


def _zone(name, netname, netidx, layers, poly, seed, keepout=None,
          priority=0, solid_pads=False) -> str:
    pts = " ".join(f"({'xy'} {a} {b})" for a, b in (_xy(x, y) for x, y in poly))
    lay = " ".join(f'"{l}"' for l in layers)
    head = (f"\t(zone\n\t\t(net {netidx.get(netname, 0)})\n"
            f'\t\t(net_name "{netname}")\n'
            f"\t\t(layers {lay})\n"
            f'\t\t(uuid "{_u(seed)}")\n'
            f'\t\t(name "{name}")\n'
            f"\t\t(hatch edge 0.5)\n")
    if priority:
        head += f"\t\t(priority {priority})\n"
    # A ground plane that reaches the module's 20 ground pads through two
    # thermal spokes each is not a ground plane. Solid connection for GND.
    conn = "(connect_pads yes\n\t\t\t(clearance 0)\n\t\t)" if solid_pads \
        else "(connect_pads\n\t\t\t(clearance 0.2)\n\t\t)"
    head += (f"\t\t{conn}\n"
             "\t\t(min_thickness 0.2)\n\t\t(filled_areas_thickness no)\n")
    if keepout:
        head += ("\t\t(keepout\n"
                 f"\t\t\t(tracks {keepout['tracks']})\n"
                 f"\t\t\t(vias {keepout['vias']})\n"
                 f"\t\t\t(pads {keepout['pads']})\n"
                 f"\t\t\t(copperpour {keepout['copperpour']})\n"
                 f"\t\t\t(footprints {keepout['footprints']})\n\t\t)\n")
        head += "\t\t(placement\n\t\t\t(enabled no)\n\t\t\t(sheetname \"\")\n\t\t)\n"
        head += ("\t\t(fill\n\t\t\t(thermal_gap 0.3)\n"
                 "\t\t\t(thermal_bridge_width 0.4)\n\t\t)\n")
    else:
        head += ("\t\t(fill yes\n\t\t\t(thermal_gap 0.3)\n"
                 "\t\t\t(thermal_bridge_width 0.4)\n"
                 "\t\t\t(island_removal_mode 1)\n\t\t\t(island_area_min 5)\n\t\t)\n")
    head += f"\t\t(polygon\n\t\t\t(pts\n\t\t\t\t{pts}\n\t\t\t)\n\t\t)\n\t)\n"
    return head


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _free_label(v: Variant, placed, w: float, h: float, prefer):
    """A spot for a silkscreen label that no courtyard already occupies.

    Silk over a pad is only cosmetic, but chasing it by hand after every
    placement change is not. Ask the placement where there is room instead."""
    # Search outward from where the label belongs, not across the whole board -
    # a "USB-C" label that wanders onto the sensor island is worse than one that
    # overlaps a courtyard.
    boxes = [p.box for p in placed]
    cands = [prefer]
    for r in range(1, 24):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                cands.append((prefer[0] + dx * 0.5, prefer[1] + dy * 0.5))
    for (x, y) in cands:
        box = (x, x + w, y - h, y)
        # Variant B's outline is not a rectangle, so a bounding-box test is not
        # enough - the label has to be inside the actual board.
        if not G.box_inside_polys(box, v.polys, margin=0.5):
            continue
        if not any(G.boxes_overlap(box, b, 0.2) for b in boxes):
            return x, y
    return prefer


KO_HARD = dict(tracks="not_allowed", vias="not_allowed", pads="not_allowed",
               copperpour="not_allowed", footprints="not_allowed")
KO_NO_POUR = dict(tracks="allowed", vias="not_allowed", pads="allowed",
                  copperpour="not_allowed", footprints="allowed")
# The module itself must be allowed to sit in its own antenna keep-out.
KO_RF = dict(tracks="not_allowed", vias="not_allowed", pads="not_allowed",
             copperpour="not_allowed", footprints="allowed")


def _zones(v: Variant, netidx) -> str:
    out = []
    # GND on the outer layers and the L2 reference plane
    out.append(_zone("GND pour", "GND", netidx,
                     ["F.Cu", "In1.Cu", "B.Cu"], v.outline, f"zone/gnd/{v.key}",
                     solid_pads=True))
    # L3 carries the system rail
    out.append(_zone("+3V0 plane", "+3V0", netidx,
                     ["In2.Cu"], v.outline, f"zone/3v0/{v.key}"))

    ax0, ax1, ay0, ay1 = antenna_keepout(v)
    out.append(_zone("RF keep-out (module antenna)", "", netidx,
                     ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"],
                     _rect(ax0, ay0, ax1, ay1), f"zone/rf/{v.key}",
                     keepout=KO_RF))

    if v.key == "b":
        nx0, ny0, nx1, ny1 = B_NECK_RECT
        ix0, iy0, ix1, iy1 = B_ISLAND_RECT
        island = _rect(min(nx0, ix0) - 0.0, ny0, max(nx1, ix1), iy1)
        # EDS S3.1.3: no copper AT ALL on the inner layers across the neck.
        out.append(_zone("Thermal isolation - no inner copper", "", netidx,
                         ["In1.Cu", "In2.Cu"],
                         _rect(nx0 - 0.2, ny0, nx1 + 0.2, iy1),
                         f"zone/neck-inner/{v.key}", keepout=KO_HARD))
        # EDS S3.1.2: outer layers carry the four traces and nothing else.
        out.append(_zone("Sensor island - traces only, no pour", "", netidx,
                         ["F.Cu", "B.Cu"], island,
                         f"zone/island/{v.key}", keepout=KO_NO_POUR))
        out.append(_zone("Sensor island - no inner copper", "", netidx,
                         ["In1.Cu", "In2.Cu"], _rect(ix0, iy0, ix1, iy1),
                         f"zone/island-inner/{v.key}", keepout=KO_HARD))
    else:
        sx0, sx1, sy0, sy1 = sensor_keepout(v)
        out.append(_zone("Sensor quiet zone - reduced copper", "", netidx,
                         ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"],
                         _rect(sx0, sy0, sx1, sy1),
                         f"zone/quiet/{v.key}", keepout=KO_NO_POUR))
    return "".join(out)


def _silk(v: Variant, placed=()) -> str:
    lines = []

    def txt(s, x, y, size=0.8, layer="F.SilkS", mirror=False, seed=""):
        size = size
        just = ' mirror' if mirror else ''
        anchor = 'right' if mirror else 'left'
        lines.append(
            f'\t(gr_text "{s}"\n\t\t(at {_xy(x, y)[0]} {_xy(x, y)[1]})\n'
            f'\t\t(layer "{layer}")\n\t\t(uuid "{_u("silk/" + v.key + "/" + (seed or s))}")\n'
            f"\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})\n"
            f"\t\t\t\t(thickness {round(size / 6, 3)})\n\t\t\t)\n"
            f"\t\t\t(justify {anchor} bottom{just})\n\t\t)\n\t)\n")

    # The antenna keep-out strip has no components in it by construction, so
    # it is the one place on this board with room for a title block. Silk is not
    # copper, so putting text there does not violate the keep-out.
    txt("ENV", 0.6, 1.7, 0.7, seed="name1")
    txt("SENSOR", 0.6, 2.9, 0.7, seed="name2")
    txt(v.revision, 0.6, 4.1, 0.7, seed="rev")
    txt("2026", 0.6, 5.3, 0.6, seed="year")
    txt("- T +", 22.0, 27.7, 0.7, layer="B.SilkS", mirror=True,
        seed="batpinout")  # J2 pins 1/2/3
    txt("USB-C 5V", *_free_label(v, placed, 5.0, 0.6, prefer=(1.2, 31.8)),
        size=0.6, seed="usb")
    txt(f"VARIANT {v.key.upper()}", 1.2, 32.6, 0.6, layer="B.SilkS",
        mirror=True, seed="variant")
    txt("POGO", 9.0, 18.2, 0.6, layer="B.SilkS", mirror=True, seed="pogo")
    return "".join(lines)


def _tracks(tracks: list[Track], vias: list[Via], netidx) -> str:
    out = []
    for t in tracks:
        for i in range(len(t.pts) - 1):
            ax, ay = _xy(*t.pts[i])
            bx, by = _xy(*t.pts[i + 1])
            out.append(
                f"\t(segment\n\t\t(start {ax} {ay})\n\t\t(end {bx} {by})\n"
                f'\t\t(width {t.width})\n\t\t(layer "{t.layer}")\n'
                f"\t\t(net {netidx[t.net]})\n"
                f'\t\t(uuid "{_u(f"seg/{t.net}/{i}/{ax}/{ay}")}")\n\t)\n')
    for vv in vias:
        x, y = _xy(vv.x, vv.y)
        out.append(
            f"\t(via\n\t\t(at {x} {y})\n\t\t(size {vv.size})\n"
            f"\t\t(drill {vv.drill})\n\t\t(layers \"F.Cu\" \"B.Cu\")\n"
            f"\t\t(net {netidx[vv.net]})\n"
            f'\t\t(uuid "{_u(f"via/{vv.net}/{x}/{y}")}")\n\t)\n')
    return "".join(out)


def _stackup() -> str:
    out = ['\t\t(stackup\n',
           '\t\t\t(layer "F.SilkS"\n\t\t\t\t(type "Top Silk Screen")\n\t\t\t)\n',
           '\t\t\t(layer "F.Paste"\n\t\t\t\t(type "Top Solder Paste")\n\t\t\t)\n',
           '\t\t\t(layer "F.Mask"\n\t\t\t\t(type "Top Solder Mask")\n'
           '\t\t\t\t(thickness 0.01)\n\t\t\t)\n']
    for name, kind, thick, _desc in STACKUP:
        if kind == "copper":
            out.append(f'\t\t\t(layer "{name}"\n\t\t\t\t(type "copper")\n'
                       f"\t\t\t\t(thickness {thick})\n\t\t\t)\n")
        else:
            out.append(f'\t\t\t(layer "{name}"\n\t\t\t\t(type "{kind}")\n'
                       f'\t\t\t\t(thickness {thick})\n\t\t\t\t(material "FR4")\n'
                       "\t\t\t\t(epsilon_r 4.5)\n\t\t\t\t(loss_tangent 0.02)\n\t\t\t)\n")
    out += ['\t\t\t(layer "B.Mask"\n\t\t\t\t(type "Bottom Solder Mask")\n'
            '\t\t\t\t(thickness 0.01)\n\t\t\t)\n',
            '\t\t\t(layer "B.Paste"\n\t\t\t\t(type "Bottom Solder Paste")\n\t\t\t)\n',
            '\t\t\t(layer "B.SilkS"\n\t\t\t\t(type "Bottom Silk Screen")\n\t\t\t)\n',
            '\t\t\t(copper_finish "ENIG")\n\t\t\t(dielectric_constraints no)\n\t\t)\n']
    return "".join(out)


def emit(v: Variant, placed: list[Placement], tracks, vias) -> str:
    netidx = _net_index()
    padnet = _pad_net_map()
    parts = ["(kicad_pcb\n\t(version 20260206)\n"
             '\t(generator "sensorly-boardgen")\n'
             '\t(generator_version "10.0")\n'
             f"\t(general\n\t\t(thickness {BOARD_THICKNESS})\n"
             "\t\t(legacy_teardrops no)\n\t)\n"
             '\t(paper "A4")\n'
             f'\t(title_block\n\t\t(title "ENV Sensor - Variant {v.key.upper()} ({v.name})")\n'
             f'\t\t(rev "{v.revision}")\n\t\t(company "sensorly-unhinged")\n'
             f'\t\t(comment 1 "SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>")\n'
             f'\t\t(comment 2 "SPDX-License-Identifier: GPL-3.0-or-later")\n'
             f'\t\t(comment 3 "Generated by tools/boardgen - edit the model, not this file")\n'
             f'\t)\n']
    parts.append("\t(layers\n")
    for i, name, kind, desc in LAYER_IDS:
        parts.append(f'\t\t({i} "{name}" {kind}'
                     + (f' "{desc}"' if desc else "") + ")\n")
    parts.append("\t)\n\t(setup\n")
    parts.append(_stackup())
    parts.append("\t\t(pad_to_mask_clearance 0)\n"
                 "\t\t(allow_soldermask_bridges_in_footprints no)\n"
                 "\t\t(tenting front back)\n"
                 f"\t\t(aux_axis_origin {ORIGIN[0]} {ORIGIN[1]})\n"
                 f"\t\t(grid_origin {ORIGIN[0]} {ORIGIN[1]})\n\t)\n")
    for name, i in sorted(netidx.items(), key=lambda kv: kv[1]):
        parts.append(f'\t(net {i} "{name}")\n')
    for p in placed:
        parts.append(_emit_footprint(p, netidx, padnet))
    parts.append(_outline(v))
    parts.append(_silk(v, placed))
    parts.append(_tracks(tracks, vias, netidx))
    parts.append(_zones(v, netidx))
    parts.append(")\n")
    return "".join(parts)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
