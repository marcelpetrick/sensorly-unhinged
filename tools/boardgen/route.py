# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""A small orthogonal maze router, used for the four sensor-island nets only.

The rest of the board is left for interactive routing in KiCad. These four are
routed here because they are the ones that carry a *rule*: EDS S3.1 says exactly
four nets cross to the sensor, at 0.15 mm, with nothing else near them. A rule
that is enforced by a generator cannot be forgotten during a re-layout.

Dijkstra on a 0.1 mm grid with a turn penalty, so the routes come out straight.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from . import geometry as G
from .design import PART_BY_REF
from .place import Placement
from .variants import B_BODY_H, B_ISLAND_RECT, Variant, antenna_keepout, sensor_keepout

GRID = 0.1
ISLAND_WIDTH = 0.15          # EDS S3.1 - the dominant thermal term
ISLAND_CLEAR = 0.15
EDGE_CLEAR = 0.50      # 0.3 mm copper-to-edge + half the widest track
TURN_PENALTY = 12


@dataclass
class Track:
    net: str
    width: float
    layer: str
    pts: list[tuple[float, float]]


@dataclass
class Via:
    net: str
    x: float
    y: float
    size: float = 0.6
    drill: float = 0.3


def center_track_ends(tracks: list[Track], vias: list[Via]) -> list[Track]:
    """Trim collinear terminal stubs contained inside a same-net via annulus.

    Never move a via or introduce a diagonal: that could change clearance away
    from the already occupied via copper. Non-collinear cases remain for DRC.
    """
    result = []
    for track in tracks:
        pts = list(track.pts)
        for end, adjacent in ((0, 1), (-1, -2)):
            if len(pts) < 2:
                break
            x, y = pts[end]
            ax, ay = pts[adjacent]
            for via in vias:
                if via.net != track.net:
                    continue
                if math.hypot(x - via.x, y - via.y) > (via.size - track.width)/2 + 1e-9:
                    continue
                cross = (x-ax)*(via.y-ay) - (y-ay)*(via.x-ax)
                if abs(cross) < 1e-9:
                    pts[end] = (via.x, via.y)
                    break
        if any(a != b for a, b in zip(pts, pts[1:])):
            result.append(Track(track.net, track.width, track.layer, pts))
    return result


def validate_neck_crossings(v: Variant, tracks: list[Track]):
    """Each cut through B's neck must meet exactly four thin top-layer traces."""
    if v.key != "b":
        return
    expected = {"SDA", "SCL", "+3V0", "GND"}
    for step in range(int((B_ISLAND_RECT[1] - B_BODY_H) / GRID)):
        y = B_BODY_H + (step + .5) * GRID
        crossings = set()
        for t in tracks:
            for (ax, ay), (bx, by) in zip(t.pts, t.pts[1:]):
                if min(ay, by) <= y < max(ay, by):
                    x = ax + (y - ay) * (bx - ax) / (by - ay)
                    crossings.add((t.net, t.layer, round(x, 6), t.width))
        if (len(crossings) != 4 or {c[0] for c in crossings} != expected or
                any(c[1] != "F.Cu" or abs(c[3] - ISLAND_WIDTH) > 1e-9 for c in crossings)):
            raise ValueError(f"B neck at y={y:.2f}: expected four thin top-layer conductors, got {crossings}")


class Grid:
    def __init__(self, v: Variant):
        self.v = v
        self.w = int(v.width / GRID) + 1
        self.h = int(v.height / GRID) + 1
        self.blocked = bytearray(self.w * self.h)
        for iy in range(self.h):
            for ix in range(self.w):
                x, y = ix * GRID, iy * GRID
                if not G.point_in_poly((x, y), v.outline):
                    self.blocked[iy * self.w + ix] = 1
        self._inflate_outline()
        ax0, ax1, ay0, ay1 = antenna_keepout(v)
        self.block_rect(ax0, ay0, ax1, ay1)

    def _inflate_outline(self):
        r = int(EDGE_CLEAR / GRID)
        src = bytes(self.blocked)
        for iy in range(self.h):
            for ix in range(self.w):
                if src[iy * self.w + ix]:
                    continue
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        jx, jy = ix + dx, iy + dy
                        if not (0 <= jx < self.w and 0 <= jy < self.h) or \
                           src[jy * self.w + jx]:
                            self.blocked[iy * self.w + ix] = 1
                            break
                    else:
                        continue
                    break

    def block_rect(self, x0, y0, x1, y1):
        # Round outward by less than a cell. `int(x) + 2` over-blocks by 0.2 mm,
        # which is enough to seal a 0.5 mm-pitch pad's own escape corridor.
        for iy in range(max(0, math.floor(y0 / GRID)),
                        min(self.h, math.ceil(y1 / GRID) + 1)):
            for ix in range(max(0, math.floor(x0 / GRID)),
                            min(self.w, math.ceil(x1 / GRID) + 1)):
                self.blocked[iy * self.w + ix] = 1

    def free(self, ix, iy):
        return 0 <= ix < self.w and 0 <= iy < self.h and not self.blocked[iy * self.w + ix]


