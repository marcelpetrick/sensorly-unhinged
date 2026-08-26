# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rebuild hardware/lib/sensorly.kicad_sym from the upstream KiCad symbol library.

The result is committed (like the footprints) so a checkout needs no system
KiCad libraries. This tool documents and reproduces how it was built.

    git clone --depth 1 https://gitlab.com/kicad/libraries/kicad-symbols.git
    python -m tools.mksymlib /path/to/kicad-symbols

Two things it does that a plain copy cannot:

* **Flattens `extends`.** USBLC6-2SC6 is defined as an override of USBLC6-2P6.
  An unresolved `extends` inside a schematic's lib_symbols block makes KiCad
  report a library mismatch, so the parent's geometry is inlined and only the
  child's own properties are kept.
* **Adds TPS62840DLC**, which upstream does not carry. Pin numbers and names are
  from TI SLVSEC6D section 6 (Pin Functions), DLC / SON-8 column.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "hardware" / "lib" / "sensorly.kicad_sym"

VENDORED = [
    ("RF_Module", "ESP32-C6-MINI-1"),
    ("Sensor_Humidity", "SHT4x"),
    ("Battery_Management", "BQ24074RGT"),
    ("Connector", "USB_C_Receptacle_USB2.0_16P"),
    ("Connector_Generic_MountingPin", "Conn_01x02_MountingPin"),
    ("Connector", "TestPoint"),
    ("Device", "R"), ("Device", "C"), ("Device", "L"), ("Device", "LED"),
    ("Switch", "SW_Push"),
    ("power", "GND"), ("power", "+3V0"), ("power", "VBUS"), ("power", "PWR_FLAG"),
]
# child -> parent, flattened on the way in
FLATTEN = [("Power_Protection", "USBLC6-2SC6", "USBLC6-2P6")]


def block(text: str, head: str) -> str:
    i = text.find("(" + head)
    j, d = i, 0
    while j < len(text):
        if text[j] == "(":
            d += 1
        elif text[j] == ")":
            d -= 1
            if d == 0:
                break
        j += 1
    return text[i:j + 1]


def read(src: Path, lib: str, name: str) -> str:
    return block((src / f"{lib}.kicad_symdir" / f"{name}.kicad_sym").read_text(),
                 f'symbol "{name}"')


def properties(body: str) -> dict[str, str]:
    out = {}
    i = 0
    while True:
        i = body.find('(property "', i)
        if i < 0:
            return out
        b = block(body[i:], 'property "')
        out[re.match(r'\(property "([^"]+)"', b).group(1)] = b
        i += len(b)


def flatten(src: Path, lib: str, child: str, parent: str) -> str:
    pbody = read(src, lib, parent)
    cprops = properties(read(src, lib, child))
    body = pbody.replace(f'(symbol "{parent}"', f'(symbol "{child}"', 1)
    body = body.replace(f'(symbol "{parent}_', f'(symbol "{child}_')
    for name, blk in cprops.items():
        existing = properties(body).get(name)
        if existing:
            body = body.replace(existing, blk, 1)
    return body


def pin(ptype, x, y, ang, name, num, ind="\t\t\t") -> str:
    e = (f"{ind}\t\t(effects\n{ind}\t\t\t(font\n{ind}\t\t\t\t(size 1.27 1.27)\n"
         f"{ind}\t\t\t)\n{ind}\t\t)\n")
    return (f"{ind}(pin {ptype} line\n{ind}\t(at {x} {y} {ang})\n"
            f"{ind}\t(length 2.54)\n{ind}\t(name \"{name}\"\n{e}{ind}\t)\n"
            f"{ind}\t(number \"{num}\"\n{e}{ind}\t)\n{ind})")


def prop(name, value, x, y, hide=False, ind="\t\t") -> str:
    h = f"\n{ind}\t(hide yes)" if hide else ""
    return (f'{ind}(property "{name}" "{value}"\n{ind}\t(at {x} {y} 0)\n'
            f"{ind}\t(show_name no)\n{ind}\t(do_not_autoplace no){h}\n"
            f"{ind}\t(effects\n{ind}\t\t(font\n{ind}\t\t\t(size 1.27 1.27)\n"
            f"{ind}\t\t)\n{ind}\t)\n{ind})")


def tps62840() -> str:
    """TI SLVSEC6D S6, DLC (SON-8): 1 GND, 2 VIN, 3 MODE, 4 EN, 5 VSET,
    6 STOP, 7 SW, 8 VOS. No exposed pad on this package."""
    pins = [pin("power_in", -12.7, 7.62, 0, "VIN", "2"),
            pin("power_in", 0, -15.24, 90, "GND", "1"),
            pin("input", -12.7, 2.54, 0, "EN", "4"),
            pin("input", -12.7, 0, 0, "MODE", "3"),
            pin("input", -12.7, -2.54, 0, "STOP", "6"),
            pin("input", -12.7, -7.62, 0, "VSET", "5"),
            pin("output", 12.7, 7.62, 180, "SW", "7"),
            pin("input", 12.7, 2.54, 180, "VOS", "8")]
    return "\n".join([
        '\t(symbol "TPS62840DLC"',
        "\t\t(exclude_from_sim no)", "\t\t(in_bom yes)", "\t\t(on_board yes)",
        "\t\t(in_pos_files yes)", "\t\t(duplicate_pin_numbers_are_jumpers no)",
        prop("Reference", "U", 0, 13.97),
        prop("Value", "TPS62840DLC", 0, -15.24),
        prop("Footprint", "sensorly:TI_DLC0008B_VSON-HR-8_2x1.5mm_P0.5mm",
             0, -17.78, True),
        prop("Datasheet", "https://www.ti.com/lit/ds/symlink/tps62840.pdf",
             0, -20.32, True),
        prop("Description", "750 mA step-down converter, 60 nA Iq, 1.8-6.5 Vin, "
             "16 VSET-selectable outputs, SON-8", 0, 0, True),
        prop("ki_keywords", "buck step-down regulator low Iq DCS-Control",
             0, 0, True),
        prop("ki_fp_filters", "SON*2x1.5mm*P0.5mm*", 0, 0, True),
        '\t\t(symbol "TPS62840DLC_1_1"',
        "\t\t\t(rectangle", "\t\t\t\t(start -10.16 10.16)", "\t\t\t\t(end 10.16 -12.7)",
        "\t\t\t\t(stroke", "\t\t\t\t\t(width 0.254)", "\t\t\t\t\t(type default)",
        "\t\t\t\t)", "\t\t\t\t(fill", "\t\t\t\t\t(type background)", "\t\t\t\t)",
        "\t\t\t)", *pins, "\t\t)", "\t\t(embedded_fonts no)", "\t)"])


def main(argv):
    src = Path(argv[0])
    out = ["(kicad_symbol_lib", "\t(version 20251024)",
           '\t(generator "sensorly-boardgen")', '\t(generator_version "10.0")']
    for lib, name in VENDORED:
        out.append("\t" + read(src, lib, name).replace("\n\t", "\n\t\t"))
    for lib, child, parent in FLATTEN:
        out.append("\t" + flatten(src, lib, child, parent).replace("\n\t", "\n\t\t"))
    out.append(tps62840())
    out.append(")")
    OUT.write_text("\n".join(out) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: "
          f"{len(VENDORED) + len(FLATTEN) + 1} symbols")


if __name__ == "__main__":
    main(sys.argv[1:])
