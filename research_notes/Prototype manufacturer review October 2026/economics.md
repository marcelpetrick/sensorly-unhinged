<!-- SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it> -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->

# Pooling, panel economics, sourcing and vendor selection

Research snapshot: 15 October 2026. No vendor contacted, files uploaded or orders placed. Public fees are evidence; calculated budgets below are assumptions, not quotations.

## What savings are defensible for three A plus three B?

### Takeaway

Consolidate procurement and shipment first. A mixed A+B panel might save a setup and feeder load, but needs a reviewed quotation. An identical electrical BOM does not turn two placement coordinate sets into one assembly program.

### Cited Findings

- Repository snapshot 23a7fd6: A bounding rectangle30×34=1,020mm²; B bounding rectangle30×51=1,530mm², actual polygon1,210mm² (body1,020+neck28+island162). B neck3.5×8mm; island18×9mm. Source: tools/boardgen/variants.py.
- Current BOM: 46 fitted placements, 26 unique fitted MPNs; R21 DNP. Fitted package-pad count: 198 SMT + 4 USB shield PTH joints. tools.cost.measure counts 47/200 because it includes DNP. Sources: hardware/outputs/bom.csv; tools/boardgen/design.py; tools/cost.py.
- JLCPCB published fees: Economic setup$8.18, stencil$1.53, hand labor$3.58/order, extended feeder$3.07/type. Standard single-side setup$25.56, stencil$8.21, feeder$1.53/type. Mixed-design panel fee$8.21; SMT$0.0016/joint; manual$0.0164/joint; X-ray additional. [JLC fees](https://jlcpcb.com/help/article/pcb-assembly-price)
- Separable boards with different traces/silkscreen count as different designs and can incur fabrication charges inside one panel. [JLC design policy](https://jlcpcb.com/quote/pcbOrderFaq/Different%20Design%20in%20Panel)
- JLC default panel edges 5 mm; complex outlines require customer panelization. [JLC panels](https://jlcpcb.com/help/article/how-do-i-order-a-panel)
- PCBWay requires an assembly array below 50×100 mm or for odd outlines, and rails where edge clearance is insufficient. [PCBWay reminders](https://www.pcbway.com/assembly-special-remind.html)
- V-score must continue across the panel; mixed irregular boards instead need tab routes. [PCBWay panel requirements](https://www.pcbway.com/pcb_prototype/Panel_Requirements_for_Assembly.html)
- JLC offers combined shipping and 15 days free storage; freight depends on combined weight. [Combined shipping](https://jlcpcb.com/help/article/combine-shipping-service)
- Adding jobs during production can incur incremental shipping; coupons cannot be used on combined new orders/additions. [Adding orders](https://jlcpcb.com/help/article/how-to-add-a-new-order-to-your-existing-order); [coupon policy](https://jlcpcb.com/help/article/how-do-i-use-a-coupon-for-my-order)

### Inferences

Use quotation variables:

```text
M = exact fitted BOM unit procurement cost, including markup/allowances
F_A,F_B = design NRE/stencil/feeder charges
B_A,B_B = bare PCB lot charges, including minimum quantities
V = variable placement/manual/X-ray/inspection charge
T = freight; D = duty; K = carrier/broker fees

Separate jobs, consolidated parcel:
C_sep = B_A+B_B+F_A+F_B+6*M+V_A+V_B+T+D+K

Accepted one-A-plus-one-B panel, three assembled panels:
C_mix = B_panel+F_panel+mixed_design_fees+6*M+V_panel+T_panel+D+K

Panel wins if avoided fixed charges exceed:
extra area/routing/design fees + panel engineering + extra freight/scrap risk.
```

A side-by-side sketch with a 2 mm route gap and 5 mm perimeter frame is 72×61=4,392mm². Both bounding rectangles sum 2,550mm²; actual FR-4 sum 2,230mm². Utilization is58.1% bounding or50.8% actual. This is not an approved or optimized panel. Actual tooling, fiducials, clamping and vendor minimum dimensions may enlarge it; rotated or stacked placement may improve it. Billing area is not necessarily routed polygon area. B does not fit 50×50 mm.

A paired panel ordered at MOQ 5 produces 5 A + 5 B bare boards. Ask whether only three panels can be populated and two returned bare. Five bare boards per design can likewise permit only three assemblies per design: bare MOQ and assembly MOQ differ.

Tabs must avoid the B neck, sensor island and top approximately 6 mm RF strip. Obtain a signed panel drawing, support during stencil/placement/reflow, depanelization method with main-body support, slot tolerance and cutter diameter. Straight V-score cannot define B.

Use one fab, stackup and process lot for both variants where possible. Shared components permit pooled purchasing, but each CPL and its panel coordinate transform, rotation/pin1 review and stencil pattern remain necessary; C6 rotates differently.

Conditional Economic fixed fees:
F(E)=13.29+3.07E USD, including hand labor. E is extended types. E=9 reproduces the old model's unverified nine likely extended types; all 26 exact MPNs need matching. F(9)=$40.92; F(26)=$93.11. One accepted job plus$8.21 panel fee instead of two jobs could save$32.71–84.90 (€29.22–75.84 at ECB below), before extra panel fabrication/engineering/inspection. This is an opportunity bound, not a vendor offer.

Fitted variable illustration excluding X-ray:
198×.0016+4×.0164=$.3824/board.

A conditional partial Economic budget for 3+3:

| Input | Assumption |
|---|---:|
| Two jobs' fixed fees, E=9–26 |$81.84–186.22|
| Two small 4-layer fabrication lots |$20–60|
| Six boards' variable placement/manual |$2.29|
| X-ray/additional inspection allowance |$15–40|
| Freight |$20–40|
| BOM planning allowance |€12–18×6=€72–108|
| Calculation before VAT, duty, carrier fees |€196–401|
| With 19% non-IOSS consumer VAT, before duty/carrier fees |€234–478|

These are assumed inputs, not current quotations. Standard may be required or cheaper. This is not a bounded all-in price: rigid-board fixtures, exact component excess/minimum purchase lots, test engineering, panel engineering, special handling and functional testing remain unquoted and can add cost beyond the range.

Central sensitivity example: E15 gives two fixed jobs$118.68; variable$2.29; assumed fabrication$30, inspection$25, freight$30, BOM€15×6. Total≈€274 net/€326 gross before D/K and excluded extras. One accepted mixed-panel setup plus$8.21, with fab increasing to$45, gives≈€242 net/€288 gross. Illustrated benefit≈€38 gross, not half the bill. Exact arithmetic is separate €273.99 net/€326.05 gross versus mixed €241.71 net/€287.64 gross.

Increasing to 5+5 adds 4M plus about$1.53 placement before inspection/fabrication changes. At unchanged M €12–18 that adds about€59–87consumer cash before extras. Lower unit cost does not mean lower program cash.

### Gaps

No received board quotation, panel approval, matched part classifications, minimum assembled panel count or freight quote. Mixed-panel acceptance and savings remain unproven.

## What sourcing, tax and ancillary work affects the budget?

### Takeaway

Six PCBAs are only part of six complete samples. Exact parts and handling come first; budget packs/cases separately unless final assembly and battery shipment are explicitly quoted.

### Cited Findings

- Exact ESP32-C6-MINI-1-N4 Mouser page: 1,562 stock; €3.90@1/€3.38@10(exVAT). Observations are not reserved inventory. [Mouser ESP](https://www.mouser.de/de/ProductDetail/Espressif-Systems/ESP32-C6-MINI-1-N4?qs=Jm2GQyTW%2FbjiJX9bVadqSw%3D%3D)
- Fresh LCSC C5736265 page: out of stock, reference$3.9719@1/$3.5381@10/$3.2817@30. Older indexed values differed. LCSC stock does not establish JLC assembly/preorder stock. [LCSC ESP](https://www.lcsc.com/product-detail/wifi-modules_espressif-systems-esp32-c6-mini-1-n4_C5736265.html)
- Exact SHT45-AD1F-R2 Mouser page: 4,056 stock; €5.27@1/€4.75@5/€4.55@10(exVAT). Its generic PTFE description conflicts with primary Sensirion polyimide documentation. [Mouser SHT](https://www.mouser.de/de/ProductDetail/Sensirion/SHT45-AD1F-R2?qs=sGAEpiMZZMt8%252Bp86Qvn10vtzehAG9M2TjbFFKoAq1UCsJ3uqziZjVw%3D%3D); [Sensirion datasheet](https://sensirion.com/media/documents/33FD6951/67EB9032/HT_DS_Datasheet_SHT4x_5.pdf)
- Exact Molex53261-0371 Reichelt:€0.39including 19% VAT; stock, 1–2 working days, freight extra. PCB header only, not mating harness. [Reichelt J2](https://www.reichelt.de/de/de/shop/produkt/molex_stiftleiste_smd_-_picoblade_-_1x3-polig_-_stecker-186227)
- PCBWay requires continuous tape; 0402 minimum 100 pieces and 50 overage; 0603 etc minimum 50 and 30 overage; expensive IC/connectors 1–5 spares. Unused parts are not returned by default. [PCBWay parts](https://www.pcbway.com/assembly-special-remind.html)
- ECB 14 October 2026:EUR1=USD1.1195, USD1≈EUR.893256. Informational, not a card conversion rate. [ECB](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
- Commission guidance updated 20 July 2026: from 1 July 2026 €3 per tariff item category for up-to-€150 B2C distance-sale consignments, regardless IOSS/Special Arrangements/standard VAT, with specified non-IOSS H1 preferential/customs-union exceptions. Proposed Union handling fee is distinct; its autumn2026 amount/date are unspecified there. [DG TAXUD](https://taxation-customs.ec.europa.eu/news/guidance-and-legal-text-temporary-flat-fee-low-value-imports-which-will-apply-until-1-july-2028-2026-06-08_en)
- IOSS collects VAT on sale, import is VAT exempt and no import VAT is due on €3 duty. Non-IOSS duty enters import VAT base. [Commission VAT addendum](https://vat-one-stop-shop.ec.europa.eu/document/download/4ba8dc4c-2600-43ee-9010-2101cd05210c_en?filename=VAT+treatment+of+the+EUR+3+customs+duty+and+of+the+announced+Union+handling+fee.pdf)
- German normal import VAT 19%; eligible businesses can normally deduct import VAT subject to records/status. Basis includes duty and transport to first domestic destination. [BMF guide](https://www.bundesfinanzministerium.de/Content/DE/Downloads/Broschueren_Bestellservice/steuern-von-a-z.pdf?__blob=publicationFile&v=8)
- Air-shipped battery types need an available UN 38.3 test summary; operators may impose restrictions. [IATA](https://www.iata.org/en/publications/newsletters/iata-knowledge-hub/what-to-know-about-how-to-ship-lithium-batteries)

### Inferences

At six, the observed ESP+SHT pair alone is€8.65 net/board before other parts, tape handling, allowance and markup. At ten it is€7.93 each: ten pairs cost €79.30 versus six pairs €51.90. The €27.40 extra cash buys four spare pairs. M €12–18 is a planning assumption for the entire BOM, not a live basket.

Exact resistor/capacitor MPNs may invalidate generic basic-library prices. Alternatives need engineering review.

Non-IOSS consumer model: (goods+freight+D)×1.19+K, with K tax determined by its invoice. IOSS uses actual checkout VAT/duty; do not add import VAT twice. Eligible VAT-registered business comparisons can exclude recoverable VAT, showing cash fronting separately. Do not assume user eligibility.

Do not assume€3 per board, €3 per parcel, or universal zero duty below €150. Real B2B procurement and consignments over €150 require actual TARIC classification, origin and import terms; bare and assembled boards may differ. Keep D variable until confirmed. Obtain an itemized delivered/DDP quote.

Complete-sample extras: qualified LP702040 pack/NTC/verified 3P harness, insulation/supports, twelve case prints for six two-part units, labels, fixture, flashing, bring-up, thermal/RF/battery tests, scrap/rework, engineering. AOI or bare-board net tests do not include these.

Local battery procurement/final assembly may simplify cross-border transport without removing qualification. Resin, adhesive and packaging outgassing can affect sensor readings.

Old docs60 has September rates, FX .92, DNP 47/200 count, wrong sub-50 mm B claim, unverified nine extended types and omitted X-ray/overages/tax uncertainty. docs62's numeric OSH$15.81+$23.72=$39.53 correctly matches$10/in²; its prose incorrectly says$5/in². No cost source edited.

### Gaps

No qualified pack/harness price, case-printing quotation, flashing/test price, reserved parts or customs/DDP/IOSS invoice. Delivered complete-sample price remains unquoted.

## Which nonprice criteria should decide?

### Takeaway

Preserve the A/B experiment and require inspectable exact-BOM assemblies. Incorrect cleaning, stackup or depanelization can invalidate all six samples despite cheap bare boards.

### Cited Findings

- Sensirion handling v9 (June 2025): ESD control, no wash, no spray on an unprotected sensor, avoid VOCs/cleaners and polyethylene antistatic bags; use last solder cycle where possible; no-clean type>=3 paste recommended; vapor-phase requires compatibility qualification. Post-reflow RH can temporarily shift negatively 1–2%RH, recovering over 1–3 days. [Sensirion handling](https://sensirion.com/media/documents/6D95AA80/6840311F/HT_Handling_Instructions_SHTxx.pdf)
- The 260°C/30 seconds reflow figure is a maximum, not a requirement to reach 260°C. A lower supplier peak alone does not prove incompatibility; review actual profile, dwell, paste and package limits. [Sensirion handling](https://sensirion.com/media/documents/6D95AA80/6840311F/HT_Handling_Instructions_SHTxx.pdf)
- JLC requires customer verification of matched parts and tooling/rails/fiducials. Its published 2.5 mm component-body edge spacing needs exception review for sensor/connectors. Consigned parts are not function tested; complaints within 3 months; compensation may be limited to soldering fees. [JLC terms](https://jlcpcb.com/help/article/terms-and-conditions-of-jlcpcb-assembly-service)
- JLC advertises AOI/visual/X-ray and optional functional tests; Standard adds SPI, Economic does not. [JLC capabilities](https://jlcpcb.com/solutions/pcb-prototype-assembly)

### Inferences

| Criterion | Evidence needed | Effect |
|---|---|---|
| Exact 26 MPNs/R21DNP | Matched BOM, substitution approval, spare/return policy | Parts access can outweigh setup price |
| Controlled A/B process | Stackup, foil/finished copper, laminate, tolerances, ENIG, lot records | Avoids confounding thermal results |
| B support/depanelization | Approved panel, neck/RF exclusions, fixture, delivery condition | Avoids mechanical damage |
| Sensor handling | Written no-wash process, compatible packaging/coating, profile/conditioning | Prevents drift or damage |
| Pin 1/hidden joints | CPL render, first-article photos, AOI/X-ray scope/results | Reduces high-consequence errors |
| Test definition | PCB net test versus powered PCBA, flashing/results per serial | “Tested” alone is ambiguous |
| Commercial/rework | Incoterm, tax/duty, extras, return freight, warranty basis | Exposes total risk/cost |
| Lead time | Procurement+fab+assembly+holds+delivery | “Two days” may cover only fab |
| Engineering access | Named contact, language/time zone, first-article hold | Helps unusual sensor-island assembly |
| Repeatability to 20 | Data retention, reorder fees, spare ownership, lot traceability | Preserves process after prototypes |

An EU premium can be rational if it resolves process questions and speeds first-article rework. Asian vendors can satisfy the same conditions. Geography alone does not establish IPC quality.

### Gaps

No vendor has accepted this project's sensor/edge/panel constraints or quoted exact test scope. Capability in principle is not manufacturing approval. Source statements are public evidence, calculations are inferences, and program budgets are assumptions.
