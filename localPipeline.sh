#!/usr/bin/env bash
# Local pipeline for the ENV sensor hardware project.
#
# Same shape as the one in GarminActivityMap: each step is a function, sets
# STEP_DETAIL, and the summary at the end says PASS/FAIL with one useful line.
# What differs is what a hardware repo has to prove - that the generated boards
# still match the model, that KiCad still agrees with them, and that the numbers
# written in the specs still match the geometry.
#
# Everything except the KiCad steps runs without KiCad installed.
set -u -o pipefail

cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1

PYTHON="${PYTHON:-python3}"
KICAD_CLI="${KICAD_CLI:-kicad-cli}"
SKIP_OUTPUTS="${SKIP_OUTPUTS:-0}"

tmp_dir="$(mktemp -d)" || exit 1
trap 'rm -rf "$tmp_dir"' EXIT

step_names=()
step_results=()
step_details=()
STEP_DETAIL=""

run_step() {
  local name="$1"
  shift

  printf '\n==> %s\n' "$name"
  step_names+=("$name")
  STEP_DETAIL=""
  if "$@"; then
    step_results+=("PASS")
    step_details+=("${STEP_DETAIL:-completed}")
    printf 'PASS: %s\n' "$name"
  else
    step_results+=("FAIL")
    step_details+=("${STEP_DETAIL:-see step output above}")
    printf 'FAIL: %s\n' "$name"
  fi
}

skip_step() {
  local name="$1" why="$2"
  printf '\n==> %s\n' "$name"
  step_names+=("$name")
  step_results+=("SKIP")
  step_details+=("$why")
  printf 'SKIP: %s (%s)\n' "$name" "$why"
}

last_line() {
  sed -e 's/^[= ]*//' -e 's/[= ]*$//' "$1" | awk 'NF { line = $0 } END { print line }'
}

have_kicad() { command -v "$KICAD_CLI" >/dev/null 2>&1; }

# --------------------------------------------------------------------------
toolchain() {
  if ! command -v "$PYTHON" >/dev/null 2>&1; then
    STEP_DETAIL="$PYTHON not found on PATH"
    return 1
  fi
  local py kc
  py="$("$PYTHON" --version 2>&1)" || return 1
  if have_kicad; then
    kc="kicad-cli $("$KICAD_CLI" version 2>/dev/null)"
  else
    kc="kicad-cli MISSING (ERC/DRC/outputs will be skipped)"
  fi
  command -v make >/dev/null 2>&1 || { STEP_DETAIL="make not found"; return 1; }
  STEP_DETAIL="$py; $kc"
}

syntax() {
  bash -n localPipeline.sh || return 1
  local log="$tmp_dir/compile.log"
  if ! "$PYTHON" -m compileall -q tools 2>&1 | tee "$log"; then
    STEP_DETAIL="$(last_line "$log")"
    return 1
  fi
  # The Makefile is the single build entry point; a broken one is a broken repo.
  make -n help >/dev/null 2>&1 || { STEP_DETAIL="Makefile does not parse"; return 1; }
  STEP_DETAIL="shell, Python and Makefile parse"
}

libraries() {
  local log="$tmp_dir/lib.log"
  if ! "$PYTHON" - >"$log" 2>&1 <<'PY'
import sys
sys.path.insert(0, "tools")
from pathlib import Path
from boardgen import geometry as G
from boardgen.design import PARTS
from boardgen.sch import LIB, Library, _symbol_for

bad = 0
for p in Path("hardware/lib/sensorly.pretty").glob("*.kicad_mod"):
    d = 0
    for ch in p.read_text():
        d += ch == "("
        d -= ch == ")"
    if d:
        print(f"UNBALANCED s-expression: {p}")
        bad += 1
for p in PARTS:
    try:
        G.get(p.footprint)
    except Exception as exc:
        print(f"{p.ref}: footprint {p.footprint} not usable: {exc}")
        bad += 1
lib = Library(LIB)
for p in PARTS:
    name = _symbol_for(p.ref)
    if name not in lib.symbols:
        print(f"{p.ref}: symbol {name} missing from sensorly.kicad_sym")
        bad += 1
print(f"{len(PARTS)} parts resolve against "
      f"{len(list(Path('hardware/lib/sensorly.pretty').glob('*.kicad_mod')))} "
      f"footprints and {len(lib.symbols)} symbols")
sys.exit(1 if bad else 0)
PY
  then
    cat "$log"
    STEP_DETAIL="$(last_line "$log")"
    return 1
  fi
  cat "$log"
  STEP_DETAIL="$(last_line "$log")"
}

generator_rules() {
  local log="$tmp_dir/check.log"
  if ! make check 2>&1 | tee "$log"; then
    STEP_DETAIL="$(grep -c 'ERROR' "$log" || true) rule errors"
    return 1
  fi
  STEP_DETAIL="$(grep -c 'ERROR' "$log" || true) rule errors on both variants"
}

