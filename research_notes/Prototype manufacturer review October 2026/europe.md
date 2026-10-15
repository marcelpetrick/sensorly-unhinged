# European prototype PCB and assembly manufacturers

Research accessed 2026-10-15. Scope: Germany delivery, three assembled A and three assembled B; A 30 × 34 mm, B bounding box 30 × 51 mm; four-layer, approximately 1.6 mm FR4, ENIG, 46 fitted components each. These project inputs came from the coordinator, not a vendor acceptance. No files uploaded, accounts created, suppliers contacted or orders placed. Public pages are not binding project quotations.

## Which European vendors can supply three of each variant?

### Takeaway

AISLER, Eurocircuits, Beta LAYOUT and LeitOn publicly accept assembly from one board, so each is a credible 3 + 3 RFQ candidate. Multi-CB is a bare-board/stencil supplier requiring a separate assembler. No defensible current project-specific total PCBA price can be obtained from the public pages alone.

### Cited Findings

- **AISLER:** assembly MOQ one; mixed SMT/THT including 0201. Its online quotation imports CAD/BOM. The page's six-day headline conflicts with its own FAQ and current status table; do not use that headline as this project's delivery promise. — [Amazing Assembly](https://aisler.net/products/assembly)
- **Eurocircuits:** one to 50 assembled boards, SMT/THT, 0201 and 0.35 mm QFP-class pitch; only assembles its own PCBs. Stencil is included in assembly cost but not delivered. Visual, SPI and X-ray are listed. Assembly is 3/5/7/10 working days, standard five, **after bare boards are available**, subject to component availability. — [Assembly capabilities](https://www.eurocircuits.com/services/pcb-assembly-capabilities/)
- **Beta LAYOUT:** assembly one to 50, SMT and THT; component charges use selected distributor prices and are approved before purchasing. Standard assembly up to 499 placements takes 12 working days after all materials arrive; 8 days costs +40%, 4 days +100%. A special two-day option is limited to 300 placements and 25 THT components per order; confirm applicability. PCB production time is additional. — [Assembly general information](https://eu.beta-layout.com/pcb/assembly/general-information/)
- **Beta PCB-POOL:** German bare-board production; 1.6 mm, four-layer and ENIG are offered. Overseas is a separate service, so select production origin explicitly. — [PCB services](https://eu.beta-layout.com/pcb/)
- **LeitOn:** current assembly RFQ form accepts quantity one. Express is 10–15 working days, minimum +100% premium, German assembly; standard prototype/small series starts at five weeks depending on parts. QFN/LGA and 0201 are supported. Gerbers, P&P, polarity-marked assembly plan and **XLS/XLSX BOM, not CSV**, are requested. Functional test, programming and traceable IDs can be specified. — [LeitOn assembly](https://www.leiton.de/leiterplattenbestueckung.html)
- **Multi-CB:** explicit division of work: it supplies PCBs/stencils and an assembler procures/solders the components. Do not treat its “PCB assembly” landing page as a turnkey PCBA offer. — [PCB assembly](https://www.multi-circuit-boards.eu/en/pcb-assembly.html), [EMS provider](https://www.multi-circuit-boards.eu/en/ems-provider-electronics-manufacturing.html)

### Inferences

- Seek comparable firm quotes from AISLER and Eurocircuits first; Beta adds another mature low-volume option, while LeitOn offers a more individually specified manufacturing/test engagement. This is a suitability shortlist, not a proven price ranking.
- Do not promise three **functionally good** units just because three placements were ordered: qualification and yield/rework acceptance must be written into the RFQ.

### Gaps

- Exact 3 + 3 assembly, components, test, depanelization and shipment totals require vendor calculation with final BOM/CPL/stackup. No public project-specific price was found for any EU assembler. Do not assign arbitrary vendor-specific ranges or present an unexecuted calculator as a quote.
- Four-layer stackup, actual copper thickness and acceptance of the narrow B neck, sensor handling and custom footprints remain project-specific technical approvals.

## What prices are genuinely public, and does batching or merging save money?

### Takeaway

AISLER provides a usable bare-board formula, but current assembly prices use unpriced task categories. Its standard service explicitly forbids mixed-design panels. Sharing a BOM does not turn two layouts into one payable design.

### Cited Findings

- AISLER's informational **net** bare-board formula is job fee + area × rate × quantity: four-layer 1.6 mm ENIG Budget **€14 + €0.13/cm² × area × quantity**, Blitz **€22 + €0.347/cm² × area × quantity**. Bare MOQ three in multiples of three. Assembly is bare boards + parts + tasks; tasks cover setup, per-panel and per-component work. No current task unit prices are published there. — [Our Simple Pricing](https://community.aisler.net/t/our-simple-pricing/102)
- AISLER sets panel allocation itself and expressly excludes multi-design panels. Panels normally come in multiples of three, so delivered individual PCB quantity can differ from ordered assembled quantity. — [Production panel specification](https://community.aisler.net/t/aisler-production-panel-specification/2779)
- Eurocircuits supports mixed-circuit delivery panels via merged Gerbers or engineering inquiry, rather than interactive import of separate circuits. Tabs forbidden near sensitive parts must be identified on a mechanical drawing. This bare-panel support does **not** by itself establish a shared assembly/setup discount. — [Panel Editor guide](https://www.eurocircuits.com/user-guides/visualizer-user-guides/panel-editor-user-guide/)
- Beta requires at least 10 mm between boards in customer-created assembly panels, supplies these panels without separation, and requires separate orders for assembly variants. Shared components for separate projects must be supplied in separate labeled strips because jobs may run on different machines. — [Assembly guide](https://eu.beta-layout.com/pcb/assembly/assembly-guide/)
- Beta's **kitting-only** fee is €9.90/€19.90/€29.90/€39.90 gross for 1–10/11–25/26–50/51+ different components, with a free laser stencil. These are not assembly fees and count different components, not 46 placements. — [Kitting](https://eu.beta-layout.com/pcb/kitting/)
- Multi-CB accepts one bare PCB, includes setup/E-test/DRC, and supports mixed multiplier panels. Public 80 × 100 mm four-layer **HAL**, 1.55 mm example: one board €59 at five working days or €25.80 at nine, excluding VAT/shipping. This is neither ENIG nor our 3 + 3 geometry and must not be transplanted as this project's quote. Sales are only to companies/public institutions. — [Prototype boards](https://www.multi-circuit-boards.eu/en/products/printed-circuit-boards/prototypes.html)
- LeitOn's public generic four-layer examples list €46.63 **per board at quantity three**, €35.98 at five and €22.42 at ten, ten working days, net including setup. The reference design is not this project's verified geometry; these illustrate quantity effects only. German UPS standard is listed as €8, 1–2 days. — [LeitOn public examples](https://www.leiton.de/)

### Inferences

**AISLER bare-board calculation, informational only:** use A's rectangular bounding area 10.2 cm² and B's 15.3 cm², not B's smaller routed material area. Treat A and B as **two jobs**, €14 each; no evidence permits sharing the fee merely by one cart or shipment. Using the published formula:

| Bare-board scenario | A, unrounded | B, unrounded | Arithmetic total net | Display total |
|---|---:|---:|---:|---:|
| Budget 3 A + 3 B | €17.978 | €19.967 | €37.945 | €37.95 |
| Budget 6 A + 6 B | €21.956 | €25.934 | €47.890 | €47.89 |
| Blitz 3 A + 3 B | €32.6182 | €37.9273 | €70.5455 | €70.55 |

These figures exclude assembly, parts, tests and any nonstandard option. AISLER advertises regular shipping as free on the [bare-board product page](https://aisler.net/products/boards); selected shipping and applicable tax remain checkout items. Different line/tax rounding may produce a cent difference.

- Doubling Budget bare quantity costs €9.945 more overall, about 26.2% more cash, for twice as many bare boards; average drops from €6.324 to €3.991. This is a calculated bare-board effect, **not** a PCBA saving. Five bare boards per design are not a standard allowable quantity; six is the next multiple.
- Three assembled per design is allowed despite bare multiples. Do not assume an assembly order for five necessarily requires buying/receiving exactly six standalone boards: AISLER selects production panels and checkout establishes chargeable quantity and extras.
- At 46 placements each, 3 + 3 = 276 total and 5 + 5 = 460; both fall under Beta's published 499-component standard bracket. Each separate three-board job is 138. Merging does not unlock an obvious lower standard lead-time band; the special two-day route still requires THT-count and process confirmation.
- Best first negotiation is a coordinated order with one common component purchase and two placements/CPLs. Mixed panels can save setup or shipment but add frame area, depanelization work, mixed-design review and neck protection; request both structures rather than assuming the savings.

### Gaps

- AISLER's price page has an outdated worked example inconsistent with its own 2-layer table; the calculation above uses only its explicit current **four-layer table**, subject to checkout confirmation.
- Exact external-quantity surcharges, partial assembly of extra PCBs, merged procurement allowance and fee reuse across separate jobs are not publicly guaranteed.
- No approved A/B mixed-panel quote exists. AISLER excludes it in the standard policy; Eurocircuits supports fabrication panels but combined assembly remains quote-specific; Beta's variant rule counsels caution.

## Which non-price factors matter for this instrument?

### Takeaway

The sensor process, neck-safe depanelization, exact component identity and sufficient inspection/testing matter more than a small bare-board discount. Confirm included work rather than comparing only headline prices or assembly throughput.

### Cited Findings

- AISLER's current dated status table (14 September 2026) gives four-layer 1.6 mm ENIG bare Budget ten / Blitz four working days; assembled standard 18, four-layer 1.6 mm Blitz 11, including material. German mail is two days or UPS one; these are estimates. — [Service Status](https://community.aisler.net/t/service-status/399)
- AISLER Amazing Assembly includes manual optical inspection; AOI is on request and IPC Class II/III compliance is not listed for that product. Programming/testing and custom stackups are requestable. Residues may remain; unused holes may be solder sealed; paste data is applied as supplied even on unplaced parts. — [Assembly portfolio](https://community.aisler.net/t/assembly-portfolio/4674)
- AISLER customer-supplied parts incur €15 per unique MPN per project; bulk may cost extra, must arrive within eight days and excess return is not guaranteed. — [Customer-supplied components](https://community.aisler.net/t/customer-supplied-parts-for-your-assembly-project/1411)
- Eurocircuits machine feeding requires 50 mm minimum tape; components up to 1212 need ten extras, others one, with tube/tray exceptions. — [Pick & Place](https://www.eurocircuits.com/technical-guidelines/assembly-manufacturing-technology/pick-place/)
- Beta's assembly guide describes vapour-phase soldering and explicitly warns some sensors/microphones are incompatible; obtain component-manufacturer confirmation. Customer supply must be machine-compatible with contiguous tape. — [Assembly guide](https://eu.beta-layout.com/pcb/assembly/assembly-guide/)
- Beta requires 0603+ supply overage of 20%, minimum ten; 0402/0201 needs 100%, minimum twenty. Valuable parts can have reduced overage if appropriately packaged. — [Assembly general information](https://eu.beta-layout.com/pcb/assembly/general-information/)
- Eurocircuits recommends generic passive components as a cost/setup simplification. That convenience must be weighed against our exact capacitor bias/temperature and thermal BOM qualification. — [The Perfect BOM](https://www.eurocircuits.com/tips-tricks/perfect-bom/)

### Inferences

- Request no cleaning, conformal coating or unreviewed process around SHT45 until checked against Sensirion's actual handling/reflow limits. Beta's sensor warning is an RFQ acceptance item, not proof its process fails our sensor.
- Explicitly preserve R21 DNP and its paste treatment; protect fixture holes/test pads; request depanelized units and tabs away from B neck/island and antenna. Do not bend-break a fragile instrument without an agreed method.
- Require correct MPNs, pin-1/cathode/connector polarity review and final CPL preview on **both** variants. Shared BOM does not imply identical placement.
- Order matched A/B quantities together for a common component/material lot when possible, reducing experiment confounding. Quantify any savings with a vendor reply, not a fabricated percentage.
- No routine visual/AOI/X-ray statement proves our radio, charge inhibit, low-power current, sensor accuracy, thermal response or RF performance. Paid functional test needs our fixture, firmware, acceptance thresholds and logs, and physical qualification remains a separate project gate.

### Gaps

- No manufacturer has reviewed the present unfinished routing, current footprints, paste apertures, B neck retention, stackup or BOM stock for this order. All offers remain conditional until final design review and actual quotation.
- The public pages cannot establish this lot's yield guarantee, functional-test coverage, rework policy, surplus ownership, component substitutions or long-term repeatability. These belong in the comparison RFQ.
