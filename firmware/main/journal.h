// SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define JOURNAL_BANK_SIZE 65536u
#define JOURNAL_ERASE_SIZE 4096u
#define JOURNAL_RECORD_SIZE 100u
#define JOURNAL_CAPACITY 500u

typedef struct {
    void *ctx;
    bool (*read)(void *, uint32_t, void *, size_t);
    bool (*write)(void *, uint32_t, const void *, size_t);
    bool (*erase)(void *, uint32_t, size_t);
} journal_io_t;

typedef struct {
    uint8_t mac[6];
    uint8_t firmware_sha256[32];
    uint64_t boot_id;
    uint64_t uptime_us;
    int32_t temperature_milli_c;
    uint32_t humidity_milli_rh;
    int32_t battery_mv;
    int16_t sensor_status;
    int16_t adc_status;
    uint16_t quality_flags;
    uint8_t reset_reason, wake_reason;
    bool usb_present, charging;
} journal_sample_t;

typedef enum {
    JOURNAL_OK, JOURNAL_OVERFLOW, JOURNAL_IO_ERROR, JOURNAL_CORRUPT,
    JOURNAL_ID_EXHAUSTED, JOURNAL_COUNTER_EXHAUSTED, JOURNAL_NOT_FOUND
} journal_result_t;

typedef struct {
    journal_io_t io;
    uint32_t bank, slots;
    uint64_t generation, highwater, overflow;
    uint16_t live;
} journal_t;

journal_result_t journal_open(journal_t *j, journal_io_t io);
journal_result_t journal_append(journal_t *j, const journal_sample_t *sample, uint64_t *id);
journal_result_t journal_ack(journal_t *j, uint64_t id);
// Returns the oldest live record and its stable ID. Repeated calls require ACK.
journal_result_t journal_oldest(journal_t *j, journal_sample_t *sample, uint64_t *id);
