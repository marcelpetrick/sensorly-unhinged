// SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "sample.h"
int main(void) {
    // SHT4x datasheet CRC example: 0xbeef -> 0x92.
    const uint8_t example[] = {0xbe, 0xef};
    assert(sensorly_crc8(example, 2) == 0x92);
    uint8_t frame[] = {0, 0, 0x81, 0xff, 0xff, 0xac};
    double t = 123, h = 456;
    assert(sensorly_decode(frame, &t, &h));
    assert(t == -45 && h == 100);
    for (unsigned byte = 0; byte < 6; ++byte) {
        for (unsigned bit = 0; bit < 8; ++bit) {
            frame[byte] ^= 1U << bit;
            t = 123; h = 456;
            assert(!sensorly_decode(frame, &t, &h));
            assert(t == 123 && h == 456); // failure never publishes a partial pair
            frame[byte] ^= 1U << bit;
        }
    }
    puts("SHT4x: known CRC, endpoints, 48 single-bit faults and atomic decode pass");
}
