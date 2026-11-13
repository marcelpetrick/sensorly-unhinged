# Current execution plan

Updated 2026-11-13. This is the current work checklist; detailed decisions,
rejected experiments and verification history stay in
[the execution record](docs/01-execution-plan.md). Follow the
[flight manual](docs/02-flight-manual.md) for commands and stop conditions.
[EDS Open items](docs/30-electrical-design-spec.md#10-open-items-this-document-does-not-close-them)
and the prototype/product manifests remain the approval authorities.

## Verified checkpoint

Latest accepted routing source: `5404aaf`, generated compact layout: `62a3252`.
Fresh generated/filled root checks verify **A19/B15 open connections**, zero
ERC/DRC errors, warnings, parity differences and GND/USB-data airwires. VBAT
and VSYS are complete on both boards; B is unchanged by the latest A-only work.
Five source guards and three actual KiCad controls pass for system supplies.

The latest complete hosted pipeline checkpoint is `03cd47d`: **160 host tests,
38 actual KiCad controls and all 15 stages pass**, plus the pinned firmware
workflow. Those full-run figures precede the current routing batch, whose full
gate must run before pushing. No source PASS authorizes fabrication.

- [x] Audit all 47 BOM references and 17 fixture targets; retain unqualified alternates and supplier gaps explicitly.
- [x] Integrate reviewed USB, local power, charger/status, sense-divider and GPIO8 pull-up plane paths.
- [x] Reserve fixed copper before maze routing; recognize real pad shapes and preserve disconnected islands.
- [x] Run full source/reproducibility, ERC/DRC/parity, mechanical and draft-output checks on the accepted checkpoint.
- [x] Document the operating procedure, component audit and rejected experiments; commit accepted work atomically.

## Current implementation review — 2026-11-12

- [x] Resolve the branch-review base: `master`/`origin/master` at `13bac7b`; the branch diff is empty. Audit the current implementation separately.
- [x] Reproduce and fix count-only routing acceptance: exact per-net budgets now prevent a same-total regression; GND/USB-data opens cannot be budgeted.
- [x] Review flash recovery, bring-up capture and package publication; reject ambiguous second-bank initialization and preserve existing package/checksum pairs with fault-injection tests.
- [x] Refresh the README and GitHub About while retaining first-PCB identity and explicit prototype limits; reconcile stale floorplan routing prose.
- [x] Independently review the combined fixes; pass all 15 pipeline stages, 154 host tests, 35 KiCad controls, the pinned firmware build and sanitizer tests. Record fixes in atomic commits; inspect published CI during handoff.

Review findings and corrective evidence: [current-state audit](docs/99-current-state-review-20261112.md).

## Work order

- [ ] **P0 — Finish routing:** close every connection in the table below on both boards. Review the U4.4 disable escape and local supply/USB-control corridors first; then supply trunks and MCU/fixture branches. Preserve all clearances, paste exclusions, thermal/RF areas and USB reference copper.
- [ ] **P0 — Validate the final layouts:** independently review actual filled copper and current source, require zero opens/errors/warnings/parity, regenerate byte-identically, run the complete pipeline and pinned toolchain checks, refresh previews, commit and push.
- [x] **P1 — Integrate the bring-up journal:** reviewed 500-record core, real ESP flash backend, partition, capture checks, read/write/erase fault cases and overflow/ACK tests; pinned ESP-IDF and address/undefined-behavior sanitizer builds pass.
- [ ] **P1 — Qualify journal recovery on devices:** exercise physical flash power cuts and endurance, including the documented fail-closed partial-erase/header-corruption case. Source integration does not close F-03, network acknowledgement or availability qualification.
- [ ] **P1 — Complete the exact prototype-order records:** electrical, assembly, procurement, mechanical and named order reviews. Obtain accepted pack/harness/NTC drawings, purchasing BOM, stackup/impedance, DFM/CPL, under-EP via/paste/inspection process and fixture registration.
- [ ] **P1 — Produce the controlled 5 A + 5 B lot:** only from checksum-verified prototype archives after the preceding gates. The researched 3+3 option does not change the locked experiment sample plan.
- [ ] **P1 — Inspect and bring up real samples:** incoming polarity/orientation, current-limited staged power, flashing/capture, wake/sleep, case/pack fit and source-policy tests, with serial-linked raw records. Keep charging and USB500 disabled until their separate gates pass.
- [ ] **P2 — Finish product firmware:** provisioning/credentials, MQTT/TLS and ACK delivery, clock/quality handling, signed OTA/rollback, factory mode and protected charge supervision; execute every applicable acceptance case in the firmware contract.
- [ ] **P2 — Run the A/B experiment:** retain calibrated references, uncertainty, charging/cooldown restrictions and the predeclared decision gate; an inconclusive result stays inconclusive.
- [ ] **P2 — Revise and qualify the controlled 20-unit series:** close measured findings and sourcing risks, repeat affected tests, retain 20 device records and pass the product release/package gates.

## Active routing closure — starting at `7d631c6`

- [ ] Join A's remaining +3V0 pull-up/fixture supply pads through guarded off-paste plane feeds; verify both variants.
- [ ] Close U4.4 disable and the remaining charger-control branches without weakening fine-pitch/paste/clearance rules.
- [x] Close VBAT and VSYS supply branches on both boards, preserving the GND reference and +3V0 connectivity.
- [ ] Close the remaining VBUS branches on both boards with the same copper, paste and reference protections.
- [ ] Close EN, boot, UART, sensor/fixture and remaining MCU branches; retain fixture registration unless explicitly reviewed.
- [ ] Integrate only independently generated/filled candidates with exact per-net deltas; recheck the combined layout after each accepted patch.
- [ ] Require zero opens/errors/warnings/parity on both boards, run the full pipeline and review actual copper/returns before removing the routing blocker. Supplier and physical gates remain separate.

Experiments run in isolated worktrees with explicit file ownership. A candidate
result is not an accepted root checkpoint. Preserve rejected results and stop
on generator failure rather than checking leftover boards.

## Routing backlog at the checkpoint

Counts are open connections from filled reports, not pad counts. A zero in one
column does not qualify that net's analog or physical behavior.

| Net | A | B |
|---|---:|---:|
| `+3V0` | 3 | 0 |
| `BOOT_MODE_H` | 1 | 1 |
| `BTN_PROV` | 1 | 0 |
| `CHARGE_ENABLE` | 1 | 1 |
| `CHARGE_EN_N` | 1 | 2 |
| `CHG_N` | 1 | 0 |
| `EN` | 1 | 1 |
| `PACK_TS` | 1 | 0 |
| `PACK_TS_SENSE` | 1 | 1 |
| `SDA` | 0 | 1 |
| `UART_RX` | 1 | 1 |
| `UART_TX` | 1 | 0 |
| `VBAT` | 0 | 0 |
| `VBAT_SENSE` | 0 | 1 |
| `VBUS` | 6 | 6 |
| `VSYS` | 0 | 0 |

## Handoff and timing

The accepted source is on `master`; experiments remain in isolated worktrees
until root integration checks pass. No quote, supplier sign-off, physical board
or measurement is implied by a source PASS. The bring-up journal source is integrated after independent recovery review.
Its partial-erase fail-closed availability limit and physical qualification
remain open; no queued measurements were collected from real hardware.

The last planning allowance for remaining routing/source closure is **2–5
focused working days, low confidence**; it is not a committed delivery date.
Manufacturing and physical completion need actual approval and delivery dates.
The thermal protocol alone contains over 47 hours of fixed acquisition/settling
windows, plus charging/cooldown, setup and any retests. Update this checklist
from evidence, not elapsed time or a percentage of checked boxes.