reproducibility() {
  local log="$tmp_dir/gen.log"
  make gen thermal bom cost >"$log" 2>&1 || {
    STEP_DETAIL="$(last_line "$log")"
    return 1
  }
  local paths=(hardware/schematic hardware/variant-a hardware/variant-b
               hardware/lib hardware/outputs/bom.csv hardware/outputs/netlist.txt
               docs/45-thermal-model.md docs/60-manufacturing-cost.md
               docs/61-cost-reduction.md
               docs/img/floorplan-a.svg docs/img/floorplan-b.svg)
  if ! git diff --quiet -- "${paths[@]}"; then
    printf 'generated files differ from the committed ones:\n'
    git diff --stat -- "${paths[@]}"
    STEP_DETAIL="regenerated output drifted; commit it or fix the generator"
    return 1
  fi
  STEP_DETAIL="schematic, both boards and all generated docs regenerate identically"
}

doc_consistency() {
  local log="$tmp_dir/docs.log"
  if ! "$PYTHON" -m tools.check_docs 2>&1 | tee "$log"; then
    STEP_DETAIL="$(last_line "$log")"
    return 1
  fi
  STEP_DETAIL="$(last_line "$log")"
}

bom_sanity() {
  local log="$tmp_dir/bom.log"
  if ! "$PYTHON" -m tools.bom 2>&1 | tee "$log"; then
    STEP_DETAIL="$(last_line "$log")"
    return 1
  fi
  if grep -q 'no second source recorded' "$log"; then
    STEP_DETAIL="$(grep 'no second source' "$log")"
    return 1
  fi
  STEP_DETAIL="$(grep -o '[0-9]* lines, [0-9]* placements' "$log" | head -n1)"
}

erc_step() {
  local log="$tmp_dir/erc.log"
  if ! make erc 2>&1 | tee "$log"; then
    STEP_DETAIL="$(last_line "$log")"
    return 1
  fi
  STEP_DETAIL="$(grep -o 'Found [0-9]* violations' "$log" | head -n1)"
}

drc_step() {
  local log="$tmp_dir/drc.log"
  if ! make drc 2>&1 | tee "$log"; then
    STEP_DETAIL="$(grep -E 'ERROR|PARITY|unconnected went' "$log" | head -n1)"
    STEP_DETAIL="${STEP_DETAIL:-DRC gate failed}"
    return 1
  fi
  STEP_DETAIL="$(grep 'variant a' "$log" | sed 's/^ *//')"
}

fab_outputs() {
  local log="$tmp_dir/outputs.log"
  if ! make outputs >"$log" 2>&1; then
    cat "$log"
    STEP_DETAIL="$(last_line "$log")"
    return 1
  fi
  local missing=0 v f
  for v in a b; do
    for f in "gerber/env-sensor-$v-F_Cu.gbr" "gerber/env-sensor-$v-In1_Cu.gbr" \
             "gerber/env-sensor-$v-In2_Cu.gbr" "gerber/env-sensor-$v-B_Cu.gbr" \
             "gerber/env-sensor-$v-Edge_Cuts.gbr" "drill/env-sensor-$v.drl" \
             "assembly/cpl-$v.csv" "step/env-sensor-$v.step"; do
      if [ ! -s "hardware/outputs/rev-$v/$f" ]; then
        printf 'missing or empty: hardware/outputs/rev-%s/%s\n' "$v" "$f"
        missing=$((missing + 1))
      fi
    done
  done
  if [ "$missing" -gt 0 ]; then
    STEP_DETAIL="$missing expected fab files missing or empty"
    return 1
  fi
  local size
  size="$(du -sh hardware/outputs 2>/dev/null | cut -f1)"
  STEP_DETAIL="4-layer gerbers, drill, CPL and STEP present for both variants (${size:-?})"
}

# --------------------------------------------------------------------------
run_step "Toolchain" toolchain
run_step "Syntax" syntax
run_step "Libraries" libraries
run_step "Generator Rules" generator_rules
run_step "Reproducibility" reproducibility
run_step "Doc Consistency" doc_consistency
run_step "BOM" bom_sanity

if have_kicad; then
  run_step "ERC" erc_step
  run_step "DRC + Parity" drc_step
  if [ "$SKIP_OUTPUTS" = "1" ]; then
    skip_step "Fab Outputs" "SKIP_OUTPUTS=1"
  else
    run_step "Fab Outputs" fab_outputs
  fi
else
  skip_step "ERC" "kicad-cli not installed"
  skip_step "DRC + Parity" "kicad-cli not installed"
  skip_step "Fab Outputs" "kicad-cli not installed"
fi

printf '\n========== Local Pipeline Summary ==========\n'

failed=0
for index in "${!step_names[@]}"; do
  printf '%-17s : %-4s %s\n' \
    "${step_names[$index]}" "${step_results[$index]}" "${step_details[$index]}"
  if [ "${step_results[$index]}" = "FAIL" ]; then
    failed=1
  fi
done

printf '============================================\n'

exit "$failed"
