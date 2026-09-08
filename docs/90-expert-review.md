# 90 — Expert review and corrective work

Reviewed 2026-09-08 against `038b3ca`. Ranked by consequence, then likelihood.
This is a prototype design review, not a declaration of electrical safety,
manufacturability, RF performance, or measured accuracy.

The strongest idea is the controlled comparison of compactness against thermal
isolation. A shared electrical model, vendored libraries, explicit requirements,
and generated layouts make design intent unusually inspectable. Keep those.
The central weakness is that successful generation is too easily confused with
a working instrument. Neither board is connected completely, and several
important physical assumptions contradict the generated geometry.

| Rank | Severity / domain | Finding and evidence at review baseline | Corrective work |
|---|---|---|---|
| 1 | Critical / battery | TMR is grounded, disabling safety timers while EDS claims they are enabled. TS is fixed and CE grounded; enclosed charging is called acceptable without pack qualification. | Leave TMR open for default timers; remove unsupported safety acceptance. Pack-temperature protection remains a release blocker. |
| 2 | Critical / manufacturing | Both boards have 58 unconnected items, but `make outputs` and CI publish a “fab-package”. | Separate draft exports from a release target that rejects unfinished routing and unresolved qualification. Routing remains open. |
| 3 | High / electrical | D1 anode (pin 2) is grounded; its cathode reaches a GPIO through R2. The active-low LED cannot work. | Wire supply → R2 → anode, cathode → GPIO; regenerate both boards and schematic. |
| 4 | High / electrical | Folding `EN_REG` into `VSYS` puts both R5 terminals on one net. Lifting R5 cannot disable U3. | Preserve the enable net and test resistor isolation. |
| 5 | High / power integrity | Nominal 3.0 V is the ESP32 module's minimum, leaving no tolerance or load-transient margin. EDS describes dropout as graceful. | Use 3.3 V as the baseline; reserve 3.0 V for controlled characterization and require measured rail limits. |
| 6 | High / USB power | R11 permits ~502 mA independent of source advertisement or USB configuration. The documentation implies any USB source is suitable. | Specify the supported bench source and require source-current qualification before release; host negotiation remains open. |
| 7 | High / mechanical | The lid locating lip is a solid plate and pillars start at `lid_total`, extending 1.2 mm too far when assembled. | Use a perimeter lip and measure pillar reach from the lid seating surface. |
| 8 | High / mechanical | B's divider is centred at y=33.5, overlapping the full-width body ending at y=34 while only a neck-width slot is cut. | Place the divider within the actual neck, with a geometric non-interference check. |
| 9 | High / product fit | The 35×30×5 mm planning battery does not fit either permitted bay; volume-derived mAh is presented as available capacity. | Check the actual planning dimensions and stop inferring purchasable cell capacity; selected pack/retention remain open. |
| 10 | High / battery life | The >3-month requirement has no numerical energy allocation and the enclosure cannot hold the assumed capacity. | Add a reproducible battery-side charge budget and feasible-upload calculation. |
| 11 | High / thermal model | The model assumes four full-width copper planes to A's sensor, but `_zones` removes all pours around it; the README promises “57x less conduction”. | Label the slab calculation as a hypothetical bound, derive shared constants, remove predicted accuracy claims. |
| 12 | High / experimental design | One-minute MQTT logging changes the default duty cycle; reference placement is geometrically inconsistent; rail subgroups are pooled; decision branches overlap. | Define acquisition independently of upload, matched positions/rails, reference uncertainty, and an ordered inconclusive-capable decision gate. |
| 13 | High / firmware and UX | F-03…F-12 have no implementation; stale, charging-biased or unauthenticated readings have no executable product contract. | Define an implementation/acceptance contract and expose missing firmware as a release blocker. Firmware and device testing remain open. |
| 14 | High / sourcing | `bom.py` calls every nonempty alternate “qualified”, including U3's incompatible TPS62841 and alternative footprints. | Distinguish candidates from qualification and report single-source risks honestly. |
| 15 | High / assembly | BOM grouping ignores `Part.dnp`; CPL export does not explicitly exclude DNP/fixture pads. | Carry population state through BOM and filter placement exports. |
| 16 | High / verification | DRC accepts entire warning types and missing parity as success. This machine reports 12/14 accepted warnings versus README's 5/4. | Validate report structure and review exact warning identities rather than unlimited categories. |
| 17 | High / build reliability | Shell loops in `outputs`, `mech`, `render`, and `drc` can conceal earlier tool failures behind a final successful command. | Make failures propagate, retain diagnostics, and test failed-tool behavior. |
| 18 | High / reproducibility | Filled-board cache excludes schematic/library dependencies; `make -j all` may run generation and checks concurrently. | Declare dependencies and serialize mutation-dependent aggregate builds. |
| 19 | High / thermal rules | B's neck rule allows every Power net, including VBAT/VBUS/VSYS; the width rule covers only SDA/SCL. | Limit the neck to the four named nets and constrain power traces there too. |
| 20 | High / model integrity | Net-to-pad dictionaries silently overwrite duplicate assignments; unknown pads and shorted resistor terminals can reach generated files. | Validate connectivity before writing artifacts, with fault-injection regression tests. |

