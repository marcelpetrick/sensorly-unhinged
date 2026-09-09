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
availability and a signed assembly review before ordering. Generic passives also
need exact purchasable MPNs, effective capacitance at bias, voltage/tolerance and
inductor saturation checks. Owner: hardware maintainer; gate: prototype order.

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