def _pad_points(p: Placement, net_pads):
    fp = G.get(p.footprint)
    out = {}
    for name, pts in fp.pads.items():
        for (lx, ly) in pts:
            out.setdefault(name, []).append(G.xform(lx, ly, p.x, p.y, p.rot))
    return out


def route_island(v: Variant, placed: list[Placement], netlist) -> list[Track]:
    """Route SDA, SCL, +3V0 and GND from the sensor to the main board."""
    by_ref = {p.ref: p for p in placed}
    grid = Grid(v)

    # every pad on the board is an obstacle, with clearance
    pads: dict[tuple[str, str], tuple[float, float]] = {}
    for p in placed:
        if G.get(p.footprint).bottom:
            continue                      # bottom-side pads do not block F.Cu
        for name, pts in _pad_points(p, None).items():
            for (x, y) in pts:
                pads[(p.ref, name)] = (x, y)
    clr = ISLAND_CLEAR + ISLAND_WIDTH / 2

    def block_pads(exclude: set):
        grid2 = Grid.__new__(Grid)
        grid2.__dict__.update(grid.__dict__)
        grid2.blocked = bytearray(grid.blocked)
        for p in placed:
            if G.get(p.footprint).bottom:
                continue
            fp = G.get(p.footprint)
            for name, pts in fp.pads.items():
                if (p.ref, name) in exclude:
                    continue
                w, h = fp.pad_size.get(name, (0.6, 0.6))
                if p.rot % 180:
                    w, h = h, w
                for (lx, ly) in pts:
                    x, y = G.xform(lx, ly, p.x, p.y, p.rot)
                    grid2.block_rect(x - w / 2 - clr, y - h / 2 - clr,
                                     x + w / 2 + clr, y + h / 2 + clr)
        return grid2

    # Sensor connections, in the order that keeps the lanes tidy in the neck.
    # The long hauls first, then C6 - the only passive allowed on the island
    # (EDS S3.1.5) - taps whichever of them it belongs to. C6 is connected
    # across the island rather than fed by its own via, because a via on the
    # island is a copper column straight through the thermal isolation.
    plan = [
        ("SDA", ("U2", "1"), ("R3", "2"), None),
        ("SCL", ("U2", "2"), ("R4", "2"), None),
        ("GND", ("U2", "4"), None, None),
        ("GND", ("C6", "2"), None, "GND"),
        ("+3V0", ("U2", "3"), None, None),
        ("+3V0", ("C6", "1"), None, "+3V0"),
    ]
    if v.key == "a":
        # A has no neck; retain its existing routing order and fan-out.
        plan = [plan[i] for i in (0, 1, 4, 2, 5, 3)]
    tracks: list[Track] = []
    vias: list[Via] = []
    extra_blocked: list[tuple] = []

    routed_cells: dict[str, set[tuple[int, int]]] = {}
    for net, src, dst, tap in plan:
        exclude = {src}
        if dst:
            exclude.add(dst)
        g = block_pads(exclude)
        for owner, (x0, y0, x1, y1) in extra_blocked:
            if tap and owner == tap:
                continue      # tapping our own net: its clearance is not ours
            g.block_rect(x0, y0, x1, y1)
        if v.key == "a":
            sx0, sx1, sy0, sy1 = sensor_keepout(v)
            quiet = (sx0, sx1, sy0, sy1)
        else:
            quiet = None

        sx, sy = pads[src]
        goals: set[tuple[int, int]] | None = None
        if tap:
            goals = routed_cells[tap]
            if v.key == "b":
                # C6 must tap on the island, never add another neck conductor.
                g.block_rect(0, 0, v.width, B_ISLAND_RECT[1])
                goals = {(x, y) for x, y in goals if y * GRID > B_ISLAND_RECT[1]}
            tx = ty = None
        elif dst:
            tx, ty = pads[dst]
        else:
            # +3V0 and GND leave F.Cu on a via and join their plane. The via
            # goes in open board next to the connectors, never on the neck.
            gv = Grid.__new__(Grid)
            gv.__dict__.update(g.__dict__)
            gv.blocked = bytearray(g.blocked)
            if quiet:
                gv.block_rect(quiet[0], quiet[2], quiet[1], quiet[3])
            preferred = PLANE_VIA[net]
            if v.key == "b":
                gv.block_rect(0, B_BODY_H - .5, v.width, v.height)
                # Geometry seed, not an electrical value: search for legal
                # main-board plane access just above the neck. Long lateral
                # fan-outs unnecessarily block the other dense board routes.
                preferred = (v.width/2 + (1.5 if net == "GND" else -2),
                             B_BODY_H - 2)
            tx, ty = _free_spot(gv, preferred, 0.55)
        path = _dijkstra(g, (sx, sy), (tx, ty) if goals is None else None,
                         goals=goals)
        if path is None:
            raise RuntimeError(f"island route failed for {net} from {src}")
        pts = _simplify(path)
        tracks.append(Track(net, ISLAND_WIDTH, "F.Cu", pts))
        cells = set()
        for i in range(len(path)):
            cells.add((int(round(path[i][0] / GRID)),
                       int(round(path[i][1] / GRID))))
        for i in range(len(path) - 1):
            ax, ay = path[i]
            bx, by = path[i + 1]
            steps = int(round(max(abs(bx - ax), abs(by - ay)) / GRID))
            for k in range(steps + 1):
                cells.add((int(round((ax + (bx - ax) * k / max(steps, 1)) / GRID)),
                           int(round((ay + (by - ay) * k / max(steps, 1)) / GRID))))
        routed_cells.setdefault(net, set()).update(cells)
        if dst is None and tap is None:
            vias.append(Via(net, pts[-1][0], pts[-1][1]))
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            extra_blocked.append((net, (min(ax, bx) - 0.3, min(ay, by) - 0.3,
                                        max(ax, bx) + 0.3, max(ay, by) + 0.3)))
        if dst is None and tap is None:
            vx, vy = pts[-1]
            extra_blocked.append((net, (vx - 0.55, vy - 0.55,
                                        vx + 0.55, vy + 0.55)))
    return tracks, vias


