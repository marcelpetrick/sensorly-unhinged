Today 12:27 PM
Okay, I have this idea. I want to integrate some kind of home sensor. I should have Wi‑Fi access. So I'm thinking for some ESP32 microcontroller, which has Wi‑Fi and Bluetooth on board, I mean directly in the chip. And then I want to connect some kind of temperature and humidity sensor, so that I can read those values from remote and then aggregate them somewhere. The question is, I would like to create some kind of custom PCB layout and design, which is then created in small series or small scale of 20 units and shipped to Germany. So I need something like a vendor. The question is, what do we have to create for such a project? Think hard and long. I mean do some check in the web what is needed for such a PCB design. And as said, I mean the more compact the better. But I mean if not, we will just create our own 3D printed case, and maybe we also want to integrate some kind of battery pack, a battery power for this. And yeah, so that they don't have to run full time on some 230 volt. Yeah, so think hard and long, do some web research, find the resources and what is necessary, and give me some plan and also some forecast of what you want to do.


Okay, then maybe make two approaches: one where everything is integrated on a small space or area, and then one version where, I mean, the temperature and humidity sensor is a bit more far away from those components which heat up. I mean make two forecasts and work really thoroughly and review yourself.

Yes. I would deliberately develop two PCB variants from one common schematic and one common firmware. That gives us an unusually useful experiment: the electronics stay essentially identical, while only the thermal/mechanical implementation changes. We can then put five units of each next to one another, measure the systematic offset, and make the choice from data rather than intuition.

After reviewing the ESP32-C6, Sensirion's humidity-sensor design guidance, low-power power-supply options, assembly vendors, and the current EU/German regulatory situation, this is the architecture I would pursue.
1. Proposed common electronics

I would base both versions on this stack:
Function	Proposed component / implementation	Reason
MCU + radio	ESP32-C6-MINI-1-N4	Wi-Fi 2.4 GHz, BLE 5.3, plus Thread/Zigbee for possible future use; module includes antenna/RF matching
Temperature/RH	Sensirion SHT40	Tiny, very low power, factory calibrated, good accuracy
Main supply	TPS62840, probably ~3.0–3.3 V	Extremely low quiescent current, 750 mA capability
Battery	Protected 1-cell LiPo, initially 500–1000 mAh	Readily available; good energy density
Charging	USB-C + BQ24074-class power-path charger	Proper LiPo charging, NTC support and device operation while charging
Provisioning	BLE → Wi-Fi credentials	No screen or keyboard required
Telemetry	MQTT/TLS or HTTPS	Easy aggregation
Firmware	ESP-IDF	Deep sleep, secure provisioning, OTA, security features
Case	3D-printed initially	Lets us tune airflow before injection molding is even relevant

The ESP32-C6-MINI-1 module is only 13.2 × 16.6 × 2.4 mm and supports 2.4-GHz Wi-Fi 6, Bluetooth LE and 802.15.4/Thread/Zigbee. Using the module rather than the bare ESP32-C6 chip avoids doing our own RF matching/crystal design and substantially reduces RF risk. Espressif already has a RED/CE type examination for the module, although the certificate explicitly says that the manufacturer of the finished host product must still assess the finished combination.

The SHT40 is a particularly good match: 1.5 × 1.5 × 0.5 mm, I²C, typical ±0.2 °C temperature accuracy and ±1.8 %RH humidity accuracy, with only about 0.4 µA average supply current.
One important architectural point

For a battery product, I would not maintain a permanent Wi-Fi connection. ESPressif specifies about 14–38 mA in various modem-sleep conditions, whereas ESP32-C6 deep sleep is about 7 µA. Wi-Fi transmission itself can peak as high as roughly 382 mA depending on modulation and transmit power.

So the operating sequence should instead be:

sleep → wake → measure temperature/RH immediately → optionally store reading → start Wi-Fi → upload → shut Wi-Fi down → deep sleep

That sequencing is important for both battery life and measurement accuracy: the SHT40 gets its reading before the ESP32 radio has had time to heat the board.
2. Approach A — ultra-compact monolithic PCB

This is the version where compactness wins.

A realistic first design target is approximately 30 × 34 mm PCB, perhaps somewhat smaller after placement optimization. The final enclosure will be bigger because of the battery, airflow and antenna clearance; roughly 40–45 mm square and 13–18 mm thick would be a reasonable design envelope rather than a guaranteed final dimension.

Conceptually:

 SENSOR END                                  RF END
 ┌───────────────────────────────────────────────┐
 │ vents                                         │
 │ SHT40     low-power       charger   ESP32-C6 │→ antenna
 │   ●        regulator      / USB-C     MINI   │
 │                                               │
 └───────────────────────────────────────────────┘
                 LiPo behind central area

The SHT40 would be located at the opposite end of the board from the ESP32, switching regulator and charger. Around the SHT40 I would remove unnecessary copper pours and use only narrow I²C, power and ground connections. The enclosure would have direct vents at that end.

The ESP32 module would be mounted with its PCB antenna at the other board edge. Espressif recommends placing the module antenna outside the carrier-board edge where possible, or as close to the edge as possible with the required keep-out. It also recommends substantial free space around the antenna in the finished enclosure—nominally around 15 mm in all directions—and testing the final enclosure for actual communication range and throughput.
What worries me about Version A

Thermal conduction through a PCB is surprisingly effective. Sensirion explicitly identifies power electronics and microprocessors as common sources of temperature measurement error, primarily because heat travels through the PCB copper.

And humidity makes the problem worse. Sensirion gives an extreme example: around 90 %RH, a 1 °C temperature error can correspond to roughly a 5 %RH humidity error.

So merely buying a ±0.2 °C sensor does not mean the finished device is a ±0.2 °C instrument.

Version A can nevertheless work quite well because this product is asleep most of the time. If it has been sleeping for five minutes, the PCB should be close to ambient temperature. We take the SHT measurement first, and only then generate RF heat.

The difficult situation is charging.

A linear charger dissipates power approximately according to the difference between USB input voltage and battery voltage multiplied by charge current. At several hundred milliamps this can become a genuine little heater. The BQ24074 supports power-path operation, Li-ion/LiPo charging up to 1.5 A and an NTC input, but we emphatically would not charge a little sensor at 1.5 A. I would probably configure the initial product around 100–250 mA, depending on battery specification.

Firmware should also know that USB is present. During charging we can either:

    mark temperature/RH readings as potentially thermally biased, or

    suspend environmental reporting and resume after a defined cool-down period.

That will make Compact A substantially better.
Version A forecast

I would expect this variant to be:
Characteristic	Compact A
PCB target	~30 × 34 mm
Parts	One rigid PCB
Assembly difficulty	Low
Case size	Smallest
BOM	Lowest
Thermal measurement quality	Good for room trends if duty-cycled correctly
Accuracy while charging	Main weakness
Sensitivity to case design	High
Mechanical robustness	Very good
Best use	Small inexpensive room sensor

I would regard Version A as a consumer comfort/environment monitor, rather than a precision reference thermometer.
3. Approach B — thermally isolated sensor island

This is the version I expect to win.

Instead of merely putting the SHT40 on the far side of the PCB, I would make the PCB something like 28 × 45–50 mm, with the final 12–20 mm forming a narrow sensor tongue.

Something like:

       SENSOR CHAMBER                ELECTRONICS CHAMBER
     ┌──────────────┐          ┌────────────────────────────┐
air ↔│     SHT40 ●  │==========│ regulator / charger       │
air ↔│              │   neck   │ ESP32-C6       antenna → │
     └──────────────┘          └────────────────────────────┘
          ↑
     milled slots
     around island

The important part of ========== is that it is not ordinary PCB copper.

Around the SHT40 we deliberately create two routed slots, leaving a narrow FR-4 bridge. Only four thin electrical connections cross it:

    VCC

    GND

    SDA

    SCL

No big ground plane. No power plane. No thermal vias.

Sensirion specifically recommends precisely these techniques: distance from heat sources, removing unnecessary metal, using thin connections, milling slots around the sensor and, when needed, using flex PCB. Their recommended enclosure examples also put a wall between the sensor and warmed internal air while exposing the sensor compartment directly to ambient air.

This is therefore not an exotic trick I'm inventing; it is very close to Sensirion's own recommended design-in approach.
The enclosure for B becomes part of the sensor

I would design two chambers:

┌────────────── case ─────────────────┐
│                                     │
│  ambient vents      dividing wall   │
│   ░ ░ ░ ░              │            │
│ ┌────────┐              │ ESP32     │
│ │ SHT40  │              │ charger   │
│ └────────┘              │ regulator │
│                         │ battery   │
└─────────────────────────────────────┘

The wall prevents warm air around the charger/MCU/battery from convecting toward the sensor.

This simultaneously addresses:

    conduction — thin PCB neck and slots;

    convection — partition between chambers;

    radiation — physical separation;

    response time — sensor is close to the ambient vent.

Version B forecast
Characteristic	Separated B
PCB target	~28 × 45–50 mm
Parts	One rigid PCB
Sensor separation	~12–20 mm isolated tongue
Assembly difficulty	Almost same as A
PCB price	Slightly higher
Case	Longer
Thermal measurement quality	Significantly better
Charging influence	Much lower
Repeatability unit-to-unit	Better
Mechanical concern	Narrow tongue needs adequate strength
Best use	Proper room/environment sensor

This is the version I would choose for the final 20 units, assuming our comparative testing confirms it.
4. I would not jump directly to a separate flex PCB

There's an even more thermally ideal B variant:

Main PCB ───── thin FPC ───── 8×8 mm SHT40 board

Sensirion itself notes that mounting the sensor on FPCB minimizes thermal conduction.

But for twenty devices, I don't think it is the right first choice.

Rigid-flex/FPC adds:

    another fabrication process,

    tooling,

    assembly complexity,

    connector or flex attachment,

    more mechanical design,

    another failure mode.

JLCPCB, for example, supports FPC assembly but explicitly notes additional fixture/tooling requirements.

A milled rigid-PCB sensor tongue gets perhaps 80–90% of the engineering benefit with far less complexity. That percentage is my engineering expectation, not a sensor-manufacturer specification; our A/B experiment is precisely how we determine the actual result.
5. PCB construction I would use

I would start with a 4-layer board, even though a two-layer design is technically possible.

Espressif's own guidance recommends four layers:

L1  Components + signals
L2  solid GND
L3  power + slow signals/GND
L4  limited signals/GND

and says two-layer construction is also possible with careful grounding.

The exception is the sensor island on Version B: underneath and around that SHT40, we intentionally remove inner-layer copper to stop L2/L3 from becoming thermal bridges.

For the first revision I would also avoid unnecessary manufacturing heroics:

    minimum 0402, not 0201;

    all SMD components on one side where practical;

    standard board thickness;

    standard ENIG or lead-free HASL;

    no blind/buried vias;

    no BGA;

    standard routed slots;

    ESP module instead of raw RF IC.

That aligns particularly well with low-cost assembly. JLCPCB's current Economic PCBA service covers 2–50 units, 2/4/6-layer PCBs, 0402 minimum packages and single-sided placement, which maps almost perfectly to this project.
6. Power subsystem

The power design deserves disproportionate attention because bad power design will destroy the battery-life objective.

I'd provision the ESP32 rail for at least 500 mA transient capability. Espressif itself specifies that the external supply should be capable of 0.5 A, and the published Wi-Fi TX peaks reach 382 mA.

The TPS62840 is attractive because TI specifies:

    1.8–6.5 V input;

    up to 750 mA output;

    only ~60 nA operating quiescent current;

    power-save operation intended for very small loads;

    RF-friendly regulation.

For a 1S LiPo, I would investigate operating the system rail around 3.0 V rather than automatically selecting 3.3 V. The ESP32-C6 module's rated supply range is 3.0–3.6 V and the SHT40 operates far lower than that. A ~3.0-V rail lets a buck converter use more of the lower end of the LiPo discharge curve before entering dropout. That needs to be validated with USB and RF operation on the prototype, but it is worth testing.
7. Battery-life forecast

There is no honest single number before measuring the real Wi-Fi association and TLS transaction time.

An ESP wakes up very briefly, but the difference between:

    good access point, connected and uploaded in 1–2 seconds

and

    poor RSSI, scans/retries and takes 5–10 seconds

is enormous.

For planning, assume a 1000 mAh cell, roughly 80% practically usable capacity, ~7–20 µA sleeping electronics and an active Wi-Fi transaction averaging perhaps 100–150 mA for a few seconds.

My engineering planning ranges would therefore be approximately:
Behaviour	1000 mAh planning range
Always connected to Wi-Fi	days, not months
Upload every 5 min	~1–2 months
Upload every 10 min	~2–4 months
Upload every 15 min	~3–5 months
Measure every 5 min, batch upload every 15–30 min	potentially ~4–8 months
Very poor Wi-Fi / many retries	considerably worse

Those are budget estimates, not component specifications.

A very useful trick is:

measure often, transmit less often.

For example:

00:00 measure, save locally
00:05 measure, save locally
00:10 measure, save locally
00:15 measure + connect Wi-Fi + upload four readings

The SHT40 measurement itself costs almost nothing. Wi-Fi association/TLS/upload is what costs the battery.

A 500 mAh cell roughly halves the resulting lifetime but makes the enclosure noticeably smaller.
8. Firmware and aggregation architecture

For the first 20 devices, I would resist building a custom cloud application.

The architecture can be:

SHT40
   │ I²C
   ▼
ESP32-C6
   │
   │ Wi-Fi + TLS
   ▼
MQTT broker
   │
   ├── Home Assistant
   │
   ├── InfluxDB
   │
   └── Grafana

For a home deployment, Mosquitto + Home Assistant is probably enough initially. If this turns into a larger system, InfluxDB/Grafana or another time-series backend can be added later.

Each unit gets something like:

