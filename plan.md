# Current execution plan

Updated 2026-11-12. This is the current work checklist; detailed decisions,
rejected experiments and verification history stay in
[the execution record](docs/01-execution-plan.md). Follow the
[flight manual](docs/02-flight-manual.md) for commands and stop conditions.
[EDS Open items](docs/30-electrical-design-spec.md#10-open-items-this-document-does-not-close-them)
and the prototype/product manifests remain the approval authorities.

## Verified checkpoint

Accepted routing source: `54541eb`, generated layouts: `025cb1e`.
Both layouts retain one electrical platform. Fresh filled checks have **A25/B19
open connections**, zero ERC/DRC errors, warnings and parity differences,
and zero GND/USB-data airwires. All 15 local pipeline stages pass with
**144 host tests and 35 actual KiCad controls**. This does not authorize fabrication.

- [x] Audit all 47 BOM references and 17 fixture targets; retain unqualified alternates and supplier gaps explicitly.
- [x] Integrate reviewed USB, local power, charger/status, sense-divider and GPIO8 pull-up plane paths.
- [x] Reserve fixed copper before maze routing; recognize real pad shapes and preserve disconnected islands.
- [x] Run full source/reproducibility, ERC/DRC/parity, mechanical and draft-output checks on the accepted checkpoint.
- [x] Document the operating procedure, component audit and rejected experiments; commit accepted work atomically.

## Work order

- [ ] **P0 — Finish routing:** close every connection in the table below on both boards. Review the U4.4 disable escape and local supply/USB-control corridors first; then supply trunks and MCU/fixture branches. Preserve all clearances, paste exclusions, thermal/RF areas and USB reference copper.
- [ ] **P0 — Validate the final layouts:** independently review actual filled copper and current source, require zero opens/errors/warnings/parity, regenerate byte-identically, run the complete pipeline and pinned toolchain checks, refresh previews, commit and push.
- [ ] **P1 — Finish journal integration:** review the isolated 500-record flash implementation, fix all confirmed recovery defects, exercise read/write/erase interruption and overflow/ACK cases, build with pinned ESP-IDF and verify capture compatibility. Its successful candidate build and host tests do not yet close F-03 or physical power-loss qualification.
- [ ] **P1 — Complete the exact prototype-order records:** electrical, assembly, procurement, mechanical and named order reviews. Obtain accepted pack/harness/NTC drawings, purchasing BOM, stackup/impedance, DFM/CPL, under-EP via/paste/inspection process and fixture registration.
- [ ] **P1 — Produce the controlled 5 A + 5 B lot:** only from checksum-verified prototype archives after the preceding gates. The researched 3+3 option does not change the locked experiment sample plan.
- [ ] **P1 — Inspect and bring up real samples:** incoming polarity/orientation, current-limited staged power, flashing/capture, wake/sleep, case/pack fit and source-policy tests, with serial-linked raw records. Keep charging and USB500 disabled until their separate gates pass.
- [ ] **P2 — Finish product firmware:** provisioning/credentials, MQTT/TLS and ACK delivery, clock/quality handling, signed OTA/rollback, factory mode and protected charge supervision; execute every applicable acceptance case in the firmware contract.
- [ ] **P2 — Run the A/B experiment:** retain calibrated references, uncertainty, charging/cooldown restrictions and the predeclared decision gate; an inconclusive result stays inconclusive.
- [ ] **P2 — Revise and qualify the controlled 20-unit series:** close measured findings and sourcing risks, repeat affected tests, retain 20 device records and pass the product release/package gates.

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
| `EN` | 2 | 2 |
| `PACK_TS` | 1 | 0 |
| `PACK_TS_SENSE` | 1 | 1 |
| `SDA` | 0 | 1 |
| `UART_RX` | 1 | 1 |
| `UART_TX` | 1 | 0 |
| `VBAT` | 2 | 2 |
| `VBAT_SENSE` | 0 | 1 |
| `VBUS` | 6 | 6 |
| `VSYS` | 3 | 1 |

## Handoff and timing

The accepted source is on `master`; experiments remain in isolated worktrees
until root integration checks pass. No quote, supplier sign-off, physical board
or measurement is implied by a source PASS. Current journal work remains an
uncommitted candidate outside the accepted checkout.

The last planning allowance for remaining routing/source closure is **2–5
focused working days, low confidence**; it is not a committed delivery date.
Manufacturing and physical completion need actual approval and delivery dates.
The thermal protocol alone contains over 47 hours of fixed acquisition/settling
windows, plus charging/cooldown, setup and any retests. Update this checklist
from evidence, not elapsed time or a percentage of checked boxes.
