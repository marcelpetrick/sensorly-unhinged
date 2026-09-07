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
