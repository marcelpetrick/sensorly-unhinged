// SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "sample.h"

struct scripted_read {
    int calls;
    int status[2];
    uint8_t frames[2][6];
};

static int read_script(void *context, uint8_t frame[6]) {
    struct scripted_read *script = context;
    assert(script->calls < 2);
    int i = script->calls++;
    if (script->status[i] == 0) memcpy(frame, script->frames[i], 6);
    return script->status[i];
}

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
    struct scripted_read success = {.status = {0, 0},
        .frames = {{0, 0, 0x81, 0xff, 0xff, 0xac}}};
    t = 123; h = 456;
    assert(sensorly_acquire(read_script, &success, 99, &t, &h) == 0);
    assert(success.calls == 1 && t == -45 && h == 100);

    struct scripted_read retry = {.status = {17, 0},
        .frames = {{0}, {0, 0, 0x81, 0xff, 0xff, 0xac}}};
    t = 123; h = 456;
    assert(sensorly_acquire(read_script, &retry, 99, &t, &h) == 0);
    assert(retry.calls == 2 && t == -45 && h == 100);

    struct scripted_read crc_then_timeout = {.status = {0, 42},
        .frames = {{0, 0, 0, 0xff, 0xff, 0xac}}};
    t = 123; h = 456;
    assert(sensorly_acquire(read_script, &crc_then_timeout, 99, &t, &h) == 42);
    assert(crc_then_timeout.calls == 2 && t == 123 && h == 456);

    struct scripted_read bad_crc = {.status = {0, 0},
        .frames = {{0, 0, 0, 0xff, 0xff, 0xac}, {0, 0, 0, 0xff, 0xff, 0xac}}};
    assert(sensorly_acquire(read_script, &bad_crc, 99, &t, &h) == 99);
    assert(bad_crc.calls == 2 && t == 123 && h == 456);
    puts("SHT4x: known CRC, endpoints, 48 single-bit faults and atomic decode pass");
    puts("SHT4x: bounded retry, transport and CRC fault paths pass");
}