# Where the two plane nets drop off F.Cu. Open board beside the battery
# connector, well clear of the neck and of the sensor's quiet zone.
PLANE_VIA = {"+3V0": (23.5, 30.2), "GND": (25.6, 30.2)}

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def _free_spot(g: Grid, pref, clear: float):
    """Nearest grid point to `pref` with `clear` mm of free space around it."""
    r = int(clear / GRID)
    px, py = int(round(pref[0] / GRID)), int(round(pref[1] / GRID))
    for radius in range(0, 200):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) != radius:
                    continue
                x, y = px + dx, py + dy
                if all(g.free(x + ix, y + iy)
                       for ix in range(-r, r + 1) for iy in range(-r, r + 1)):
                    return x * GRID, y * GRID
    raise RuntimeError(f"no free spot near {pref}")


def _dijkstra(g: Grid, start, goal, goals: set[tuple[int, int]] | None = None):
    """Route to `goal`, or to any cell in `goals` (used to tap an existing net)."""
    sx, sy = int(round(start[0] / GRID)), int(round(start[1] / GRID))
    if goals is None:
        gx, gy = int(round(goal[0] / GRID)), int(round(goal[1] / GRID))
        targets = {(gx, gy)}
    else:
        targets = set(goals)
        gx = gy = None
    # our own pads are always reachable
    for (px, py) in [(sx, sy)] + ([(gx, gy)] if goals is None else []):
        if 0 <= px < g.w and 0 <= py < g.h:
            g.blocked[py * g.w + px] = 0
    best: dict[tuple[int, int, int], float] = {}
    prev: dict[tuple[int, int, int], tuple] = {}
    pq = [(0.0, sx, sy, -1)]
    found = None
    while pq:
        cost, x, y, d = heapq.heappop(pq)
        key = (x, y, d)
        if key in best and best[key] < cost:
            continue
        if (x, y) in targets:
            found = key
            break
        for nd, (dx, dy) in enumerate(DIRS):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < g.w and 0 <= ny < g.h):
                continue
            if not g.free(nx, ny) and (nx, ny) not in targets:
                continue
            nc = cost + 1 + (TURN_PENALTY if d != -1 and nd != d else 0)
            nk = (nx, ny, nd)
            if nk not in best or nc < best[nk]:
                best[nk] = nc
                prev[nk] = key
                heapq.heappush(pq, (nc, nx, ny, nd))
    if found is None:
        return None
    out = []
    k = found
    while k in prev:
        out.append((k[0] * GRID, k[1] * GRID))
        k = prev[k]
    out.append((sx * GRID, sy * GRID))
    out.reverse()
    return out


