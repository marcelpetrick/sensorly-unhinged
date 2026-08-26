# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""A two-layer maze router for the rest of the board.

The four sensor-island nets are routed by `route.py` under their own rules.
Everything else is routed here, on F.Cu and B.Cu, against the In1 ground plane
and the In2 +3V0 plane.

Why write one instead of exporting Specctra DSN to freerouting: this repository's
whole claim is that a rule change regenerates *both* boards identically. A manual
routing session, however good the router, breaks that - the next time the neck
width changes, someone has to route both boards again by hand and hope they made
the same decisions twice. A router in the generator keeps the property.

It is a plain Dijkstra on a 0.1 mm grid with a turn penalty and a via penalty,
multi-terminal via repeated multi-source searches (Prim-style), routing the
shortest nets first. No rip-up, no shoving. It is not a good autorouter; it is a
reproducible one, and KiCad's DRC is the judge.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from . import geometry as G
from .design import NETS, PART_BY_REF
from .place import Placement
from .route import GRID, Grid, Track, Via
from .variants import (B_ISLAND_RECT, B_NECK_RECT, Variant, antenna_keepout,
                       sensor_keepout)

LAYERS = ("F.Cu", "B.Cu")
SIGNAL_W = 0.20
POWER_W = 0.35
# KiCad applies the larger of the two nets' class clearances, so the router has
# to as well. Using one worst-case number everywhere is safe and useless: at
# 0.22 the blocking band around a 0.5 mm-pitch pad is 0.52 mm, which seals its
# own escape corridor, and every QFN and SON on the board becomes unroutable.
CLR_DEFAULT = 0.15        # Default net class
CLR_POWER = 0.20          # Power / USB net classes
SAFETY = 0.06             # we round outward on a 0.1 mm grid; KiCad does not
CLEAR = CLR_POWER + SAFETY
VIA_SIZE = 0.6
VIA_DRILL = 0.3

# Blocking radii are measured from a centreline or centre, and depend on the
# width of the net being routed *now* - blocking everything at worst-case width
# is correct but throws away most of the board.
MASK_EXP = 0.03


def is_power(net: str | None) -> bool:
    return bool(net) and (net in POWER_NETS or net in PLANE_NETS)


def clr(net_a: str | None, net_b: str | None) -> float:
    return (CLR_POWER if (is_power(net_a) or is_power(net_b))
            else CLR_DEFAULT) + SAFETY


def m_track(existing_w: float, mine: float, c: float) -> float:
    return c + existing_w / 2 + mine / 2


def m_pad(mine: float, c: float) -> float:
    return c + mine / 2 + MASK_EXP


def m_via(mine: float, c: float) -> float:
    return VIA_SIZE / 2 + c + mine / 2


R_VIA = VIA_SIZE / 2 + CLR_POWER + SAFETY + SIGNAL_W / 2

TURN_PENALTY = 8
VIA_PENALTY = 140         # a via costs about 14 mm of detour

# Nets that reach a plane and therefore need a via, not a route.
PLANE_NETS = {"GND": "In1.Cu", "+3V0": "In2.Cu"}
POWER_NETS = {"VSYS", "VBUS", "VBAT"}
# Routed elsewhere, under their own rules (EDS S3.1).
ISLAND_NETS = {"SDA", "SCL"}


@dataclass
class Term:
    x: float
    y: float
    layer: int          # 0 = F.Cu, 1 = B.Cu
    ref: str
    pad: str


def _terminals(placed: list[Placement]) -> dict[str, list[Term]]:
    by_net: dict[str, list[Term]] = {}
    padnet = {}
    for net, conns in NETS.items():
        for ref, pad in conns:
            padnet[(ref, pad)] = net
    for p in placed:
        fp = G.get(p.footprint)
        bottom = fp.bottom
        for name, pts in fp.pads.items():
            net = padnet.get((p.ref, name))
            if net is None:
                continue
            for (lx, ly) in pts:
                x, y = G.xform(lx, ly, p.x, p.y, p.rot)
                by_net.setdefault(net, []).append(
                    Term(x, y, 1 if bottom else 0, p.ref, name))
    return by_net


