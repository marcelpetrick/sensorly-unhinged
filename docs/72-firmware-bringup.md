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
If `_build/firmware/sdkconfig` predates the custom partition setting, remove
that generated file before rebuilding; the firmware compile guard rejects a
cached configuration without the custom table.

`make firmware-test` runs the wire decoder on the host with a known
manufacturer CRC vector, endpoint conversions, and all 48 one-bit frame faults.
It also exercises the flash journal with NOR-style writes, partial ACKs, bank
compaction, repeated overflow, reboot recovery and torn/ambiguous writes.
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
Use 50 ms I²C transaction limits. A transport error or CRC failure causes at
most one new command/wait/read attempt; a second failure produces null
temperature and RH, never a previous sample or a partially updated pair. The
reported status is the final attempt's transport error or CRC error. This retry
is a bring-up policy choice, not a measured reliability or energy guarantee.
Conversion and CRC follow
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
A chip MAC is **not** a production serial. The image now appends the measurement
to a dedicated flash journal before emitting JSON. `journal_id` and
`journal_overflow` are decimal strings to avoid loss above the exact-integer
range of JSON numbers. `journal_write_status` reports accepted, overflow or
flash error. This image has no provisioning, network credentials, TLS, MQTT,
OTA or user button actions; acknowledgement is an API for later upload code,
not an automatic deletion. Those acceptance cases remain open. The
USB/cooldown/ADC qualification flags are explicit.

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


## Flash journal engineering format

`firmware/partitions.csv` reserves `journal` at 0x200000–0x21ffff in the
configured 4 MB flash. The factory image ends at 0x1fffff; this partition map
must be reviewed again for OTA slots. Two 64 KiB banks are independently erased
in 4 KiB units. Each starts with a CRC-protected, commit-last header holding a
monotonic generation, maximum assigned ID and overflow baseline. The newer
committed generation wins after reset. The other bank is erased and filled with
all live records before its header is committed. An interrupted write before
the destination header commit leaves the prior bank authoritative if its header
remains valid. A partial erase of the destination's old committed header can
leave a bad CRC and a programmed commit word. Recovery then returns `CORRUPT`
without choosing a bank; actual flash power-cut behavior remains unqualified.
At 100 bytes per slot and a 64 byte header, each
bank has 654 slots; the live limit is 500. Once slots fill, compaction copies
unacknowledged records. Full-queue arrivals write durable overflow events;
compaction folds those into the next header's counter. Counter and ID exhaustion
return explicit errors rather than wrapping. A fully programmed commit whose
flash call reports failure is found by acquisition token on recovery, including
across a reboot. A partially programmed ACK remains live and can be retried.

Record v1 encodes a 6 byte chip MAC, 32 byte ELF SHA-256, 64 bit boot nonce,
64 bit monotonic journal ID, 64 bit acquisition uptime in microseconds,
temperature and RH in milli-units, battery millivolts, 16 bit sensor/ADC status,
reset/wake reason, USB/charging bits and quality bits. Signed `INT32_MIN` marks
an unavailable temperature or battery; `UINT32_MAX` marks unavailable RH. The
quality bits are engineering-unqualified, battery-meter-pending,
cooldown-unqualified, USB thermal bias and unexpected charging status, in that
order. A CRC-32 covers the 88 byte payload; separate programmed words mark
commit and acknowledgement. A committed CRC mismatch stops recovery with an
error so corrupted data cannot silently disappear. This bring-up record does
not claim production serial, hardware revision, calibrated UTC, network delivery
or physical power-loss qualification. Before the MQTT contract can close,
firmware must map inventory serial/variant/revision, establish a trusted clock,
exercise power cuts on actual flash, and ACK only confirmed broker deliveries.

The first flash use initializes an erased journal partition only after the data
areas of both banks are confirmed blank. Unexplained nonblank data behind blank
headers returns `CORRUPT`; a read failure returns `IO_ERROR`. Neither case writes
or erases flash. This check rejects ambiguous or foreign media; it does not claim
that ordinary append interruptions produce that state. A torn first header can
still be retried when both data areas are blank. Reflashing only
the application preserves the partition; a whole-flash erase destroys queued
measurements. Do not ACK through the API until a delivery implementation defines
its acknowledgement and duplicate handling. Firmware uses the same partition
and format on A and B.

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
5. Compute the built ELF hash with `sha256sum _build/firmware/sensorly_bringup.elf`.
   Run `make production-capture` using the command below, replacing the example
   MAC, hash, serial, variant, operator and log path with the fixture inventory
   and actual capture. The example values are not device evidence.

   ```sh
   make production-capture CAPTURE_ARGS='--input capture.log --serial ENV-0001 --variant a --chip-id aabbccddeeff --firmware-sha256 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef --operator bench --output-dir measurements/bringup'
   ```
6. Preserve the result and independent meter/scope traces. `BRINGUP_PASS` checks
   only the emitted record and identity; it does not pass rails, current, RF,
   charging, thermal accuracy, sleep energy or product release.

The capture tool rejects malformed/missing/duplicate records and mismatched
identity/image. It retains reported failures with a nonzero exit code, carries
the raw console text and digest, and refuses to overwrite an existing serial.
Review/retest failures with a new explicit run directory, preserving the first
record. No synthetic record belongs in the qualification manifest.