device ID: sensor-01

home/sensors/sensor-01/telemetry
home/sensors/sensor-01/status

Telemetry could contain:

timestamp
temperature
humidity
battery_voltage
battery_percent
RSSI
firmware_version
charging

I would use BLE only during commissioning. The phone discovers the device, sends SSID/password securely, and thereafter BLE is normally disabled.

ESP-IDF already provides secure Wi-Fi provisioning, TLS, HTTPS OTA, secure boot, flash encryption and encrypted storage facilities. Espressif explicitly recommends TLS for external communications and secure boot on production devices.

For twenty devices this matters. I would give every device a unique identity/credential, rather than baking one shared MQTT password into all twenty.
9. Details I would put on the PCB that are easy to forget

I'd include production/test features from revision one.

There should be pogo-pin test pads for:

GND
VBAT
3V rail
EN/reset
BOOT
USB D+
USB D-
and/or UART TX/RX

The ESP32-C6 has native USB Serial/JTAG pins, so we don't need a separate USB-to-UART IC just to program it.

I'd also provide:

    USB-C ESD protection;

    correct USB-C CC resistors;

    battery connector;

    battery thermistor support;

    charger-state input to ESP32;

    test point for SHT40 I²C;

    switchable battery-voltage ADC divider;

    reset/provisioning button;

    optional status LED that can be completely disabled.

The last point sounds trivial, but a permanently lit LED consuming even 1 mA is disastrous in a product whose sleeping electronics are consuming microamps.
10. Battery and enclosure strategy

I would not ask a Chinese PCBA house to ship twenty LiPo cells with the boards unless there is a good reason.

Instead:

PCBA manufacturer → Germany: assembled electronics without batteries

and then:

German/EU supplier → us: protected LiPo packs

This simplifies lithium-battery transport and lets us choose a battery whose UN 38.3 transport documentation is readily available.

More importantly, I would make the battery physically replaceable from day one.

EU Battery Regulation Article 11 starts applying from 18 February 2027. For products incorporating portable batteries, the regulation generally requires the battery to be readily removable and replaceable by the end user using commercially available tools, with removal/replacement information available.

So the enclosure should be:

2–4 screws
     ↓
cover removed
     ↓
battery connector accessible
     ↓
battery slides out

Not:

glued enclosure + glued LiPo + soldered battery leads

Even for this prototype, designing the former costs almost nothing and saves a redesign later.
11. The manufacturing vendors I would shortlist
Lowest-cost route: JLCPCB

For this exact quantity, JLCPCB is highly suitable. Its Economic PCBA category currently supports 2–50 pieces, 2/4/6-layer boards, single-sided assembly, 0402 packages and quoted assembly build times in the 1–3-day range before shipping.

JLCPCB PCBA capabilities

I would design the board intentionally around its economic assembly capabilities.
European/German-friendly route: AISLER

AISLER is attractive if quick local iteration and supply-chain simplicity matter more than absolute lowest price. Their bare prototype boards are manufactured in Germany, they support native KiCad projects, and their prototype assembly service operates through a European manufacturing network. They list an assembly MOQ of one unit, double-sided assembly, 0201 capability, customer-supplied parts, and testing/programming options by arrangement.

AISLER prototype assembly

AISLER would be particularly convenient for the 5 + 5 experimental batch because turnaround between revisions matters more than saving €50 at this point.
PCBWay

PCBWay is also a perfectly legitimate turnkey alternative, particularly if we eventually need more manual operations, unusual parts or box-build. I would get a comparison quote at the final-20 stage rather than architect the electronics around it.

So my vendor ranking would be:
Situation	My choice
Lowest-cost prototypes	JLCPCB
Easiest EU/local iteration	AISLER
More custom assembly requirements	PCBWay
Final 20 if design is stable	JLCPCB or AISLER quote comparison
12. What we actually need to create

This is more than "a Gerber file."

The project package eventually needs these deliverables:
Package	Contents
Requirements	dimensions, accuracy target, reporting interval, battery-life target, environment
Electrical schematic	full circuit + component values
BOM	manufacturer part number, quantity, approved alternates
PCB	native KiCad layout and stack-up
Fabrication output	Gerber/ODB++, drill files, fabrication drawing
Assembly output	BOM CSV, pick-and-place/CPL, paste layers, assembly drawing
Mechanical	PCB STEP model, enclosure STEP/STL
Firmware	source, build configuration, versioning
Production image	signed binary / provisioning procedure
Test specification	electrical and functional acceptance criteria
Programming fixture	pogo-pin pattern/jig
Device identity	serial/QR and credentials
Documentation	assembly instructions, battery replacement, product information
Compliance file if commercial	drawings, BOM, risk assessment, test evidence, DoC etc.

This is also very close to the sort of technical documentation seen in Espressif's own module RED assessment: schematic, block diagram, BOM, PCB layout, risk assessment, test reports and product documentation are all listed in that technical file.
13. How I would prototype this — specifically

I would not order twenty Version A and twenty Version B.

I would do this:

    Breadboard/development validation. Use an ESP32-C6 development board plus SHT40 breakout. Prove Wi-Fi provisioning, MQTT/TLS, deep sleep, upload timing and current consumption before PCB layout.

    One shared schematic. Define ESP32-C6-MINI-1, SHT40, charger, regulator, USB-C and battery connector once. Lock the pin mapping.

    PCB Rev A1 — Compact. Target roughly 30 × 34 mm. SHT40 at the opposite end from charger/ESP32.

    PCB Rev B1 — Isolated. Same schematic/BOM, but approximately 28 × 48 mm with sensor tongue, milled thermal slots and separate enclosure chamber.

    Order five A + five B. Not twenty. Ideally populate them in the same production period so component variation is minimized.

    Build two 3D-printed enclosures. A is maximally compact. B has a proper sensor chamber, vents and internal partition.

    Run a comparative test. Put all ten devices together with one trusted reference sensor. Test sleeping, repeated Wi-Fi transmission, USB charging, high/low RSSI, temperature step changes and humidity changes.

    Measure power properly. Capture the wake→measure→Wi-Fi→TLS→publish→sleep current waveform. Battery-life forecasts then become measurements instead of guesses.

    Choose A or B. My expectation is B wins on measurement quality. If A is within the error budget, however, we have quantitative justification for making the smaller product.

    Rev B2/A2 and manufacture 20. Fix everything found during testing, add the programming/test fixture, assign unique identities and then order the twenty-unit run.

That is the sequence I would actually spend money on.
14. What specifically constitutes a successful A/B test

I wouldn't merely put the two designs on a desk and see whether the numbers "look similar."

I'd measure four operating states:
Test	Purpose
30+ min deep sleep equilibrium	Baseline PCB/enclosure offset
Wi-Fi upload every minute	Artificially exaggerate ESP heating
USB charging	Worst charger-induced heating
Normal 5-min measurement / 15-min upload	Real use case

Then compare:

Tdevice – Treference
RHdevice – RHreference

across all five A units and all five B units.

The important result isn't only average offset. We want:

    mean offset;

    unit-to-unit spread;

    warm-up transient;

    recovery after Wi-Fi;

    recovery after charging;

    response time after environmental change.

That will tell us whether thermal compensation in firmware is sensible or whether the mechanical solution has already eliminated most of the problem.
15. Preliminary cost forecast

These numbers are engineering budget envelopes, not vendor quotes, because we don't yet have a final BOM or actual PCB files.
Prototype stage

For 5 Compact + 5 Separated PCBAs:
Path	Planning budget
China turnkey assembly	roughly €180–400 total
European prototype assembly	roughly €350–900 total
Batteries	~€50–100 total depending on capacity/source
Initial 3D-printed cases	~€30–100
Dev boards/test accessories	~€50–150

So I would reserve roughly €300–600 for a cost-focused prototype exercise or €500–1,100 for a more EU-centric iteration.
Final twenty

Once the board is stable:
Item	Approximate planning range
20 PCBAs, low-cost turnkey	~€250–550
20 PCBAs, European assembly	~€500–1,200
20 protected LiPos	~€100–200
20 printed cases	~€60–200
Misc. screws/connectors/labels	~€30–100

A reasonable prototype-series expectation is therefore somewhere around €20–45 per finished unit on the cost-oriented route, before engineering time and regulatory/compliance work.

The ESP module and SHT40 themselves are not what make this expensive. Low-volume setup, power circuitry, connectors, batteries, enclosure, logistics and testing dominate.
16. Germany/EU: the part I would not ignore

There are two very different scenarios.

Scenario 1: twenty engineering prototypes for your own/internal experimentation.

We should design responsibly but avoid spending thousands on formal compliance testing before the electronics are stable.

Scenario 2: selling, giving out or commercially distributing these as a product.

Then this is internet-connected radio equipment, and the compliance project becomes real.

The finished device needs consideration under the Radio Equipment Directive 2014/53/EU for safety, EMC, RF exposure/spectrum and associated conformity documentation. Again, Espressif's module certification helps, but its certificate expressly says the manufacturer of the final host product has to assess the finished combination.

There is also a cybersecurity dimension now. Internet-connected radio equipment has been subject to the RED cybersecurity requirements since 1 August 2025. The EU Cyber Resilience Act becomes generally applicable on 11 December 2027, with its vulnerability-reporting Article 14 beginning on 11 September 2026. The EU has already adopted the transition that repeals the overlapping RED delegated cybersecurity regulation when the CRA becomes fully applicable.

Since today is August 2026, I'd build the firmware architecture with this direction in mind now: authenticated OTA, a vulnerability/update process, no universal default credentials, unique device identity, TLS and secure boot.

For Germany specifically, if this eventually becomes a commercial product, WEEE/electronics and battery producer-responsibility obligations also enter the picture. Germany's BattDG replaced the previous BattG on 7 October 2025, and Stiftung EAR now carries the relevant authority responsibilities under that regime.

That regulatory effort can easily become more expensive than twenty pieces of hardware, which is another reason to separate the engineering prototype phase from the commercial product phase.
17. Things I caught on a second design review

There are several failure modes that wouldn't be obvious from a simple "ESP32 + humidity sensor" schematic.

First, the battery cannot sit beneath the ESP antenna. A LiPo pouch, wiring, ground plane or metal in the wrong location can hurt RF. The antenna and its free-space region therefore constrain the enclosure almost as much as the PCB dimensions. Espressif explicitly says to test the finished enclosure for throughput/range.

Second, charging is likely to cause more temperature error than normal telemetry. The ESP transmits for seconds. A linear charger can dissipate heat for hours. This strengthens the argument for Version B.

Third, the humidity sensor must be protected during manufacturing. Humidity sensors are susceptible to contamination; Sensirion has separate handling and contamination guidance and notes that contamination can cause humidity offsets. I would keep conformal coating, uncured adhesives, excessive flux/cleaning chemistry and some freshly printed/resin enclosure materials away from the sensor opening.

Fourth, Wi-Fi quality controls battery life. A sensor far from an access point may spend several times longer awake. The firmware therefore needs retry limits rather than endlessly attempting to connect.

Fifth, OTA is not optional once twenty boxes are deployed around a building. Physically recovering twenty devices to correct one firmware bug gets old very quickly.

Sixth, don't calibrate away a mechanical problem too early. A constant software offset might fix one room condition but fail as charging, duty cycle or airflow changes. Thermal isolation comes first; compensation comes afterward.
18. My resulting recommendation

I would pursue both versions for revision one, exactly as you suggested, but with a very deliberate purpose:
A — Compact experiment

~30 × 34 mm, everything on one rigid PCB, sensor at extreme opposite end, aggressive copper removal around it, measure-before-Wi-Fi firmware.

This tells us how small we can get away with.
B — Accuracy-oriented experiment

~28 × 48 mm, same electrical design, but SHT40 on a 12–20 mm isolated PCB tongue with routed slots, minimal copper and a dedicated vented sensor chamber.

This tells us what a mechanically well-designed temperature/RH instrument looks like.

5 units A + 5 units B → comparative validation → one revised design → 20 units.

I would currently put roughly 75% probability on B becoming the design we actually want. The increase in PCB area is small in monetary terms, while temperature/humidity measurement is literally the purpose of the device. Saving 15 mm of PCB at the cost of having to mathematically guess the true room temperature is usually the wrong trade.

And critically, B does not require a separate flex PCB or expensive exotic manufacturing. It remains a normal four-layer rigid PCB with two routed slots. That keeps it firmly in the "small batch of twenty is easy" category.

The next useful engineering step is to turn this architecture into a component-level Rev-A design specification: exact schematic blocks, pin assignments, resistor/capacitor values, USB-C/charger circuit, battery connector, test pads, BOM with manufacturer part numbers, and dimensioned floorplans for A and B. That would get us very close to the point where an actual KiCad schematic/PCB can be laid out and uploaded to JLCPCB/AISLER for the first 5+5 quote.

Today 4:12 PM
Okay, get the plan then and write down everything what needs to be done. I mean for both ideas and the philosophy that is out and how to, I mean everything what is needed for such a hardware. PCB design, okay?

Yes. I would now treat this as a real hardware product-development project with a controlled sequence: requirements → schematic → two PCB layouts → enclosure → prototype manufacturing → electrical/thermal/RF validation → revision → final 20-unit batch.

The central philosophy is important: we should not design two completely different devices. We design one electrical platform and produce two physical implementations of it. That lets us determine experimentally how much compactness costs us in temperature/humidity accuracy.
Master plan: ESP32 environmental sensor
1. Product philosophy

We lock these principles before drawing the PCB.
Common electrical platform

Both versions use essentially the same:

    ESP32 module

    temperature/humidity sensor

    battery

    battery charger

    regulator

    USB-C charging

    test/programming interface

    firmware

    Wi-Fi/BLE provisioning

    cloud/MQTT interface

Only the PCB geometry, thermal isolation and enclosure differ.

That means:

Version A — Compact

    Make the complete product as small as reasonably possible.

Version B — Measurement-first

    Spend another ~15–20 mm of PCB length to physically and thermally separate the environmental sensor.

Everything else should remain identical.
2. Proposed block architecture

The common architecture should look approximately like this:

                         ┌─────────────────────┐
                         │      SHT40          │
                         │ Temperature + RH    │
                         └──────────┬──────────┘
                                    │ I²C
                                    │
┌──────────────┐             ┌──────▼───────────┐
│ LiPo battery │             │ ESP32-C6-MINI-1 │
│ 500-1000mAh │             │                  │
└──────┬───────┘             │ Wi-Fi            │
       │                     │ Bluetooth LE     │
       ▼                     │ Thread/Zigbee    │
┌──────────────┐             │                  │
│ Protection   │             └─────┬────────────┘
└──────┬───────┘                   │
       │                           │
       ├──────────────┐            │
       │              │            │
       ▼              ▼            │
┌────────────┐  ┌────────────┐     │
│ LiPo       │  │ Low-power  │─────┘
│ charger    │  │ regulator  │
└─────┬──────┘  └────────────┘
      │
      ▼
   USB-C

For the MCU I would continue with the ESP32-C6-MINI-1 module rather than the bare ESP32-C6 IC. The module is about 13.2 × 16.6 × 2.4 mm, incorporates flash, crystal, RF matching and PCB antenna, and Espressif publishes the land pattern and 3D model.

Using the module removes one of the riskiest parts of a small production PCB: designing and tuning our own 2.4-GHz antenna circuit.
3. Requirements document — do this first

Before KiCad starts, we create a one-page engineering requirements specification.

I would provisionally set these requirements:
Requirement	Initial target
Temperature	approximately ±0.3 °C system target
Humidity	approximately ±3 %RH system target
Measurement interval	5 min configurable
Upload interval	15 min configurable
Connectivity	2.4-GHz Wi-Fi
Provisioning	Bluetooth LE
Local storage	enough for temporary network outage
Battery	replaceable rechargeable 1S LiPo
Initial capacity	500–1000 mAh
Charging	USB-C 5 V
Runtime	target >3 months
Firmware update	OTA
Operating environment	indoor residential
Quantity Rev 1	5 A + 5 B
Quantity Rev 2	20
PCB	4-layer FR-4
Assembly	predominantly one-sided SMT
Enclosure	initially 3D printed

Some values intentionally remain targets rather than promises until we measure prototypes.
4. Sensor selection
Baseline: Sensirion SHT40

This is still my preferred starting point.

It is:

    1.5 × 1.5 × 0.5 mm;

    factory calibrated;

    digital I²C;

    suitable for low-power products;

    available in versions with protective/filter options.

Sensirion explicitly warns that product-level accuracy depends strongly on PCB and enclosure design, not merely on sensor accuracy. Their design guide calls for good ambient-air access, small dead volume, separation from trapped internal air and thermal decoupling from heat sources.

For a finished product I would investigate using one of the SHT4x versions with a filter membrane rather than exposing an unprotected sensor cavity directly through an enclosure opening. Sensirion also offers membrane and FPCB approaches for exactly this type of mechanical integration.
5. ESP32 subsystem

The schematic needs:

    ESP32-C6-MINI-1;

    bulk input capacitance;

    local 100 nF decoupling;

    EN/reset circuit;

    provisioning/reset button;

    programming/debug pads;

    optional LED;

    I²C;

    charger-status input;

    battery-voltage ADC input.

Espressif recommends a 3.3-V-class power supply capable of at least 500 mA and at least 10 µF near the supply entrance.

That apparently oversized current capacity is necessary because Wi-Fi transmission peaks are significant: the module datasheet specifies peaks up to about 382 mA, while deep sleep is approximately 7 µA.

That fact determines almost the complete firmware and power philosophy.
6. Power philosophy

The sensor must not remain Wi-Fi-connected continuously.

Normal operation becomes:

DEEP SLEEP
    ↓
Wake by RTC
    ↓
Read SHT40
    ↓
Save measurement
    ↓
Is it upload time?
   / \
 no   yes
 │     ↓
 │   Start Wi-Fi
 │     ↓
 │   Connect
 │     ↓
 │   Upload measurements
 │     ↓
 │   Shut Wi-Fi down
 │
 └───────────────→ DEEP SLEEP

And importantly:

    Take the environmental measurement before starting the Wi-Fi transmitter.

This reduces both battery consumption and self-heating error.
7. Battery architecture

For Rev 1 I would design around:

1-cell LiPo/Li-ion

Nominal:

    3.7 V;

    maximum charge ~4.2 V;

    approximately 500–1000 mAh.

The battery pack should itself have appropriate protection against:

    overcharge;

    over-discharge;

    excessive current/short circuit.

We then need separate charging and system regulation on the PCB.
8. Charger subsystem

We need a charger with:

    5-V USB input;

    single-cell LiPo charging;

    programmable charge current;

    temperature/NTC capability preferably;

    low standby consumption;

    charger-status output;

    ideally proper power-path behaviour.

The exact charger IC should be locked during the schematic design rather than chosen only because it is cheap.

For this application I would constrain the charge current somewhere around 100–250 mA initially, subject to the chosen battery manufacturer's charging specification.

We explicitly do not want 1 A charging in a temperature sensor.

Why?

Because a linear Li-ion charger behaves as a heat source.

If:

USB = 5.0 V
Battery = 3.7 V
Charge current = 250 mA

the charger may have to dissipate on the order of:

(5.0 - 3.7) × 0.25
≈ 0.325 W

under an illustrative operating condition.

Three hundred milliwatts inside a tiny temperature sensor enclosure is significant.

That directly supports Version B.
9. Regulator subsystem

The ESP32 supply needs:

    very low quiescent current;

    approximately 500–750 mA transient capability;

    good transient response;

    high efficiency at extremely small sleep loads.

A part such as the TPS62840 class is worth considering.

During schematic design we should compare:

    buck converter;

    buck-boost converter;

    simple LDO.

For a battery sensor, I expect a low-Iq switching regulator to win.

We should test approximately 3.0 V versus 3.3 V system operation rather than automatically selecting 3.3 V.
10. Battery measurement

The ESP32 should measure its own battery voltage.

But we should not place a low-value permanent resistor divider across the battery, because it would drain the battery continuously.

Use either:

    very high-value divider + filtering;

    MOSFET-switched divider;

    charger/fuel-gauge battery monitoring.

My preferred first implementation is a switchable ADC divider.

ESP wakes:

enable divider
wait briefly
measure battery
disable divider

11. USB-C design

I would make USB-C primarily:

charging/power

rather than automatically adding every USB feature.

That keeps Version A smaller and avoids unnecessary USB routing.

Required items include:

    USB-C receptacle;

    CC1 resistor;

    CC2 resistor;

    VBUS;

    ground;

    ESD protection;

    charger input;

    mechanical reinforcement.

We can optionally connect native ESP32 USB Serial/JTAG later.

For twenty production units, programming through a pogo-pin fixture is entirely acceptable.
12. Version A — compact PCB

The approximate physical philosophy:

   SENSOR                                        ANTENNA
      ↓                                             ↓

┌──────────────────────────────────────────────────────┐
│ SHT40      regulator    battery/charger    ESP32-C6 │
│   ●                                      ┌─────────┐│
│                                          │         ││
│ USB-C                                    │ MINI-1  ││
│                                          │ antenna→││
└──────────────────────────────────────────┴─────────┘

Initial target:

~30 × 34 mm, subject to real placement.

The SHT40 goes:

    at one extreme board edge;

    as far as practical from ESP32;

    far from regulator;

    far from charger;

    far from battery;

    beside enclosure ventilation.

ESP32 antenna goes at the opposite board edge.
13. Version A thermal rules

Around SHT40:

    no large ground pour;

    no power plane where avoidable;

    narrow SDA trace;

    narrow SCL trace;

    narrow VDD;

    narrow GND;

    minimum nearby vias;

    no LED;

    no charger;

    no regulator;

    no high-current traces;

    no battery directly underneath.

The PCB itself should effectively have:

normal electronics PCB
        │
        │ increasingly little copper
        │
        ▼
    SHT40 edge

The measurement should be made before radio activity.

The charging state should also be reported to firmware so that data captured while charging can be identified.
14. Compact-A enclosure

The enclosure probably looks approximately like:

┌────────────────────────────┐
│ :::::                   RF │
│ :air: SHT40              → │
│ :::::                      │
│                            │
│        PCB                 │
│                            │
│      battery               │
│                      USB-C │
└────────────────────────────┘

Important:

The vents must be beside the SHT40, not randomly located in the enclosure.

The product housing is part of the sensing system.
15. Version B — thermally isolated PCB

Version B uses the same schematic.

But geometrically:

 SENSOR ISLAND                MAIN ELECTRONICS
                                   BOARD

 ┌───────────┐              ┌─────────────────────┐
 │           │              │                     │
 │   SHT40   │──────────────│ regulator           │
 │     ●     │ narrow neck  │ charger             │
 │           │──────────────│ battery connector   │
 └───────────┘              │ ESP32-C6      RF → │
   ↑       ↑                └─────────────────────┘
   │       │
 routed PCB slots

Target approximately:

28–32 × 45–50 mm

depending on placement.
16. The sensor island

The PCB has two milled slots:

      ┌───────────────┐
      │     SHT40     │
      │       ●       │
──────┘               └──────
──────┐               ┌──────
      └───────────────┘

leaving a narrow mechanical bridge.

Only four electrical paths cross it:

VDD
GND
SDA
SCL

And these should be narrow.

Crucially:

remove internal L2/L3 copper underneath the thermal neck.

Otherwise we carefully mill slots in the visible FR-4 while leaving a large inner copper plane that conducts heat straight across the isolation structure.

Sensirion specifically recommends reducing thermal coupling to heat sources and shows PCB/enclosure separation techniques for SHT-class sensors.
17. Version B enclosure

Here I would create two air chambers.

┌─────────────────────────────────────────────┐
│                                             │
│ AMBIENT SENSOR          ELECTRONICS         │
│ CHAMBER                 CHAMBER             │
│                                             │
│ ::::::::::::     │                          │
│ :: SHT40 ::      │   ESP32                  │
│ ::::::::::::     │   charger                │
│                  │   regulator              │
│                  │   battery                │
│                  │                          │
└─────────────────────────────────────────────┘
                   ↑
             internal wall

The PCB tongue passes through the wall.

This blocks warm internal air from simply flowing toward the environmental sensor.
18. Why not use a cable immediately?

The thermally best architecture could be:

main PCB
   │
thin flex cable
   │
tiny SHT40 PCB

But I would not start there.

It creates:

    another PCB;

    another BOM;

    FPC;

    connector;

    mechanical retention;

    more assembly steps;

    more possible failures;

    increased cost.

Sensirion does note that FPCB mounting is useful because it reduces thermal conduction, so we retain this as a Version C fallback if rigid-PCB isolation is insufficient.

But Version B is deliberately designed to avoid needing it.
19. PCB stack-up

Use 4 layers.

My baseline:

L1  components + signals
L2  continuous GND
L3  power + slow signals / GND
L4  minimal signals / GND

Espressif itself recommends four layers for ESP32-C6 designs, although two-layer construction is possible.

For the bulk of our PCB, L2 should remain a strong continuous ground reference.

The exception is the SHT40 thermal island where thermal isolation deliberately takes precedence.
20. ESP32 antenna placement

This part has to be treated as a hard mechanical constraint.

Espressif recommends positioning the module so its PCB antenna extends beyond the carrier PCB if possible. If it cannot, the antenna should be near the board edge with appropriate clearance. Espressif also recommends keeping approximately 15 mm free around the antenna in the finished product and validating actual RF performance in the completed enclosure.

Therefore no:

    LiPo pouch;

    big copper area;

    USB connector;

    screws;

    metal mounting plate;

    wiring;

should sit directly against the antenna area.
21. PCB component-placement order

Don't simply drop components onto the board arbitrarily.

Placement order should be:

    ESP32 antenna.

    SHT40.

    USB connector.

    battery connector.

    charger.

    regulator/inductor.

    bulk capacitors.

    ESP32 module.

    buttons.

    debug/test pads.

    miscellaneous passives.

Why that order?

Because antenna, sensor and external connectors are mechanically constrained.

Resistors are not.
22. Component-size philosophy

For the first revision:

Use 0402 as our normal minimum.

Avoid 0201 unless genuinely necessary.

Use larger components where board area isn't important:

    0603 test-friendly components;

    larger capacitor packages where capacitance derating matters.

The board is already small enough.

Making everything 0201 to save 2 mm makes hand inspection, debugging and rework unnecessarily difficult.
23. Single-sided assembly

I would try hard to put virtually all components on one side.

Benefits:

    cheaper assembly;

    easier manufacturing;

    easier inspection;

    easier rework;

    simpler fixture;

    simpler enclosure design.

The battery can occupy space behind the bare backside of the PCB.

JLCPCB's current assembly workflow for low-volume products readily supports Gerber + BOM + CPL production and small SMT components; its assembly documentation explicitly identifies Gerber, BOM and component-placement data as the key inputs.
24. PCB design rules

Before routing, create actual design constraints in KiCad.

We define:
General

    minimum track width;

    minimum clearance;

    minimum via drill;

    annular ring;

    copper-to-edge;

    solder-mask clearance.

Power

Separate net classes for:

    VBAT;

    USB 5 V;

    ESP32 supply;

    low-current digital signals.

Sensor

Special constraints:

    narrow thermal traces;

    no copper fills across thermal neck.

Antenna

Create an explicit:

RF KEEP-OUT

on every relevant layer.

Do not rely on remembering not to route there.
25. Schematic design blocks

I would divide the KiCad schematic into logical sheets:

00_System
01_ESP32
02_Sensor
03_Power_Regulator
04_Battery_Charger
05_USB
06_Buttons_LED
07_Programming_Test

This makes later review significantly easier than one enormous sheet.
26. Component library work

Before PCB layout we verify the footprint of every nontrivial component.

Especially:

    ESP32 module;

    SHT40;

    charger IC;

    regulator;

    inductor;

    USB-C connector;

    battery connector.

For every important component check:

schematic symbol
↓
pin numbers
↓
footprint
↓
pad dimensions
↓
pin 1
↓
rotation
↓
3D model

Footprint errors are among the easiest ways to turn 20 perfectly fabricated PCBs into garbage.

The ESP32 module datasheet contains the official recommended land pattern and links to STEP data.
27. Design-for-test

This should not be an afterthought.

Add test pads for at least:

GND

VBUS
VBAT
V_SYS / 3V rail

ESP EN
BOOT

UART TX
UART RX

or USB D+
USB D-

SDA
SCL

charger status

Potentially also one GPIO dedicated to a production-test mode.
28. Pogo fixture

For 20 units, I would already build a tiny programming jig.

Something like:

            PCB
       ┌───────────┐
       │ ● ● ● ● ● │
       └─┬─┬─┬─┬─┬─┘
         │ │ │ │ │
      pogo pins
         │ │ │ │ │
       fixture PCB

You press the finished PCB into it and:

    power it;

    flash firmware;

    run self-test;

    verify SHT40;

    verify charger;

    read MAC address;

    assign serial number;

    write credentials;

    run Wi-Fi test.

That transforms twenty handmade prototypes into something approaching an actual production process.
29. Hardware self-test firmware

The factory firmware should provide an explicit test mode.

It should return something like:

Device serial: ENV-0017
ESP MAC: ...
Firmware: 0.1.0

3V3: PASS
Battery ADC: PASS
SHT40: PASS
Temperature: 23.42 C
Humidity: 45.7 %
Wi-Fi radio: PASS
RSSI: -46 dBm
Flash: PASS

FINAL TEST: PASS

Then production becomes repeatable.
30. Unique device identity

Every device gets:

ENV-0001
ENV-0002
...
ENV-0020

and preferably a QR label containing its ID.

Avoid putting one universal cloud password into twenty devices.

Each device should have its own credentials or authentication material.
31. Firmware architecture

I'd use ESP-IDF rather than starting the production firmware as an Arduino sketch.

Modules:

/app
/sensor
/power
/storage
/wifi
/provisioning
/mqtt
/ota
/security
/diagnostics

Firmware requirements include:

    BLE provisioning;

    Wi-Fi credential storage;

    RTC wake-up;

    SHT40 driver;

    local ring buffer;

    MQTT/HTTPS;

    TLS;

    battery monitoring;

    retry policy;

    watchdog;

    OTA;

    configuration;

    firmware versioning.

32. Wi-Fi failure handling

Very important for battery life.

Don't do:

while(!wifi_connected)
    retry_forever();

Instead:

try for 10-20 seconds

success?
  upload

failure?
  store data
  sleep

retry next scheduled interval

A sensor at the edge of Wi-Fi coverage must not flatten its battery because the router disappeared.
33. Local data buffer

The device should retain some measurements during outages.

For example:

100–500 measurements

inside flash.

If network is unavailable:

measurement
   ↓
local queue
   ↓
sleep

Once network returns:

new measurement
+
queued measurements
   ↓
upload

34. Backend data format

I would keep it boring and transparent.

Example:

{
  "id": "ENV-0017",
  "ts": 1787666700,
  "temperature_c": 22.84,
  "humidity_rh": 46.1,
  "battery_v": 3.91,
  "rssi_dbm": -54,
  "charging": false,
  "firmware": "0.2.1"
}

That is sufficient for Home Assistant, InfluxDB, Grafana or essentially any custom backend.
35. Mechanical CAD

After preliminary component placement — not after final PCB routing — export PCB STEP.

Build the enclosure around the real board.

Mechanical CAD needs:

    PCB outline;

    battery volume;

    USB location;

    button location;

    sensor opening;

    antenna exclusion volume;

    mounting points;

    battery access;

    lid;

    wall thickness;

    ventilation.

Then feed mechanical changes back into KiCad.

PCB design and enclosure design should iterate together.
36. Sensor vent design

The sensing opening needs engineering.

For Version B:

outside air
    ↓
large vent
    ↓
very small sensor chamber
    ↓
SHT40

Avoid:

outside air
    ↓
tiny hole
    ↓
large enclosed cavity
    ↓
SHT40

because that produces slow response and encourages internal heat to influence the reading.

Sensirion specifically recommends small dead volume and good environmental access.
37. Contamination

Humidity sensors are chemically sensitive.

We therefore need manufacturing rules covering:

    soldering;

    board cleaning;

    adhesives;

    conformal coating;

    enclosure printing/resin;

    storage;

    packaging.

If conformal coating is ever used, the sensing element needs proper process protection.

Sensirion publishes dedicated contamination and design-in guidance for SHT4x devices.
38. Battery placement

Battery placement has three competing constraints:

Antenna

Keep it away from ESP32 antenna.

Sensor

Keep it away from SHT40.

Thickness

Put it behind the central electronics area to minimize enclosure footprint.

So a likely cross-section is:

                 sensor
                    ↓
PCB ───────────────────────────
        battery
    ┌─────────────┐
    │             │
    └─────────────┘

                antenna area
                has no battery

39. Enclosure battery replacement

I would design Rev 1 with:

    screws;

    replaceable battery;

    connector;

    no permanent adhesive.

This is good engineering regardless of compliance, and it aligns with upcoming EU battery-replaceability requirements. Article 11 of the EU Battery Regulation becomes applicable from 18 February 2027 for products incorporating portable batteries, subject to its scope and exceptions.
40. PCB design review — schematic

Before routing begins, conduct a formal schematic review.

Verify:

    every supply voltage;

    every IC maximum rating;

    ESP32 strapping pins;

    EN/reset;

    pull-ups;

    charger programming;

    battery polarity;

    USB CC configuration;

    SHT40 I²C;

    ADC range;

    GPIO boot state;

    unused pins;

    ESD;

    power-off current;

    programming path.

Run ERC.

Zero unexplained errors.
41. PCB layout review

Then a separate layout review:
RF

    antenna correctly positioned;

    keep-out correct;

    no battery near antenna;

    no copper below antenna where prohibited;

    enclosure clearance.

Thermal

    SHT40 separated;

    sensor copper minimized;

    Version B thermal neck clear on all four layers;

    charger distant.

Power

    short regulator loop;

    decoupling immediately beside IC;

    adequate power traces;

    good grounding.

Manufacturing

    components aren't too close to edges;

    correct pin 1;

    assembly access;

    USB reinforcement;

    board slots valid.

Mechanical

    screws don't hit copper;

    battery fits;

    enclosure fits;

    USB opening aligned;

    sensor aligned with ventilation.

Run DRC.

Again:

zero unexplained DRC violations.
42. Generate PCB production outputs

A PCB fabricator will need a Gerber package containing appropriate layers such as:

Top copper
Inner copper 1
Inner copper 2
Bottom copper

Top soldermask
Bottom soldermask

Top silkscreen
Bottom silkscreen

Board outline
Drill files

JLCPCB's documentation lists these standard Gerber layers and explicitly calls out the drill/outline information.
43. PCBA production outputs

For assembly we additionally need:
BOM

Every part:

Reference
Value
Package
Manufacturer
Manufacturer part number
Supplier part number
Quantity

CPL / Pick-and-Place

For every component:

Reference
X
Y
Rotation
Side

JLCPCB requires Gerber, BOM and CPL for assembly; the same essential information is requested by PCBWay.
44. Additional manufacturing documents

I would also produce:

    PDF schematic;

    top assembly drawing;

    bottom assembly drawing;

    PCB fabrication drawing;

    STEP model;

    board dimensions;

    stack-up specification;

    special slot instructions;

    programming procedure;

    test procedure;

    acceptable component alternates.

PCBWay explicitly recommends assembly drawings/instructions in addition to the machine files to prevent ambiguous placements.
45. Production package structure

Keep the repository disciplined:

environment-sensor/

  hardware/
    schematic/
    pcb/
    libraries/

    outputs/
      rev-a/
        gerber/
        drill/
        bom/
        cpl/
        assembly/
        step/

      rev-b/
        gerber/
        drill/
        bom/
        cpl/
        assembly/
        step/

  mechanical/
    compact-a/
    isolated-b/

  firmware/

  production/
    flashing/
    fixture/
    testing/

  compliance/

  documentation/

  measurements/
    thermal/
    battery/
    rf/

Do not keep production files named:

final.zip
final2.zip
final-final.zip
final-really-final.zip

Use actual revisions.
46. Revision naming

For example:

HW-A1
Compact PCB prototype

HW-B1
Thermal isolation prototype

HW-B2
Selected design, corrected prototype

HW-B3
20-unit production

PCB silkscreen should actually contain:

ENV SENSOR
HW B1
2026

That becomes invaluable later.
47. Initial manufacturing run

Order:

5 × Compact A

and:

5 × Isolated B

Not twenty of either.

Preferably:

    same ESP module;

    same SHT40 lot if possible;

    same regulator;

    same firmware;

    same battery;

    manufactured at approximately the same time.

Then we have a controlled comparison.
48. Incoming PCB inspection

Before powering anything:

Inspect every board under magnification.

Look for:

    ESP32 orientation;

    SHT40 orientation;

    diode orientation;

    IC pin 1;

    solder bridges;

    missing components;

    USB solder joints;

    charger;

    regulator;

    connector polarity.

Do not immediately plug ten unknown boards into ten LiPo batteries.
49. First board bring-up

Power the first prototype from a current-limited laboratory supply.

Sequence:

1. visual inspection
2. resistance VBAT → GND
3. resistance 3V3 → GND
4. set current limit
5. apply power
6. verify regulator
7. verify ESP reset
8. flash minimal firmware
9. verify serial
10. detect SHT40
11. measure sensor
12. test Wi-Fi
13. test charging
14. test battery

Only after one board works do we move to the rest.
50. Power measurement

We need a current profiler or suitable measurement setup.

Measure the complete waveform:

wake
 ↓
sensor measurement
 ↓
CPU
 ↓
Wi-Fi scan
 ↓
association
 ↓
TLS
 ↓
upload
 ↓
shutdown
 ↓
deep sleep

From that we calculate actual energy per measurement cycle.

Then battery life becomes:

Battery capacity
────────────────────────────
actual average consumption

instead of guessing.
51. Thermal A/B validation

Place:

    all five A devices;

    all five B devices;

    one good reference instrument;

together in a controlled location.

Test:
Test 1

30–60 minutes idle/deep sleep.

Measure baseline error.
Test 2

Force Wi-Fi upload every minute.

Observe self-heating.
Test 3

Charge the battery.

Observe charger heating.
Test 4

Return to normal operating cycle.

Measure recovery.
Test 5

Move all devices to another temperature.

Measure response time.
Test 6

Change humidity.

Measure response.
52. What we record

For every sensor:

T_reference
RH_reference

T_device
RH_device

battery
charging
RSSI
time since boot
time since Wi-Fi TX

Then calculate:

    temperature offset;

    humidity offset;

    standard deviation;

    device-to-device variation;

    thermal transient;

    recovery time;

    charging error.

53. Decision criteria

Version A wins only if:

    it meets our measurement requirements;

    Wi-Fi heating is negligible at normal duty cycle;

    charging effect is acceptable;

    response time is acceptable.

Otherwise Version B wins.

My expectation remains that B will measure better, but we explicitly refuse to assume that before testing.
54. RF testing

Test both versions:

    beside router;

    one room away;

    several walls away;

    worst location in the intended house/building.

Record:

RSSI
association time
upload time
failed attempts
energy per transaction

The finished enclosure is important enough that Espressif explicitly recommends testing communication range and throughput in the final product configuration.
55. Battery tests

Test:
Runtime

Continuous accelerated cycles.
Charging

From low battery to full.
Heat

Sensor error while charging.
Low battery

Behaviour near shutdown.
Brownout

No corrupt flash/network credentials.
Reconnection

After battery removal.
56. Firmware reliability tests

Also force:

    Wi-Fi missing;

    Wi-Fi password changed;

    MQTT broker offline;

    DNS failure;

    TLS failure;

    sudden power loss;

    full data queue;

    OTA failure;

    corrupt update;

    weak battery.

An IoT device is mostly defined by how well it behaves when something is broken.
57. Rev 2

Once testing is complete we produce:

one selected architecture.

Probably something like:

HW-B2

Changes may include:

    board dimensions;

    sensor-neck geometry;

    vent size;

    antenna clearance;

    charger current;

    regulator component;

    capacitor values;

    programming pads;

    battery connector;

    mounting holes.

Then order perhaps:

3–5 B2 engineering verification units

if A1/B1 uncovered significant changes.

For a very minor change, we could move directly to 20, but I would prefer a small B2 verification batch if budget allows.
58. Production of the final twenty

Once B2 has passed:

Generate a frozen manufacturing package.

It should contain:

HW revision
schematic
Gerber ZIP
drills
BOM
CPL
assembly drawing
STEP
firmware version
production binary
test specification
serial numbers
label layout

Then obtain quotes from:

    JLCPCB;

    AISLER;

    optionally PCBWay.

JLCPCB would probably be my first cost-oriented quote. AISLER is worth comparing if European production/iteration is valuable.
59. Manufacturing philosophy

The manufacturer should ideally deliver:

fully assembled PCBs

not bags of PCBs and bags of components.

For 20 pieces there is very little reason to manually solder ~30–50 tiny components per unit.

At most, we might separately install:

    battery;

    enclosure;

    screws;

    labels.

