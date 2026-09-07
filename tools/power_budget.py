# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Battery-side charge budget. Inputs are scenarios until measured."""
import argparse
import math


def budget(capacity_mah, usable_fraction, days, sleep_ua, sample_uas,
           upload_uas, sample_minutes=5, upload_minutes=15):
    values = (capacity_mah, usable_fraction, days, sleep_ua, sample_uas,
              upload_uas, sample_minutes, upload_minutes)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("inputs must be finite")
    if min(capacity_mah, usable_fraction, days, sample_minutes, upload_minutes) <= 0:
        raise ValueError("capacity, fraction, duration and intervals must be positive")
    if usable_fraction > 1 or min(sleep_ua, sample_uas, upload_uas) < 0:
        raise ValueError("invalid fraction or negative charge/current")
    samples, uploads = 1440 / sample_minutes, 1440 / upload_minutes
    baseline = sleep_ua * 24 / 1000
    sample_daily = sample_uas * samples / 3_600_000
    upload_daily = upload_uas * uploads / 3_600_000
    daily = baseline + sample_daily + upload_daily
    allowance = capacity_mah * usable_fraction / days - baseline - sample_daily
    return dict(daily_mah=daily,
                runtime_days=capacity_mah * usable_fraction / daily if daily else math.inf,
                max_upload_uas=allowance * 3_600_000 / uploads,
                target_feasible=allowance >= 0 and daily * days < capacity_mah * usable_fraction)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name, value in (("capacity-mah", 500), ("usable-fraction", .8),
                        ("days", 90), ("sleep-ua", 25), ("sample-uas", 2000),
                        ("upload-uas", 160000), ("sample-minutes", 5),
                        ("upload-minutes", 15)):
        p.add_argument(f"--{name}", type=float, default=value)
    args = vars(p.parse_args())
    try:
        result = budget(**args)
    except ValueError as exc:
        p.error(str(exc))
    print("SCENARIO ONLY; replace every charge/capacity input with pack-side measurements")
    for name, value in result.items():
        print(f"{name}: {value}")


if __name__ == "__main__":
    main()
