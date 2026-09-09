# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Single source of truth for the ENV sensor electrical design.

Everything here is common to Variant A and Variant B: same parts, same values,
same netlist, same design rules.  Only `variants.py` differs between the boards.

Values and pin numbers trace to docs/30-electrical-design-spec.md.
"""
from dataclasses import dataclass, field

FP = "sensorly"          # project footprint library nickname

R0402 = f"{FP}:R_0402_1005Metric"
R0603 = f"{FP}:R_0603_1608Metric"
C0402 = f"{FP}:C_0402_1005Metric"
C0603 = f"{FP}:C_0603_1608Metric"
C0805 = f"{FP}:C_0805_2012Metric"


@dataclass
class Part:
    ref: str
    value: str
    footprint: str
    mpn: str = ""
    manufacturer: str = ""
    desc: str = ""
    dnp: bool = False
    exclude_from_bom: bool = False
    alt: str = ""          # candidate only; see BOM sourcing status and release gate


# --------------------------------------------------------------------------
# Bill of materials
# --------------------------------------------------------------------------
PARTS = [
    # --- 01 ESP32 -----------------------------------------------------------
    Part("U1", "ESP32-C6-MINI-1-N4", f"{FP}:ESP32-C6-MINI-1", "ESP32-C6-MINI-1-N4",
         "Espressif", "Wi-Fi 6 / BLE 5.3 / 802.15.4 module, 4 MB flash",
         alt="ESP32-C6-MINI-1U-N4 (u.FL, needs external antenna)"),
    Part("C1", "22uF/6.3V X5R", C0805, desc="ESP32 bulk, >=10uF required by Espressif"),
    Part("C2", "100nF/16V X7R", C0402, desc="ESP32 HF decoupling"),
    Part("C3", "1uF/16V X7R", C0402, desc="ESP32 mid-frequency decoupling"),
    Part("R1", "10k 1%", R0402, desc="EN pull-up"),
    Part("C4", "1uF/16V X7R", C0402, desc="EN RC delay (~10 ms)"),
    Part("SW1", "SW_PROV", f"{FP}:Panasonic_EVQPUJ_EVQPUA", "EVQ-PUJ02K", "Panasonic",
         "provisioning / boot button", alt="TS-1187A-B-A-B (generic 3.5x2.9)"),
    Part("C5", "100nF/16V X7R", C0402, desc="SW1 debounce"),
    Part("D1", "LED_GREEN", f"{FP}:LED_0603_1608Metric", "KP-1608SGC", "Kingbright",
         "status LED, active low", alt="any 0603 green LED, Vf < 2.4 V at 0.5 mA"),
    Part("R2", "3k3 1%", R0402, desc="LED series, ~0.5 mA"),

    # --- 02 Sensor ----------------------------------------------------------
    Part("U2", "SHT45-AD1F", f"{FP}:Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad",
         "SHT45-AD1F-R2", "Sensirion",
         "+-0.1 C / +-1.0 %RH, integrated PTFE filter membrane, I2C 0x44",
         alt="SHT40-AD1B (cost-down, same footprint) / HDC3022 (2nd source, alt FP)"),
    Part("C6", "100nF/16V X7R", C0402, desc="sensor VDD decoupling - ONLY passive on the island"),
    Part("R3", "10k 1%", R0402, desc="SDA pull-up - main board, never on the island"),
    Part("R4", "10k 1%", R0402, desc="SCL pull-up - main board, never on the island"),

    # --- 03 Regulator -------------------------------------------------------
    Part("U3", "TPS62840DLC", f"{FP}:TI_DLC0008B_VSON-HR-8_2x1.5mm_P0.5mm", "TPS62840DLCR",
         "Texas Instruments", "750 mA buck, 60 nA Iq, 16 VSET-selectable outputs",
         alt="TPS62841DLCR (lower Vout range - NOT drop-in for 3.0 V)"),
    Part("L1", "2.2uH", f"{FP}:L_Murata_DFE201610P", "DFE201612E-2R2M", "Murata",
         "2.2 uH, DCR 116 mOhm - datasheet SLVSEC6D Table 4",
         alt="DFE201210S-2R2M (thinner, same land pattern family)"),
    Part("C7", "4.7uF/10V X5R", C0603, desc="buck input - 4.7 uF required at VIN"),
    Part("C8", "10uF/6.3V X5R", C0603, desc="buck output"),
    Part("R5", "0R", R0402, desc="EN tie - a resistor so EN can be lifted to measure Iq"),
    Part("R6", "267k 1%", R0402, desc="VSET -> 3.30 V. Characterization only: 52k3 -> 3.00 V"),

    # --- 04 Charger ---------------------------------------------------------
    Part("U4", "BQ24074RGTR", f"{FP}:VQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm", "BQ24074RGTR",
         "Texas Instruments", "1S Li-ion charger with power path, NTC, status outputs",
         alt="BQ24075RGTR (same pinout, different DPPM/timer defaults)"),
    Part("Q1", "2N7002", f"{FP}:SOT-23", "2N7002LT1G", "onsemi",
         "low-side /CE driver; VBUS pull-up keeps charging disabled at power-up",
         alt="2N7002,215 (Nexperia; same G-S-D pinout and SOT-23 land pattern)"),
    Part("R7", "100k 1%", R0402,
         desc="Q1 gate pull-down: charge enable defaults low/off"),
    Part("R8", "100k 1%", R0402,
         desc="EN1 pull-down: USB100 is the fail-safe reset/unconfigured state"),
    Part("R9", "100k 1%", R0402, desc="/PGOOD pull-up"),
    Part("R10", "100k 1%", R0402, desc="/CHG pull-up"),
    Part("R11", "8k00 1%", R0402,
         desc="ILIM fallback: <=217 mA incl. KILIM and resistor tolerance; mode not selected"),
    Part("R12", "3k01 1%", R0402,
         desc="ITERM: 0.03*3010/4420 = 20.4 mA nominal"),
    Part("R13", "4k42 1%", R0402,
         desc="ISET: 890/4420 = 201 mA nominal; <=223 mA worst case"),
    Part("R18", "47k 1%", R0402,
         desc="/CE pull-up to VBUS: charger disabled before MCU power-up"),
    Part("C9", "10uF/16V X5R", C0805, desc="charger IN bypass"),
    Part("C10", "10uF/6.3V X5R", C0805, desc="charger OUT bypass"),
    Part("C11", "10uF/6.3V X5R", C0805, desc="charger BAT bypass"),
    Part("C12", "100nF/16V X7R", C0402, desc="charger IN HF bypass"),

    # --- 05 USB -------------------------------------------------------------
    Part("J1", "USB-C 16P", f"{FP}:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "TYPE-C-31-M-12",
         "HRO", "USB-C receptacle, sink only, TH mounting lugs",
         alt="GCT USB4085 (different land pattern - do not swap without relayout)"),
    Part("U5", "USBLC6-2SC6", f"{FP}:SOT-23-6", "USBLC6-2SC6", "STMicroelectronics",
         "USB ESD protection array", alt="PRTR5V0U2X"),
    Part("R16", "5k1 1%", R0402, desc="CC1 pull-down - UFP advertisement"),
    Part("R17", "5k1 1%", R0402, desc="CC2 pull-down - separate resistor, never shared"),
    Part("C14", "100nF/16V X7R", C0402, desc="VBUS local"),

    # --- 06 Battery ---------------------------------------------------------
    Part("J2", "Molex PicoBlade 3P",
         f"{FP}:Molex_PicoBlade_53261-0371_1x03-1MP_P1.25mm_Horizontal",
         "53261-0371", "Molex",
         "LP702040 pack: pin 1 GND(-), pin 2 PACK_TS/103AT-2, pin 3 VBAT(+)",
         alt="single-sourced connector family; accepted for prototypes pending pack qualification"),
    Part("R14", "2M2 1%", R0402, desc="VBAT divider top"),
    Part("R15", "2M2 1%", R0402, desc="VBAT divider bottom - 0.95 uA continuous, see EDS S6"),
    Part("C13", "100nF/16V X7R", C0402, desc="ADC filter"),

    # --- 07 Mechanical ------------------------------------------------------
    # No mounting holes in Rev 1, deliberately: M-04 forbids metal fasteners
    # near the antenna, a nylon M2 boss costs ~19 mm2 of a 1020 mm2 board, and
    # the printed enclosure registers the board on ribs against the USB-C and
    # connector cut-outs. Revisit at Rev 2 if that retention proves unreliable.
]

# Test pads (bottom side, 2.54 mm grid) - EDS section 9
TESTPADS = [
    ("TP1", "GND"), ("TP2", "VBUS"), ("TP3", "VSYS"), ("TP4", "+3V0"),
    ("TP5", "VBAT"), ("TP6", "EN"), ("TP7", "BTN_PROV"), ("TP8", "UART_TX"),
    ("TP9", "UART_RX"), ("TP10", "USB_DP"), ("TP11", "USB_DM"), ("TP12", "SDA"),
    ("TP13", "SCL"), ("TP14", "CHG_N"), ("TP15", "PG_N"), ("TP16", "TEST_MODE"),
    ("TP17", "GND"),
]
for _ref, _net in TESTPADS:
    PARTS.append(Part(_ref, _net, f"{FP}:TestPad_D1.5mm_Bottom",
                      exclude_from_bom=True, desc="pogo test pad, bottom side"))

PART_BY_REF = {p.ref: p for p in PARTS}

# --------------------------------------------------------------------------
# Netlist:  net name -> [(ref, pad), ...]
# ESP32 module pin numbers are from datasheet v1.5 Table 3-1.
# --------------------------------------------------------------------------
ESP_GND_PADS = ["1", "2", "11", "14"] + [str(n) for n in range(36, 54)]

NETS = {
    "GND": (
        [("U1", p) for p in ESP_GND_PADS]
        + [("U2", "4"), ("U3", "1"), ("U3", "3"), ("U3", "6"),
           ("U4", "8"), ("U4", "17"), ("U4", "5"), ("Q1", "2"),
           ("U5", "2"),
           ("J1", "A1"), ("J1", "A12"), ("J1", "B1"), ("J1", "B12"), ("J1", "SH"),
           ("J2", "1"),
           ("C1", "2"), ("C2", "2"), ("C3", "2"), ("C4", "2"), ("C5", "2"),
           ("C6", "2"), ("C7", "2"), ("C8", "2"), ("C9", "2"), ("C10", "2"),
           ("C11", "2"), ("C12", "2"), ("C13", "2"), ("C14", "2"),
           ("R7", "2"), ("R8", "2"), ("R11", "2"), ("R12", "2"),
           ("R13", "2"),
           ("R15", "2"), ("R16", "2"), ("R17", "2"),
           ("SW1", "2"),
           ("TP1", "1"), ("TP17", "1")]
    ),
    "+3V0": [("U1", "3"), ("U2", "3"), ("U3", "8"),
             ("C1", "1"), ("C2", "1"), ("C3", "1"), ("C6", "1"), ("C8", "1"),
             ("R1", "1"), ("R3", "1"), ("R4", "1"), ("R9", "1"), ("R10", "1"),
             ("R2", "1"), ("TP4", "1")],
    "VSYS": [("U3", "2"), ("U4", "10"), ("U4", "11"), ("C7", "1"), ("C10", "1"),
             ("R5", "1"), ("TP3", "1")],
    "VBAT": [("U4", "2"), ("U4", "3"), ("J2", "3"), ("C11", "1"), ("R14", "1"),
             ("TP5", "1")],
    "VBUS": [("U4", "13"), ("U5", "5"), ("J1", "A4"), ("J1", "A9"),
             ("J1", "B4"), ("J1", "B9"), ("C9", "1"), ("C12", "1"), ("C14", "1"),
             ("R18", "2"), ("TP2", "1")],
    "SW_L": [("U3", "7"), ("L1", "1")],
    "L_OUT": [("L1", "2")],            # merged into +3V0 below
    "EN": [("U1", "8"), ("R1", "2"), ("C4", "1"), ("TP6", "1")],
    "EN_REG": [("U3", "4"), ("R5", "2")],
    "VSET": [("U3", "5"), ("R6", "1")],
    "VSET_GND": [("R6", "2")],         # merged into GND below
    "SDA": [("U1", "15"), ("U2", "1"), ("R3", "2"), ("TP12", "1")],
    "SCL": [("U1", "16"), ("U2", "2"), ("R4", "2"), ("TP13", "1")],
    "VBAT_SENSE": [("U1", "5"), ("R14", "2"), ("R15", "1"), ("C13", "1")],
    "CHG_N": [("U1", "29"), ("U4", "9"), ("R10", "2"), ("TP14", "1")],
    "PG_N": [("U1", "28"), ("U4", "7"), ("R9", "2"), ("TP15", "1")],
    # Vendored KiCad LED symbol/0603 footprint: pin 1 K, pin 2 A.
    "LED_N": [("U1", "25"), ("D1", "1")],
    "LED_A": [("R2", "2"), ("D1", "2")],
    "BTN_PROV": [("U1", "23"), ("SW1", "1"), ("C5", "1"), ("TP7", "1")],
    "USB_DM": [("U1", "17"), ("U5", "1"), ("U5", "6"), ("J1", "A7"), ("J1", "B7"),
               ("TP11", "1")],
    "USB_DP": [("U1", "18"), ("U5", "3"), ("U5", "4"), ("J1", "A6"), ("J1", "B6"),
               ("TP10", "1")],
    "UART_TX": [("U1", "31"), ("TP8", "1")],
    "UART_RX": [("U1", "30"), ("TP9", "1")],
    "TEST_MODE": [("U1", "26"), ("TP16", "1")],
    # VBUS pulls /CE high before the charger reaches its operating threshold.
    # Q1 isolates the 5 V domain; firmware may enable only after NTC validation.
    "CHARGE_EN_N": [("U4", "4"), ("Q1", "3"), ("R18", "1")],
    "CHARGE_ENABLE": [("U1", "24"), ("Q1", "1"), ("R7", "1")],
    # IO21 may assert this only after USB enumeration/configuration. R8 keeps
    # the charger in its hardware USB100 state during reset, boot and faults.
    "USB_ISEL": [("U1", "27"), ("U4", "6"), ("R8", "1")],
    "CC1": [("J1", "A5"), ("R16", "1")],
    "CC2": [("J1", "B5"), ("R17", "1")],
    # U1.IO3 is ADC1_CH3. Firmware measures the same 103AT-2 that feeds the
    # charger's independent TS window before it may assert CHARGE_ENABLE.
    "PACK_TS": [("U1", "6"), ("U4", "1"), ("J2", "2")],
    "ILIM": [("U4", "12"), ("R11", "1")],
    "ITERM": [("U4", "15"), ("R12", "1")],
    "ISET": [("U4", "16"), ("R13", "1")],
}
# fold the helper nets into their real ones
NETS["+3V0"] += NETS.pop("L_OUT")
NETS["GND"] += NETS.pop("VSET_GND")

# --------------------------------------------------------------------------
# Net classes / design rules  (AGENTS.md: rules live in the model, not in a GUI)
# --------------------------------------------------------------------------
NETCLASSES = {
    "Default":  dict(track=0.25, clearance=0.15, via=0.6, drill=0.3,
                     nets=[]),
    "Power":    dict(track=0.50, clearance=0.20, via=0.8, drill=0.4,
                     nets=["VBUS", "VSYS", "VBAT", "+3V0", "GND"]),
    "Switch":   dict(track=0.60, clearance=0.25, via=0.8, drill=0.4,
                     nets=["SW_L"]),
    "USB":      dict(track=0.25, clearance=0.20, via=0.5, drill=0.3,
                     nets=["USB_DP", "USB_DM"], diff_pair_width=0.25,
                     diff_pair_gap=0.20),
    # The whole point of Variant B.  0.15 mm is not a routing convenience,
    # it is the dominant term in the sensor island's thermal conductance.
    "SensorIsland": dict(track=0.15, clearance=0.15, via=0.4, drill=0.2,
                         nets=["SDA", "SCL"]),
}

STACKUP = [
    ("F.Cu",   "copper",     0.035, "signal + components"),
    ("dielectric 1", "core", 0.200, "prepreg"),
    ("In1.Cu", "copper",     0.035, "solid GND reference"),
    ("dielectric 2", "core", 1.065, "core"),
    ("In2.Cu", "copper",     0.035, "power + slow signals"),
    ("dielectric 3", "core", 0.200, "prepreg"),
    ("B.Cu",   "copper",     0.035, "limited signals + GND, test pads"),
]

BOARD_THICKNESS = 1.6
COPPER_LAYERS = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
