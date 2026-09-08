# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
# ENV sensor - everything the project builds, buildable from here.
# AGENTS.md rule: if a step cannot be run from make, it is not part of the build.

KICAD_CLI ?= kicad-cli
PY        ?= python3
VARIANTS  := a b
ROOT      := $(CURDIR)
BUILD     := $(ROOT)/_build

# A successful final echo must never conceal a failed exporter in a loop.
.SHELLFLAGS := -eu -c
.DELETE_ON_ERROR:
# Generation mutates inputs consumed by later goals, including `make -j all`.
.NOTPARALLEL:

.PHONY: all gen check erc drc outputs render bom thermal cost mech license clean help test
.DEFAULT_GOAL := help
.PHONY: release-check release
.PHONY: power

power:
	$(PY) -m tools.power_budget

help:
	@echo "make gen      - regenerate the schematic, both boards, project files, DRC rules and SVGs"
	@echo "make check    - generator-side rule checks only (no KiCad needed)"
	@echo "make license  - verify every authored source carries an SPDX header"
	@echo "make erc      - KiCad ERC on the shared schematic"
	@echo "make drc      - KiCad DRC + schematic parity on both variants"
	@echo "make bom      - BOM + placement CSVs from the shared design model"
	@echo "make outputs  - gerbers, drill, BOM, CPL, STEP, PDF into hardware/outputs"
	@echo "make render   - KiCad 3D renders + schematic SVG into docs/img"
	@echo "make thermal  - regenerate docs/45-thermal-model.md from the geometry"
	@echo "make cost     - regenerate docs/60-manufacturing-cost.md from the design"
	@echo "make mech     - enclosure model, checks, OpenSCAD params (+ STL if openscad)"
	@echo "make all      - gen + check + drc + bom + outputs"

all: license gen check erc drc bom thermal cost mech outputs

gen:
	$(PY) -m tools.boardgen

check:
	$(PY) -m tools.boardgen --check-only

test:
	$(PY) -m unittest discover -s tools/tests -v

.PHONY: test-kicad
test-kicad: $(BUILD)/b/env-sensor-b.kicad_pcb
	KICAD_CLI=$(KICAD_CLI) $(PY) -m unittest discover -s tools/tests_kicad -v

license:
	@$(PY) -m tools.check_license

bom:
	$(PY) -m tools.bom

thermal:
	@$(PY) -m tools.mkthermal
	@echo "wrote docs/45-thermal-model.md"

cost:
	@$(PY) -m tools.cost --write

mech:
	@$(PY) -m tools.boardgen.enclosure --write >/dev/null
	@echo "wrote docs/80-enclosure.md and mechanical/params-*.scad"
	@if command -v openscad >/dev/null 2>&1; then \
	  for v in $(VARIANTS); do \
	    for p in base lid; do \
	      openscad -D "part=\"$$p\"" -o mechanical/case-$$v-$$p.stl \
	        mechanical/case-$$v.scad; \
	        echo "wrote mechanical/case-$$v-$$p.stl"; \
	    done; \
	  done; \
	  $(PY) -m tools.check_stl; \
	  $(PY) -m tools.check_case_interference; \
	else \
	  echo "openscad not installed - STL export skipped"; \
	fi

.PHONY: mech-render
mech-render:
	@for v in $(VARIANTS); do \
	    openscad -D 'part="base"' --camera=20,28,10,55,0,25,190 \
	      --imgsize=640,640 --colorscheme=Tomorrow \
	      -o docs/img/case-$$v-base.png mechanical/case-$$v.scad; \
	    openscad -D 'part="lid"' --camera=20,28,2,235,0,25,190 \
	      --imgsize=640,640 --colorscheme=Tomorrow \
	      -o docs/img/case-$$v-lid.png mechanical/case-$$v.scad; \
	  done; \
	  echo "wrote docs/img/case-*.png"

