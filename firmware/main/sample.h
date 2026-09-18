// SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <stdbool.h>
#include <stdint.h>

// No ESP-IDF dependency: the exact wire decoder is also exercised on the host.
uint8_t sensorly_crc8(const uint8_t *data, unsigned length);
bool sensorly_decode(const uint8_t frame[6], double *temperature_c, double *humidity_rh);