def _simplify(path):
    if len(path) < 3:
        return path
    out = [path[0]]
    for i in range(1, len(path) - 1):
        ax, ay = out[-1]
        bx, by = path[i]
        cx, cy = path[i + 1]
        if (bx - ax, by - ay) and ((bx - ax) * (cy - by) != (by - ay) * (cx - bx)):
            out.append(path[i])
    out.append(path[-1])
    return [(round(x, 3), round(y, 3)) for x, y in out]


# --------------------------------------------------------------------------
def stitch_ground(v: Variant, placed: list[Placement], tracks: list[Track],
                  vias: list[Via], pitch: float = 2.5) -> list[Via]:
    """A perimeter ring of GND vias tying the four copper layers together.

    Standard practice on a 4-layer board with a module radio: it stops the
    outer pours breaking into isolated islands and keeps the return path under
    the antenna feed short. Placed nowhere near the antenna keep-out, the
    sensor island or the thermal neck - a via there would be a copper column
    straight through the board, which is the one thing Variant B exists to
    avoid.
    """
    from .variants import B_ISLAND_RECT, B_NECK_RECT, sensor_keepout

    g = Grid(v)
    for p in placed:
        fp = G.get(p.footprint)
        for name, pts in fp.pads.items():
            w, h = fp.pad_size.get(name, (0.6, 0.6))
            if p.rot % 180:
                w, h = h, w
            for (lx, ly) in pts:
                x, y = G.xform(lx, ly, p.x, p.y, p.rot)
                g.block_rect(x - w / 2 - 0.55, y - h / 2 - 0.55,
                             x + w / 2 + 0.55, y + h / 2 + 0.55)
    for t in tracks:
        for i in range(len(t.pts) - 1):
            ax, ay = t.pts[i]
            bx, by = t.pts[i + 1]
            g.block_rect(min(ax, bx) - 0.55, min(ay, by) - 0.55,
                         max(ax, bx) + 0.55, max(ay, by) + 0.55)
    for vv in vias:
        g.block_rect(vv.x - 0.9, vv.y - 0.9, vv.x + 0.9, vv.y + 0.9)
    if v.key == "b":
        nx0, ny0, nx1, ny1 = B_NECK_RECT
        ix0, iy0, ix1, iy1 = B_ISLAND_RECT
        g.block_rect(nx0 - 1.0, ny0 - 1.0, nx1 + 1.0, iy1 + 1.0)
        g.block_rect(ix0 - 1.0, iy0 - 1.0, ix1 + 1.0, iy1 + 1.0)
    else:
        sx0, sx1, sy0, sy1 = sensor_keepout(v)
        g.block_rect(sx0, sy0, sx1, sy1)

    out: list[Via] = []
    steps = int(pitch / GRID)
    for iy in range(0, g.h, steps):
        for ix in range(0, g.w, steps):
            x, y = ix * GRID, iy * GRID
            r = int(0.55 / GRID)
            if not all(g.free(ix + dx, iy + dy)
                       for dx in range(-r, r + 1) for dy in range(-r, r + 1)):
                continue
            out.append(Via("GND", round(x, 3), round(y, 3)))
            g.block_rect(x - pitch * 0.6, y - pitch * 0.6,
                         x + pitch * 0.6, y + pitch * 0.6)
    return out
