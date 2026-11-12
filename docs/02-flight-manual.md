<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# 02 — Flight manual

Use this as the operating checklist for a design change, a prototype order,
first-board bring-up, and a later product release. Record what actually ran and
what it proved. The [working agreement](../AGENTS.md),
[execution plan](01-execution-plan.md), [electrical specification](30-electrical-design-spec.md)
and [prototype-to-production handoff](65-prototype-to-production.md) remain the
authorities for design choices and open gates. Do not turn an unrun step into a
PASS by copying a prior result.

## Before changing the design

1. Read `git status --short`, `git log -1 --oneline`, the affected source and
   documentation, and the [requirements/non-goals](10-requirements.md). Record
   the starting commit and any existing edits. Keep unrelated edits intact.
2. Write the question or failure, intended change, and expected evidence in the
   work record. Check the EDS §10 Open table before claiming that a value or
   architecture is locked. A new electrical split between A and B needs an ADR.
3. For every new component value, rating, footprint or pin map, retain the
   manufacturer document, revision and page/section beside the claim. Compare
   pin 1, rotation and land pattern against the *exact* part. Record a missing
   source as `TBC` with owner and closing gate; do not fill it from memory.
   Every populated BOM line needs an alternate or an accepted single-source
   risk. Vendor listings are leads, not controlled drawings or quotes.
4. Change the shared model under `tools/boardgen/` where applicable and
   regenerate both layouts. State why any A-only or B-only geometry change does
   not alter the shared netlist, BOM or firmware. Review power returns, USB/RF
   geometry, sensor neck and enclosure as physical paths, not only DRC objects.

## Source flight: run and record

From the repository root, with KiCad 10 and the pinned firmware environment
available when their gates apply:

```sh
make gen
make check test firmware-test
make erc drc
git diff --check
git diff --stat
```

`make gen` writes the schematic, both boards and model drawings. Review these
changes and make atomic source/documentation commits and a separate generated
output commit where practical. The reproducibility gate compares against Git,
so intentional regenerated changes must be committed before this final gate:

```sh
./localPipeline.sh
git status --short
```

Push only after the final gate passes. The pipeline
regenerates deterministic sources, checks drift, libraries, docs, BOM, ERC,
DRC/parity, actual KiCad negative controls and draft outputs. Save its final
PASS/FAIL summary, tool versions, source commit and changed-file diff with the
review. Inspect the filled-board DRC reports and the live unconnected counts;
zero errors/warnings/parity differences with remaining airwires is a development
checkpoint only. The development gate checks both the exact total and exact
per-net counts in `hardware/drc-budget.json`; review every changed net before
updating either field. GND and USB-data airwires are prohibited even if a budget
lists them. Unknown endpoint/net descriptions fail closed; use KiCad's English
JSON format so the gate can identify each endpoint's net. `make firmware` additionally requires the exact ESP-IDF setup
in [bring-up instructions](72-firmware-bringup.md). Compilation and synthetic
tests are source evidence, never device evidence.

When geometry changes, update documentation previews with `make render` and
`make mech-render`, then inspect both boards and all four enclosure images.
On a headless machine with Xvfb installed, use `xvfb-run -a make render` and
`xvfb-run -a make mech-render`. These are design previews, not photographs or
physical fit evidence. Enclosure previews automatically frame the whole part.
`make schematic-render` refreshes just the shared schematic SVG; the export
removes trailing whitespace so generated previews pass the same diff checks.

**Stop and repair** on any failed step, generated drift, unexpected A/B
difference, missing provenance, or relaxed rule used to hide a violation. Do not
advance a package using an older PASS from another commit. Commit the reason and
affected docs with the source; keep generated changes in a separate commit
where practical, as [AGENTS.md](../AGENTS.md) requires.

## Prototype order flight: controlled 5 A + 5 B

Follow [the handoff](65-prototype-to-production.md) and the five review slots in
[`hardware/prototype-readiness.json`](../hardware/prototype-readiness.json).
Close the sourcing, pin/rotation, assembly/DFM, stackup, enclosure and named
order reviews against the *exact* clean commit. Confirm zero unconnected items
on both layouts, not just a clean development DRC. Then run:

