# 01 — Recovery and completion plan

Audit started 2026-09-18 at `d50053b`. This is the executable work order for
the [master plan](00-plan.md), not a manufacturing approval. The starting tree
was clean. GitHub had no issues; task history lives in the master plan,
[expert review](90-expert-review.md), EDS Open table and release manifest.
The latest Hardware Quality run at the starting commit passed.

## What was done, and what remains

The original task is one shared electrical platform, two layouts and enclosures,
5 + 5 prototypes, a measured A/B decision, then a revised 20-unit series.
The earlier review corrected circuit/model/build defects and added release
gates. The subsequent pack/USB change selected a protected three-wire pack,
added temperature sensing and default-disabled charge control, and resized
both cases. CI was then installed and repaired. These changes did not finish
routing, implement firmware or qualify the product.

At the audit baseline, both boards were incomplete (documented A: 59, B: 60
unconnected items); all seven qualification evidence fields were null.
`firmware/`, `production/` and `measurements/` did not exist. Thus “phase 6” is
a description of active layout work, not proof that every earlier phase gate
has closed: the EDS/library review checklist and exact purchasing BOM remain
open. The maintainer has confirmed that no physical boards, pack samples or measurements
exist outside the repository either.

## Historical implementation checkpoint — 2026-09-18

The original audit below is retained as history. Since it, the repository gained:

- a compiled ESP32-C6 bring-up application, pinned ESP-IDF build and CI;
- host-tested SHT45 CRC/error handling, ADC reporting, default-low charge/current
  control, watchdog and timer sleep, with radio/charging/USB500 disabled;
- immutable serial-linked fixture-log capture with chip/image checks and failure
  retention; no records are presented as real device measurements;
- corrected spatial sensor-via rules, tested in KiCad for both allowed main-board
  routing and forbidden neck copper;
- an independent, fail-closed prototype gate/package implementation and a concrete
  [prototype-to-production handoff](65-prototype-to-production.md).

No electrical architecture hold has been silently closed. EDS-13 now records
that hard-low charger EN2 prevents standby/suspend mode, and EDS-14 records that
IO9 cannot wake a C6 from deep sleep. Both need resolution before routing freeze.
The firmware is **bring-up only**: persistent journal, provisioning, MQTT/TLS and
signed OTA are still unimplemented. Boards remain at 59/60 unrouted connections.
All five prototype review slots and all seven product qualification slots remain
open. A public engineering source prerelease does not authorize fabrication.

## Active prototype completion plan — 2026-10-21

### Execution order and review gates for the resumed work

The starting revision is `507ca93`, with a clean working tree. The October 15
manufacturer review is committed; its public prices are dated research, not
received quotations or supplier acceptance. The last verified electrical state
is zero ERC/DRC errors, warnings and parity differences, with **59 A / 52 B
unconnected items**. The following work packages replace an undifferentiated
"finish everything" task. The historical checkpoints below remain evidence of
what was checked then, rather than current fabrication approval.

