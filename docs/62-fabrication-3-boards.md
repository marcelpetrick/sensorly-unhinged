# 62 — Fabricating Three Boards

The question: **who will make just three of these, and what does the antenna
need from them?**

Most low-cost fabs have a five-piece minimum. Two vendors sell in multiples of
three as their standard product, and three German fabs have no minimum at all.

---

## 1. Shortlist

| Vendor | Where | MOQ | 4-layer | Notes |
|---|---|---|---|---|
| **AISLER** | NL/DE, delivers from Germany | **multiples of 3** | yes | Priced purely by board area × quantity. Entry price €14.20. No import VAT, no customs, short shipping. Also offers assembly. **Best fit for this request.** |
| **OSH Park** | USA | **multiples of 3** | yes, $10/in² incl. 3 copies | FR408-HR, 1 oz outer / **0.5 oz inner**, 1.6 mm, 5 mil/5 mil, 10 mil drill, 9–14 days. US import + 19 % VAT into DE. |
| **Multi-CB** | Germany | **1 piece** | yes | No minimum quantity, express from 1 working day. Calculator-based. |
| **LeitOn** | Berlin, Germany | **1 piece** | yes, 3-day express on multilayer | German and Asian production at different price points. |
| **Beta LAYOUT (PCB-POOL)** | Germany | prototype pool | yes (4/6 layer) | Climate-neutral pool service, calculator up to 1000 pcs. |
| Eurocircuits | Belgium | pool, low | yes | EU, well-documented stackups. |
| JLCPCB / PCBWay | China | **5 pieces** | yes | Cheapest per board, but cannot do three, and adds freight + 19 % VAT. |

### What three boards actually costs, bare

Computed from the real outlines at OSH Park's published 4-layer rate:

| Board | Size | Area | OSH Park 4-layer (3 copies) | Per board |
|---|---|---:|---:|---:|
| A — Compact | 30 × 34 mm | 1.58 in² | $15.81 | $5.27 |
| B — Thermally isolated | 28 × 51 mm | 2.21 in² | $22.13 | $7.38 |
| **Both, 3 + 3 = 6 boards** | | | **$37.94** | **$6.32** |

AISLER prices by area as well and quotes instantly from the uploaded files;
their published entry point is €14.20 and roughly €9 for three small boards, so
for boards this size expect the same order of magnitude as OSH Park, with no
customs and a much shorter trip. **Get the real quote from the uploader — these
two lines are for sizing the decision, not for the accounting.**

### Recommendation

**AISLER for three boards.** It is the only vendor on the list that is
simultaneously a native "multiples of three" service, inside the EU, and short
on shipping. OSH Park is the direct alternative and its stackup is published in
detail, but see §3 — its inner copper is half the weight, which for *this*
project is not a neutral difference.

If the order ever grows past three, the calculus flips back to JLCPCB, where the
5-piece minimum stops being a constraint and the panelisation saving in
`61-cost-reduction.md` becomes available.

---

## 2. What the antenna needs from the fab — and what it doesn't

The radio is a **pre-certified module with its own PCB antenna**. That removes
most of what people assume an RF board needs. What is left is short and specific.

### It does need

1. **The outline routed as drawn, with the keep-out kept clear.** The antenna
   sits in a full-width strip at the top of both boards that carries no copper
   on any of the four layers. That is already in the Gerbers; the fab simply has
   to not add anything to it.

2. **No panel rails, tabs or mouse-bites inside the antenna strip — and
   absolutely none across Variant B's neck.** Every pooled service panelises
   internally, so break-off tabs land somewhere on your outline. In the antenna
   strip a tab is only cosmetic (bare FR-4, no copper, no RF effect). **In the
   3.5 mm neck it is a stress riser at the single weakest point of the board.**
   State this on the order in one sentence:

   > *Please keep break-off tabs off the narrow neck between the main board and
   > the sensor island, and off the top 6 mm of the board.*

3. **ENIG, not HASL.** The SHT45 is a 0.5 mm-pitch DFN and the charger is a
   3 × 3 mm QFN with a centre pad. HASL leaves a domed, uneven surface that
   makes fine-pitch placement and inspection worse. The price difference at
   three boards is small; the yield difference is not.

4. **Outline tolerance stated.** At a 3.5 mm nominal neck, ±0.2 mm of routing
   tolerance is ±6 % on the FR-4 conduction term — thermally irrelevant, but it
   is the mechanical margin on the thinnest feature of the board, so it is worth
   knowing which way the fab errs. Ask for the router bit diameter too.

### It does *not* need

- **Controlled impedance.** There is no RF trace on this board — the antenna is
  inside the module. The only differential pair is USB D+/D−, running about
  30 mm at full speed (12 Mbit/s). Specifying controlled impedance here would
  cost money and buy nothing. This is worth saying out loud, because "it has USB
  and an antenna, so it needs controlled impedance" is a reflex that quietly
  doubles small-batch quotes.
- **Special laminate.** Standard FR-4 is correct. The module's antenna was
  characterised against a normal carrier; low-loss laminate changes nothing that
  the keep-out has not already handled.
- **Soldermask restrictions over the antenna.** Mask is a thin dielectric and is
  fine there.
- **Any minimum feature we don't already meet.** Tightest features on the board
  are 0.15 mm island traces and 0.2 mm drills, both inside every vendor above.

---

## 3. The trap: stackup is an experimental variable

This one matters more than the price.

Variant A's whole problem is that its inner copper planes conduct **112×** more
heat than the FR-4 they sit in. That number is computed for **1 oz (35 µm)
copper on all four layers**, which is what `docs/45-thermal-model.md` assumes and
what most fabs supply by default.

OSH Park's 4-layer service is **1 oz outer, 0.5 oz inner**. That halves the inner
planes and therefore materially reduces Variant A's conduction — moving the
result *towards* Variant B and shrinking the very effect the experiment is
trying to measure.

Two consequences, both non-negotiable:

- **Every board in the comparison must come from one fab, one stackup, one
  order.** Mixing an AISLER A with an OSH Park B would not be an A/B test of
  geometry; it would be an A/B test of copper weight.
- **Record the actual stackup with the results.** It belongs in
  `measurements/thermal/` alongside the data, and it is a new entry on the
  "what would make this experiment invalid" list in
  `50-thermal-ab-test-plan.md`.

If the boards do come back with 0.5 oz inner layers, re-run `make thermal` with
`T_CU` halved for the inner layers before comparing model to measurement.

---

## 4. What to send them

Everything a bare-board order needs is already generated:

```
hardware/outputs/rev-a/gerber/     11 layers, RS-274X
hardware/outputs/rev-a/drill/      Excellon + map
hardware/outputs/rev-b/gerber/
hardware/outputs/rev-b/drill/
```

Both variants are 4-layer FR-4, 1.6 mm, and both fit inside 50 × 50 mm. Run
`make outputs` first — the fab package is built by CI, not committed.

For assembled boards rather than bare ones, add:

```
hardware/outputs/rev-*/assembly/cpl-*.csv    placement
hardware/outputs/bom.csv                     with MPNs and second sources
hardware/outputs/rev-*/assembly/*.pdf        assembly drawing (F.Fab)
```

Note that at three boards, assembly is usually the wrong call: the setup,
stencil and feeder fees are per *order*, not per board, so they land on three
units instead of ten. Three bare boards hand-populated is the cheaper route if
you have a reflow plate; three assembled boards is the cheaper route if your
time is worth anything. The break-even is roughly where the assembly fixed cost
(~$35–45) equals the hours you would spend on 190 solder joints × 3.