```sh
./localPipeline.sh
make prototype-check
make prototype-package PROTOTYPE_VARIANT=a
make prototype-package PROTOTYPE_VARIANT=b
```

The package commands produce reviewed prototype archives and SHA-256 sidecars;
record both hashes, source commit, printed revisions, lot, reviewer and order
quantity. Independently inspect copper, drill, assembly drawings, CPL and
enclosure outputs before sending the archives to fabrication. `make outputs`
produces **draft** exports and is not an order package. If a review record is
missing, a package command fails, or an archive differs from the reviewed
commit, hold the order. A populated manifest path proves that a file exists;
the reviewer must judge its content. The manifest currently has open slots, so
the gate is expected to fail until genuine reviews exist.

## First-board power and bring-up flight

Use [battery and USB power qualification](51-power-safety-qualification.md) as
the bench procedure and [bring-up instructions](72-firmware-bringup.md) for the
image and capture commands. Before applying power, record board/pack serials,
variant, printed revision, BOM/assembly lots, instrument IDs and calibration;
inspect polarity, shorts, component orientation and physical R21 DNP. Use a
protected charged pack or declared VBAT simulator with a current-limited setup.
Battery-less USB startup is unsupported. Keep charging and USB500 disabled in
the initial image. Do not bridge R21 to raw TS.

Stage the measurements: unpowered inspection → limited VBAT and rail/startup
waveforms → reset/standby and fault behavior → flash the recorded image → one
boot/fixture capture → sleep/wake and input-current measurements → any later
USB/charging experiment only under its separately reviewed procedure. Capture
EN1/EN2, MCU rail, VBUS/VSYS, charge control and independent meter/scope traces
where the [power protocol](51-power-safety-qualification.md) calls for them.
For flashing, use `make firmware-flash PORT=/dev/ttyACM0`, replacing the
example device with the inspected serial port. For capture, copy the complete
`make production-capture` example in [doc 72](72-firmware-bringup.md) and supply
the real chip ID, ELF hash, inventory and input/output paths. A `BRINGUP_PASS` validates a console record
and identity only. Retain failed captures and retest in a new run directory.

**Stop immediately** for the pack, electrical or charge-suspension conditions
listed in [doc 51](51-power-safety-qualification.md); isolate the unit under the
lab's lithium-battery procedure. For any unexplained rail, current, thermal or
pin behavior, remove power, preserve raw traces and record a failure before
repair or rework. Never invent a fixture log or convert an unmeasured check
into a qualification record.

## Experiment and product flight

After qualified first boards, use the [predeclared A/B protocol](50-thermal-ab-test-plan.md):
same electrical platform and firmware, serial-linked packs/enclosures,
calibrated reference, raw immutable samples, documented uncertainty and the
ordered decision gate. Charging Test 3 waits for its power/temperature gate.
An inconclusive interval stays inconclusive; it does not select a winner.

Implement and device-test the remaining [firmware contract](71-firmware-contract.md)
before closing firmware qualification. The product manifest
[`hardware/release-readiness.json`](../hardware/release-readiness.json) links
the required reviewed evidence. Run `make release-check` only after those
records and complete routing exist. For the finally reviewed printed revision,
create the matching Git tag as described in [release packaging](64-release-packaging.md),
then run `make release-package RELEASE_TAG=hw-a1` for a board actually marked
HW-A1 (substitute the matching revision for another board). Verify the ZIP,
sidecar checksum, source commit, included raw-evidence references and final
manufacturing review before authorizing the revised controlled series. A
prototype package or development pipeline PASS does not close product gates.

## Incident and session handoff

On a failed gate or bench incident, preserve the original log, board/pack
identity, instrument trace, command, tool versions and source commit. Mark the
affected manifest slot open, state the observed failure and containment, and
link a corrective change and fresh run. Never overwrite raw measurements or
silently edit a failed capture into a pass.

Before stopping or handing work to another person or agent, leave a short
checkpoint in the active work record: starting/current commit, touched files,
last commands and their exact results, evidence paths, open gates, physical
state of any unit, and the next safe action. On resuming, read that checkpoint
and `git status --short`, verify the source commit and current manifest state,
then rerun the affected gates. A prior session's claimed running task or PASS
is not evidence for the current tree.
