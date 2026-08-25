# ENV sensor - everything the project builds, buildable from here.
# AGENTS.md rule: if a step cannot be run from make, it is not part of the build.

KICAD_CLI ?= kicad-cli
PY        ?= python3
VARIANTS  := a b
ROOT      := $(CURDIR)
BUILD     := $(ROOT)/_build

.PHONY: all gen check drc outputs render bom clean help
.DEFAULT_GOAL := help

help:
	@echo "make gen      - regenerate both boards, project files, DRC rules and SVGs"
	@echo "make check    - generator-side rule checks only (no KiCad needed)"
	@echo "make drc      - KiCad DRC on both variants (errors fail the build)"
	@echo "make bom      - BOM + placement CSVs from the shared design model"
	@echo "make outputs  - gerbers, drill, BOM, CPL, STEP, PDF into hardware/outputs"
	@echo "make render   - KiCad 3D renders into docs/img"
	@echo "make all      - gen + check + drc + bom + outputs"

all: gen check drc bom outputs

gen:
	$(PY) -m tools.boardgen

check:
	$(PY) -m tools.boardgen --check-only

bom:
	$(PY) -m tools.bom

# Zones are left unfilled in the committed source so that `make gen` is
# byte-reproducible; the outputs pipeline fills them into a scratch copy.
define FILLED_RULE
$(BUILD)/$(1)/env-sensor-$(1).kicad_pcb: hardware/variant-$(1)/env-sensor-$(1).kicad_pcb \
                               hardware/variant-$(1)/env-sensor-$(1).kicad_pro \
                               hardware/variant-$(1)/env-sensor-$(1).kicad_dru
	@mkdir -p $(BUILD)/$(1)
	@cp hardware/variant-$(1)/env-sensor-$(1).kicad_pro $(BUILD)/$(1)/env-sensor-$(1).kicad_pro
	@cp hardware/variant-$(1)/env-sensor-$(1).kicad_dru $(BUILD)/$(1)/env-sensor-$(1).kicad_dru
	@printf '(fp_lib_table\n  (version 7)\n  (lib (name "sensorly")(type "KiCad")(uri "%s/hardware/lib/sensorly.pretty")(options "")(descr ""))\n)\n' "$(ROOT)" > $(BUILD)/$(1)/fp-lib-table
	@cp $$< $$@
	@$(KICAD_CLI) pcb drc --refill-zones --save-board -o /dev/null $$@ >/dev/null
endef
$(foreach v,$(VARIANTS),$(eval $(call FILLED_RULE,$(v))))

drc: $(foreach v,$(VARIANTS),$(BUILD)/$(v)/env-sensor-$(v).kicad_pcb)
	@for v in $(VARIANTS); do \
	  $(KICAD_CLI) pcb drc --severity-error --severity-warning \
	    --format json -o $(BUILD)/$$v/drc.json $(BUILD)/$$v/env-sensor-$$v.kicad_pcb \
	    >/dev/null; \
	  $(PY) -m tools.drc_gate $(BUILD)/$$v/drc.json $$v || exit 1; \
	done
	@echo "DRC gate passed for all variants"

outputs: $(foreach v,$(VARIANTS),$(BUILD)/$(v)/env-sensor-$(v).kicad_pcb) bom
	@for v in $(VARIANTS); do \
	  o=hardware/outputs/rev-$$v; \
	  mkdir -p $$o/gerber $$o/drill $$o/assembly $$o/step; \
	  $(KICAD_CLI) pcb export gerbers --no-protel-ext \
	    --layers "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts" \
	    -o $$o/gerber/ $(BUILD)/$$v/env-sensor-$$v.kicad_pcb >/dev/null; \
	  $(KICAD_CLI) pcb export drill --format excellon --drill-origin absolute \
	    --excellon-units mm --generate-map --map-format gerberx2 -o $$o/drill/ \
	    $(BUILD)/$$v/env-sensor-$$v.kicad_pcb >/dev/null; \
	  $(KICAD_CLI) pcb export pos --format csv --units mm --side both \
	    -o $$o/assembly/cpl-$$v.csv $(BUILD)/$$v/env-sensor-$$v.kicad_pcb >/dev/null; \
	  $(KICAD_CLI) pcb export pdf --layers "F.Cu,F.SilkS,F.Fab,Edge.Cuts" \
	    -o $$o/assembly/assembly-top-$$v.pdf $(BUILD)/$$v/env-sensor-$$v.kicad_pcb >/dev/null; \
	  $(KICAD_CLI) pcb export step --no-dnp --subst-models --force \
	    -o $$o/step/env-sensor-$$v.step $(BUILD)/$$v/env-sensor-$$v.kicad_pcb >/dev/null; \
	  echo "wrote $$o"; \
	done

render: $(foreach v,$(VARIANTS),$(BUILD)/$(v)/env-sensor-$(v).kicad_pcb)
	@mkdir -p docs/img
	@for v in $(VARIANTS); do \
	  $(KICAD_CLI) pcb render --side top --background opaque --quality high \
	    --width 760 --height 1200 --zoom 0.72 \
	    -o docs/img/render-$$v.png $(BUILD)/$$v/env-sensor-$$v.kicad_pcb >/dev/null; \
	  echo "wrote docs/img/render-$$v.png"; \
	done

clean:
	rm -rf $(BUILD)
