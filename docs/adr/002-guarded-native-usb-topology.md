# ADR-002 — Classify native USB trunks, contact joins and fixture branches

Date: 2026-10-22. Status: proposed engineering-layout decision.
Owner: hardware maintainer. EDS-19 remains open; no USB qualification is claimed.

The initial shared A/B geometry left USB unrouted. A single aggregate 2 mm
uncoupled-length rule cannot distinguish the paired main trunks from mandatory
reversible-receptacle joins, ESD pad escapes and the two manufacturing probe
branches. Simply increasing the global allowance can admit long divergent
routes. The generator now retains the global 2 mm default, defines narrow named
areas only for classified local polylines, and reapplies the 2 mm limit to fully
enclosed paired-trunk segments. The local-area aggregate ceiling is 10.5 mm,
an engineering backstop budget: 2 mm trunks + 1.75 mm input + 1 mm output +
3.5 mm contact join + 2.25 mm fixture copper. It is not a USB specification.

Independent source validation rejects unknown USB copper, changed paired
spines, wrong polarity/layer/width, detached endpoints, changed critical pad
placements, excess local path length, extra USB transitions and missing nearby
return-via pairs. Both variants share the same topology. Actual KiCad controls
retain the 2 mm trunk check and reject a fully divergent 6 mm route under the
default rule. Native USB remains a controlled engineering interface.

The main pair stays on F.Cu with nominal 0.25 mm width and 0.20 mm gap; maximum
nominal main copper skew is 0.1 mm (engineering assumption). Two short bottom
probe branches each use one standard 0.6/0.3 mm through via, with return-via
pairs. An In2.Cu GND corridor beneath these branches replaces local +3V0 fill;
In2 signal tracks are prohibited in that corridor. Signal antipads must not
interrupt the paired F.Cu trunk reference. Filled-reference sampling supplements
DRC, and is a geometric control rather than impedance extraction.

Primary sources: [Espressif ESP32-C6 USB layout guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32c6/pcb-layout-design.html#usb)
requires parallel matched routing, 90 Ω ±10%, continuous reference and pairs of
ground return vias at transitions. [TI TUSB320LI Rev D §10.1, p29](https://www.ti.com/lit/ds/symlink/tusb320li.pdf)
limits A6–B6/A7–B7 contact-join stubs to 3.5 mm. TUSB320 is a layout-guidance
reference and is not fitted to this board. Other numerical geometric caps are
explicit engineering assumptions in `usbroute.py`.

EDS-19 closes only after retained stackup/impedance and return-path review,
fixture registration/clearance acceptance, and physical USB enumeration,
programming and repeated reset/sleep/attach tests in both plug orientations.
The existing ADR-001 USB current/charging restrictions remain applicable.

U5 pin continuity and orientation are checked against [ST USBLC6-2 DS4260
Rev 7 p1 functional top view and Fig.19 land pattern](https://www.st.com/resource/en/datasheet/usblc6-2.pdf):
pins 1/6 and 3/4 are the continuous data lines, pin2 is GND and pin5 VBUS.
ST §2.3 requires short rail/ground connections; physical ESD performance is
not established by the nominal component rating or the DRC report.
