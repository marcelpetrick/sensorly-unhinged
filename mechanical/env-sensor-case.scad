// SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
// ENV sensor enclosure - common geometry for both variants.
//
// Do not edit the numbers here. Every dimension comes from params-<variant>.scad,
// which tools/boardgen/enclosure.py generates from the board model, so the case
// cannot drift away from the PCB it is meant to hold.
//
//   openscad -D 'part="base"' -o case-a-base.stl mechanical/case-a.scad
//   openscad -D 'part="lid"'  -o case-a-lid.stl  mechanical/case-a.scad
//
// The enclosure is part of the instrument: on Variant B the dividing wall at the
// neck and the vents over the island are what the thermal model's convection
// term actually depends on. See docs/45-thermal-model.md.

part = "base";      // "base" | "lid" | "both"
$fn = 48;

eps = 0.01;

// board position inside the cavity
bx = wall + (inner_w - board_w) / 2;
by = wall + (inner_h - board_h) / 2;
bz = floor_t + board_z;

module rrect(w, h, r) {
    hull() for (x = [r, w - r], y = [r, h - r]) translate([x, y]) circle(r);
}

module shell(height, r) {
    linear_extrude(height) rrect(outer_w, outer_h, r);
}

module cavity(height) {
    translate([wall, wall, 0])
        linear_extrude(height) rrect(inner_w, inner_h, max(0.5, fillet - wall));
}

// ---- cut-outs -------------------------------------------------------------
module wall_cutout(w, cx, cy, cw, ch, z) {
    // cx, cy are the board coordinates of the part the opening serves
    zz = bz + board_t + z;
    if (w == "left")
        translate([-eps, by + cy - cw / 2, zz - ch / 2])
            cube([wall + 2 * eps, cw, ch + tol]);
    else if (w == "right")
        translate([outer_w - wall - eps, by + cy - cw / 2, zz - ch / 2])
            cube([wall + 2 * eps, cw, ch + tol]);
    else if (w == "top")
        translate([bx + cx - cw / 2, -eps, zz - ch / 2])
            cube([cw, wall + 2 * eps, ch + tol]);
    else if (w == "bottom")
        translate([bx + cx - cw / 2, outer_h - wall - eps, zz - ch / 2])
            cube([cw, wall + 2 * eps, ch + tol]);
}

// The lid is the plate PLUS the locating lip, so anything cut in it has to go
// through both. Cutting only `lid_t` deep leaves the lip filling the slots
// straight back in - which is exactly what the first render showed.
lid_total = lid_t + 1.2;

module lid_cutout(centre_x, centre_y, d) {
    translate([bx + centre_x, by + centre_y, -eps])
        cylinder(d = d, h = lid_total + 2 * eps);
}

module vent_slots() {
    for (v = vents)
        translate([bx + v[0], by + v[1], -eps])
            cube([v[2], v[3], lid_total + 2 * eps]);
}

// Slots in the wall next to the sensor. Lid slots alone leave the sensor
// chamber a cup; M-03 wants ambient air at the sensor, not a pocket of it.
module side_vent_slots() {
    zz = bz + board_t + 1.0;
    for (s = side_vents) {
        if (vent_wall == "bottom")
            translate([bx + s[0] - s[1] / 2, outer_h - wall - eps, zz])
                cube([s[1], wall + 2 * eps, s[2]]);
        else
            translate([bx + s[0] - s[1] / 2, -eps, zz])
                cube([s[1], wall + 2 * eps, s[2]]);
    }
}

// Short pillars from the lid down onto bare board, so the PCB cannot rattle
// on its ribs. Positions come from the generator, which searched the placement
// for free space rather than assuming a corner was empty.
module holddown_pillars() {
    h = inner_z - (board_z + board_t);
    for (p = holddowns)
        translate([bx + p[0], by + p[1], lid_t - eps])
            cylinder(d = p[2], h = h + eps);
}

// ---- support --------------------------------------------------------------
module ribs() {
    // Four short ribs under the board corners, kept out of the antenna
    // keep-out so nothing dense sits behind the antenna (M-04).
    ay1 = antenna_keepout[3];
    for (p = [[3, ay1 + 3], [board_w - 3, ay1 + 3],
              [3, board_h - 3], [board_w - 3, board_h - 3]])
        translate([bx + p[0] - rib_w / 2, by + p[1] - rib_w / 2, floor_t])
            cube([rib_w, rib_w, board_z]);
}

module divider() {
    // Variant B only: the wall between the electronics chamber and the sensor
    // chamber, with a slot for the PCB neck to pass through.
    if (divider_y > 0) {
        difference() {
            translate([wall, by + divider_y - wall / 2, floor_t])
                cube([inner_w, wall, inner_z]);
            translate([bx + board_w / 2 - neck_slot[0] / 2,
                       by + divider_y - wall / 2 - eps,
                       bz - tol])
                cube([neck_slot[0], wall + 2 * eps, neck_slot[1]]);
        }
    }
}

// ---- parts ----------------------------------------------------------------
module base() {
    difference() {
        union() {
            difference() {
                shell(floor_t + inner_z, fillet);
                translate([0, 0, floor_t]) cavity(inner_z + eps);
            }
            ribs();
            divider();
        }
        for (c = cutouts)
            if (c[0] != "lid") wall_cutout(c[0], c[1], c[2], c[3], c[4], c[5]);
        side_vent_slots();
    }
}

module lid() {
    union() {
        difference() {
            union() {
                linear_extrude(lid_t) rrect(outer_w, outer_h, fillet);
                // lip that locates the lid in the cavity
                difference() {
                    translate([wall + 0.3, wall + 0.3, lid_t])
                        linear_extrude(1.2)
                            difference() {
                                rrect(inner_w - 0.6, inner_h - 0.6,
                                      max(0.5, fillet - wall));
                                translate([1.2, 1.2])
                                    rrect(inner_w - 3.0, inner_h - 3.0, 0.5);
                            }
                    // The chamber wall reaches the lid seating plane. Relieve
                    // the ring where it crosses that wall, not the whole lid.
                    if (divider_y > 0)
                        translate([0, by + divider_y - wall/2 - tol, lid_t - eps])
                            cube([outer_w, wall + 2*tol, 1.2 + 2*eps]);
                }
            }
            vent_slots();
            for (c = cutouts)
                if (c[0] == "lid") lid_cutout(c[1], c[2], c[3]);
        }
        holddown_pillars();
    }
}

if (part == "base") base();
else if (part == "lid") lid();
else if (part == "interference") {
    intersection() {
        base();
        translate([0, 0, floor_t + inner_z + lid_t]) mirror([0, 0, 1]) lid();
    }
}
else if (part == "both") { base(); translate([0, outer_h + 5, 0]) lid(); }
else assert(false, "unknown enclosure part");
