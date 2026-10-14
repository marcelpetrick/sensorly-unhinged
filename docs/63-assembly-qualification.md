# 63 — Purchasing and assembly qualification

The BOM is a design BOM. Nonempty “Second source” text is a candidate list, not
qualification. Every specified part is currently single-sourced; that risk is
accepted only for design exploration. No purchasing substitution is authorized.
The BOM now carries this distinction explicitly and missing sourcing records
make `make bom` fail.

The TPS62841 candidate cannot supply the baseline rail. The HDC3022 and GCT USB
connector candidates require different footprints. The alternate radio module
changes the antenna system. None may be fitted automatically. For every MPN,
record source drawing/revision, pin numbering, land pattern, rotation, ratings,
availability and a signed assembly review before ordering. All fitted passives now have exact candidate MPNs. Effective capacitance at
bias and inductor saturation still require qualification records. Owner: hardware maintainer; gate: prototype order.

Validate the KiCad CPL convention against the assembler's preview, with explicit
pin-1 checks for U1–U5, J1/J2 and D1. The library coordinates are not a guarantee
of the assembler's zero-degree orientation. Record the approved preview and
as-built BOM with the board revision. A later substitute invalidates that review.

`Populate=no` BOM lines identify DNP options and are never merged with fitted
parts. CPL export excludes DNP, and fixture-only footprints are explicitly
excluded from placement files. Qty is the number of references on a line;
assemble it only when Populate is yes. These are KiCad placement coordinates;
the assembler still must approve orientation and through-hole connector handling.
The committed BOM uses LF line endings for readable, reproducible Git diffs.

J2 is now the Molex 53261-0371 PicoBlade header and the selected LP702040 pack
uses a 51021-0300 three-circuit housing. Before releasing placement data, compare
the J2 pads, pin-1 marker and 90° board rotation with Molex drawing 532610271-SD
and the assembler preview. Before any pack is plugged in, incoming inspection
must continuity-check the configured harness as `1=black/-`, `2=yellow/NTC`,
`3=red/+`; connector keying does not protect the board from a supplier-built
harness with the wrong cavity order. The pack, its configured harness and the
header family are single-source prototype risks pending the second-source gate.


## Desk review, 2026-10-12

Primary drawing and rail-capacitance review continued through 2026-10-14.

The following closes component identity and records source comparisons for both
variants. It does not close sourcing, assembly orientation or physical
qualification. `make bom` rejects fitted lines lacking an MPN, manufacturer or
alternate/accepted-risk record; DNP and fixture-only pads do not require purchase.

### Resistors

Panasonic ERJ2RKF parts below are 0402, ±1%, 0.1 W, ±100 ppm/K, as listed under
Specification on each manufacturer's product page. Values and case size match
the common model. R6 satisfies TPS62840's ±200 ppm/°C VSET requirement.