class Board:
    """Occupancy for both routable layers."""

    def __init__(self, v: Variant, placed: list[Placement]):
        base = Grid(v)                      # outline + antenna keep-out
        self.v = v
        self.w, self.h = base.w, base.h
        self.blocked = [bytearray(base.blocked), bytearray(base.blocked)]
        self.placed = placed
        self._pad_cells: dict[tuple[int, int, int], str] = {}

        # Thermal zones: nothing but the island nets may cross them.
        if v.key == "b":
            nx0, ny0, nx1, ny1 = B_NECK_RECT
            ix0, iy0, ix1, iy1 = B_ISLAND_RECT
            for L in (0, 1):
                self.block(L, nx0 - 0.4, ny0, nx1 + 0.4, iy1 + 0.4)
                self.block(L, ix0 - 0.4, iy0 - 0.4, ix1 + 0.4, iy1 + 0.4)
        else:
            sx0, sx1, sy0, sy1 = sensor_keepout(v)
            for L in (0, 1):
                self.block(L, sx0, sy0, sx1, sy1)

    def block(self, layer: int, x0, y0, x1, y1):
        # Round outward, but by less than one cell. The obvious `int(x)+2` form
        # over-blocks by 0.2 mm, which is enough to seal every pad on a 0.5 mm
        # pitch part and make the whole connector unroutable.
        b = self.blocked[layer]
        y_lo = max(0, math.floor(y0 / GRID))
        y_hi = min(self.h, math.ceil(y1 / GRID) + 1)
        x_lo = max(0, math.floor(x0 / GRID))
        x_hi = min(self.w, math.ceil(x1 / GRID) + 1)
        for iy in range(y_lo, y_hi):
            row = iy * self.w
            for ix in range(x_lo, x_hi):
                b[row + ix] = 1

    def free(self, ix, iy, layer):
        return (0 <= ix < self.w and 0 <= iy < self.h
                and not self.blocked[layer][iy * self.w + ix])

    def add_pads(self, exclude_net: str | None, padnet: dict,
                 mine: float = SIGNAL_W):
        """Block every pad that is not on `exclude_net`, at that pad's own
        net-class clearance rather than a single worst-case number."""
        for p in self.placed:
            fp = G.get(p.footprint)
            layer = 1 if fp.bottom else 0
            for name, pts in fp.pads.items():
                if padnet.get((p.ref, name)) == exclude_net:
                    continue
                pw, ph = fp.pad_size.get(name, (0.6, 0.6))
                if p.rot % 180:
                    pw, ph = ph, pw
                through = "thru_hole" in fp.text.split(f'(pad "{name}"')[-1][:60]
                layers = (0, 1) if through else (layer,)
                m = m_pad(mine, clr(exclude_net, padnet.get((p.ref, name))))
                for (lx, ly) in pts:
                    x, y = G.xform(lx, ly, p.x, p.y, p.rot)
                    for L in layers:
                        self.block(L, x - pw / 2 - m, y - ph / 2 - m,
                                   x + pw / 2 + m, y + ph / 2 + m)

    def add_track(self, t: Track, mine: float = SIGNAL_W,
                  mine_net: str | None = None):
        L = LAYERS.index(t.layer)
        m = m_track(t.width, mine, clr(mine_net, t.net))
        for i in range(len(t.pts) - 1):
            ax, ay = t.pts[i]
            bx, by = t.pts[i + 1]
            self.block(L, min(ax, bx) - m, min(ay, by) - m,
                       max(ax, bx) + m, max(ay, by) + m)

    def add_via(self, vv: Via, mine: float = SIGNAL_W,
                mine_net: str | None = None):
        m = m_via(mine, clr(mine_net, vv.net))
        for L in (0, 1):
            self.block(L, vv.x - m, vv.y - m, vv.x + m, vv.y + m)


def _erode(src: bytearray, w: int, h: int, r: int) -> bytearray:
    """1 where any blocked cell lies within `r` cells (Chebyshev). O(w*h)."""
    tmp = bytearray(w * h)
    for y in range(h):
        row = y * w
        cnt = sum(src[row + x] for x in range(0, min(r + 1, w)))
        for x in range(w):
            tmp[row + x] = 1 if cnt else 0
            if x - r >= 0:
                cnt -= src[row + x - r]
            if x + r + 1 < w:
                cnt += src[row + x + r + 1]
    out = bytearray(w * h)
    for x in range(w):
        cnt = sum(tmp[y * w + x] for y in range(0, min(r + 1, h)))
        for y in range(h):
            out[y * w + x] = 1 if cnt else 0
            if y - r >= 0:
                cnt -= tmp[(y - r) * w + x]
            if y + r + 1 < h:
                cnt += tmp[(y + r + 1) * w + x]
    return out


