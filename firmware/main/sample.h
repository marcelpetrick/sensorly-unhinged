// SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <stdbool.h>
#include <stdint.h>

// No ESP-IDF dependency: the exact wire decoder is also exercised on the host.
uint8_t sensorly_crc8(const uint8_t *data, unsigned length);
bool sensorly_decode(const uint8_t frame[6], double *temperature_c, double *humidity_rh);

// One callback invocation performs a complete command/wait/read transaction.
// Zero means transport success; all other values are preserved for reporting.
typedef int (*sensorly_read_frame_fn)(void *context, uint8_t frame[6]);
int sensorly_acquire(sensorly_read_frame_fn read_frame, void *context,
                     int crc_error, double *temperature_c, double *humidity_rh);