| Work package | Owner / allowed edits | Concrete result and acceptance | Dependency / state |
|---|---|---|---|
| W0 — Reconcile the plan and establish the baseline | Coordinator; plan and review record | Map each ordered gate to existing source, executable checks or missing external evidence; run current checks and record the integration branch and merge base. | Complete: baseline pipeline and pinned SDK build pass; review recorded below |
| W1 — Correct misleading generated cost/quantity claims | Cost maintainer; cost generator, its tests and generated cost reports | Count fitted parts/joints/MPNs with R21 excluded; derive A/B envelopes and area comparison; stop presenting unsupported panel/setup savings, historical rates or vendor ranking as current quotes. Add focused regressions and regenerate from `make cost`. | Complete: `681f69b` source/tests, `6447fe7` generated reports; full pipeline passes |
| W2a — Finish deliberate power, ground and fine-pitch fanout | PCB maintainer; isolated scratch model first | Route regulator/charger supply and returns deliberately, including required ground stitching; preserve power widths, bounded escapes and keepouts. Integrate only changes validated on **both** filled boards, with reviewed remaining connectivity. | Starts after W0; first routing stream |
| W2b — Finish native USB pair and fixture branches | PCB maintainer; separate scratch model first | A coupled U1/U5/J1 route plus reversible contacts and test-pad branches; actual differential DRC remains active. Any placement change must pass both board and enclosure checks and retain documented pin numbering. | Starts after W0; independent experiment, coordinated integration with W2a |
| W2c — Close every remaining connection | Coordinator + PCB maintainers; shared generator | Finish control/test-pad branches, then require **zero unconnected items**, errors, warnings and parity differences on A and B. Review power loops, sense points and return paths separately from DRC. | Depends on accepted W2a/W2b; fabrication blocker |
| W3 — Verify the complete source checkpoint | Coordinator + independent reviewer | Byte-identical generation, host and actual KiCad controls, ERC/DRC/parity, enclosure meshes/interference, pinned firmware build and full local pipeline. Review the branch and current uncommitted files; fix confirmed findings before atomic commits/push. | After each accepted source checkpoint and finally after W2c |
| W4 — Obtain fabrication and order acceptance | Hardware maintainer, supplier, assembler and named order reviewer | Exact available BOM/attrition quote, pack/harness/NTC confirmation, accepted stackup/panel/CPL/DFM and sensor handling, then genuine prototype-review evidence and checksum-verified order archive. | Requires completed layouts; external records absent |
| W5 — Build and qualify the experiment | Hardware/test maintainer with physical samples | Receive the controlled 5 A + 5 B lot, inspect and execute staged power/wake/fit/RF/thermal/RH tests with serial-linked raw records. The researched 3 + 3 pricing option does not change the locked sample plan. | Requires W4 and physical boards; cannot be replaced by simulation |
| W6 — Finish product behavior and the controlled series | Firmware/test/hardware maintainers | Implement and test journal/provisioning/MQTT/TLS/signed OTA and protected charge supervision against docs 71; execute the A/B decision, Rev 2 and the 20-unit acceptance gates. | Preserve the ordered gates below; do not silently enable charging or USB500 |

**Integration discipline.** Keep hardware experiments isolated until their exact
source has passed fresh KiCad checks; do not merge competing placement/router
changes concurrently. Both layouts retain one electrical model and firmware.
Never relax clearances, differential-pair checks, thermal/RF exclusions or
manufacturing evidence gates to obtain a passing result. An unrouted development
checkpoint may be committed with its exact count documented, but W2c remains
open until both counts are zero. Physical safety and measurement gates remain
open until actual evidence is supplied.

**Review cadence.** Apply `reviewBranch` at the initial baseline, after an
accepted routing/integration checkpoint, and before the final push. Resolve
`master`/`main`/`develop` from Git refs and record the merge base. In addition to
the committed three-dot branch diff, inspect the current working-tree diff and
new files, as requested. Each checkpoint records confirmed Code/Architecture
findings with actual file/line locations; check removed or bypassed guards and
trace their replacement invariants. Treat DRC as one check, alongside explicit
pin/polarity, power-loop, sensor-process, mechanics and firmware-policy review.

**Progress reporting.** Report completed work, new evidence, remaining blockers
and the next concrete action while work runs. Do not report tasks or checks as
running between sessions, or assign completion percentages from partially
implemented gates. W4/W5 require outside records and hardware; continue all
independent source work while those inputs are unavailable.

### Fresh baseline verification — 2026-10-21

At `507ca93`, an isolated clean worktree passed all 15 local pipeline stages,
90 host regressions and 14 actual KiCad controls. Both filled boards have zero
errors, warnings and parity differences, with 59 A / 52 B unconnected items.
The pinned ESP-IDF v5.5.4 build passed (application size `0x2d5f0` bytes).
Logs are local diagnostics at `/tmp/sensorly-baseline-20261021.log` and
`/tmp/sensorly-firmware-20261021.log`, not physical qualification records.

The cost checkpoint at `6447fe7` also passes all 15 pipeline stages, now
with 96 host regressions; KiCad's 14 controls, enclosure checks and deterministic
regeneration pass. Fitted costing excludes R21 and reports 46 parts, 198 SMT
joints and 26 exact MPNs. The September rates remain historical illustrations;
no panel acceptance or fresh quote is implied. Log:
`/tmp/sensorly-cost-checkpoint-20261021.log`.

