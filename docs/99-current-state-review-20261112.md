# Current implementation review — 2026-11-12

## Branch review scope

Base: `master` @ `13bac7b`   Head: `13bac7b`  
Files changed: 0   +0 / -0 lines

**Findings:** The integration-branch diff is empty: local and remote master
match. This concludes the literal reviewBranch run; it is not a claim that the
current implementation is defect-free.

**Verdict:** No unmerged branch changes to assess.

## Additional current-state audit

The requested implementation audit reviewed the journal and ESP backend,
bring-up/capture paths, development DRC gate, prototype/product gates and
packagers, their tests/call sites, and reader-facing documentation. The starting
revision was `13bac7b`. The following confirmed findings describe that revision;
all three have corrective commits. These are software/source findings, not
physical hardware qualification.

```text
#1  MEDIUM  Code  tools/package_release.py:140
    Rebuilding opens the existing reviewed ZIP with truncation before the replacement succeeds, leaving the previous checksum beside changed or partial bytes on failure. Stage the complete archive and checksum, then publish without replacing existing files; apply the same correction to package_prototype.py:39.

#2  MEDIUM  Code  tools/drc_gate.py:98
    Total-only budgeting accepts a new GND/USB-data airwire or another net regression when an unrelated connection closes. Enforce exact per-net counts and prohibit GND/USB-data opens independently of budget entries.

#3  MEDIUM  Code  firmware/main/journal.c:118
    Factory initialization checks only bank zero data, so blank headers with unexplained nonblank second-bank data are accepted as fresh media. Check both banks before initialization and reject nonblank data or read errors without writes or erases.
```

| Finding | Accepted fix | Evidence |
|---|---|---|
| Package replacement | `c467e7c` | Prior ZIP/checksum preserved on retry; staged write failure leaves no published package; archive/sidecar publication races preserve the competing file; both packagers covered. |
| Hidden net regression | `da5c966` | Reproducer changed a real A report's first open from +3V0 to GND with its total unchanged: old gate returned 0. New tests reject changed nets, explicitly budgeted GND/USB opens, inconsistent budgets and unidentified/mismatched endpoints. Actual A25/B19 reports still pass. |
| Ambiguous initialization | `0163925` | New fault cases assert CORRUPT/IO_ERROR, zero writes/erases and unchanged flash; the regression test fails against original `13bac7b`. Existing factory/torn-header recovery and sanitizer tests pass. This is not a demonstrated normal-append data-loss path. |

The combined `13bac7b...0163925` diff received an independent second review:
16 files, +478 / -204 lines; no new blocking Code/Architecture defect was
confirmed. Forty focused DRC/package/readiness/capture tests pass, as do the
live A/B development gates. The real pinned ESP-IDF v5.5.4 build passes with
image size `0x2f320` in the `0x1f0000` app partition. Log:
`/tmp/sensorly-current-review-idf-20261112.log`.

Package publication does not claim a two-file crash-atomic transaction: a ZIP
without its matching checksum is invalid. Journal recovery retains its
documented fail-closed partial-erase availability limit; automatic recovery
from every interruption and device endurance remain open.

## Combined verification

All 15 `./localPipeline.sh` stages pass on the `0163925` source: **154 host
regressions, firmware C host tests and 35 actual KiCad controls**, byte-identical
generated sources, enclosure checks, ERC, filled-board DRC/parity and draft
exports. Python 3.14.7 / KiCad 10.0.6; log:
`/tmp/sensorly-current-review-pipeline-20261112.log`.
Root ASan/UBSan checks pass (`/tmp/sensorly-current-review-sanitizers-20261112.log`).
Fresh filled reports retain A25/B19 with zero errors, warnings and parity;
the exact per-net gate passes, with no GND/USB-data airwires.

Both manufacture gates remain effective: `python3 -m tools.prototype_gate`
returns 1 with seven blockers, and `python3 -m tools.release_gate` returns 1
with nine blockers. These expected rejections retain the layout and missing
review/qualification requirements; they are not pipeline failures.

`xvfb-run -a make render` refreshed both board PNGs in `386f657`; both were
visually inspected. The shared schematic SVG differed only in export timestamp,
so that unrelated churn was discarded. No physical geometry changed. README
local link targets resolve to tracked files; documentation figures and whitespace
checks pass. New public CI is checked after pushing this review checkpoint.

## Reader-facing corrections

The README now leads with the first-PCB story, the thermal design question and
a side-by-side board/enclosure gallery. The AI disclosure, source prerelease,
verification limits and build procedures remain visible. The schematic links
to committed SVG/KiCad sources instead of an unpublished build PDF. The
floorplan summary now matches A25/B19 and explains guarded variant geometry
outside `variants.py`; dated historical checkpoints remain intact.

The githubAbout skill was applied to
[the repository](https://github.com/marcelpetrick/sensorly-unhinged).
The previous About described the first PCB as a shared electrical design with
compact and isolated layouts. Its topics were `esp32`, `pcb`, `electronics`,
`esp32-c6`, `humidity-sensor`, `kicad`, `open-source-hardware`, `openscad`,
`pcb-design`, and `temperature-sensor`.

Applied description:

> My very first PCB: an ESP32-C6 temperature/humidity sensor prototype in two layouts, exploring whether thermal isolation earns its extra space through one shared electrical design and a planned A/B experiment.

Applied ten topics: `esp32-c6`, `esp-idf`, `kicad`, `openscad`,
`open-source-hardware`, `pcb-design`, `temperature-sensor`, `humidity-sensor`,
`thermal-design`, `battery-powered`.

Every claim has a source: first-PCB identity is the author's explicit statement
and README; the shared parts/electrical model is `tools/boardgen/design.py`;
layout geometry is `variants.py` and guarded route modules; the experiment and
5+5 quantity are doc 50; prototype limits are `plan.md` and the open manifests.
The firmware folder and pinned workflow support ESP-IDF; the mechanical folder
supports OpenSCAD; LICENSE supports the open-source description. No measured
thermal improvement, working physical device or manufacturing approval is
claimed. GitHub metadata was read back after applying the change.

Alternative short description: “My first PCB, twice: compact and thermally
isolated ESP32-C6 sensor prototypes sharing one electrical design.” Technical
alternative: “Parametric KiCad/OpenSCAD A/B sensor prototypes with shared ESP-IDF
bring-up firmware and a predeclared thermal experiment.” Possible topic swaps:
`electronics`, `hardware-prototyping`, `sensor-node`.

## Engineering disposition and next work

The reproducible build, shared electrical platform, fault tests and explicit
source/supplier/physical gates support an inspectable prototype workflow.
They do not substitute for an experienced hardware reviewer inspecting the
finished electrical/current/return paths, exact parts/CPL and supplier process.
A25/B19 open connections block manufacturing. Supplier approvals and bench
measurements are still absent; all associated manifest slots remain open.

Continue the ordered root plan: finish U4/control escapes and supply/fixture
branches on both boards; review the fully filled layouts with zero opens;
obtain controlled pack/harness, stackup, assembly and order approvals; produce
and inspect 5 A + 5 B; then qualify device behavior and run the predeclared
experiment. No order or physical test was performed in this audit.
