// SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
#include "sample.h"

// Sensirion SHT4x datasheet, Data Processing and Checksum Calculation:
// CRC-8 polynomial 0x31, initial 0xff; equations use unsigned 16-bit words.
// https://sensirion.com/products/catalog/SHT45
uint8_t sensorly_crc8(const uint8_t *data, unsigned length) {
    uint8_t crc = 0xff;
    for (unsigned i = 0; i < length; ++i) {
        crc ^= data[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x31) : (uint8_t)(crc << 1);
    }
    return crc;
}

bool sensorly_decode(const uint8_t frame[6], double *temperature_c, double *humidity_rh) {
    if (sensorly_crc8(frame, 2) != frame[2] || sensorly_crc8(frame + 3, 2) != frame[5])
        return false;
    unsigned t = ((unsigned)frame[0] << 8) | frame[1];
    unsigned h = ((unsigned)frame[3] << 8) | frame[4];
    *temperature_c = -45.0 + 175.0 * t / 65535.0;
    double rh = -6.0 + 125.0 * h / 65535.0;
    *humidity_rh = rh < 0 ? 0 : rh > 100 ? 100 : rh;
    return true;
}

int sensorly_acquire(sensorly_read_frame_fn read_frame, void *context,
                     int crc_error, double *temperature_c, double *humidity_rh) {
    // One retry is a bring-up policy choice, not a measured reliability claim.
    int status = crc_error;
    for (unsigned attempt = 0; attempt < 2; ++attempt) {
        uint8_t frame[6];
        status = read_frame(context, frame);
        if (status == 0) {
            if (sensorly_decode(frame, temperature_c, humidity_rh)) return 0;
            status = crc_error;
        }
    }
    return status;
}