The initial `reviewBranch` checkpoint resolves `master` at merge base
`d50053b`. It includes current edits and new files. A confirmed new issue at
`tools/boardgen/project.py:160` applies the 0.6 mm Switch trunk minimum at U3's
0.5 mm-pitch pads, preventing a clearance-compliant escape. W2a must replace
that impossible constraint with a reviewed, bounded pad escape and actual
positive/negative KiCad controls while retaining the trunk minimum. The cost
corrections in W1 address DNP counting and unsupported panel/vendor claims.
The charger bypass placement concern predates this branch and is treated as
layout completion work, rather than a branch regression. All external evidence
and physical qualification states remain open.

### Integrated local-power checkpoint — 2026-10-22

The shared generator now reserves the regulator/charger bypass placement before
small-signal packing, routes U3's local switching/input/output/VOS paths, and
adds U1 centre-ground access plus U4's exposed-pad array/direct VSS link.
A single reviewed 1.15 mm Switch escape has a 1.2 mm maximum; the 0.6 mm
trunk and top-layer/no-via policy are enforced by source and actual KiCad
controls. Independent review also tested chained escapes and live placement
drift; those attempts now fail closed.

Fresh root `make erc drc` reports zero errors, warnings and parity differences
on both boards, with **56 A / 49 B unconnected items**. The development count
fell from 59/52 and is still not a manufacturing approval. All four enclosure
mesh extents and both lid/base and cable/case-plus-pack intersections pass.
EDS-17 keeps the under-EP via sealing, paste/reflow/inspection process and
repriced supplier acceptance open; generic tent flags do not close it.
The next W2a work is charger supply fanout/trunks. W2b USB and W2c remaining
connections are still open, as are all physical qualification gates.

Local diagnostics: `/tmp/sensorly-power-drc-20261022.log`,
`/tmp/sensorly-power-controls-20261022.log`, and
`/tmp/sensorly-power-mech-20261022.log`. These are executable design checks,
not measurements or assembler acceptance.

### Integrated charger-bypass checkpoint — 2026-10-22

U4 IN13 now reaches C9, OUT10/11 reaches C10, and BAT2/3 reaches C11 via
five explicit 0.8 mm pad escapes and 0.4 mm same-face trunks. Independent
review checked the removed generic IC-via search against its local replacement.
Nine focused host tests pass, including transformed manufacturer-pad connectivity
for both variants. Fresh root ERC/DRC reports zero errors, warnings and parity
with **47 A / 45 B unconnected items**; diagnostics are retained at
`/tmp/sensorly-charger-drc-20261022.log`. Placement, enclosure, BOM, stackup
and process requirements are unchanged from the preceding checkpoint.
Remote supplies, controls, USB and genuine manufacturing acceptance remain open.

### Integrated regulator-control checkpoint — 2026-10-22

Explicit EN_REG/VSET paths connect U3 to R5/R6 through standard signal vias,
with fail-closed placement snapshots. Both actual KiCad positive controls
require no violations and no airwires on those two nets; placement-mutation
negative controls also pass. Fresh root ERC/DRC reports zero errors, warnings
and parity differences with **45 A / 44 B unconnected items**. Placement and
mechanical geometry are unchanged. Diagnostics:
`/tmp/sensorly-controls-tests-20261022.log` and
`/tmp/sensorly-controls-drc-20261022.log`.
EDS-18 retains the TI 100 pF VSET parasitic limit and startup/output-selection
qualification; no extracted or measured parasitic bound is asserted.

### Connector mounting-ground checkpoint — 2026-10-22

Both independent J2 mounting nails now belong to GND in the one shared model.
The original footprint retains its real separate lands and no internal-jumper
exception. Independent scratch review and fresh root ERC/DRC both verify actual
copper connectivity: zero violations/parity, **44 A / 43 B unconnected items**.
The three battery contacts, BOM, footprint geometry and enclosure are unchanged.
Diagnostics: `/tmp/sensorly-mount-ground-drc-20261022.log`.

### Immediate source cleanup and atomic commit plan

The current work order is to finish and verify the existing changed files before
starting additional routing experiments. Freeze delegated edits after their
validated handoffs, then:

1. Review manufacturer-derived libraries and the shared electrical model; retain
   the controlled-power ADR and all unresolved supplier/bench gates.
