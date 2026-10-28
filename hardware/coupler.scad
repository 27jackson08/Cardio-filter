// CardioFilter microphone coupler
// Joins the stethoscope tubing to a 9.7 mm electret capsule and gives the
// capsule a small sealed air chamber so chest-wall vibration reaches it as
// pressure, not as handling noise.
//
// Print in PETG (rigid) or TPU (quieter; recommended). 0.2 mm layers, 100 % infill.

$fn = 96;

tube_id        = 6.0;   // inner diameter of the stethoscope tubing (mm)
tube_wall      = 1.5;   // tubing wall thickness (mm)
barb_len       = 12;    // length of the barbed inlet (mm)
chamber_d      = 8.0;   // air chamber diameter in front of the capsule (mm)
chamber_h      = 3.0;   // air chamber height (mm)
capsule_d      = 9.9;   // electret capsule diameter + 0.2 mm clearance (mm)
capsule_h      = 4.7;   // capsule height (mm)
body_wall      = 2.5;   // wall around the capsule pocket (mm)
cable_slot_w   = 2.4;   // slot for the two microphone leads (mm)

body_d = capsule_d + 2 * body_wall;
body_h = barb_len + chamber_h + capsule_h + body_wall;

module barb() {
    difference() {
        union() {
            cylinder(d = tube_id + 0.4, h = barb_len);
            for (i = [0 : 2])
                translate([0, 0, 2 + i * 3.5])
                    cylinder(d1 = tube_id + 1.4, d2 = tube_id + 0.4, h = 2);
        }
        translate([0, 0, -1]) cylinder(d = tube_id - 2.5, h = barb_len + 2);
    }
}

module body() {
    difference() {
        translate([0, 0, barb_len]) cylinder(d = body_d, h = body_h - barb_len);
        // air chamber
        translate([0, 0, barb_len - 0.01]) cylinder(d = chamber_d, h = chamber_h + 0.02);
        // capsule pocket, open at the back so the capsule press-fits
        translate([0, 0, barb_len + chamber_h]) cylinder(d = capsule_d, h = capsule_h + body_wall + 1);
        // lead slot
        translate([-cable_slot_w / 2, 0, barb_len + chamber_h + capsule_h - 1])
            cube([cable_slot_w, body_d, body_wall + 2]);
        // sound path from barb into chamber
        translate([0, 0, barb_len - 2]) cylinder(d = tube_id - 2.5, h = 3);
    }
}

barb();
body();