def via_mask(board: "Board") -> bytearray:
    """1 where a via may be dropped: clear of copper and keep-outs on both
    layers by the via's own radius. KiCad measures the via pad, not its
    centre, which is what made the first attempt place vias inside the RF
    keep-out and on top of neighbouring pads."""
    r = int(math.ceil(R_VIA / GRID))
    fa = _erode(board.blocked[0], board.w, board.h, r)
    fb = _erode(board.blocked[1], board.w, board.h, r)
    return bytearray(1 if (fa[i] or fb[i]) else 0 for i in range(len(fa)))


DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def _search(board: Board, sources: set[tuple[int, int, int]],
            targets: set[tuple[int, int, int]], allow_vias: bool,
            vmask: bytearray | None = None):
    """Multi-source Dijkstra. Returns a path (list of (ix,iy,layer)) or None."""
    best: dict[tuple[int, int, int, int], float] = {}
    prev: dict = {}
    pq = []
    for (x, y, L) in sources:
        st = (x, y, L, -1)
        best[st] = 0.0
        heapq.heappush(pq, (0.0, x, y, L, -1))
    goal = None
    while pq:
        cost, x, y, L, d = heapq.heappop(pq)
        st = (x, y, L, d)
        if best.get(st, 1e18) < cost:
            continue
        if (x, y, L) in targets and (x, y, L) not in sources:
            goal = st
            break
        for nd, (dx, dy) in enumerate(DIRS):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < board.w and 0 <= ny < board.h):
                continue
            if not board.free(nx, ny, L) and (nx, ny, L) not in targets:
                continue
            nc = cost + 1 + (TURN_PENALTY if d != -1 and nd != d else 0)
            ns = (nx, ny, L, nd)
            if nc < best.get(ns, 1e18):
                best[ns] = nc
                prev[ns] = st
                heapq.heappush(pq, (nc, nx, ny, L, nd))
        if allow_vias and vmask is not None and not vmask[y * board.w + x]:
            nl = 1 - L
            if board.free(x, y, nl) or (x, y, nl) in targets:
                nc = cost + VIA_PENALTY
                ns = (x, y, nl, -1)
                if nc < best.get(ns, 1e18):
                    best[ns] = nc
                    prev[ns] = st
                    heapq.heappush(pq, (nc, x, y, nl, -1))
    if goal is None:
        return None
    out = []
    st = goal
    while st in prev:
        out.append((st[0], st[1], st[2]))
        st = prev[st]
    out.append((st[0], st[1], st[2]))
    out.reverse()
    return out


def _to_geometry(path, width: float, net: str):
    """Split a grid path into per-layer tracks plus the vias between them."""
    tracks: list[Track] = []
    vias: list[Via] = []
    run = [path[0]]
    for node in path[1:]:
        if node[2] != run[-1][2]:
            tracks.append(_track(run, width, net))
            vias.append(Via(net, round(node[0] * GRID, 3),
                            round(node[1] * GRID, 3), VIA_SIZE, VIA_DRILL))
            run = [node]
        else:
            run.append(node)
    tracks.append(_track(run, width, net))
    return [t for t in tracks if len(t.pts) > 1], vias


def _track(run, width, net) -> Track:
    pts = [(round(x * GRID, 3), round(y * GRID, 3)) for x, y, _L in run]
    simple = [pts[0]]
    for i in range(1, len(pts) - 1):
        ax, ay = simple[-1]
        bx, by = pts[i]
        cx, cy = pts[i + 1]
        if (bx - ax) * (cy - by) != (by - ay) * (cx - bx):
            simple.append(pts[i])
    if len(pts) > 1:
        simple.append(pts[-1])
    return Track(net, width, LAYERS[run[0][2]], simple)


