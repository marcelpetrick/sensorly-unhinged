// SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
#include "journal_esp.h"
#include "esp_partition.h"

static bool rd(void *ctx,uint32_t at,void *out,size_t len) {
    return esp_partition_read(ctx,at,out,len)==ESP_OK;
}
static bool wr(void *ctx,uint32_t at,const void *data,size_t len) {
    return esp_partition_write(ctx,at,data,len)==ESP_OK;
}
static bool er(void *ctx,uint32_t at,size_t len) {
    return esp_partition_erase_range(ctx,at,len)==ESP_OK;
}
journal_result_t journal_esp_open(journal_t *j) {
    const esp_partition_t *p=esp_partition_find_first(ESP_PARTITION_TYPE_DATA,0x40,"journal");
    if(!p||p->size!=2*JOURNAL_BANK_SIZE) return JOURNAL_IO_ERROR;
    journal_io_t io={.ctx=(void *)p,.read=rd,.write=wr,.erase=er};
    return journal_open(j,io);
}
