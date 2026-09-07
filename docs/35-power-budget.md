# 35 — Battery-side power budget

`make power` runs an explicit scenario, not a runtime prediction. Inputs are
usable rated pack capacity, sleep current and integrated **battery-side** charge
per sample/upload. Event charge is additional to the continuous sleep baseline;
include wake, association, retries, TLS, flash writes and shutdown. Measuring at
the battery includes regulator/power-path loss. Do not mix rail-side and
battery-side charge without conversion.

For the default 5/15-minute schedule there are 288 samples and 96 uploads/day.
25 µA continuous sleep consumes 0.6 mAh/day. A hypothetical 500 mAh pack with
80% usable capacity permits 4.44 mAh/day for 90 days. The default illustrative
upload charge is 160,000 µA·s (80 mA for two seconds); with 2,000 µA·s per sample
the scenario exceeds that allowance. These are chosen scenarios, not datasheet
claims or measured performance. The exact cell has not been selected.

Run `python3 -m tools.power_budget --help` for measured-input overrides. A
negative max_upload_uas means sleep and sampling alone exceed the target.
Runtime must exceed the declared test duration, not merely equal it. Use the
actual calendar interval for a literal three-month claim; 90 days is a planning
approximation. Include aging, temperature, self-discharge and cutoff losses in
usable capacity. Owner: hardware/firmware maintainer; gate: E-04/E-05 closure
with current traces and repeated normal/outage runs, not this calculator.