2. Fix generator routing/rule defects and enclosure interference/retention in
   both variants. Keep incomplete routes visible in the development DRC record;
   never weaken prototype or product qualification to obtain a passing gate.
3. Regenerate all deterministic sources and reports, run host/KiCad regressions,
   ERC/DRC/parity, enclosure meshes and the pinned firmware build.
4. Commit library, electrical, firmware/capture, routing, enclosure and BOM/build
   changes as separate reviewable ideas with their affected documentation.
   Commit regenerated artifacts separately where practical, referencing the
   source commits. Record exact remaining routing counts and review limitations.
5. Run the complete local pipeline against committed generated files, fix any
   remaining drift or failures, and push the branch without rewriting history.

These commits preserve an engineering checkpoint. A fabrication package still
requires completed routing and genuine pack, assembler and order-review records.

### Verified source cleanup checkpoint — 2026-10-14

The existing changed files have been corrected, regenerated and committed as
separate library, electrical, firmware/capture, routing, enclosure, purchasing
and generated-output changes. The final full local pipeline passed **all 15
stages without skips** at `dfc85a2`, using Python 3.14.7 and KiCad 10.0.6.
This record concerns source/build verification, not tested physical prototypes.

| Check | Result |
|---|---|
| Host regressions | 90 tests pass; the firmware decoder also passes its known-CRC, endpoints and 48 single-bit fault controls. |
| KiCad controls | 14 tests pass, covering sensor/antenna keepouts, thermal neck rules, component internal conductors, bounded power escapes and USB coupling. The isolated USB control exposed the missing maximum gap; the corrected rule rejects separated tracks and accepts the preferred geometry. |
| Generated sources | Shared schematic, both PCB projects/rules, BOM/netlist, model SVGs, enclosure parameters and generated reports reproduce byte-identically against committed files. No duplicate PCB UUIDs or whitespace errors remain. |
| ERC / DRC / parity | Zero ERC violations; both filled boards have zero DRC errors, warnings and schematic parity differences. A has 59 unconnected items; B has 52. The development budget records these counts and has no warning allowances. |
| Mechanical | Four meshes pass bounds checks; both seated lid/base and both cable/case-plus-pack intersections are empty. Physical printed fit and handling remain untested. |
| Docs / BOM / outputs | 19/19 checked figures match; 47 BOM lines and 46 fitted placements. Complete A/B draft fabrication outputs are generated and explicitly unapproved for fabrication. |
| ESP-IDF application | Pinned ESP-IDF v5.5.4 build passes at source checkpoint `60f56e3`; later changes affect routing rules, tests and documentation, not the application. No device behavior is inferred from this build. |
| Qualification rejection | `make prototype-check` rejects unfinished routing and all five missing prototype review records. `make release-check` rejects unfinished routing and all seven missing product qualification records. Evidence fields remain null. |

Local diagnostics are retained under `_build/current-checkpoint-*.log`; they
are ignored build artifacts, not supplier, assembler or physical evidence.
The next implementation task is deliberate completion of the USB pair, power
loops/ground returns and remaining branches on both boards. Pack/harness,
stackup/DFM/CPL and named order-review records are also still required before
producing the 5 A + 5 B batch. Physical bring-up, A/B measurement, product firmware,
Rev 2 and the controlled 20-unit series retain their ordered gates below.

The requested target is a reproducible **5 A + 5 B fabrication package**, followed
by verification on the manufactured prototypes. Source preparation and physical
qualification are separate gates; no board, pack sample, supplier confirmation
or assembler approval has been supplied during this continuation.

The delegated electrical review, sourcing review and mechanical work are recorded
in [ADR-001](adr/001-controlled-prototype-power-and-wake.md),
[the purchasing review](63-assembly-qualification.md) and
[the enclosure model](80-enclosure.md). The shared prototype now separates the
runtime IO1 wake button from the IO9 download strap, pulls GPIO8 high for joint
ROM download, controls EN2, defaults the bring-up image to standby, and leaves
R21 unpopulated to isolate raw TS from the ADC. B widens to 30 mm to accommodate
the shared controls; both variants still use one electrical model and firmware.
These changes do not implement unrestricted USB charging or close measured
startup/suspend/watchdog/pack fault qualification.

