# 65 — From repository to physical production

**Current disposition: hold fabrication.** No boards, packs or bench data exist.
The public engineering release makes the design history and bring-up implementation
available for review; it is not an order authorization. The next order is 5 A +
5 B, followed by the planned experiment, revision and controlled 20-unit series.

## Three separate deliverables

| Deliverable | Gate | Meaning |
|---|---|---|
| Public engineering source prerelease | Full development pipeline, firmware compilation, reviewed limitations | Discuss/reproduce the work; no manufacturing readiness claim. |
| Controlled prototype package | `make prototype-package PROTOTYPE_VARIANT=a` and `b` | Clean layout, reviewed electrical/sourcing/assembly/mechanical/order records; fabricate only the reviewed engineering batch. |
| Qualified product package | `make release-package RELEASE_TAG=hw-a1` (actual printed revision) | All product qualification evidence, complete routing and final manufacturing review; use the revised tag for the eventual series. |

The prototype gate is intentionally independent of measurement evidence that
requires first boards. It still requires **zero DRC warnings/errors, zero
unconnected items and zero schematic/PCB parity differences on both layouts**,
clean ERC, and five nonempty review records in
`hardware/prototype-readiness.json`. It builds the pinned bring-up firmware and
runs its host tests. The product manifest and release gate are unchanged.
A file-existence gate cannot certify review quality; reviewers must check the
engineering content against the exact commit, BOM, generated outputs and
remaining risks. No placeholder, generated PASS or synthetic log closes a review.

## Order of work and handoffs

1. **Electrical architecture — hardware/firmware maintainers.** Close the C6
   USB configuration/current and BQ24074 suspend-mode problems (EDS-11/13),
   watchdog/control shutdown design (EDS-12), IO9 wake conflict (EDS-14), and
   PACK_TS open/short/unpowered voltage limits. Record the selected shared
   architecture and any changed locked decisions in the EDS before routing freeze.
2. **Sourcing/library — hardware maintainer.** Obtain the pack/harness drawing,
   polarity, protection and NTC specification; resolve the current-limit
   discrepancy. Select exact MPNs for every populated line, with ratings and
   alternates or accepted single-source risks. Check the manufacturer drawings
   against every IC/connector/diode pin, pad, pin-1 and rotation. Pack purchasing
   and assembler communication require actual quotes/records; none are invented.
3. **Layout — PCB maintainer.** Complete both boards together, inspect power-loop
   and ground return paths, USB geometry/stackup, RF clearance and the four-trace
   sensor neck. Review rule priority and fine-pitch neckdowns; the development
   DRC budget is not permission to ship unfinished connections. Re-run ERC,
   DRC/parity and deterministic generation, then obtain assembler DFM/CPL approval.
4. **Mechanical — mechanical maintainer.** Resolve B retention, review connector
   access, battery leads and ventilation. Generate all meshes and board STEP.
   Plan dimensional/insertion/retention checks on actual boards and five pack
   samples; model checks alone do not prove fit.
5. **Prototype disposition — project maintainer/reviewer.** Review the exact
   clean source commit and intended 5+5 quantity, populate the five prototype
   review references, source the pinned ESP-IDF environment, and run the complete
   local pipeline followed by both prototype-package commands. Inspect every
   archive, assembly drawing, drill and copper layer in a separate viewer; record
   approval and archive SHA-256 with the order. Do not upload the repository's
   draft output directories to a manufacturer.
6. **Incoming assembly/bring-up — hardware/test maintainers.** Record lot and
   serial traceability, inspect polarity/placement and shorts before power.
   Follow docs 51 in staged, current-limited bench operation. Flash the recorded
   bring-up image and retain fixture output using docs 72. Scope/measure rails,
   GPIO fault behavior, charge inhibit, USB modes, battery/NTC faults, temperatures
   and sleep current. Do not infer these from firmware's printed booleans.
7. **Instrument firmware and experiment — firmware/test maintainers.** Complete
   and device-test docs 71: journal/recovery, provisioning, MQTT/TLS, signed OTA,
   timestamps/quality and bounded energy. Run the predeclared thermal/RH/RF and
   battery experiments; keep raw records and uncertainty/calibration provenance.
8. **Revision and controlled series — all maintainers.** Apply measured findings,
   rerun affected qualification, select A/B using the guarded decision, then
   approve a new printed revision and 20-unit batch. Every unit gets an immutable
   serial-linked result. Product release requires all seven product evidence
   slots; a prototype acceptance never substitutes for them.

## Package behavior

The prototype packager requires a clean committed tree, runs fresh ERC/DRC,
prototype reviews, host tests and firmware build, then regenerates draft outputs
and mandatory enclosure meshes. It rechecks the tree and evidence, requires all
manufacturing inputs, and emits a variant/revision/commit-named ZIP plus SHA-256.
Project symbol/footprint library tables are included so the archived KiCad
sources resolve their vendored libraries. Only its reviewed, explicit input list
enters the archive; the archive carries
`PROTOTYPE.txt`, both readiness manifests and the applicable review records.
The working output directories retain their draft classification. Prototype
packaging does not create a `RELEASE.txt` marker or bypass `make release-check`.
No boards are ordered by any Make target.

The current manifests deliberately have null evidence. A successful public
source release therefore coexists with failing prototype and product gates.
That is the accurate state until the above engineering reviews and physical
work are complete.
