# 64 — Release export and packaging controls

Development exports are draft review artifacts. Product release requires
`make release-check`: clean ERC, clean DRC/parity with complete routing on both
variants, and all seven qualification-evidence records. The current design
does not meet that gate. Prototype-order review and packaging are implemented separately in
[the production handoff](65-prototype-to-production.md) and
`hardware/prototype-readiness.json`. Public engineering source prereleases do not
carry a manufacturing-readiness claim or a product release marker.

## One release path

Run `make release-package RELEASE_TAG=hw-a1` (or the revision actually printed
on the selected board). The packager checks the tag, requires a clean committed
source tree, runs gated fabrication exports and mandatory OpenSCAD mesh
generation, and checks the source commit again before archiving. An explicitly
supplied `RELEASE_COMMIT` must be the full current HEAD. The default archive and
SHA-256 sidecar are written under `_build/release/`.

The Python CLI is used by Make and applies the same live export gate when
invoked directly. `--validate-only` validates only the printed revision/tag;
it is not qualification and does not create an archive. `make release` and
`make outputs OUTPUT_CLASS=release` also enforce qualification. Unknown output
classes fail instead of silently selecting a mode.

Before starting an export, invalidate old release markers for both variants.
Keep draft markers until every board and shared schematic export succeeds.
Only then write the release markers. A failed exporter therefore cannot leave
a partially regenerated directory carrying a release marker from this run or
an earlier successful run.

## Archive completeness

The packager independently checks the qualification manifest/reports and
requires nonempty copper, mask, paste, silkscreen and outline Gerbers, drill,
CPL, assembly drawing, STEP, shared schematic PDF/netlist, board/project/rules,
schematic, used library footprints/symbols, BOM, model netlist, and both enclosure
meshes for the selected variant. Gerber filenames follow the actual KiCad 10
exports, including `F_Silkscreen` and `B_Silkscreen`. It rejects a remaining draft
marker even when a release marker is also present.

The reviewed evidence files referenced by `hardware/release-readiness.json`
travel in the archive at their repository-relative paths. Missing/empty evidence,
absolute or parent-traversing paths, and symlinks escaping the repository fail.
This proves that the referenced review records exist and are shipped; it does
not automatically judge their engineering content or bundle unlisted attachments.
The final reviewer must confirm raw-data accessibility and that evidence applies
to the manufactured revision.

`make test` injects missing manufacturing files/evidence, mixed draft/release
markers, failed exports/live gates, an incorrect source commit and an uncommitted
source tree. The success fixture verifies evidence inclusion and the archive
checksum. These fixtures are synthetic test data, never qualification evidence.