Primary drawing reviews also corrected L1, U4, U5, Q1 and D1 land patterns,
D1 manufacturer polarity numbering, J1 orientation, and the filtered sensor
height. C1/C8 now use sourced 10 µF/16 V, ±10% capacitors: the conservative
positive tolerance/temperature rail sum is 26.818 µF below the regulator’s
40 µF effective maximum. Minimum DC-bias/aging assumptions and physical
startup/TX/load-step qualification remain explicit in EDS-16.

All fitted passives have exact candidate ordering codes and BOM validation rejects
missing MPN/manufacturer/risk dispositions. Alternatives remain unqualified.
The model now respects each pad's local angle when constructing routing obstacles;
previously rotated module pads were represented with their width/height reversed.
The sensor-island router respects the package-body keepout, actual net-class
clearances and four reserved pad escapes. Both island-only layouts pass actual
KiCad DRC; B uses C6 at 180° for planar supply taps while A retains 90°.
USB pair names now use complementary P/N suffixes and a KiCad negative control
proves the uncoupled-pair rule is active. Full-board routing remains open.

Both cases use electronics-body edge retention with removable tape lid closure;
the side-actuated button is accessed with the lid removed. Printed fit is untested.

| Next action | Owner / handoff | Acceptance |
|---|---|---|
| Complete explicit IC fanout, power loops, USB pair and remaining branches on **both** boards | PCB maintainer; isolated generator experiments only until KiCad validates them | Zero errors, warnings, unconnected items and parity differences; reviewed return paths/stackup; no budget-based fabrication approval |
| Finish primary land-pattern overlays, effective capacitance/inductor ratings and exact purchasing review | Hardware maintainer + supplier | Source drawings, retained calculations and actual available order codes; no unqualified alternate fitted |
| Obtain pack lot/harness/NTC/current-limit confirmation | Supplier + hardware maintainer | Written records matching the selected drawing, reconciled limits and incoming continuity/inspection procedure |
| Review assembly/CPL, stackup and DFM on the completed layouts | Assembler + named hardware reviewer | Actual preview and DFM disposition linked to exact source revision |
| Approve and package the controlled engineering batch | Project maintainer + reviewer | Five genuine prototype review records, clean committed sources, full pipeline, pinned firmware build, successful A/B prototype packaging and archive checksums |
| Inspect and measure received prototypes | Hardware/test maintainer | Staged docs 51 tests and serial-linked docs 72 records; measured rails/faults/sleep/wake/fit before enclosed operation |

Commit and push reviewable source/model changes after validation. Do not manufacture
from draft outputs or populate readiness evidence with this plan, synthetic logs
or agent-generated approval placeholders. The product firmware/thermal experiment,
Rev 2 and 20-unit series remain later work in the ordered plan below.

## Ordered work and completion gates

Work in this order. Where a task needs unavailable hardware or supplier data,
retain it as blocked and continue independent work below it. Do not close a
physical gate with a model, synthetic test record or a placeholder evidence file.
Owners below are engineering roles; the project maintainer assigns people.