60. Shipping batteries

I would initially buy batteries within Germany/EU rather than package them with the PCBA shipment from Asia.

Reasons include:

    simpler lithium transport;

    easier documentation;

    easier replacement sourcing;

    easier quality control;

    simpler logistics.

Design the PCB around an explicitly selected battery connector/polarity.
61. Compliance architecture

For internal prototypes, formal certification doesn't need to block the first boards.

But design it so it can eventually become compliant.

The ESP32-C6-MINI-1 already has Espressif certification documentation including CE/RED certification, which is useful, although that does not automatically certify the completed product.

If we eventually place the finished device commercially on the EU market, we need to assess things including:

    Radio Equipment Directive;

    EMC;

    RF/spectrum performance;

    electrical safety as applicable;

    RoHS;

    WEEE;

    battery obligations;

    cybersecurity;

    CE technical documentation;

    Declaration of Conformity.

And because this is an internet-connected radio product, cybersecurity should be designed in rather than bolted on afterward. RED cybersecurity requirements became applicable to relevant classes of radio equipment from August 2025; the EU Cyber Resilience Act becomes generally applicable on 11 December 2027, while its Article 14 reporting provisions begin 11 September 2026.

That makes OTA and proper credential handling architectural requirements, not optional luxuries.
62. Security hardware/firmware requirements

Plan for:

    secure boot;

    flash encryption as appropriate;

    TLS;

    device-specific credentials;

    signed OTA;

    rollback mechanism;

    no hard-coded universal passwords;

    factory reset;

    credential reset/reprovisioning.

63. Things we should deliberately NOT do

I would explicitly ban these from Rev 1:

    bare ESP32-C6 RF design;

    custom PCB antenna;

    rigid-flex PCB;

    0201 everywhere;

    BGA;

    two-sided assembly unless necessary;

    glued-in battery;

    Wi-Fi continuously active;

    permanently illuminated LED;

    sensor beside charger;

    sensor directly above battery;

    battery under antenna;

    no test points;

    manual soldering of all twenty;

    ordering twenty before prototype validation.

Each makes the project harder without solving the actual problem.
64. What we lock now

I think these decisions are mature enough to lock:

MCU architecture

ESP32-C6-MINI-1 module.

Sensor family

Sensirion SHT4x.

Connectivity

Wi-Fi plus BLE provisioning.

Power

1-cell rechargeable LiPo.

Charging

USB-C.

Operation

RTC duty cycling/deep sleep.

PCB

4-layer.

Manufacturing

SMT assembly.

Prototype strategy

5 Compact A + 5 Isolated B.

Version B approach

Milled rigid-PCB sensor tongue, not separate FPC.

Case

3D printed during development.
65. What we should NOT lock yet

These need actual engineering selection:

    exact SHT40 variant/filter version;

    exact charger IC;

    exact regulator;

    3.0 vs 3.3-V rail;

    exact USB connector;

    exact battery connector;

    exact battery capacity;

    exact PCB dimensions;

    exact vent geometry;

    exact charge current;

    exact sleep/upload interval;

    exact MQTT/cloud system.

Those should come out of the schematic/BOM and prototype work.
66. Actual project sequence

If I were managing the engineering work, this is the order I would follow:
Phase	Work	Deliverable
0	Requirements	Product requirements v1
1	Component selection	Approved preliminary BOM
2	Architecture	Block diagram
3	Schematic	KiCad schematic
4	Schematic review	Reviewed schematic
5	Footprints	Verified libraries
6	Mechanical floorplan	A/B dimensions
7	PCB A	Compact layout
8	PCB B	Isolated layout
9	Enclosures	A/B STEP/STL
10	PCB review	DRC/DFM signoff
11	Production package	Gerber/BOM/CPL
12	Prototype order	5 A + 5 B
13	Firmware bring-up	Prototype firmware
14	Electrical tests	Test report
15	Power tests	Battery model
16	Thermal tests	A/B comparison
17	RF tests	Coverage results
18	Decision	A or B
19	Rev 2	Corrected PCB/case
20	Verification	B2 verification
21	Production package	Frozen HW/FW
22	Production	20 assembled PCBs
23	Programming	IDs + firmware
24	Final test	20 test records
25	Enclosure	Final assembly
26	Deployment	Install + aggregate data
67. Reasonable schedule

For somebody working on this seriously rather than continuously full-time:

Week 1

Requirements, component selection, architecture.

Week 2

Schematic, libraries, schematic review.

Week 3

A/B PCB placement/layout and enclosure concept.

Week 4

Review, DFM, order.

Week 5–6

Fabrication, assembly, shipping. In parallel: firmware and test fixture.

Week 6–7

Board bring-up, thermal/RF/power tests.

Week 8

Rev 2 layout/enclosure.

Week 9–10

Verification boards.

Week 11

Freeze production design.

Week 12–13

20-unit production and final testing.

So I would budget roughly 8–13 weeks from clean sheet to a tested small series, depending mainly on PCB shipping/revisions and how polished we want firmware/enclosures.
68. Definition of "done"

The project isn't done because KiCad says:

    DRC passed.

It is done when we possess:

Hardware

20 functioning boards.

Measurement

Known temperature/RH performance.

Power

Measured battery lifetime.

Radio

Verified Wi-Fi performance.

Mechanical

Repeatable enclosure.

Firmware

Provisioning, communication and OTA.

Manufacturing

Reproducible Gerbers/BOM/CPL.

Testing

A documented production-test procedure.

Traceability

Serial number and hardware/firmware revision per device.

Documentation

Enough information that we could order another twenty six months later without reverse-engineering our own prototype.
The immediate next engineering deliverable

We are now at the point where more high-level brainstorming has diminishing returns. The next artifact should be the Rev 1 electrical design specification.

That should define every actual circuit block:

ESP32-C6-MINI-1
exact GPIO assignment

SHT40
I²C pull-ups
decoupling

charger
exact IC
exact charge current
exact resistors/capacitors

regulator
exact IC
inductor
feedback
input/output capacitors

USB-C
connector
CC resistors
ESD

battery
connector
polarity
ADC circuit

buttons
LED

test pads
pogo geometry

From that document we can create the actual KiCad schematic, and from the schematic create Compact A and Isolated B PCB floorplans.

That is the next step I would take before spending any money on boards.

list ten funny geeky names for such a project. as github repo name

    therminal-velocity

    humidifier-than-thou

    espionage32

    room-temp-exception

    packet-of-air

    sht-happens

    ambiently

    wifi-and-chill

    degrees-of-freedom

    sensorly-unhinged

My favorites for an actual GitHub repo are sht-happens, packet-of-air, and room-temp-exception.

put all (except the naming) into a vision.md all ddetails and ideas. just this as download

from pathlib import Path