def route_rest(v: Variant, placed: list[Placement],
               island_tracks: list[Track], island_vias: list[Via]):
    """Route everything except the sensor island. Returns (tracks, vias, stats)."""
    padnet = {}
    for net, conns in NETS.items():
        for ref, pad in conns:
            padnet[(ref, pad)] = net
    terms = _terminals(placed)

    tracks: list[Track] = []
    vias: list[Via] = []
    failed: list[str] = []

    def snap(t: Term):
        return (int(round(t.x / GRID)), int(round(t.y / GRID)), t.layer)

    # --- 1. plane nets: a via beside each pad, not a route -----------------
    for net, _layer in PLANE_NETS.items():
        board = Board(v, placed)
        board.add_pads(net, padnet, POWER_W)
        for t in island_tracks + tracks:
            board.add_track(t, POWER_W, net)
        for vv in island_vias + vias:
            board.add_via(vv, POWER_W, net)
        vmask = via_mask(board)
        for t in terms.get(net, []):
            if net == "GND" and t.layer == 0:
                continue          # the F.Cu pour already covers these
            if t.ref in ("U2", "C6"):
                continue          # island parts are fed across the neck
            # The stub from pad to via has to be *routed*, not drawn. Drawing
            # a straight line was the source of the last round of shorts.
            src = (int(round(t.x / GRID)), int(round(t.y / GRID)), t.layer)
            done = False
            for (vx, vy) in _via_spots(board, t, vmask):
                path = _search(board, {src}, {(vx, vy, t.layer)},
                               allow_vias=False)
                if path is None:
                    continue
                trs, _unused = _to_geometry(path, POWER_W, net)
                vv = Via(net, round(vx * GRID, 3), round(vy * GRID, 3),
                         VIA_SIZE, VIA_DRILL)
                vias.append(vv)
                for tr in trs:
                    tracks.append(tr)
                    board.add_track(tr, POWER_W, net)
                board.add_via(vv, POWER_W, net)
                vmask = via_mask(board)
                done = True
                break
            if not done:
                failed.append(f"{net}: no plane via for {t.ref}.{t.pad}")

    # --- 2. everything else, shortest nets first ---------------------------
    # Order matters more than anything else in a router without rip-up. The
    # constrained nets - the ones that have to escape a 0.5 mm-pitch part or
    # cross a connector's own pins - go first, while there is still room. Sorting
    # purely by length put the USB pair last, after the board was full.
    FINE = {"U1", "U2", "U3", "U4", "U5", "J1"}

    def difficulty(kv):
        _net, ts = kv
        fine = sum(1 for t in ts if t.ref in FINE)
        return (-fine, _spread(ts))

    todo = [(net, ts) for net, ts in terms.items()
            if net not in PLANE_NETS and net not in ISLAND_NETS and len(ts) > 1]
    todo.sort(key=difficulty)

    for net, ts in todo:
        width = POWER_W if net in POWER_NETS else SIGNAL_W
        board = Board(v, placed)
        board.add_pads(net, padnet, width)
        for t in island_tracks + tracks:
            board.add_track(t, width, net)
        for vv in island_vias + vias:
            board.add_via(vv, width, net)
        vmask = via_mask(board)

        # Seed from a terminal that can actually leave its pad. A pad on a
        # 0.5 mm-pitch part can be sealed by its neighbours' clearance, and
        # seeding on one of those strands the whole net.
        cells = [snap(t) for t in ts]
        seed_i = 0
        for i, c in enumerate(cells):
            if any(board.free(c[0] + dx, c[1] + dy, c[2]) for dx, dy in DIRS):
                seed_i = i
                break
        connected = {cells[seed_i]}
        remaining = [c for i, c in enumerate(cells) if i != seed_i]
        while remaining:
            path = _search(board, connected, set(remaining), allow_vias=True,
                           vmask=vmask)
            if path is None:
                # Nothing left is reachable from what we have. Report the pads,
                # not just a count - the count hides which part is the problem.
                stuck = {c: t for c, t in zip(cells, ts)}
                names = ", ".join(f"{stuck[c].ref}.{stuck[c].pad}"
                                  for c in remaining if c in stuck)
                failed.append(f"{net}: {names}")
                break
            trs, vs = _to_geometry(path, width, net)
            if any(math.hypot(p.x - q.x, p.y - q.y) < 0.9
                   for i, p in enumerate(vs) for q in vs[i + 1:]):
                failed.append(f"{net}: vias too close, left unrouted")
                break
            for t in trs:
                tracks.append(t)
                board.add_track(t, width, net)
            for vv in vs:
                vias.append(vv)
                board.add_via(vv, width, net)
            for node in path:
                connected.add(node)
            remaining = [r for r in remaining if r not in connected]

    stats = dict(tracks=len(tracks), vias=len(vias), failed=failed)
    return tracks, vias, stats


def _via_spots(board: Board, t: Term, vmask: bytearray, limit: int = 24):
    """Points near a pad where a via legally fits, nearest first."""
    px, py = int(round(t.x / GRID)), int(round(t.y / GRID))
    out = []
    for radius in range(int(0.5 / GRID), int(4.0 / GRID)):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) != radius:
                    continue
                x, y = px + dx, py + dy
                if not (0 <= x < board.w and 0 <= y < board.h):
                    continue
                if not vmask[y * board.w + x]:
                    out.append((x, y))
                    if len(out) >= limit:
                        return out
    return out


def _spread(ts: list[Term]) -> float:
    xs = [t.x for t in ts]
    ys = [t.y for t in ts]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys))