Repository corrections can be verified here. Battery safety, finished routing,
RF/rail measurements, physical enclosure fit, and firmware behavior cannot be
closed by a document or a green generator check. The final disposition below
will record what was actually verified.

Model integrity: `tools/boardgen/validate.py` runs before schematic generation.
Fault-injection tests reject duplicate references, multiply assigned pins,
unknown pads and bypassed passives, including the original R5 regression.

Build failure propagation: Make recipes use `-eu` and delete failed targets.
Mesh export retains OpenSCAD diagnostics; optional PNG previews are explicitly
`make mech-render` so a headless mesh gate needs no graphics display.
Filled-board prerequisites include schematic, symbols, footprints, project rules
and the Makefile. Aggregate builds are serialized even with `make -j` because
generation writes inputs to subsequent checks.
DRC development waivers are capped per violation type and item UUID set in
`hardware/drc-budget.json`; missing parity, omitted severity checks, ignored
checks and reports for another board fail. Release requires zero warnings.
KiCad 10 disables five checks by default; the generated project enables them
explicitly so the report cannot silently omit those checks.
Mesh verification rejects missing/nonfinite files and reads both ASCII and
binary STL; all three axes, including pillar height, are checked.
Isolated build tests inject failing KiCad/OpenSCAD executables and verify that
the first failed export terminates its recipe without a success message.

Verification exposed another model-integrity failure under finding 20: J1's four
SH pads have different lengths, but the parser kept only the last length. After
the LED correction this caused a real 0.18 mm clearance on B against a 0.20 mm
rule. The parser now conservatively retains the largest repeated-pad dimensions;
the library land pattern itself is unchanged.
`make mech` also renders the seated lid/base intersection for each variant;
it accepts only OpenSCAD's explicit empty-intersection result, not a generic
export failure. This checks the corrected lid/divider relationship in 3D.
Enabling the default-ignored via-centering check exposed a 0.1 mm CHG_N stub
past a via centre. The generator trims only collinear endpoints already wholly
inside same-net via copper; it neither moves vias nor redirects other routes.
`make test-kicad` injects VBAT and widened GND tracks into scratch copies of B
and requires KiCad to report the corresponding island-rule violations.
The routing audit also found five physical B neck traces: C6 ground detoured to
the main board. C6 taps are now confined to the island, and every neck cut must
contain exactly four conductors. This corrects finding 19 beyond net-class rules.
The injected tracks use B.Cu to avoid KiCad associating a touching test track
with an existing F.Cu sensor net; both tests assert the actual named DRC rule.