| Order | Priority / owner | Work | Completion and review gate | State |
|---|---|---|---|---|
| 1 | P0 / build maintainer | Close release-export and packaging bypasses; require the complete manufacturing set and carry qualification evidence in the archive. | Fault injection proves missing qualification, files or failed exports cannot produce a release; full development pipeline still passes. | Done and reviewed; see verification below |
| 2 | P0 / hardware + firmware | Resolve EDS-11 USB configuration/current-allocation and suspend implementation; resolve EDS-12 watchdog/sleep output release. Keep USB500 and charging disabled until their prerequisites hold. | Review a C6-specific implementation and actual descriptor; define and measure fault latency and total suspend current. Use an ADR if architecture/policy changes. | Controlled prototype architecture implemented in ADR-001; product USB policy, TS protection and measured transitions remain open |
| 3 | P0 / hardware | Obtain the controlled pack drawing/lot confirmation; confirm harness polarity, NTC curve, protection and current-limit discrepancy. Review PACK_TS electrical limits under open/short/unpowered faults. | Supplier evidence and a reviewed worst-case calculation; five incoming-inspection records before mating/charging. | Supplier records and samples required |
| 4 | P1 / hardware | Recheck U1–U5, Q1, J1/J2 and D1 pin numbers, pin-1 and rotations against primary drawings; select exact passive and connector MPNs. | EDS §11 checklist and assembly review signed; BOM ratings/DC bias/inductor saturation and second-source risks recorded. | Exact passive candidates and desk review recorded; overlays, ratings and assembler approvals remain open |
| 5 | P1 / PCB maintainer | Finish routing on A and B from the shared model: power/ground and regulator loops, fine-pitch escapes, charger controls, USB pair, remaining signals and test pads. | Zero unconnected items, errors, warnings and parity differences on both; review return paths, USB geometry/stackup, thermal neck and antenna keepouts. Reduce budgets only after inspecting the new DRC results. | Open |
| 6 | P1 / mechanical | Verify PCB/pack retention, connector access and lead routing, sensor vents/chambers and antenna clearance in both cases. | Mesh gates plus physical fit/handling records for all five packs; address weak B board retention before deployment. | Model exists; physical tests pending |
| 7 | P1 / firmware | Add a pinned ESP-IDF build and minimal safe bring-up: default-low charge/current controls, calibrated NTC supervision, acquisition before radio, bounded failures and sleep. | Reproducible build, executable policy/fault tests, and scope traces on hardware. EDS-11/12 block enabling higher current/charging. | Bring-up image compiles with pinned ESP-IDF v5.5.4; decoder/failure tests pass. NTC supervision and device traces remain open |
| 8 | P1 / production | Prepare fixture/flashing/self-test and serialized result capture; get assembler DFM/CPL approval, quotes and controlled prototype-order files. | Exact as-built BOM, stackup, pin-1 preview, reviewed order package and incoming inspection plan. Prototype order remains a separate engineering decision from product release. | Fixture capture/flashing and controlled prototype packager implemented/tested; exact BOM, assembler reviews and quotes remain open |
| 9 | P1 / hardware + test | Build 5 A + 5 B and perform staged bench bring-up and docs 51 power-safety qualification. | Rail transients, power modes, pack faults, watchdog, host/suspend and charge tests pass before enclosed charging. | Requires steps 2–8 and physical boards |
| 10 | P2 / firmware | Complete F-03…F-12: 500-record recoverable journal, provisioning/credentials, MQTT/TLS, signed OTA/rollback, quality flags, factory mode and measured energy limits. | Every acceptance case in docs 71 passes, including interrupted writes/OTA, outages, invalid certificates and stale/charging readings. | Not started |
| 11 | P2 / test | Measure sleep/runtime, RF and finished-case thermal/RH performance; execute the predeclared A/B experiment. | Raw data, calibration/uncertainty and run metadata retained; guarded decision gate chooses A, B or inconclusive without pooling incompatible builds. | Requires prototypes and firmware |
| 12 | P2 / all maintainers | Implement Rev 2 from measured findings and repeat affected qualification; close sourcing and assembly risks. | Reviewed revised schematic/layout/case/firmware, zero rule failures, byte-identical generation, all release evidence linked to the qualified design. | Depends on measurement results |
| 13 | P2 / production + reviewer | Build and test the controlled 20-unit series; review the final package and release provenance. | 20 serial-linked test records, approved assembly/orientation, complete release-check and checksum-verified package; review confirms every earlier gate is actually closed. | Depends on Rev 2 qualification |

The existing product release gate deliberately requires measurements that can
only exist after prototypes. Do not fabricate evidence to get a prototype order
through that gate or rename a draft export a product release. Step 8 needs a
reviewed prototype-order disposition with explicit remaining qualification risks.

## Original audit verification record (`b5a06c6`)

Both development runs passed all 14 stages with Python 3.14.7 and KiCad 10.0.6;
the final run completed at `b5a06c6` with no skipped stages. No physical
qualification or manufacturing release is inferred from either run.

