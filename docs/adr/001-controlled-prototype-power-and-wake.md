# ADR-001 — Isolate raw TS and make controlled prototype standby explicit

Date: 2026-10-12. Status: accepted **for the shared A1/B1 engineering prototype**.
Owner: hardware/firmware maintainer. Product qualification remains open.

The previous architecture connected charger TS directly to a MCU ADC, tied EN2
low, and put the runtime button on IO9. It could neither prove ADC fault safety,
select charger standby, nor wake the C6 from deep sleep with that button.

We retain one shared schematic, netlist, BOM and firmware. R21 is a mandatory
DNP link between raw `PACK_TS` and `PACK_TS_SENSE`; it must not be populated as
a plain short. This makes the initial assembled prototype's ADC connection
physically open. Native pack NTC→charger TS stays connected. EDS-15 requires a
protected, bounded sensing interface before temperature-supervised charging.
A high-impedance input in software would not provide this isolation.

EN2 moves from ground to IO14/module pin19 (`USB_EN2`). R8 (EN1) and new R20
(EN2) each pull up to the MCU rail using 100 kΩ, an engineering choice requiring
margin/startup qualification. With that rail valid, both pins high select
standby. The bring-up image only selects this state; its charge-enable output
always remains low. A supervised lab image may select USB100 (both EN pins low)
only after a separate bench-source procedure is reviewed. USB500 and programmed
ILIM remain prohibited. Pull-ups on an absent or collapsing rail cannot prove
standby: battery-less USB boot is unsupported and attach/brownout/suspend current
must still be measured. The fixture powers VBAT with a declared battery simulator.
Do not call this unrestricted USB compliance or fulfilled USB-C charging.

SW1 moves to IO1/module pin13, an EXT1 wake-capable non-strapping pin, with new
100 kΩ R19 pull-up and existing 100 nF C5 (10 ms RC, engineering choice).
TP7 remains an independent IO9/module pin23 download strap, named `BOOT_N`.
R22 = 10 kΩ (engineering choice) pulls IO8/module pin22 high because the
module datasheet Tables 4-1/4-3 identify GPIO8 as floating by default and require
GPIO8=1/IO9=0 for joint download. The fixture holds TP7 low before and at least
3 ms after EN release (Table 4-2), verified on the first boards.
Bring-up arms low-level EXT1 only after the button is released, to avoid an
immediate wake loop. This implements a wake experiment, not BLE provisioning.
Allocating IO1 prevents fitting the previously optional IO0/IO1 clock crystal
without another reviewed reassignment; measured timing remains EDS-6.

The alternative of a full programmable USB device/source detection and protected
analog frontend adds parts, sourcing and layout risk. It remains a valid product
redesign if these controlled prototypes establish that unrestricted charging is
required. The current disposition prioritizes a reviewable safe bench instrument,
with blocked product functions clearly retained in the release gates.

Primary references: [TI BQ24074 SLUS810N](https://www.ti.com/lit/ds/symlink/bq24074.pdf),
Table 7-2 EN truth table and §9.3.6 TS behavior;
[ESP32-C6-MINI-1 v1.5](https://www.espressif.com/sites/default/files/documentation/esp32-c6-mini-1_datasheet_en.pdf),
Table 3-1 module pins;
[ESP-IDF v5.5.4 sleep API](https://docs.espressif.com/projects/esp-idf/en/v5.5.4/esp32c6/api-reference/system/sleep_modes.html),
EXT1; and [v5.5.4 Serial/JTAG API](https://github.com/espressif/esp-idf/blob/v5.5.4/components/esp_driver_usb_serial_jtag/include/driver/usb_serial_jtag.h).

Acceptance still required: DNP assembly inspection and continuity; rail-rise/loss
and EN/CE traces; measured source current through attach/suspend/reset/sleep;
held/released-button, independent download strap and timing tests. No physical
measurement is claimed by this ADR. EDS-9Q/10Q/11/12/13/14/15 remain open as
applicable; the EDS locked table records only the prototype architecture.