content = r"""# Vision: Battery-Powered ESP32 Environmental Sensor

## 1. Project Vision

Build a compact, battery-powered indoor environmental sensor that measures temperature and relative humidity, connects to Wi-Fi, and periodically reports measurements to a remote aggregation system.

The project is intended to begin as a small hardware run of approximately 20 units, with an earlier prototype batch used to compare two PCB and enclosure philosophies:

- **Approach A — Compact:** minimize total device size while still applying sensible thermal design.
- **Approach B — Thermally Isolated:** physically separate the temperature/humidity sensor from the heat-generating electronics to maximize measurement quality and repeatability.

The core electrical design, firmware, backend protocol, battery concept, manufacturing approach, and test infrastructure should remain common between both variants. Only the physical PCB geometry, thermal isolation strategy, and enclosure architecture should differ.

The project should be designed so that it can begin as an internal prototype but can later evolve into a repeatable small-series product suitable for deployment in Germany/EU.

---

# 2. Core Design Philosophy

## 2.1 One electrical platform, two physical implementations

Do not create two unrelated products.

Both prototype variants should share:

- the same ESP32 family and module;
- the same temperature/humidity sensor;
- the same power architecture;
- the same charger;
- the same battery connector;
- the same firmware;
- the same test interface;
- the same telemetry format;
- the same provisioning flow;
- the same backend integration.

This makes the A/B prototype comparison meaningful.

The main experiment is:

> How much measurement quality is gained by spending additional PCB area and enclosure volume on thermal isolation?

---

## 2.2 Measurement quality before cosmetic compactness

The temperature/humidity sensor is the purpose of the device.

The design should therefore avoid sacrificing measurement quality purely to save a few millimeters unless testing demonstrates that the compact design remains within the required system accuracy.

The finished product should not merely contain an accurate sensor IC. It should behave like an accurate environmental sensing system.

---

## 2.3 Measure first, transmit afterward

The ESP32 radio and power electronics are heat sources.

Normal measurement sequencing should therefore be:

1. wake from deep sleep;
2. measure temperature and humidity immediately;
3. store the result locally;
4. only then enable Wi-Fi;
5. transmit stored data if an upload is due;
6. disable Wi-Fi;
7. return to deep sleep.

This reduces both self-heating error and power consumption.

---

## 2.4 Measure often, transmit less often

Environmental sensing is inexpensive in energy terms.

Wi-Fi scanning, association, TLS setup, and data transfer are comparatively expensive.

A recommended initial policy is:

- measure every 5 minutes;
- store measurements locally;
- connect and upload every 15 minutes.

Example:

```text
00:00 measure, store
00:05 measure, store
00:10 measure, store
00:15 measure, store + Wi-Fi upload

The actual intervals should remain configurable.
3. Initial Product Requirements

The first requirements baseline is:
Requirement	Initial Target
Primary measurement	Temperature
Secondary measurement	Relative humidity
Temperature system target	approximately ±0.3 °C
Humidity system target	approximately ±3 %RH
Measurement interval	5 min configurable
Upload interval	15 min configurable
Main connectivity	2.4 GHz Wi-Fi
Provisioning	Bluetooth LE
Firmware update	OTA
Local buffering	Yes
Power	Rechargeable 1-cell LiPo
Initial battery range	500–1000 mAh
Charging	USB-C, 5 V
Target runtime	>3 months if practical
Deployment	Indoor residential / building
Prototype quantity	5 Compact + 5 Isolated
Initial small series	20 units
PCB technology	4-layer FR-4
Assembly	Primarily one-sided SMT
Initial enclosure	3D printed
Final product	Replaceable battery, serviceable enclosure

These are design targets and should be revised after prototype measurements.
4. System Architecture

                         ┌─────────────────────┐
                         │      SHT4x          │
                         │ Temperature + RH    │
                         └──────────┬──────────┘
                                    │ I²C
                                    │
┌──────────────┐             ┌──────▼───────────┐
│ LiPo battery │             │ ESP32-C6-MINI-1 │
│ 500-1000mAh │             │                  │
└──────┬───────┘             │ Wi-Fi            │
       │                     │ Bluetooth LE     │
       ▼                     │ Thread/Zigbee    │
┌──────────────┐             │                  │
│ Protection   │             └─────┬────────────┘
└──────┬───────┘                   │
       │                           │
       ├──────────────┐            │
       │              │            │
       ▼              ▼            │
┌────────────┐  ┌────────────┐     │
│ LiPo       │  │ Low-power  │─────┘
│ charger    │  │ regulator  │
└─────┬──────┘  └────────────┘
      │
      ▼
    USB-C

5. MCU and Radio
5.1 Preferred MCU module

Use an ESP32-C6-MINI-1 class module, not a bare ESP32-C6 RF design.

Advantages:

    integrated 2.4 GHz Wi-Fi;

    Bluetooth LE;

    IEEE 802.15.4 support for possible future Thread/Zigbee use;

    integrated crystal;

    integrated flash;

    integrated RF matching;

    integrated PCB antenna;

    published reference layout and land pattern;

    significantly reduced RF design risk;

    existing module-level regulatory test documentation.

Approximate module size:

    13.2 × 16.6 mm;

    approximately 2.4 mm tall.

Using the pre-certified module does not automatically certify the final device, but it substantially simplifies product development compared with designing the RF section from the bare chip.
5.2 ESP32 schematic requirements

Include:

    ESP32-C6-MINI-1;

    correct supply decoupling;

    bulk supply capacitance;

    EN/reset circuitry;

    boot/provisioning button;

    optional status LED;

    SHT4x I²C;

    battery-voltage input;

    charger-state input;

    programming and debug test pads;

    native USB Serial/JTAG option if useful.

Power design should allow at least approximately 500 mA of short-duration current capability because Wi-Fi transmission current can reach several hundred milliamps.
6. Environmental Sensor
6.1 Preferred family

Use the Sensirion SHT4x family, with SHT40 as the baseline candidate.

Reasons:

    extremely small footprint;

    factory calibration;

    digital I²C interface;

    low sleep and measurement power;

    good temperature accuracy;

    good humidity accuracy;

    good manufacturer design guidance;

    variants with protective filter options are available.

Approximate package size:

    1.5 × 1.5 × 0.5 mm.

A device-level accuracy target must account for mechanical and thermal effects, not only the IC data sheet.
6.2 Thermal measurement problem

Heat sources include:

    ESP32 during radio activity;

    power regulator;

    charger IC;

    charging battery;

    LED;

    high-current PCB copper;

    warm air trapped inside the enclosure.

Temperature error also propagates into relative-humidity error.

At high humidity, even a small temperature bias can create a substantial RH error.

Therefore the sensor layout and enclosure are central parts of the measurement system.
6.3 Sensor PCB rules

Around the environmental sensor:

    no large copper pours;

    no unnecessary ground plane;

    no power plane where avoidable;

    use narrow VDD trace;

    use narrow GND trace;

    use narrow SDA/SCL traces;

    minimize thermal vias;

    keep away from regulator;

    keep away from charger;

    keep away from ESP32;

    keep away from battery;

    keep away from LEDs;

    avoid high-current traces;

    provide direct access to ambient air.

7. Approach A — Compact Version
7.1 Objective

Produce the smallest practical integrated board while still applying reasonable thermal separation.

Initial PCB target:

    approximately 30 × 34 mm;

    exact dimensions to be determined during placement.

Potential enclosure target:

    approximately 40–45 mm square;

    roughly 13–18 mm thick depending on battery;

    final size depends strongly on battery and antenna clearance.

7.2 Physical concept

 SENSOR END                                  RF END
 ┌───────────────────────────────────────────────┐
 │ vents                                         │
 │ SHT4x     low-power       charger   ESP32-C6 │→ antenna
 │   ●        regulator      / USB-C     MINI   │
 │                                               │
 └───────────────────────────────────────────────┘
                 LiPo behind central area

The sensor should be located at one extreme end of the PCB.

The ESP32 antenna should be located at the opposite end.

The regulator and charger should remain as far from the sensor as practical.
7.3 Compact thermal strategy

Even though all electronics live on one board:

    put the SHT4x at the board edge;

    remove unnecessary copper around the sensor;

    minimize inner-plane copper near the sensor if feasible;

    route only thin sensor connections;

    take the environmental measurement before enabling Wi-Fi;

    reduce charger current;

    identify charging state in firmware;

    mark or suppress measurements captured during severe charging-induced heating if necessary;

    place enclosure vents directly around the sensor.

7.4 Compact enclosure concept

┌────────────────────────────┐
│ :::::                   RF │
│ :air: SHT4x              → │
│ :::::                      │
│                            │
│        PCB                 │
│                            │
│      battery               │
│                      USB-C │
└────────────────────────────┘

The ventilation opening must be placed deliberately next to the sensor.

Do not use arbitrary decorative ventilation elsewhere in the enclosure.
7.5 Expected characteristics
Characteristic	Compact Version
PCB area	Smallest
Mechanical complexity	Low
Assembly complexity	Low
Cost	Lowest
Enclosure size	Smallest
Temperature accuracy	Potentially good under duty-cycled operation
Humidity accuracy	Sensitive to thermal bias
Charging influence	Main weakness
Sensitivity to enclosure airflow	High
Robustness	High
Best use	Small low-cost room sensor

The compact version should be considered acceptable only if measurements demonstrate that it meets the selected system accuracy targets.
8. Approach B — Thermally Isolated Version
8.1 Objective

Use modest additional board area to materially improve thermal isolation and ambient-air coupling.

Initial target:

    approximately 28–32 mm wide;

    approximately 45–50 mm long.

8.2 Physical concept

 SENSOR ISLAND                MAIN ELECTRONICS
                                   BOARD

 ┌───────────┐              ┌─────────────────────┐
 │           │              │                     │
 │   SHT4x   │──────────────│ regulator           │
 │     ●     │ narrow neck  │ charger             │
 │           │──────────────│ battery connector   │
 └───────────┘              │ ESP32-C6      RF → │
   ↑       ↑                └─────────────────────┘
   │       │
 routed PCB slots

The sensor sits on a narrow PCB tongue connected to the main PCB through a thermally resistive neck.
8.3 Sensor-island construction

Use routed slots around the environmental sensor.

Concept:

      ┌───────────────┐
      │     SHT4x     │
      │       ●       │
──────┘               └──────
──────┐               ┌──────
      └───────────────┘

Only the necessary electrical conductors should cross the narrow bridge:

    VDD;

    GND;

    SDA;

    SCL.

All should be narrow.

Critically:

    Remove internal-layer copper across the thermal neck.

Otherwise the visible FR-4 slots are undermined by hidden copper planes conducting heat directly into the sensing area.
8.4 Two-chamber enclosure

Version B should have physically separated air volumes.

┌─────────────────────────────────────────────┐
│                                             │
│ AMBIENT SENSOR          ELECTRONICS         │
│ CHAMBER                 CHAMBER             │
│                                             │
│ ::::::::::::     │                          │
│ :: SHT4x ::      │   ESP32                  │
│ ::::::::::::     │   charger                │
│                  │   regulator              │
│                  │   battery                │
│                  │                          │
└─────────────────────────────────────────────┘
                   ↑
             internal wall

The PCB tongue passes through the internal partition.

The sensor chamber should:

    have direct ambient-air access;

    have low dead volume;

    isolate the sensor from the electronics chamber;

    avoid warm internal airflow;

    support rapid response to environmental changes.

8.5 Expected characteristics
Characteristic	Thermally Isolated Version
PCB area	Slightly larger
Mechanical complexity	Moderate
Assembly complexity	Almost identical to Compact
Cost	Slightly higher
Enclosure	Longer / more structured
Temperature accuracy	Better
Humidity accuracy	Better
Charging influence	Lower
Unit-to-unit repeatability	Better
Response time	Potentially better
Main mechanical concern	PCB tongue strength
Best use	Measurement-focused room/environment sensor

The working expectation is that Version B will become the final design, but the prototype program should prove this rather than assume it.
9. Possible Future Approach C — Separate Sensor Board or Flex

A thermally superior but mechanically more complicated architecture would be:

main PCB
   │
thin FPC / cable
   │
tiny SHT4x PCB

Benefits:

    excellent thermal isolation;

    excellent freedom in sensor placement.

Disadvantages:

    second PCB;

    flex cable or connector;

    additional BOM;

    more assembly;

    more mechanical retention;

    more failure modes;

    greater manufacturing cost;

    more complex enclosure.

Do not start with this unless the rigid isolated sensor tongue proves insufficient.
10. Power Architecture
10.1 Battery

Baseline:

    rechargeable 1-cell LiPo;

    nominal 3.7 V;

    maximum charge approximately 4.2 V;

    approximately 500–1000 mAh initially.

The selected battery should ideally include suitable protection against:

    overcharge;

    over-discharge;

    short circuit;

    excessive current.

Battery capacity should be considered a mechanical parameter as well as an electrical one.
10.2 Charger

Required features:

    USB 5 V input;

    single-cell LiPo charging;

    programmable charge current;

    low standby current;

    charger-state output;

    battery-temperature support/NTC preferred;

    power-path functionality preferred.

A BQ24074-class charger is a useful reference design, but the exact charger must be selected during schematic engineering.

Initial charging current should likely be only:

    approximately 100–250 mA;

subject to the battery manufacturer's charge specification.

High charging current is undesirable because a linear charger can create significant local heat.

Illustrative thermal estimate:

USB input = 5.0 V
Battery = 3.7 V
Charge current = 250 mA

Power dissipation ≈ (5.0 - 3.7) × 0.25
                  ≈ 0.325 W

Several hundred milliwatts inside a small temperature sensor can strongly bias measurements.
10.3 Regulator

The regulator should provide:

    very low quiescent current;

    high efficiency at microamp loads;

    adequate transient response;

    at least approximately 500–750 mA current capability;

    good RF-friendly behavior.

A TPS62840-class buck regulator is a useful candidate.

The design should experimentally compare approximately:

    3.0 V system rail;

    3.3 V system rail.

A 3.0 V rail may allow the system to use more of the LiPo discharge curve before a buck converter reaches dropout, but prototype validation is required.
10.4 Battery-voltage measurement

Do not use a low-resistance divider that permanently drains the battery.

Preferred options:

    MOSFET-switched resistor divider;

    very high-value divider with suitable filtering;

    dedicated fuel-gauge solution.

A simple switched divider is probably sufficient for Rev 1.

Sequence:

enable divider
wait briefly
measure ADC
disable divider

11. USB-C

USB-C should primarily serve as:

    5 V input;

    charging interface.

Required design elements:

    USB-C receptacle;

    CC1 resistor;

    CC2 resistor;

    VBUS;

    ground;

    ESD protection;

    charger input;

    suitable mechanical anchoring.

Optional:

    route USB D+/D− to native ESP32 USB Serial/JTAG.

Production programming can instead use pogo pins to simplify the PCB and enclosure.
12. Deep-Sleep Firmware Philosophy

Normal operation:

DEEP SLEEP
    ↓
RTC wake
    ↓
Read SHT4x
    ↓
Measure battery
    ↓
Store record
    ↓
Upload due?
   / \
 no   yes
 │     ↓
 │   Enable Wi-Fi
 │     ↓
 │   Associate
 │     ↓
 │   TLS
 │     ↓
 │   Upload
 │     ↓
 │   Disable Wi-Fi
 │
 └───────────────→ DEEP SLEEP

Never keep Wi-Fi continuously connected unless a future mains-powered version specifically requires it.
13. Battery-Life Planning

Actual battery life depends heavily on:

    Wi-Fi signal strength;

    access-point behavior;

    scan time;

    association time;

    DNS;

    TLS handshake;

    retries;

    upload duration;

    regulator efficiency;

    real deep-sleep current;

    battery self-discharge;

    measurement/upload interval.

Planning assumptions for a 1000 mAh cell suggest roughly:
Behavior	Rough Planning Range
Continuously connected Wi-Fi	days
Upload every 5 min	~1–2 months
Upload every 10 min	~2–4 months
Upload every 15 min	~3–5 months
Measure every 5 min, upload every 15–30 min	potentially ~4–8 months
Weak Wi-Fi / frequent retries	substantially worse

These are planning ranges, not specifications.

The prototype must measure the real current waveform and derive battery life from measured energy consumption.
14. Wi-Fi Failure Policy

Never retry forever.

Bad:

while (!wifi_connected) {
    retry_forever();
}

Preferred:

attempt connection for a bounded interval

if successful:
    upload queued measurements
else:
    retain local data
    sleep
    retry next cycle

A router outage should not drain the device battery.
15. Local Storage

Store a rolling queue of measurements so the device survives temporary network outages.

Initial capacity:

    approximately 100–500 records.

When offline:

measurement
   ↓
local queue
   ↓
sleep

When online again:

new measurement
+
queued measurements
   ↓
upload

Care should be taken to avoid unnecessary flash wear.
16. Backend Architecture

A practical first deployment:

SHT4x
   │ I²C
   ▼
ESP32-C6
   │
   │ Wi-Fi + TLS
   ▼
MQTT broker
   │
   ├── Home Assistant
   ├── InfluxDB
   └── Grafana

For a home or small-building deployment:

    Mosquitto MQTT;

    Home Assistant;

    optional InfluxDB;

    optional Grafana.

Avoid building unnecessary custom cloud infrastructure for the first 20 devices.
17. Provisioning

Recommended flow:

    device is powered for the first time;

    ESP32 exposes BLE commissioning service;

    phone or provisioning tool discovers the sensor;

    Wi-Fi SSID/password are transferred securely;

    device tests Wi-Fi;

    credentials are stored;

    BLE provisioning becomes inactive during normal operation.

A physical button should support:

    factory reset;

    reprovisioning mode.

18. Telemetry Format

Example payload:

{
  "id": "ENV-0017",
  "ts": 1787666700,
  "temperature_c": 22.84,
  "humidity_rh": 46.1,
  "battery_v": 3.91,
  "battery_percent": 74,
  "rssi_dbm": -54,
  "charging": false,
  "firmware": "0.2.1"
}

Recommended fields:

    device ID;

    timestamp;

    temperature;

    humidity;

    battery voltage;

    optional battery percentage;

    RSSI;

    charging state;

    firmware version;

    optional diagnostic flags.

19. MQTT Topic Structure

Example:

home/sensors/ENV-0017/telemetry
home/sensors/ENV-0017/status

Potential future topics:

home/sensors/ENV-0017/config
home/sensors/ENV-0017/command
home/sensors/ENV-0017/diagnostics

20. Firmware Architecture

Use ESP-IDF for production firmware.

Suggested structure:

/app
/sensor
/power
/storage
/wifi
/provisioning
/mqtt
/ota
/security
/diagnostics

Firmware capabilities:

    RTC wake-up;

    SHT4x driver;

    battery ADC;

    charger-state detection;

    local data queue;

    Wi-Fi provisioning;

    bounded Wi-Fi reconnect strategy;

    TLS;

    MQTT or HTTPS;

    watchdog;

    OTA;

    configuration;

    firmware versioning;

    factory-test mode;

    secure credential storage.

21. Firmware Security

Design for:

    TLS;

    device-specific identity;

    unique credentials;

    secure boot;

    signed firmware;

    OTA verification;

    rollback;

    flash encryption where appropriate;

    protected stored Wi-Fi credentials;

    factory reset;

    no shared universal production password.

Every device should receive its own identity and credentials.
22. Device Identity

Assign a serial number to every device.

Example:

ENV-0001
ENV-0002
...
ENV-0020

Use a QR label if helpful.

Store or associate:

    serial number;

    ESP MAC;

    hardware revision;

    firmware revision;

    manufacturing date;

    test result;

    device credential identifier.

23. PCB Layer Stack

Use a 4-layer board.

Baseline:

L1  Components + signals
L2  Solid ground reference
L3  Power + slow signals / ground
L4  Limited signals / ground

Benefits:

    better RF return paths;

    cleaner power distribution;

    better EMC behavior;

    simpler routing;

    compact layout.

Exception:

For the Version B sensor island, remove inner-layer copper where necessary to reduce thermal conduction.
24. PCB Manufacturing Philosophy

Rev 1 should avoid unnecessary manufacturing complexity.

Prefer:

    4-layer FR-4;

    standard board thickness;

    standard surface finish;

    0402 as normal minimum;

    0603 where space allows and debug convenience matters;

    no 0201 unless necessary;

    no BGA;

    no blind/buried vias;

    no rigid-flex;

    normal routed slots;

    primarily one-sided assembly;

    ESP32 RF module instead of bare RF IC.

25. One-Sided Assembly

Try to place essentially all SMD parts on one side.

Benefits:

    lower assembly cost;

    simpler manufacturing;

    easier inspection;

    easier rework;

    easier pogo fixture design;

    easier enclosure construction.

The battery can occupy the opposite side of the PCB, subject to antenna and sensor constraints.
26. Component Placement Priority

PCB placement should occur in this order:

    ESP32 antenna;

    environmental sensor;

    USB-C connector;

    battery connector;

    charger;

    regulator and inductor;

    bulk capacitors;

    ESP32 module body;

    buttons;

    debug/test pads;

    remaining passives.

Reason:

The antenna, sensor, and external connectors are mechanically constrained. Small passive components are not.
27. Antenna Rules

The ESP32 module antenna should be placed at a PCB edge and preferably extend beyond the host PCB edge if permitted by the module design rules.

Maintain the vendor's antenna keep-out region.

Avoid putting near the antenna:

    LiPo pouch;

    battery wiring;

    USB connector;

    metal screws;

    large copper planes;

    shields;

    metal enclosure parts;

    mounting plates.

The enclosure should provide free space around the antenna.

RF performance must be tested in the final enclosure.
28. Battery Placement

Battery placement must balance:

    RF;

    thermal behavior;

    enclosure thickness.

Likely geometry:

                 sensor
                    ↓
PCB ───────────────────────────
        battery
    ┌─────────────┐
    │             │
    └─────────────┘

                antenna area
                has no battery

Do not place the LiPo directly behind the antenna.

Do not place it directly underneath or against the environmental sensor.
29. Schematic Organization

Suggested KiCad hierarchy:

00_System
01_ESP32
02_Sensor
03_Power_Regulator
04_Battery_Charger
05_USB
06_Buttons_LED
07_Programming_Test

This improves reviewability and maintenance.
30. Component Library Verification

Before layout, verify every critical symbol, footprint, and 3D model.

Especially:

    ESP32 module;

    SHT4x;

    charger IC;

    regulator;

    inductor;

    USB-C connector;

    battery connector.

For each:

schematic symbol
↓
pin numbering
↓
footprint
↓
pad dimensions
↓
pin 1
↓
rotation
↓
3D model

A footprint error can ruin an otherwise perfect PCB batch.
31. PCB Design Rules

Create explicit KiCad net classes and constraints.
General

Define:

    track width;

    clearance;

    via diameter;

    via drill;

    annular ring;

    copper-to-edge;

    solder-mask clearance.

Power

Create dedicated classes for:

    USB 5 V;

    VBAT;

    regulated system rail;

    low-current signals.

Sensor

Create rules to prevent:

    copper planes through thermal neck;

    excessive trace width;

    local heat-source placement.

Antenna

Create a hard RF keep-out area.

Do not rely on visual memory.
32. Thermal PCB Rules

For both versions:

    no heat sources near the sensor;

    reduce copper near the sensor;

    avoid wide ground connections;

    avoid regulator copper near sensor;

    avoid charger heat path;

    keep battery away from sensor.

For Version B specifically:

    two routed slots;

    narrow FR-4 bridge;

    thin VDD/GND/SDA/SCL;

    remove L2/L3 copper across the bridge;

    no thermal vias;

    no pour fill across the isolated region.

33. Mechanical CAD

Mechanical design should begin as soon as preliminary PCB placement exists.

Workflow:

    create initial PCB placement;

    export STEP;

    create enclosure around real board;

    add battery volume;

    add USB opening;

    add sensor vent;

    add antenna exclusion zone;

    add mounting points;

    feed mechanical changes back into PCB;

    repeat.

PCB and enclosure should evolve together.
34. Enclosure Requirements

The enclosure should provide:

    serviceable lid;

    screws rather than glue;

    accessible battery connector;

    replaceable battery;

    USB-C access;

    provisioning/reset access;

    controlled sensor airflow;

    antenna clearance;

    mechanical protection;

    no stress on sensor tongue;

    no warm airflow directly from charger to sensor.

35. Sensor Vent Design

Preferred airflow geometry:

outside air
    ↓
large vent
    ↓
small sensor chamber
    ↓
SHT4x

Avoid:

outside air
    ↓
tiny hole
    ↓
large internal cavity
    ↓
sensor

Large dead volume causes slow response and allows electronics heat to contaminate readings.
36. Humidity Sensor Contamination

Humidity sensors are sensitive to contamination.

Manufacturing and enclosure processes must consider:

    flux;

    board cleaning;

    solvents;

    conformal coatings;

    adhesives;

    silicone;

    uncured plastics;

    resin prints;

    off-gassing materials;

    packaging;

    storage.

If conformal coating is used, the sensing element must be protected appropriately.

A filtered SHT4x variant may be preferable for the final product.
37. Test and Programming Pads

Provide accessible pogo pads for at least:

GND
VBUS
VBAT
system rail
ESP EN / RESET
BOOT
UART TX
UART RX
USB D+
USB D-
SDA
SCL
charger status

Not every signal must be exposed if USB-based flashing becomes the preferred production interface, but debugging access should exist on Rev 1.
38. Production Pogo Fixture

Build a small fixture for the first small-series production.

Concept:

            PCB
       ┌───────────┐
       │ ● ● ● ● ● │
       └─┬─┬─┬─┬─┬─┘
         │ │ │ │ │
      pogo pins
         │ │ │ │ │
       fixture PCB

Fixture workflow:

    power PCB;

    flash firmware;

    run self-test;

    verify sensor;

    verify power rails;

    verify charger;

    verify Wi-Fi;

    read MAC;

    assign serial number;

    provision device identity;

    store test result.

39. Factory Test Firmware

Provide an explicit hardware-test mode.

Example output:

Device serial: ENV-0017
ESP MAC: xx:xx:xx:xx:xx:xx
Hardware: B2
Firmware: 0.2.1

3V rail: PASS
Battery ADC: PASS
SHT4x: PASS
Temperature: 23.42 C
Humidity: 45.7 %
Wi-Fi radio: PASS
RSSI: -46 dBm
Flash: PASS
Charging state: PASS

FINAL TEST: PASS

This enables repeatable production instead of manual subjective inspection.
40. Manufacturing Deliverables

A complete hardware product requires more than a Gerber ZIP.
Requirements

    product requirements;

    target dimensions;

    target accuracy;

    target battery life;

    environmental assumptions;

    prototype quantity.

Electrical

    KiCad schematic;

    schematic PDF;

    component library;

    exact BOM;

    approved alternates;

    net classes;

    power architecture.

PCB

    native KiCad PCB;

    4-layer stack specification;

    board outline;

    antenna keep-out;

    thermal keep-out;

    routed slot geometry;

    test pads.

Fabrication

    Gerber files;

    drill files;

    board outline;

    fabrication drawing;

    stack-up notes;

    slot/routing notes.

Assembly

    BOM CSV;

    CPL / pick-and-place;

    top assembly drawing;

    bottom assembly drawing if needed;

    polarity/orientation notes;

    assembly instructions.

Mechanical

    PCB STEP;

    enclosure STEP;

    STL/3MF for prototypes;

    battery envelope;

    screw specification;

    label geometry.

Firmware

    source code;

    build configuration;

    version information;

    factory image;

    production image;

    OTA process.

Production

    pogo fixture;

    flashing script;

    provisioning process;

    test script;

    serial number allocation;

    pass/fail criteria.

Documentation

    battery replacement;

    product assembly;

    charging instructions;

    provisioning;

    reset procedure;

    troubleshooting.

Compliance if commercialized

    BOM;

    schematic;

    block diagram;

    PCB layout;

    risk assessment;

    test evidence;

    product documentation;

    Declaration of Conformity;

    supporting CE technical file.

41. Production Repository Structure

Suggested repository:

environment-sensor/

  hardware/
    schematic/
    pcb/
    libraries/

    outputs/
      rev-a/
        gerber/
        drill/
        bom/
        cpl/
        assembly/
        step/

      rev-b/
        gerber/
        drill/
        bom/
        cpl/
        assembly/
        step/

  mechanical/
    compact-a/
    isolated-b/

  firmware/

  production/
    flashing/
    fixture/
    testing/

  compliance/

  documentation/

  measurements/
    thermal/
    battery/
    rf/

42. Revision Naming

Use explicit hardware revisions.

Example:

HW-A1
Compact prototype

HW-B1
Thermally isolated prototype

HW-B2
Selected architecture, corrected revision

HW-B3
20-unit production revision

Print the revision on the PCB silkscreen.

Example:

ENV SENSOR
HW B1
2026

Avoid ambiguous filenames such as:

final.zip
final2.zip
final-final.zip

43. Schematic Review Checklist

Before layout:

    verify every supply voltage;

    verify every IC absolute maximum;

    verify ESP32 strapping pins;

    verify EN/reset circuitry;

    verify required pull-ups;

    verify I²C pull-ups;

    verify SHT4x supply/decoupling;

    verify charger current programming;

    verify battery polarity;

    verify USB-C CC configuration;

    verify ADC voltage range;

    verify GPIO startup behavior;

    verify unused pins;

    verify ESD;

    verify sleep-current leakage paths;

    verify programming interface;

    verify test access.

Run ERC.

There should be no unexplained ERC errors.
44. PCB Layout Review Checklist
RF

    antenna at board edge;

    correct module footprint;

    correct keep-out;

    no battery near antenna;

    no copper where prohibited;

    enclosure leaves RF clearance.

Thermal

    SHT4x physically separated;

    no heat source beside sensor;

    copper minimized near sensor;

    Version B neck isolated on every layer;

    charger sufficiently distant.

Power

    short switching-current loops;

    decoupling placed at pins;

    regulator layout follows vendor guidance;

    power traces sized adequately;

    stable ground return.

USB

    correct CC resistors;

    ESD placement;

    connector reinforcement;

    suitable VBUS routing.

Manufacturing

    components not too close to board edges;

    polarity indicators;

    pin 1 indicators;

    sensible component orientation;

    routed slots correctly defined;

    assembly access.

Mechanical

    screw locations clear copper;

    enclosure fits;

    battery fits;

    battery connector accessible;

    USB aligned;

    sensor aligned with vent;

    antenna not obstructed.

Run DRC.

No unexplained DRC violations should remain.
45. PCB Fabrication Outputs

Generate:

Top copper
Inner copper 1
Inner copper 2
Bottom copper

Top solder mask
Bottom solder mask

Top silkscreen
Bottom silkscreen if needed

Board outline
Drill files

Also provide fabrication notes covering:

    layer count;

    thickness;

    copper weight;

    surface finish;

    board dimensions;

    slot geometry;

    special keep-outs where required.

46. PCBA Outputs

BOM fields:

Reference
Value
Package
Manufacturer
Manufacturer Part Number
Supplier Part Number
Quantity
Alternate

CPL / pick-and-place:

Reference
X
Y
Rotation
Side

Also provide:

    assembly drawings;

    polarity notes;

    do-not-fit options;

    special handling notes for humidity sensor.

47. Prototype Manufacturing Strategy

Do not order the final 20 immediately.

First prototype:

    5 × Compact A;

    5 × Thermally Isolated B.

Prefer:

    same MCU module;

    same sensor lot if practical;

    same battery;

    same firmware;

    same charger;

    same regulator;

    production at approximately the same time.

This allows meaningful comparison.
48. Vendor Strategy
JLCPCB

Likely strongest cost-oriented candidate for:

    low-volume 4-layer PCB;

    SMT assembly;

    approximately 5–20 units;

    common 0402 components;

    single-sided assembly.

Design the PCB so it fits standard/economic PCBA capability.
AISLER

Strong alternative when:

    EU-based iteration matters;

    convenient KiCad workflow matters;

    local/European production is preferred;

    very small prototype runs are needed.

PCBWay

Useful comparison vendor, especially if:

    more unusual assembly;

    manual operations;

    non-standard parts;

    custom production services;

    box-build complexity.

Final vendor should be selected from actual quotes once BOM and PCB data exist.
49. Battery Sourcing Strategy

Prefer initially:

    PCBA shipped without batteries;

    protected LiPo batteries sourced separately in Germany/EU.

Benefits:

    simpler shipping;

    easier lithium transport handling;

    easier battery replacement;

    easier sourcing of documentation;

    simpler quality control.

The battery connector and polarity must be explicitly defined and documented.
50. First Board Bring-Up

Do not power every board immediately.

For the first board:

1. visual inspection
2. check resistance VBAT → GND
3. check resistance system rail → GND
4. configure current-limited bench supply
5. apply power
6. verify regulator output
7. verify ESP32 reset state
8. flash minimum firmware
9. verify serial/debug communication
10. detect SHT4x
11. read temperature/humidity
12. test Wi-Fi
13. test charging
14. test battery measurement

Only after the first board behaves correctly should the remaining units be powered.
51. Incoming Inspection

Inspect all prototype PCBAs under magnification for:

    wrong component orientation;

    ESP32 module alignment;

    SHT4x alignment;

    diode polarity;

    IC pin-1 orientation;

    missing parts;

    solder bridges;

    USB mechanical joints;

    charger soldering;

    regulator soldering;

    connector polarity.

52. Power Measurement

Capture the real current waveform:

wake
 ↓
sensor measurement
 ↓
CPU work
 ↓
Wi-Fi scan
 ↓
association
 ↓
TLS handshake
 ↓
upload
 ↓
radio shutdown
 ↓
deep sleep

Measure:

    wake energy;

    scan energy;

    association time;

    TLS time;

    upload energy;

    deep-sleep current;

    charger-off leakage;

    battery-divider leakage;

    regulator quiescent current.

Use these values to calculate battery life rather than relying on typical current values alone.
53. Thermal A/B Test Plan

Use:

    5 Compact A units;

    5 Thermally Isolated B units;

    one trusted reference sensor.

Place them in the same environment.
Test 1 — Deep-Sleep Equilibrium

Leave devices mostly asleep for 30–60 minutes.

Measure baseline offset.
Test 2 — Heavy Wi-Fi Activity

Force upload every minute.

Measure self-heating.
Test 3 — Charging

Charge battery while logging.

Measure charger-induced temperature and humidity error.
Test 4 — Normal Duty Cycle

Return to normal measurement/upload policy.

Measure realistic operating error.
Test 5 — Temperature Step

Move devices between environments or use a controlled test setup.

Measure:

    response speed;

    peak deviation;

    settling time.

Test 6 — Humidity Step

Change humidity and compare:

    response speed;

    unit-to-unit consistency;

    offset.

54. Thermal Data to Record

For every record:

timestamp
reference temperature
reference humidity
device temperature
device humidity
battery voltage
charging state
RSSI
time since wake
time since Wi-Fi transmit
hardware revision
device serial

Calculate:

    mean temperature offset;

    mean humidity offset;

    standard deviation;

    unit-to-unit spread;

    warm-up transient;

    post-transmit recovery;

    charging bias;

    environmental step response;

    settling time.

55. A/B Decision Gate

The Compact version is selected only if it meets the defined performance target under:

    equilibrium;

    normal Wi-Fi duty cycle;

    charging;

    environmental transitions.

Otherwise the Thermally Isolated version becomes the baseline.

The expectation is that the isolated version will likely win, because the additional PCB area costs very little compared with the value of improved measurement integrity.
56. RF Test Plan

Test both designs:

    next to access point;

    one room away;

    through several walls;

    worst expected installation position.

Measure:

    RSSI;

    association time;

    DNS time;

    TLS setup time;

    upload duration;

    retry count;

    failed uploads;

    total energy per upload.

Perform tests with the final or near-final enclosure installed.
57. Battery Test Plan

Test:
Runtime

Accelerated cycling and realistic duty cycles.
Charging

Low battery to full charge.
Thermal influence

Observe environmental-sensor error during charging.
Low battery

Verify clean shutdown behavior.
Brownout

Verify no credential or flash corruption.
Battery removal

Verify clean restart and reprovisioning behavior if needed.
Self-discharge / shelf state

Verify acceptable current when sleeping for long periods.
58. Firmware Failure Testing

Simulate:

    Wi-Fi unavailable;

    password changed;

    router reboot;

    DHCP failure;

    DNS failure;

    MQTT broker offline;

    TLS failure;

    poor RSSI;

    repeated packet loss;

    device reboot during upload;

    full local queue;

    sudden power loss;

    OTA interruption;

    invalid update;

    low battery during OTA.

The device should fail safely and return to a low-power state.
59. OTA

OTA should be implemented before widespread deployment.

Requirements:

    authenticated update source;

    signed firmware;

    version check;

    integrity verification;

    rollback if boot fails;

    no permanent bricking from interrupted update;

    safe behavior on low battery.

Physically retrieving 20 distributed sensors for every firmware fix should be avoided.
60. Revision 2

After A/B testing:

    select the architecture;

    fix all electrical issues;

    fix all mechanical issues;

    optimize sensor-neck geometry if using Version B;

    adjust antenna clearance;

    adjust charger current;

    adjust power components;

    improve programming fixture;

    refine battery connector;

    refine enclosure.

If changes are significant:

    manufacture 3–5 Rev 2 verification units.

If changes are truly minor:

    consider moving directly to the 20-unit batch.

A small verification batch is preferred if budget permits.
61. Final 20-Unit Production Package

Freeze:

    hardware revision;

    schematic;

    Gerber ZIP;

    drill files;

    BOM;

    CPL;

    fabrication drawing;

    assembly drawing;

    STEP model;

    firmware version;

    production binary;

    provisioning procedure;

    serial-number range;

    labels;

    test specification.

The package should be sufficient to reorder another 20 units months later without reconstructing the project from memory.
62. Final Production Flow

For each board:

    incoming visual inspection;

    pogo fixture contact;

    flash bootloader/firmware;

    program unique identity;

    run electrical self-test;

    verify SHT4x;

    verify Wi-Fi;

    verify battery ADC;

    verify charging;

    store test record;

    attach serial/QR label;

    install battery;

    install enclosure;

    final functional test;

    package.

63. Definition of Done

The project is complete when the following are true.
Hardware

    20 functioning PCBs;

    correct hardware revision;

    repeatable assembly.

Measurement

    known temperature error;

    known humidity error;

    known response time;

    documented charging influence.

Power

    measured deep-sleep current;

    measured upload energy;

    measured or credibly modeled battery life.

Radio

    tested Wi-Fi range;

    bounded retry behavior;

    tested final enclosure.

Firmware

    commissioning works;

    telemetry works;

    offline buffering works;

    OTA works;

    failure handling works.

Mechanical

    enclosure repeatable;

    battery replaceable;

    USB accessible;

    sensor airflow deliberate;

    antenna unobstructed.

Manufacturing

    complete reproducible Gerber/BOM/CPL set;

    verified production fixture;

    documented test process.

Traceability

Each device has:

    serial;

    hardware revision;

    firmware revision;

    MAC;

    test record.

Documentation

Enough information exists to reproduce the product without reverse-engineering it.
64. Compliance and Germany/EU Considerations

The first engineering prototypes do not need to be treated exactly like a finished commercial product, but the architecture should avoid decisions that make future compliance unnecessarily difficult.

If the device is eventually sold or otherwise placed on the EU market, evaluate requirements including:

    Radio Equipment Directive;

    RF spectrum requirements;

    EMC;

    applicable electrical safety;

    RF exposure where applicable;

    CE technical documentation;

    Declaration of Conformity;

    RoHS;

    WEEE;

    battery obligations;

    cybersecurity obligations.

The use of an ESP32 module with existing radio test/certification documentation is helpful, but the final host device still requires its own conformity assessment.
65. Battery Replaceability

Design the product with a serviceable battery from the beginning.

Preferred:

remove screws
     ↓
remove cover
     ↓
disconnect battery
     ↓
replace battery

Avoid:

glued enclosure
+
glued LiPo
+
soldered battery leads

This is good engineering independently of regulation and also aligns with evolving EU battery-replaceability requirements.
66. Cybersecurity Direction

Because this is internet-connected radio equipment, design security in from the start.

Include:

    encrypted communications;

    secure provisioning;

    unique device credentials;

    signed OTA;

    secure boot;

    firmware update process;

    vulnerability-response capability;

    no shared factory password;

    documented reset/recovery.

Cybersecurity architecture should not be postponed until after hardware production.
67. Explicit Non-Goals for Rev 1

Do not introduce the following unless prototypes prove they are necessary:

    bare ESP32-C6 RF design;

    custom PCB antenna;

    rigid-flex PCB;

    separate sensor PCB;

    0201 everywhere;

    BGA components;

    blind/buried vias;

    two-sided assembly;

    permanently lit LEDs;

    continuous Wi-Fi;

    glued battery;

    battery under antenna;

    sensor next to charger;

    sensor above battery;

    no test pads;

    manual soldering of all 20 production units;

    ordering 20 before prototype validation.

68. Decisions That Can Be Locked Early

These are sufficiently mature to use as baseline assumptions:

    ESP32-C6-MINI-1 class module;

    Sensirion SHT4x family;

    Wi-Fi telemetry;

    BLE provisioning;

    1S rechargeable LiPo;

    USB-C charging;

    deep-sleep duty cycling;

    4-layer PCB;

    SMT assembly;

    3D-printed prototype enclosure;

    5 Compact + 5 Thermally Isolated prototypes;

    rigid-PCB thermal tongue for isolated version;

    production test pads;

    OTA support;

    unique device identity.

69. Decisions That Should Remain Open Until Schematic/Prototype Work

Do not prematurely lock:

    exact SHT4x variant;

    exact charger IC;

    exact regulator;

    exact inductor;

    3.0 V versus 3.3 V system rail;

    exact USB-C connector;

    exact battery connector;

    exact battery size/capacity;

    exact PCB dimensions;

    exact sensor-neck width;

    exact routed-slot geometry;

    exact vent geometry;

    exact charge current;

    exact sleep interval;

    exact upload interval;

    exact MQTT/backend implementation;

    exact enclosure dimensions.

70. End-to-End Project Plan
Phase	Work	Deliverable
0	Requirements	Product requirements v1
1	Component selection	Preliminary approved BOM
2	Architecture	Block diagram
3	Schematic	KiCad schematic
4	Review	Reviewed schematic
5	Libraries	Verified footprints/models
6	Mechanical floorplan	A/B board envelopes
7	PCB A	Compact layout
8	PCB B	Thermally isolated layout
9	Enclosures	A/B CAD
10	PCB review	ERC/DRC/DFM signoff
11	Production output	Gerber/BOM/CPL
12	Prototype order	5 A + 5 B
13	Firmware bring-up	Prototype firmware
14	Electrical test	Bring-up report
15	Power test	Battery model
16	Thermal test	A/B comparison
17	RF test	Coverage/energy data
18	Design selection	A or B decision
19	Rev 2	Corrected PCB/enclosure
20	Verification	Rev 2 test
21	Production freeze	Final package
22	Small-series build	20 PCBAs
23	Programming	IDs + firmware
24	Final test	20 test records
25	Enclosure	Final assembly
26	Deployment	Install and aggregate data
71. Rough Project Schedule

A realistic development schedule for serious part-time or focused project work:
Week 1

    finalize requirements;

    select major components;

    define architecture.

Week 2

    schematic;

    symbol/footprint verification;

    schematic review.

Week 3

    A/B PCB placement;

    routing;

    enclosure concept.

Week 4

    DRC;

    DFM;

    production package;

    order prototypes.

Weeks 5–6

While boards are fabricated and shipped:

    firmware;

    backend;

    test fixture;

    test scripts;

    enclosure prints.

Weeks 6–7

    board bring-up;

    power profiling;

    RF tests;

    thermal A/B testing.

Week 8

    Rev 2 design.

Weeks 9–10

    Rev 2 manufacture;

    verification.

Week 11

    freeze final design.

Weeks 12–13

    final 20-unit production;

    programming;

    testing;

    enclosure assembly.

Approximate total:

    roughly 8–13 weeks from clean-sheet design to a tested small series.

72. Preliminary Cost Philosophy

Exact pricing must come from real PCB/BOM files and vendor quotes.

Useful planning ranges:
5 Compact + 5 Isolated prototypes

Possible planning envelope:

    low-cost China PCBA: roughly €180–400 total;

    European prototype PCBA: roughly €350–900 total;

    batteries: roughly €50–100;

    printed cases: roughly €30–100;

    dev boards/test accessories: roughly €50–150.

Overall prototype program:

    roughly €300–600 on a cost-focused route;

    roughly €500–1,100 on a more EU-centric route.

Final 20 units

Possible planning envelope:

    low-cost turnkey PCBAs: roughly €250–550;

    European assembly: roughly €500–1,200;

    batteries: roughly €100–200;

    printed cases: roughly €60–200;

    screws/connectors/labels: roughly €30–100.

A rough cost-oriented finished-unit target could be on the order of:

    approximately €20–45 per unit;

before engineering time and formal compliance costs.

These are budget estimates only.
73. Main Engineering Risks
Thermal bias

Most important product-specific risk.

Mitigation:

    sensor placement;

    isolated PCB tongue;

    enclosure partition;

    measure-before-radio;

    reduced charge current;

    prototype characterization.

Battery life

Dominated by Wi-Fi behavior.

Mitigation:

    deep sleep;

    bounded retries;

    batched uploads;

    low-Iq regulator;

    measured power waveform.

RF range

Affected by battery, enclosure, metal, and antenna placement.

Mitigation:

    module antenna keep-out;

    mechanical clearance;

    final-enclosure RF testing.

Charger heat

Potentially larger thermal issue than radio activity.

Mitigation:

    slow charge;

    physical separation;

    charging-state awareness;

    isolated sensor chamber.

Humidity sensor contamination

Can create permanent RH offset.

Mitigation:

    safe assembly processes;

    controlled materials;

    protective sensor variant/filter;

    careful enclosure handling.

Production repeatability

Twenty hand-built devices can become inconsistent.

Mitigation:

    full PCBA;

    fixed BOM;

    fixture;

    test firmware;

    serial numbers;

    stored test records.

74. Immediate Next Engineering Deliverable

The next concrete artifact should be a Rev 1 Electrical Design Specification.

It should lock every circuit-level detail required to create the schematic.

Required sections:
ESP32

    exact ESP32-C6-MINI-1 part;

    pin assignment;

    EN/reset;

    boot button;

    debug interface;

    LED;

    provisioning GPIO.

SHT4x

    exact part variant;

    supply voltage;

    I²C address;

    pull-ups;

    decoupling;

    sensor filtering option.

Charger

    exact IC;

    charge-current resistor;

    NTC arrangement;

    input/output capacitors;

    power-path behavior;

    charger-state GPIO.

Regulator

    exact regulator;

    output voltage;

    inductor;

    input capacitor;

    output capacitors;

    enable behavior;

    estimated transient performance.

USB-C

    exact connector;

    CC resistors;

    ESD parts;

    VBUS path;

    optional D+/D−.

Battery

    exact connector;

    polarity;

    expected battery dimensions;

    protection assumptions;

    ADC measurement circuit.

Test

    pogo pad functions;

    dimensions;

    spacing;

    programming method;

    test-mode GPIO if required.

From that specification:

    create the actual KiCad schematic;

    conduct formal schematic review;

    create Compact A floorplan;

    create Thermally Isolated B floorplan;

    begin enclosure CAD;

    generate the first manufacturable 5+5 prototype package.

75. Project Success Criterion

The goal is not merely:

    a PCB that works.

The goal is a repeatable hardware platform that can be manufactured again, tested quantitatively, deployed confidently, and improved without losing design history.

The first prototype batch is an experiment.

The second revision is an engineering product.

The 20-unit run is the first controlled small series.
"""

path = Path("/mnt/data/vision.md")
path.write_text(content, encoding="utf-8")
print(f"Created {path} ({len(content):,} characters)")