| References | Candidate MPN (manufacturer specification) |
|---|---|
| R1/R3/R4/R22 | [ERJ2RKF1002X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF1002X) |
| R2 | [ERJ2RKF3301X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF3301X) |
| R6 | [ERJ2RKF2673X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF2673X) |
| R7/R8/R9/R10/R19/R20 | [ERJ2RKF1003X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF1003X) |
| R11 | [ERJ2RKF8061X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF8061X) |
| R12 | [ERJ2RKF3011X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF3011X) |
| R13 | [ERJ2RKF4421X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF4421X) |
| R18 | [ERJ2RKF4702X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF4702X) |
| R16/R17 | [ERJ2RKF5101X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2RKF5101X) |
| R5/R21 (R21 DNP) | [ERJ2GE0R00X](https://industrial.panasonic.com/ww/products/pt/general-purpose-chip-resistors/models/ERJ2GE0R00X), 0402 zero-ohm jumper |
| R14/R15 | Vishay CRCW04022M20FKED, 0402, ±1%, ±100 ppm/K; [D/CRCW e3 document 20035, revision 14-Apr-2026, pp.1–3](https://www.vishay.com/docs/20035/dcrcwe3.pdf) identifies rating and ordering codes; use conservative standard-operation 0.063 W rating |

R11 changes from a generic 8.00 kΩ to standard 8.06 kΩ: nominal
1550/8060 = 192.3 mA; worst case 1720/(8060 × 0.99) = 215.6 mA.
This only reduces the unselected ILIM-mode limit; firmware prohibits selecting
that mode. Factors trace to [BQ2407x SLUS810N §8.5](https://www.ti.com/lit/ds/symlink/bq24074.pdf).

### Capacitors

| References | Candidate MPN | Nominal specification / primary source |
|---|---|---|
| C2/C5/C6/C12/C13/C14 | GRM155R71C104KA88D | 100 nF, 16 V, X7R, ±10%, 0402; [Murata SimSurfing](https://ds.murata.com/simsurfing/mlcc.html?oripartnumbers=%5B%22GRM155R71C104KA88J%22%5D&partnumbers=%5B%22GRM155R71C104KA88%22%5D&rgear=suaykx&rgearinfo=com), same electrical base part, paper reel D candidate pending purchasing check |
| C3/C4 | GRM155R61C105KA12D | 1 µF, 16 V, X5R, ±10%, 0402; [Murata SimSurfing](https://ds.murata.com/simsurfing/mlcc.html?oripartnumbers=%5B%22GRM155R61C105KA12D%22%5D&partnumbers=%5B%22GRM155R61C105KA12%22%5D&rgear=jomoqke&rgearinfo=au) |
| C7 | GRM188R61A475KE15D | 4.7 µF, 10 V, X5R, ±10%, 0603; [Murata reference sheet §Rated Value/Package](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM188R61A475KE15-01.pdf) |
| C1/C8/C9/C10/C11 | GRM21BR61C106KE15L | 10 µF, 16 V, X5R, ±10%, 0805; [Murata SimSurfing](https://ds.murata.com/simsurfing/mlcc.html?oripartnumbers=%5B%22GRM21BR61C106KE15L%22%5D&partnumbers=%5B%22GRM21BR61C106KE15%22%5D&rgear=jomoqke&rgearinfo=com&videoId=5970368750001) |

C3/C4's previously generic X7R requirement becomes X5R at the same nominal
capacitance, voltage and footprint; X5R's range covers the project operating
envelope. EN delay still requires a measured reset waveform. C10/C11's voltage
rating rises from 6.3 V to 16 V without changing package or capacitance; this
uses the same candidate as C9 and avoids obsolete lower-voltage candidates.
These choices apply identically to A and B.

Nominal capacitance is **not** effective capacitance. Archive the chosen MPN's
DC-bias/temperature/aging curves and compute worst-case values at actual rail
voltages before assembly approval. [TPS62840 SLVSEC6D §7.3](https://www.ti.com/lit/ds/symlink/tps62840.pdf)
requires effective CIN ≥1 µF and COUT ≥3 µF; C1's Espressif requirement and
charger bypass requirements need their own retained calculation. No capacitance
margin is claimed by this desk review. Distributor stock, pricing, package-code
availability, assembler reel handling and second-source acceptance remain open.

### Effective capacitance review

[The Murata-authored withdrawn 0603 C8 candidate electrical-characteristics sheet, May 2019](https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/GRM188R60J106ME47_5F00_EC_2D00_data.pdf), hosted by TI,
was rendered and inspected. At 3.3 V its **typical** DC-bias curve loses about 52%,
leaving approximately 4.8 µF. Applying ±20% nominal tolerance and X5R's 15%
full-range temperature allowance gives 4.8 ×0.8 ×0.85 =3.26 µF. An illustrative
10% aging reserve (engineering assumption, not a manufacturer guarantee) would
reduce this to 2.94 µF, below the regulator's 3 µF minimum.

This establishes a narrow margin requiring closure, not a qualified bound.
The sheet explicitly provides typical characteristics and requests a product
approval specification before ordering. The weak0603 candidate is withdrawn from both variants. C8 now uses the same
**GRM21BR61C106KE15L,10 µF/16 V X5R ±10%, 0805** as the charger capacitors.
[Murata's manufacturer-authored characteristic sheet hosted by RS](https://docs.rs-online.com/ea1a/0900766b813885d2.pdf)
was rendered and inspected for that exact base part: the typical curve loses
approximately 30% at 3.3 V (rounded reading). Applying 10% tolerance, 15% X5R
full-range temperature allowance and the explicit 10% illustrative aging reserve
gives 10 ×0.70 ×0.90 ×0.85 ×0.90 =**4.82 µF**, materially above 3 µF. This
supports selection but does not convert a typical curve to a guaranteed bound.
The [current manufacturer listing](https://ds.murata.com/simsurfing/mlcc.html?oripartnumbers=%5B%22GRM21BR61C106KE15L%22%5D&partnumbers=%5B%22GRM21BR61C106KE15%22%5D&rgear=jomoqke&rgearinfo=com&videoId=5970368750001)
confirms electrical identity/in-production status; the accepted approval sheet
and effective-capacitance measurement remain prerequisites for ordering.
The larger package applies to both boards and enclosure models.

TPS62840's permitted effective output capacitance is 3–40 µF, and §9.2.2.2
accepts X5R/X7R ceramics; 10 µF is a recommended nominal filter combination.
The upper 40 µF limit applies to the **total rail capacitance**. Directly
parallel parts are C1/C2/C3/C6/C8. The former 22 µF C1 gave 33.2 µF nominal
and 44.528 µF at positive tolerance plus 15% temperature allowance, exceeding
the 40 µF recommended operating maximum before bias.

C1 now uses the same **10 µF/16 V X5R ±10%,0805 GRM21BR61C106KE15L** as C8.
[Espressif's current C6 schematic checklist §Power Supply](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c6/schematic-checklist.html#power-supply)
recommends a named 10 µF capacitor at the rail/entrance, with nearby capacitors
working together. It does not establish a guarantee of 10 µF effective after
DC bias. We interpret the recommendation as a **nominal component value**;
rail collapse/startup/TX performance must still be measured at the module pins.
This shared change keeps both 0805 footprints and placements.

The new nominal total is10+0.1+1+0.1+10 = **21.2 µF**. All five candidates have
±10% nominal tolerance, so the positive sum is **23.32 µF**. Applying the
positive15% X5R/X7R full-range temperature allowance gives **26.818 µF**, below
40 µF even without DC-bias reduction. This closes the previous paper-design
upper-envelope problem without a startup bias waiver. It assumes capacitors
meet the selected nominal tolerance/dielectric specifications and DC bias does
not increase capacitance; any replacement must be reviewed on that basis.
C4 is separated by the EN pull-up and is not a directly parallel rail capacitor.

C8 alone gives 4.82 µF under the explicit typical-curve/tolerance/temperature/
aging-reserve illustration above, supporting the 3 µF minimum selection; this
is not a supplier-guaranteed effective lower bound. **EDS-16 remains open** for
review of these stated assumptions before controlled prototype order, and for
accepted effective-capacitance bounds plus measured startup/TX/load-step
stability before unrestricted operation. The prototype's scope and staged power
measurements stay explicit; this is not an unrestricted-product qualification.


C1/C3/C4/C7/C9/C10/C11 need their own accepted DC-bias/reset or bypass records;
C8's curve cannot qualify them.

### Inductor

L1 is the exact orderable **DFE201612E-2R2M=P2**. [Murata's product
specification](https://www.murata.com/products/productdetail?partno=DFE201612E-2R2M%23)
identifies 2.2 µH ±20%, DCR maximum 0.116 Ω, Isat 2.4 A at 30% inductance
reduction and temperature-rise current 1.8 A at 40 °C rise. These ratings do
not replace a load/ripple/temperature calculation.

The [Murata J(E)TE243A-0006D-01 reference specification p.5](https://search.murata.co.jp/Ceramy/image/img/P02/J(E)TE243A-0006.pdf)
was rendered and inspected: recommended pads are **0.8 ×1.8 mm**, centres
x=±0.8 mm, gap 0.8 mm, outer span 2.4 mm. The old DFE201610P footprint's
0.55 ×1.6 mm pads do not match. A correctly named local DFE201612E footprint
now uses the manufacturer's dimensions for A and B. The proposed DFE201210S
has a different 2.0 ×1.2 mm body and is not a drop-in qualified alternate.

A more conservative desk-selection comparison uses the [TI SLVSEC6D §7.5
static high-side switch-current maximum](https://www.ti.com/lit/ds/symlink/tps62840.pdf)
**1.4 A**, rather than an invented switching-frequency minimum. L1's2.4 A
Isat rating is 1.71 times this limit (1.0 A absolute headroom); its 1.8 A
40 °C-temperature-rise rating is 1.29 times it (0.4 A headroom). TI lists this
exact inductor in its application components, supporting the selection.

These comparisons are not guaranteed transient/thermal bounds: TI's current
limit excludes propagation overshoot, and 50 ns propagation delay is typical,
not a specified maximum. Murata defines Isat at **30% inductance reduction**;
initial−20% tolerance plus that full loss would give 2.2×0.8×0.7 =1.232 µH,
below TI's 1.51 µH effective-inductance minimum. With initial tolerance alone
Lmin = 1.76 µH, additional current/temperature loss must remain below approximately
14.2% to retain 1.51 µH. Measure actual peak/overshoot and thermal operation,
and retain the manufacturer's current/temperature curves or accepted bounds.
The ratings do not prove that 14.2% condition at all temperatures; no fSW minimum
or unqualified temperature margin is assumed.

### Pin and footprint record

| Part | Source comparison / remaining approval |
|---|---|
| U1 | [Espressif module datasheet v1.5 §3.2/§10.2](https://www.espressif.com/sites/default/files/documentation/esp32-c6-mini-1_mini-1u_datasheet_en.pdf): supply pin 3, EN 8, USB D−/D+ 17/18, shared GND pads and GPIO mapping are the model's source. Figure 11-1 rendered: perimeter 0.8 × 0.4 mm at 0.8 mm pitch, corner 0.7 mm square and pin 1 top-left agree. Central 1.45 mm pads at 1.975 mm pitch match the [manufacturer's original DXF](https://www.espressif.com/sites/default/files/modules-dxf/ESP32-C6-MINI-1%20PCB%20Footprint.dxf) linked from PDF p.44; coordinates were parsed from its ASCII polylines. This resolves the PDF's inconsistent 0.60 mm gap label; preserve the CAD-based geometry. Assembler zero-degree preview remains open. |
| U2 | [Sensirion SHT4x v7.3 §5.3/5.4](https://sensirion.com/resource/datasheet/sht4x): inspected figure 17 and local footprint; four 0.5 ×0.3 mm pads at x=±0.7, y=±0.4 match. Pin 1 SDA top-left, 2 SCL bottom-left, 3 VDD bottom-right, 4 VSS top-right. No central pad. §6.1 identifies **polyimide**, correcting older PTFE wording. |
| U3 | [TI SLVSEC6D §6, drawing 4224310/A](https://www.ti.com/lit/ds/symlink/tps62840.pdf): DLC 1=GND, 2=VIN, 3=MODE, 4=EN, 5=VSET, 6=STOP, 7=SW, 8=VOS; local footprint matches existing documented 0.5 mm pitch with no EP. |
| U4 | [TI SLUS810N §7, RGT0016B](https://www.ti.com/lit/ds/symlink/bq24074.pdf): pin functions checked against model, including EN2 pin 5 and EP 17 GND. Local footprint now follows [TI RGT0016B drawing 4219033/A land/stencil examples](https://www.ti.com/lit/ds/symlink/cdclvp2102.pdf), 0.6 ×0.25 mm perimeter pads, row centres ±1.4 mm and EP 1.6 mm; assembler process approval remains open; BQ24075 is not a drop-in because pin 15 is SYSOFF instead of ITERM. |
| U5 | [ST DS4260 revision 7 figure 1/§3.1](https://www.st.com/resource/en/datasheet/usblc6-2.pdf): paired I/O pads 1/6 and 3/4, GND 2, VBUS 5 agree. Dedicated ST_USBLC6_SOT23_6 follows Figure 19: all six 1.2 ×0.6 mm lands, row centres ±1.15 mm, pitch 0.95 mm. The diagram was visually corroborated using [ST-authored Doc11265 Rev 5 p.12](https://datasheet.lcsc.com/datasheet/pdf/0d3a2ab954b34651a0695e7ccf534db0.pdf?productCode=C7519), hosted by a distributor; all dimensions agree with current Rev 7 Figure 19. Supplier revision acceptance and assembler process approval remain open. |
| Q1 | [onsemi 2N7002L drawing](https://www.onsemi.com/download/data-sheet/pdf/2n7002l-d.pdf): 1=gate, 2=source, 3=drain agree with model. Case 318 Issue AU pp.4/5 inspected: dedicated local footprint follows recommended 0.95 ×0.56 mm pads, row centres ±0.975, pitch 1.90. Low-current /CE driver waveform remains a powered test. |
| J1 | [HRO product page](https://en.krhro.com/Product-Details/726.html): exact connector family identified. [HRO drawing 2020-12-08](https://datasheet.lcsc.com/datasheet/pdf/9e56b777c022540fcce7c7f67825f55e.pdf?productCode=C165948), hosted by the distributor, rendered and inspected: solder tails are rear/local−Y and mouth faces local+Y. Rotation 270° faces the left board/case opening; 90° would face inward. Recommended PCB-edge datum is 5.79 mm forward of the NPTH row; with local row −2.6, origin x=3.19 aligns the left edge. Signal numbering/pitch agrees; generic KiCad pads/holes include small solder/drill allowances. Supplier drawing revision acceptance, hole fit and through-hole solder process remain open; generic clones are prohibited. |
| J2 | [Molex drawing 532610271-SD](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/532/53261/532610271_sd.pdf): [Molex-authored drawing 532610001-SD rev E, 2023-07-24](https://robu.in/wp-content/uploads/2025/06/C293630.pdf), hosted by a distributor, rendered and inspected: PCB-view pin 1 right with solder tails downward becomes local pin 1 left with tails upward after 180° rotation. 0.8 ×1.6 mm signal lands at 1.25 pitch and 2.1 ×3.0 mm hold-downs match. Current manufacturer URL serves rev E1 (obsolete part-number removal); ordering must retain the accepted revision. Assembler rotation and configured harness cavity continuity remain open. |
| D1 | [Kingbright DSAB0301 V.21B package/polarity drawing](https://www.kingbright.com/attachments/file/psearch/000/00/20160808bak/KP-1608SGC%28Ver.21B%29.pdf): pages 1/4 rendered and inspected: manufacturer pin 1=A, pin 2=K. Dedicated local symbol/footprint use that numbering, 0.8 mm square lands, 0.85 mm gap (centres ±0.825). The cathode mark is on pin 2/right; active-low LED_N goes to pin 2. Assembler orientation and low-current visibility remain open. |
| SW1 | [Panasonic EVQPUJ02K reference specification 20160114 p.2](https://industrial.panasonic.com/cdbs/www-data/pdf/ATK0000/ATK0000COS4319.pdf): drawing inspected visually. Local pads 1.55 ×1.0 mm at x=±2.625, y=±0.85 match the recommended pattern rotated 90°. Paired terminals map to common upper/lower rows. Local pad angle 180° does not change rectangular pad extents. Side-operated body height 1.65 +0.3/−0.1 mm means **1.95 mm maximum**; lid removal gives service access. The generic top-button alternative is removed. |

A signed assembler preview and an as-built record are still required for every
polarized part. The above comparison is engineering desk evidence and cannot
stand in for a supplier's production drawing or an approved physical first article.

The bottom silkscreen identifies the battery housing cavities explicitly as
`J2 1- 2T 3+`. The old horizontal, unnumbered `- T +` legend was ambiguous
with J2's vertically rotated row. Cavity numbers refer to the manufacturer's
drawing; the printed legend never substitutes for pack continuity inspection.