| Verification | Final result |
|---|---|
| Regression tests | 50 passed, including release export, archive completeness, evidence inclusion, checksum and clean-source provenance cases. |
| KiCad negative tests | 2 passed: forbidden neck net and widened neck trace rejected. |
| Generated sources | Schematic, both boards and generated reports regenerate byte-identically. No routing experiment entered the source tree. |
| ERC | Zero violations. |
| DRC/parity | A: 0 errors, 7 reviewed warnings, 0 parity differences, 59 unconnected. B: 0 errors, 17 reviewed warnings, 0 parity differences, 60 unconnected. |
| Mechanical | Four meshes pass bounds checks; both seated lid/base intersections are empty. One model retention warning and physical qualification remain open. |
| Docs/BOM/exports | 19/19 checked figures match; 43 BOM lines/43 populated placements; draft fabrication outputs exist for both variants. Required archive filenames were checked against actual KiCad exports. |
| Release rejection | `make release-check`, `make outputs OUTPUT_CLASS=release`, and `make release-package RELEASE_TAG=hw-a1` each reject unfinished routing and missing evidence. No release archive was created. |
| Additional fault checks | Mandatory mesh generation rejects absent OpenSCAD; evidence resolution rejects external absolute paths, parent traversal and escaping symlinks. |
| Branch review | Reviewed against `master` at `d50053b`; no remaining confirmed Code/Architecture findings in the corrective diff. See [review report](91-readiness-branch-review.md). |

Local reproduction logs are `_build/readiness-review-pipeline.log`,
`_build/readiness-review-release-check.log`, `_build/readiness-release-outputs.log`
and `_build/readiness-release-package.log`. They are ignored build diagnostics,
not qualification evidence. At that checkpoint no boards/packs were ordered or tested and no firmware
was implemented. All seven physical/product qualification slots still remain null.
Steps 2–13 were open at that checkpoint; the current implementation status is
listed above. No outside hardware or measurement records were supplied. The next engineering action is the EDS-11/12 architecture
review, followed by library/purchasing verification and deliberate routing of
both variants. Supplier and bench work require actual records and hardware.

### Routing experiment disposition

A scratch-only experiment reduced the router's extra clearance padding from
0.06 to 0.01 mm and removed its extra mask expansion from copper-pad obstacles.
Both retained the existing electrical clearance rules and had zero KiCad DRC
errors/parity differences, but A still had 53 unconnected items and 27 warnings;
B had 59 unconnected items and 19 warnings. A also acquired an unreviewed
off-centre-via warning. These are worse warning totals than the current 7/17,
so the experiment was **not adopted** and neither committed board nor the DRC
budget changed. Scratch reports are under `_build/routing-experiment/`.

The remaining route list includes U3/U4 power and control-pad escapes,
J1/U1/U5 USB connections, supply-plane access, and test-pad branches. Next steps
are explicit fine-pitch fan-out with pad geometry preserved, placement/loop
review of the regulator and charger, and intentional USB pair routing; merely
reducing the router's padding does not finish this design. Complete EDS-11/12's
architecture review before freezing those routes.

### External-router experiment disposition

Freerouting 2.4.1 was evaluated only in `_build/`, using the official checksum-
verified Linux bundle and analytics disabled. Routing the existing partial A
board did not resolve its blockers. A clean-island-only routing experiment,
imported back into KiCad with the real project/rules and fresh zone fill, yielded
23 unconnected items, 36 DRC errors (33 width and 3 clearance), 74 warnings and
zero parity differences. Fewer airwires alone do not make acceptable copper.
Neither experiment was adopted or added to the release inputs; the committed
boards retain their zero-error baseline. Main-board fine-pitch escape, power-loop
and USB routing need deliberate layout work after the architecture decisions.

### Via/paste review correction — 2026-10-22

Review of the current files found ordinary through drills under same-net paste
lands, which electrical DRC alone permits. Generator emission now independently
rejects these holes, and generic routing masks paste even on its own net, with
an explicit 0.10 mm engineering drill-edge reserve. Only U4's exact four reviewed
EP vias retain the EDS-17 process exception. C9/C10 ground returns move outside
paste. Updated branch obstacles also prevent off-centre corner connections.

Fresh filled-board checks give **42 A / 34 B unconnected items**, with zero
ERC/DRC errors, warnings and parity differences. Six focused regressions pass,
including same-net paste rejection, the narrowly defined EP exception and
centred-via corner handling. An independent drill/paste audit finds only the
four specified U4 EP holes on each board. These are development counts; W2a,
W2b and W2c remain open, as do all external manufacturing and physical gates.
At `28bcb50`, all 15 full-pipeline stages pass without skips, including 112
host regressions, 22 actual KiCad controls, byte-identical generation, enclosure
checks and draft exports. Log: `/tmp/sensorly-paste-checkpoint-pipeline-20261022.log`.
No physical measurements or supplier approval are implied.