# Zones are left unfilled in the committed source so that `make gen` is
# byte-reproducible; the outputs pipeline fills them into a scratch copy.
define FILLED_RULE
$(BUILD)/$(1)/env-sensor-$(1).kicad_pcb: hardware/variant-$(1)/env-sensor-$(1).kicad_pcb \
                               hardware/variant-$(1)/env-sensor-$(1).kicad_pro \
                               hardware/variant-$(1)/env-sensor-$(1).kicad_dru \
                               hardware/schematic/env-sensor.kicad_sch \
                               hardware/lib/sensorly.kicad_sym \
                               $(wildcard hardware/lib/sensorly.pretty/*.kicad_mod) Makefile
	@mkdir -p $(BUILD)/$(1)
	@cp hardware/variant-$(1)/env-sensor-$(1).kicad_pro $(BUILD)/$(1)/env-sensor-$(1).kicad_pro
	@cp hardware/variant-$(1)/env-sensor-$(1).kicad_dru $(BUILD)/$(1)/env-sensor-$(1).kicad_dru
	@cp hardware/schematic/env-sensor.kicad_sch $(BUILD)/$(1)/env-sensor-$(1).kicad_sch
	@printf '(sym_lib_table\n  (version 7)\n  (lib (name "sensorly")(type "KiCad")(uri "%s/hardware/lib/sensorly.kicad_sym")(options "")(descr ""))\n)\n' "$(ROOT)" > $(BUILD)/$(1)/sym-lib-table
	@printf '(fp_lib_table\n  (version 7)\n  (lib (name "sensorly")(type "KiCad")(uri "%s/hardware/lib/sensorly.pretty")(options "")(descr ""))\n)\n' "$(ROOT)" > $(BUILD)/$(1)/fp-lib-table
	@cp $$< $$@
	@$(KICAD_CLI) pcb drc --refill-zones --save-board -o /dev/null $$@ >/dev/null
endef
$(foreach v,$(VARIANTS),$(eval $(call FILLED_RULE,$(v))))

erc:
	@mkdir -p $(BUILD)
	@$(KICAD_CLI) sch erc --severity-error --severity-warning --exit-code-violations \
	  --format json -o $(BUILD)/erc.json hardware/schematic/env-sensor.kicad_sch \
	  || { echo "ERC violations - see $(BUILD)/erc.json"; exit 1; }

drc: $(foreach v,$(VARIANTS),$(BUILD)/$(v)/env-sensor-$(v).kicad_pcb)
	@for v in $(VARIANTS); do \
	  $(KICAD_CLI) pcb drc --severity-error --severity-warning --schematic-parity \
	    --format json -o $(BUILD)/$$v/drc.json $(BUILD)/$$v/env-sensor-$$v.kicad_pcb \
	    >/dev/null; \
	  $(PY) -m tools.drc_gate $(BUILD)/$$v/drc.json $$v || exit 1; \
	done
	@echo "DRC gate passed for all variants"

release-check: erc drc
	$(PY) -m tools.release_gate

# Qualification runs before any release export. Development exports stay draft.
release: release-check
	$(MAKE) outputs
	@echo "Qualification gate passed; outputs are available for final manufacturing review"

outputs: drc bom
	@for v in $(VARIANTS); do \
	  o=hardware/outputs/rev-$$v; \
	  mkdir -p $$o/gerber $$o/drill $$o/assembly $$o/step; \
	  printf '%s\n' 'DRAFT DESIGN REVIEW ONLY - NOT FOR FABRICATION' \
	    'Unfinished routing and qualification are tracked in hardware/release-readiness.json.' > $$o/DRAFT.txt; \
	  $(KICAD_CLI) pcb export gerbers --no-protel-ext \
	    --layers "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts" \
	    -o $$o/gerber/ $(BUILD)/$$v/env-sensor-$$v.kicad_pcb >/dev/null; \
	  $(KICAD_CLI) pcb export drill --format excellon --drill-origin absolute \
	    --excellon-units mm --generate-map --map-format gerberx2 -o $$o/drill/ \
	    $(BUILD)/$$v/env-sensor-$$v.kicad_pcb >/dev/null; \
	  $(KICAD_CLI) pcb export pos --format csv --units mm --side both --exclude-dnp \
	    -o $$o/assembly/cpl-$$v.csv $(BUILD)/$$v/env-sensor-$$v.kicad_pcb >/dev/null; \
	  $(KICAD_CLI) pcb export pdf --layers "F.Cu,F.SilkS,F.Fab,Edge.Cuts" \
	    -o $$o/assembly/assembly-top-$$v.pdf $(BUILD)/$$v/env-sensor-$$v.kicad_pcb >/dev/null; \
	  $(KICAD_CLI) pcb export step --no-dnp --subst-models --force \
	    -o $$o/step/env-sensor-$$v.step $(BUILD)/$$v/env-sensor-$$v.kicad_pcb >/dev/null; \
	  echo "wrote $$o"; \
	done
	@mkdir -p hardware/outputs/schematic
	@$(KICAD_CLI) sch export pdf --black-and-white \
	  -o hardware/outputs/schematic/env-sensor.pdf \
	  hardware/schematic/env-sensor.kicad_sch >/dev/null
	@$(KICAD_CLI) sch export netlist --format kicadsexpr \
	  -o hardware/outputs/schematic/env-sensor.net \
	  hardware/schematic/env-sensor.kicad_sch >/dev/null
	@echo "wrote hardware/outputs/schematic"

render: $(foreach v,$(VARIANTS),$(BUILD)/$(v)/env-sensor-$(v).kicad_pcb)
	@mkdir -p docs/img
	@for v in $(VARIANTS); do \
	  $(KICAD_CLI) pcb render --side top --background opaque --quality high \
	    --width 760 --height 1200 --zoom 0.72 \
	    -o docs/img/render-$$v.png $(BUILD)/$$v/env-sensor-$$v.kicad_pcb >/dev/null; \
	  echo "wrote docs/img/render-$$v.png"; \
	done
	@$(KICAD_CLI) sch export svg --black-and-white --no-background-color \
	  -o docs/img/ hardware/schematic/env-sensor.kicad_sch >/dev/null
	@mv docs/img/env-sensor.svg docs/img/schematic.svg
	@echo "wrote docs/img/schematic.svg"

clean:
	rm -rf $(BUILD)
