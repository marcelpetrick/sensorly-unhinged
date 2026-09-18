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
open. Physical artifacts outside this repository have not been verified.

## Ordered work and completion gates

Work in this order. Where a task needs unavailable hardware or supplier data,
retain it as blocked and continue independent work below it. Do not close a
physical gate with a model, synthetic test record or a placeholder evidence file.
Owners below are engineering roles; the project maintainer assigns people.

| Order | Priority / owner | Work | Completion and review gate | State |
|---|---|---|---|---|
| 1 | P0 / build maintainer | Close release-export and packaging bypasses; require the complete manufacturing set and carry qualification evidence in the archive. | Fault injection proves missing qualification, files or failed exports cannot produce a release; full development pipeline still passes. | Done and reviewed; see verification below |
| 2 | P0 / hardware + firmware | Resolve EDS-11 USB configuration/current-allocation and suspend implementation; resolve EDS-12 watchdog/sleep output release. Keep USB500 and charging disabled until their prerequisites hold. | Review a C6-specific implementation and actual descriptor; define and measure fault latency and total suspend current. Use an ADR if architecture/policy changes. | Open; source-level contract gap recorded |
| 3 | P0 / hardware | Obtain the controlled pack drawing/lot confirmation; confirm harness polarity, NTC curve, protection and current-limit discrepancy. Review PACK_TS electrical limits under open/short/unpowered faults. | Supplier evidence and a reviewed worst-case calculation; five incoming-inspection records before mating/charging. | Supplier records and samples required |
| 4 | P1 / hardware | Recheck U1–U5, Q1, J1/J2 and D1 pin numbers, pin-1 and rotations against primary drawings; select exact passive and connector MPNs. | EDS §11 checklist and assembly review signed; BOM ratings/DC bias/inductor saturation and second-source risks recorded. | Open |
| 5 | P1 / PCB maintainer | Finish routing on A and B from the shared model: power/ground and regulator loops, fine-pitch escapes, charger controls, USB pair, remaining signals and test pads. | Zero unconnected items, errors, warnings and parity differences on both; review return paths, USB geometry/stackup, thermal neck and antenna keepouts. Reduce budgets only after inspecting the new DRC results. | Open |
| 6 | P1 / mechanical | Verify PCB/pack retention, connector access and lead routing, sensor vents/chambers and antenna clearance in both cases. | Mesh gates plus physical fit/handling records for all five packs; address weak B board retention before deployment. | Model exists; physical tests pending |
| 7 | P1 / firmware | Add a pinned ESP-IDF build and minimal safe bring-up: default-low charge/current controls, calibrated NTC supervision, acquisition before radio, bounded failures and sleep. | Reproducible build, executable policy/fault tests, and scope traces on hardware. EDS-11/12 block enabling higher current/charging. | Not started; SDK absent from PATH |
| 8 | P1 / production | Prepare fixture/flashing/self-test and serialized result capture; get assembler DFM/CPL approval, quotes and controlled prototype-order files. | Exact as-built BOM, stackup, pin-1 preview, reviewed order package and incoming inspection plan. Prototype order remains a separate engineering decision from product release. | Not started |
| 9 | P1 / hardware + test | Build 5 A + 5 B and perform staged bench bring-up and docs 51 power-safety qualification. | Rail transients, power modes, pack faults, watchdog, host/suspend and charge tests pass before enclosed charging. | Requires steps 2–8 and physical boards |
| 10 | P2 / firmware | Complete F-03…F-12: 500-record recoverable journal, provisioning/credentials, MQTT/TLS, signed OTA/rollback, quality flags, factory mode and measured energy limits. | Every acceptance case in docs 71 passes, including interrupted writes/OTA, outages, invalid certificates and stale/charging readings. | Not started |
| 11 | P2 / test | Measure sleep/runtime, RF and finished-case thermal/RH performance; execute the predeclared A/B experiment. | Raw data, calibration/uncertainty and run metadata retained; guarded decision gate chooses A, B or inconclusive without pooling incompatible builds. | Requires prototypes and firmware |
| 12 | P2 / all maintainers | Implement Rev 2 from measured findings and repeat affected qualification; close sourcing and assembly risks. | Reviewed revised schematic/layout/case/firmware, zero rule failures, byte-identical generation, all release evidence linked to the qualified design. | Depends on measurement results |
| 13 | P2 / production + reviewer | Build and test the controlled 20-unit series; review the final package and release provenance. | 20 serial-linked test records, approved assembly/orientation, complete release-check and checksum-verified package; review confirms every earlier gate is actually closed. | Depends on Rev 2 qualification |

The existing product release gate deliberately requires measurements that can
only exist after prototypes. Do not fabricate evidence to get a prototype order
through that gate or rename a draft export a product release. Step 8 needs a
reviewed prototype-order disposition with explicit remaining qualification risks.

## Verification record

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
not qualification evidence. No boards/packs were ordered or tested, no firmware
was implemented, and all seven physical/product qualification slots remain null.
Steps 2–13 remain open; no outside hardware or measurement records were supplied
during this audit. The next engineering action is the EDS-11/12 architecture
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