### Local charger programming checkpoint — 2026-10-22

C9 now faces U4 IN13 directly, and R12/R13 sit beside U4 with explicit
ITERM/ISET paths and off-paste ground returns on both boards. No netlist,
component value, firmware policy or electrical rule is changed. Fresh ERC/DRC
reports retain zero violations, warnings and parity differences, with **42 A /
34 B unconnected items**; ISET and ITERM have no remaining airwires. Seventeen
focused regressions pass, as do docs consistency and the four enclosure mesh
bounds plus both lid/base and cable/case-plus-pack intersection checks.

This checkpoint improves the local loops without claiming complete routing or
assembled analog/ground performance. W2a continues with actual ground-plane
access and remaining charger fanout; W2b remains open. Relevant diagnostics:
`/tmp/sensorly-charger-programming-drc-20261022.log`,
`/tmp/sensorly-charger-programming-tests-20261022.log` and
`/tmp/sensorly-charger-programming-mech-20261022.log`.

### Filled ground-connectivity checkpoint — 2026-10-22

Pad-derived returns now connect U1.11/14/51/52, C5.2, J2.1 and the current
U5.2 ground region to the inner plane. The J2/U5 additions were required by
fresh integration: charger repacking created extra islands that standalone
checks did not expose. The new CLI regression requires **zero GND airwires on
both actual filled boards**; it passes, alongside four focused host controls.
Fresh root reports have **39 A / 35 B unconnected items**, zero ERC violations,
DRC errors, warnings or parity differences. Extra fixed copper changes generic
routing outcomes; a total airwire count alone is not a ground-connectivity test.

The U5 placement guard requires its current return to be replaced explicitly
when USB moves it. EDS-20 now records the separate U4 low-current/power-ground
review required before ordering; the prototype assembly manifest references it.
No assembled or manufacturer approval is inferred. Logs:
`/tmp/sensorly-ground-integration-{drc,kicad,tests}-20261022.log`.

The combined ground/CI checkpoint at `7e75b86` passes all 15 local pipeline
stages with 117 host regressions and 23 actual KiCad tests. The exact pinned
container also passes firmware-host/provenance smoke checks after the CI setup
fix, and passes the new ground-connectivity regression under KiCad 10.0.5.
See [the checkpoint review](94-ground-and-ci-checkpoint-review.md); GitHub CI
will rerun on push. All physical/ordering evidence remains open.

### Resumed completion order — 2026-10-28

1. Verify and review the existing USB/fixture integration on both variants;
   record exact filled-board results and commit source and generated files as
   separate reviewable checkpoints. Preserve EDS-19 and the prototype gate.
2. Integrate reviewed charger-control fanouts and ground returns against the
   accepted USB geometry. Verify actual pad connectivity, paste clearance, USB
   reference copper and both boards' filled DRC before accepting the changes.
3. Complete supply trunks and remaining MCU, fixture and sensor connections.
   Retain the shared electrical model and require zero unconnected items, DRC
   errors, warnings and parity differences on both layouts.
4. Complete independent firmware work permitted by the existing bring-up
   safety policy. Keep radio, charging and USB500 disabled until their documented
   requirements and physical qualification are satisfied.
5. Re-run the full local pipeline, branch/current-file review and applicable
   firmware build; make atomic commits and push. Obtain actual supplier,
   assembly and order reviews, then build and measure the 5 + 5 prototypes.
   No source-only check substitutes for those records or physical tests.

The previous GitHub Hardware Quality and Firmware Bring-up runs passed at
`147d0f5`. The USB candidate is currently uncommitted; a fresh filled-board
check reports A31/B27 unconnected and zero ERC/DRC errors, warnings and parity
differences. On 2026-10-28, regeneration, 11 focused host tests, four actual KiCad USB/ground
controls, 19/19 documentation checks and both enclosure interference checks
passed. Neither USB data net nor GND has a remaining airwire on either board.
A full pipeline remains required before pushing the accepted checkpoint.
