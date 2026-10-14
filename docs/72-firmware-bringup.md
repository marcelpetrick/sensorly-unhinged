# 72 — Engineering bring-up firmware

The repository now contains a buildable **engineering bring-up application**, shared
by A and B. It is not the completed telemetry firmware in [the contract](71-firmware-contract.md).
No device has run it yet. The firmware qualification slot remains open.

## Build and verification

Use ESP-IDF **v5.5.4**, commit `735507283d5b2f9fb363a1901172dbd9e847945d`.
Install with Espressif's `install.sh esp32c6`, source that checkout's `export.sh`,
then run `make firmware`. The wrapper rejects another SDK commit or tracked SDK
modifications. SDK-managed compiler versions come from that checkout's
`tools/tools.json`. SDK binaries and dependencies are not vendored here and keep
Espressif/upstream licences. The application is GPL-3.0-or-later.

`make firmware-test` runs the same wire decoder on the host with a known
manufacturer CRC vector, endpoint conversions, and all 48 one-bit frame faults.
`make firmware` puts binaries, ELF, map, sdkconfig and flash arguments under
`_build/firmware/`. Never treat successful compilation or these host tests as
board measurements. ESP-IDF reproducible-build mode excludes build timestamps;
record the ELF SHA-256, git commit and tool versions with each flashed unit.

## Implemented behavior

On entry, preload GPIO18 low and GPIO21/14 high before configuring outputs.
GPIO18 never enables Q1. EN1/EN2 both high select charger standby; R8/R20 pull
them high while the MCU rail is valid. No active USB-current mode is selected.
LED off, no radio initialization, no charger enable, no USB500. See
[ADR-001](adr/001-controlled-prototype-power-and-wake.md); unpowered rail and
suspend current still need qualification.
Configure a five-second task watchdog with panic/reset and subscribe the main
task. This timeout is an engineering choice, not a measured shutdown guarantee.

Read SHT45 at 0x44 over IO6/IO7 at a conservative 100 kHz. Use high precision
command 0xFD and a 10 ms wait, as in [Sensirion's reference driver](https://github.com/Sensirion/embedded-i2c-sht4x/blob/master/sht4x_i2c.c).
Use 50 ms I²C transaction limits; CRC failures produce null temperature and RH,
never a previous sample or a partially updated pair. Conversion and CRC follow
the [SHT4x datasheet](https://sensirion.com/products/catalog/SHT45) sections
Data Processing and Checksum Calculation. The extra 10 ms startup wait is a
bring-up margin, not a measured power budget.

After acquisition, allow 550 ms divider settling (EDS §6), read ADC1 channel 2
with ESP-IDF curve-fitting calibration, and multiply by the nominal 2:1 divider.
A failed calibration/read produces null voltage. Resistor, loading and ADC errors
still need external-meter characterization. PACK_TS is physically separated from the ADC by mandatory DNP R21 and is not
sampled. Never populate R21 as a zero-ohm link; EDS-15 requires a protected interface.

Emit one JSON line with chip MAC identity, image hash, reset cause, acquisition
uptime, values/status and quality flags. UTC is null and clock validity false.
A chip MAC is **not** a production serial. This image has no persistent journal,
provisioning, network credentials, TLS, MQTT, OTA or user button actions; those
acceptance cases remain open. The USB/cooldown/ADC qualification flags are explicit.

Charger status inputs IO22/23 disable MCU pull-ups/pull-downs: R9/R10 are the
sole pull-ups for these open-drain nets, keeping the declared loading intact.
The independent TEST_MODE/IO20 input enables its internal pull-up; the fixture
pulls IO20 low before reset. Factory mode gives a three-second
console receive window, then clears control outputs again and enters five-minute
timer deep sleep. Normal mode sleeps after the record. These intervals are
engineering bring-up defaults. SW1 now uses IO1 and supports EXT1 low-level wake. The image arms it only if
released at sleep entry; a held button leaves timer wake armed. IO9/TP7 is an
independent factory download strap; R22 holds IO8 high. The fixture holds
TP7 low before EN release and at least 3 ms afterward (module Table 4-2),
then verifies joint USB/UART download on the first boards. Button wake and EDS-14 still require bench
evidence; no provisioning behavior is implemented. Console logs and the watchdog
can affect consumption; measure the eventual release firmware separately.

## First-board procedure

Follow [power-safety qualification](51-power-safety-qualification.md) before
energizing assembled boards. Current PCB drafts are not fabrication approved.
Use a protected charged pack or the declared battery simulator at VBAT.
Battery-less USB startup is unsupported. EN standby and the DNP ADC link do not
prove complete suspend compliance, startup behavior or temperature supervision.
Inspect R21 DNP and capture those circuits independently.

1. Record serial, variant/revision, assembly/BOM lot and independently read chip ID.
2. Build from the recorded commit; archive the ELF/binary hashes and tool versions.
3. With a current-limited bench setup, run `make firmware-flash PORT=/dev/ttyACM0`.
   This writes only the image/bootloader/partition files selected by ESP-IDF;
   no eFuse, secure-boot key burning or whole-flash erase is requested.
4. Pull TEST_MODE low, reset, and capture exactly one boot's USB console into a log.
5. Run `make production-capture CAPTURE_ARGS='--input capture.log --serial ENV-0001
   --variant a --chip-id <inventory-MAC> --firmware-sha256 <ELF-SHA256>
   --operator <name> --output-dir measurements/bringup'` on one shell line.
6. Preserve the result and independent meter/scope traces. `BRINGUP_PASS` checks
   only the emitted record and identity; it does not pass rails, current, RF,
   charging, thermal accuracy, sleep energy or product release.

The capture tool rejects malformed/missing/duplicate records and mismatched
identity/image. It retains reported failures with a nonzero exit code, carries
the raw console text and digest, and refuses to overwrite an existing serial.
Review/retest failures with a new explicit run directory, preserving the first
record. No synthetic record belongs in the qualification manifest.
