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
module wall_cutout(w, centre, cw, ch, z) {
    // `centre` is in board coordinates along the wall
    zz = bz + board_t + z;
    if (w == "left")
        translate([-eps, by + centre - cw / 2, zz - ch / 2])
            cube([wall + 2 * eps, cw, ch + tol]);
    else if (w == "right")
        translate([outer_w - wall - eps, by + centre - cw / 2, zz - ch / 2])
            cube([wall + 2 * eps, cw, ch + tol]);
    else if (w == "top")
        translate([bx + centre - cw / 2, -eps, zz - ch / 2])
            cube([cw, wall + 2 * eps, ch + tol]);
    else if (w == "bottom")
        translate([bx + centre - cw / 2, outer_h - wall - eps, zz - ch / 2])
            cube([cw, wall + 2 * eps, ch + tol]);
}

module lid_cutout(centre_x, d) {
    translate([bx + centre_x, by + inner_h / 2, -eps])
        cylinder(d = d, h = lid_t + 2 * eps);
}

module vent_slots() {
    for (v = vents)
        translate([bx + v[0], by + v[1], -eps])
            cube([v[2], v[3], lid_t + 2 * eps]);
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
            if (c[0] != "lid") wall_cutout(c[0], c[1], c[2], c[3], c[4]);
        // battery bay is simply the space under the board; nothing to cut,
        // but mark it so the model documents itself in the preview
    }
}

module lid() {
    difference() {
        union() {
            linear_extrude(lid_t) rrect(outer_w, outer_h, fillet);
            // lip that locates the lid in the cavity
            translate([wall + 0.3, wall + 0.3, lid_t])
                linear_extrude(1.2)
                    rrect(inner_w - 0.6, inner_h - 0.6, max(0.5, fillet - wall));
        }
        vent_slots();
        for (c = cutouts)
            if (c[0] == "lid") lid_cutout(c[1], c[2]);
    }
}

if (part == "base") base();
else if (part == "lid") lid();
else { base(); translate([0, outer_h + 5, 0]) lid(); }
