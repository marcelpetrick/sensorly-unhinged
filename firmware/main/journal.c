// SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
#include "journal.h"
#include <limits.h>
#include <string.h>

#define HEADER_SIZE 64u
#define SLOTS ((JOURNAL_BANK_SIZE - HEADER_SIZE) / JOURNAL_RECORD_SIZE)
#define COMMIT 0x00000000u
#define SAMPLE_MAGIC 0x314d4c53u
#define OVERFLOW_MAGIC 0x314f4c53u
#define HEADER_MAGIC 0x31484c53u

static void put16(uint8_t *p, uint16_t v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); }
static void put32(uint8_t *p, uint32_t v) { for (unsigned n=0;n<4;n++) p[n]=(uint8_t)(v>>(8*n)); }
static void put64(uint8_t *p, uint64_t v) { for (unsigned n=0;n<8;n++) p[n]=(uint8_t)(v>>(8*n)); }
static uint16_t get16(const uint8_t *p) { return (uint16_t)(p[0]|((uint16_t)p[1]<<8)); }
static uint32_t get32(const uint8_t *p) { uint32_t v=0; for (unsigned n=0;n<4;n++) v|=(uint32_t)p[n]<<(8*n); return v; }
static uint64_t get64(const uint8_t *p) { uint64_t v=0; for (unsigned n=0;n<8;n++) v|=(uint64_t)p[n]<<(8*n); return v; }
static uint32_t crc32(const uint8_t *p, size_t len) {
    uint32_t c=UINT32_MAX;
    for (size_t i=0;i<len;i++) { c^=p[i]; for (unsigned b=0;b<8;b++) c=(c>>1)^(0xedb88320u & (0u-(c&1u))); }
    return ~c;
}
static uint32_t offset(const journal_t *j, uint32_t slot) { return j->bank*JOURNAL_BANK_SIZE+HEADER_SIZE+slot*JOURNAL_RECORD_SIZE; }
static bool blank(const uint8_t *p, size_t len) { for(size_t i=0;i<len;i++) if(p[i]!=0xff) return false; return true; }
static void encode(uint8_t r[JOURNAL_RECORD_SIZE], const journal_sample_t *s, uint64_t id) {
    memset(r, 0xff, JOURNAL_RECORD_SIZE);
    put32(r, SAMPLE_MAGIC); r[4]=1; r[5]=(s->usb_present?1u:0u)|(s->charging?2u:0u);
    r[6]=s->reset_reason; r[7]=s->wake_reason;
    put64(r+8,id); put64(r+16,s->boot_id); put64(r+24,s->uptime_us);
    memcpy(r+32,s->mac,6); memcpy(r+38,s->firmware_sha256,32);
    put32(r+70,(uint32_t)s->temperature_milli_c); put32(r+74,s->humidity_milli_rh);
    put32(r+78,(uint32_t)s->battery_mv); put16(r+82,(uint16_t)s->sensor_status);
    put16(r+84,(uint16_t)s->adc_status); put16(r+86,s->quality_flags);
    put32(r+88,crc32(r,88));
}
static void decode(const uint8_t r[JOURNAL_RECORD_SIZE], journal_sample_t *s) {
    memset(s,0,sizeof(*s)); s->usb_present=!!(r[5]&1); s->charging=!!(r[5]&2);
    s->reset_reason=r[6]; s->wake_reason=r[7]; s->boot_id=get64(r+16); s->uptime_us=get64(r+24);
    memcpy(s->mac,r+32,6); memcpy(s->firmware_sha256,r+38,32);
    s->temperature_milli_c=(int32_t)get32(r+70); s->humidity_milli_rh=get32(r+74);
    s->battery_mv=(int32_t)get32(r+78); s->sensor_status=(int16_t)get16(r+82);
    s->adc_status=(int16_t)get16(r+84); s->quality_flags=get16(r+86);
}
static bool valid(const uint8_t *r) {
    uint32_t magic=get32(r);
    return (magic==SAMPLE_MAGIC || magic==OVERFLOW_MAGIC) && r[4]==1 &&
           get32(r+92)==COMMIT && get32(r+88)==crc32(r,88);
}
static bool committed_corrupt(const uint8_t *r) {
    return get32(r+92)==COMMIT && !valid(r);
}
typedef enum { HEADER_INVALID, HEADER_VALID, HEADER_CORRUPT, HEADER_IO_ERROR } header_result_t;
static header_result_t header(const journal_t *j,uint32_t bank,uint64_t *gen,uint64_t *high,uint64_t *over) {
    uint8_t h[HEADER_SIZE];
    if(!j->io.read(j->io.ctx,bank*JOURNAL_BANK_SIZE,h,sizeof(h))) return HEADER_IO_ERROR;
    if(get32(h+32)!=COMMIT) return HEADER_INVALID;
    if(get32(h)!=HEADER_MAGIC || get32(h+28)!=crc32(h,28)) return HEADER_CORRUPT;
    *gen=get64(h+4); *high=get64(h+12); *over=get64(h+20); return HEADER_VALID;
}
static bool write_header(journal_t *j,uint32_t bank,uint64_t gen,uint64_t high,uint64_t over) {
    uint8_t h[HEADER_SIZE]; memset(h,0xff,sizeof(h));
    put32(h,HEADER_MAGIC); put64(h+4,gen); put64(h+12,high); put64(h+20,over);
    put32(h+28,crc32(h,28));
    uint32_t base=bank*JOURNAL_BANK_SIZE;
    if(!j->io.write(j->io.ctx,base,h,32)) return false;
    uint8_t commit[4]={0,0,0,0};
    if(!j->io.write(j->io.ctx,base+32,commit,4)) {
        uint64_t g,x,o; return header(j,bank,&g,&x,&o)==HEADER_VALID&&g==gen&&x==high&&o==over;
    }
    return true;
}
static journal_result_t scan(journal_t *j) {
    j->slots=0; j->live=0;
    for(uint32_t n=0;n<SLOTS;n++) {
        uint8_t r[JOURNAL_RECORD_SIZE]; if(!j->io.read(j->io.ctx,offset(j,n),r,sizeof(r))) return JOURNAL_IO_ERROR;
        if(blank(r,sizeof(r))) break;
        j->slots=n+1; // A torn slot is never reused.
        if(!valid(r)) { if(committed_corrupt(r)) return JOURNAL_CORRUPT; continue; }
        if(get32(r)==SAMPLE_MAGIC) {
            uint64_t id=get64(r+8); if(id>j->highwater) j->highwater=id;
            if(get32(r+96)!=COMMIT) j->live++;
        } else {
            if(j->overflow==UINT64_MAX) return JOURNAL_COUNTER_EXHAUSTED;
            j->overflow++;
        }
    }
    return j->live>JOURNAL_CAPACITY?JOURNAL_CORRUPT:JOURNAL_OK;
}
static journal_result_t reopen(journal_t *j) {
    uint64_t g0=0,h0=0,o0=0,g1=0,h1=0,o1=0;
    header_result_t a=header(j,0,&g0,&h0,&o0), b=header(j,1,&g1,&h1,&o1);
    if(a==HEADER_IO_ERROR||b==HEADER_IO_ERROR) return JOURNAL_IO_ERROR;
    if(a==HEADER_CORRUPT||b==HEADER_CORRUPT) return JOURNAL_CORRUPT;
    if(a!=HEADER_VALID&&b!=HEADER_VALID) return JOURNAL_CORRUPT;
    j->bank=(b==HEADER_VALID&&(a!=HEADER_VALID||g1>g0))?1u:0u;
    j->generation=j->bank?g1:g0; j->highwater=j->bank?h1:h0; j->overflow=j->bank?o1:o0;
    return scan(j);
}
static header_result_t bank_data_blank(journal_t *j,uint32_t bank) {
    uint8_t chunk[256];
    for(uint32_t at=HEADER_SIZE;at<JOURNAL_BANK_SIZE;at+=sizeof(chunk)) {
        size_t len=JOURNAL_BANK_SIZE-at;
        if(len>sizeof(chunk)) len=sizeof(chunk);
        if(!j->io.read(j->io.ctx,bank*JOURNAL_BANK_SIZE+at,chunk,len)) return HEADER_IO_ERROR;
        if(!blank(chunk,len)) return HEADER_INVALID;
    }
    return HEADER_VALID;
}
journal_result_t journal_open(journal_t *j,journal_io_t io) {
    if(!j||!io.read||!io.write||!io.erase) return JOURNAL_IO_ERROR;
    memset(j,0,sizeof(*j)); j->io=io;
    uint8_t first[HEADER_SIZE],second[HEADER_SIZE];
    if(!io.read(io.ctx,0,first,sizeof(first))||!io.read(io.ctx,JOURNAL_BANK_SIZE,second,sizeof(second))) return JOURNAL_IO_ERROR;
    if(blank(second,sizeof(second)) &&
       (blank(first,sizeof(first)) || get32(first+32)!=COMMIT)) {
        header_result_t data=bank_data_blank(j,0);
        if(data==HEADER_IO_ERROR) return JOURNAL_IO_ERROR;
        if(data==HEADER_VALID) {
        // Factory-empty partition only. Erase whole bank on first use.
            if(!io.erase(io.ctx,0,JOURNAL_BANK_SIZE)||!write_header(j,0,1,0,0)) return JOURNAL_IO_ERROR;
        }
    }
    return reopen(j);
}
static journal_result_t compact(journal_t *j) {
    if(j->generation==UINT64_MAX) return JOURNAL_COUNTER_EXHAUSTED;
    uint32_t src=j->bank, dst=1u-src, copied=0;
    if(!j->io.erase(j->io.ctx,dst*JOURNAL_BANK_SIZE,JOURNAL_BANK_SIZE)) return JOURNAL_IO_ERROR;
    for(uint32_t n=0;n<j->slots;n++) {
        uint8_t r[JOURNAL_RECORD_SIZE];
        if(!j->io.read(j->io.ctx,src*JOURNAL_BANK_SIZE+HEADER_SIZE+n*JOURNAL_RECORD_SIZE,r,sizeof(r))) return JOURNAL_IO_ERROR;
        if(committed_corrupt(r)) return JOURNAL_CORRUPT;
        if(!valid(r)||get32(r)!=SAMPLE_MAGIC||get32(r+96)==COMMIT) continue;
        uint32_t at=dst*JOURNAL_BANK_SIZE+HEADER_SIZE+copied*JOURNAL_RECORD_SIZE;
        // Copy record including its already committed word; new bank stays invisible until header commit.
        if(!j->io.write(j->io.ctx,at,r,sizeof(r))) return JOURNAL_IO_ERROR;
        copied++;
    }
    if(!write_header(j,dst,j->generation+1,j->highwater,j->overflow)) return JOURNAL_IO_ERROR;
    return reopen(j);
}
static journal_result_t reserve(journal_t *j) {
    if(j->slots<SLOTS) return JOURNAL_OK;
    return compact(j);
}
static journal_result_t write_record(journal_t *j,uint8_t r[JOURNAL_RECORD_SIZE]) {
    journal_result_t v=reserve(j); if(v!=JOURNAL_OK) return v;
    uint32_t at=offset(j,j->slots++);
    if(!j->io.write(j->io.ctx,at,r,92)) {
        journal_result_t recovered=reopen(j);
        return recovered==JOURNAL_OK?JOURNAL_IO_ERROR:recovered;
    }
    uint8_t commit[4]={0,0,0,0};
    if(!j->io.write(j->io.ctx,at+92,commit,4)) return JOURNAL_IO_ERROR;
    return JOURNAL_OK;
}
static bool same_token(const uint8_t r[JOURNAL_RECORD_SIZE],const journal_sample_t *s) {
    return valid(r)&&get64(r+16)==s->boot_id&&get64(r+24)==s->uptime_us&&
           memcmp(r+32,s->mac,6)==0;
}
journal_result_t journal_append(journal_t *j,const journal_sample_t *s,uint64_t *id) {
    if(!j||!s||!id||!j->io.read||!j->io.write||!j->io.erase) return JOURNAL_IO_ERROR;
    journal_result_t v=reopen(j); if(v!=JOURNAL_OK) return v;
    // The boot/acquisition token resolves an ambiguous failed commit write, including after reboot.
    for(uint32_t n=0;n<j->slots;n++) {
        uint8_t r[JOURNAL_RECORD_SIZE]; if(!j->io.read(j->io.ctx,offset(j,n),r,sizeof(r))) return JOURNAL_IO_ERROR;
        if(committed_corrupt(r)) return JOURNAL_CORRUPT;
        if(same_token(r,s)) {
            *id=get64(r+8);
            if(get32(r)==OVERFLOW_MAGIC) return JOURNAL_OVERFLOW;
            uint8_t expected[JOURNAL_RECORD_SIZE]; encode(expected,s,*id);
            return memcmp(r,expected,92)==0?JOURNAL_OK:JOURNAL_CORRUPT;
        }
    }
    if(j->live==JOURNAL_CAPACITY) {
        if(j->overflow==UINT64_MAX) return JOURNAL_COUNTER_EXHAUSTED;
        uint8_t r[JOURNAL_RECORD_SIZE]; memset(r,0xff,sizeof(r));
        put32(r,OVERFLOW_MAGIC); r[4]=1; put64(r+16,s->boot_id); put64(r+24,s->uptime_us);
        memcpy(r+32,s->mac,6); put32(r+88,crc32(r,88));
        v=write_record(j,r); if(v!=JOURNAL_OK) {
            journal_result_t recovered=reopen(j);
            if(recovered!=JOURNAL_OK) return recovered;
            for(uint32_t n=0;n<j->slots;n++) {
                uint8_t x[JOURNAL_RECORD_SIZE]; if(!j->io.read(j->io.ctx,offset(j,n),x,sizeof(x))) return JOURNAL_IO_ERROR;
                if(committed_corrupt(x)) return JOURNAL_CORRUPT;
                if(same_token(x,s)&&get32(x)==OVERFLOW_MAGIC) return JOURNAL_OVERFLOW;
            }
            return v;
        }
        j->overflow++; return JOURNAL_OVERFLOW;
    }
    if(j->highwater==UINT64_MAX) return JOURNAL_ID_EXHAUSTED;
    uint64_t candidate=j->highwater+1; uint8_t r[JOURNAL_RECORD_SIZE]; encode(r,s,candidate);
    v=write_record(j,r);
    if(v!=JOURNAL_OK) {
        // A backend may report failure after programming all commit bits.
        journal_result_t recovered=reopen(j); if(recovered!=JOURNAL_OK) return recovered;
        for(uint32_t n=0;n<j->slots;n++) {
            uint8_t x[JOURNAL_RECORD_SIZE]; if(!j->io.read(j->io.ctx,offset(j,n),x,sizeof(x))) return JOURNAL_IO_ERROR;
            if(committed_corrupt(x)) return JOURNAL_CORRUPT;
            if(same_token(x,s)&&get32(x)==SAMPLE_MAGIC) {
                *id=get64(x+8); uint8_t expected[JOURNAL_RECORD_SIZE]; encode(expected,s,*id);
                return memcmp(x,expected,92)==0?JOURNAL_OK:JOURNAL_CORRUPT;
            }
        }
        return v;
    }
    j->highwater=candidate; j->live++; *id=candidate; return JOURNAL_OK;
}
journal_result_t journal_ack(journal_t *j,uint64_t id) {
    if(!j||!j->io.read||!j->io.write||!j->io.erase) return JOURNAL_IO_ERROR;
    if(!id) return JOURNAL_NOT_FOUND;
    journal_result_t v=reopen(j); if(v!=JOURNAL_OK) return v;
    for(uint32_t n=0;n<j->slots;n++) {
        uint8_t r[JOURNAL_RECORD_SIZE]; uint32_t at=offset(j,n);
        if(!j->io.read(j->io.ctx,at,r,sizeof(r))) return JOURNAL_IO_ERROR;
        if(committed_corrupt(r)) return JOURNAL_CORRUPT;
        if(valid(r)&&get32(r)==SAMPLE_MAGIC&&get64(r+8)==id) {
            if(get32(r+96)==COMMIT) return JOURNAL_OK;
            uint8_t zero[4]={0,0,0,0};
            if(!j->io.write(j->io.ctx,at+96,zero,4)) {
                if(!j->io.read(j->io.ctx,at,r,sizeof(r))) return JOURNAL_IO_ERROR;
                if(committed_corrupt(r)) return JOURNAL_CORRUPT;
                if(get32(r+96)!=COMMIT) return JOURNAL_IO_ERROR;
            }
            j->live--; return JOURNAL_OK;
        }
    }
    return JOURNAL_NOT_FOUND;
}
journal_result_t journal_oldest(journal_t *j,journal_sample_t *s,uint64_t *id) {
    if(!j||!s||!id||!j->io.read||!j->io.write||!j->io.erase) return JOURNAL_IO_ERROR;
    journal_result_t v=reopen(j); if(v!=JOURNAL_OK) return v;
    for(uint32_t n=0;n<j->slots;n++) {
        uint8_t r[JOURNAL_RECORD_SIZE]; if(!j->io.read(j->io.ctx,offset(j,n),r,sizeof(r))) return JOURNAL_IO_ERROR;
        if(committed_corrupt(r)) return JOURNAL_CORRUPT;
        if(valid(r)&&get32(r)==SAMPLE_MAGIC&&get32(r+96)!=COMMIT) {
            decode(r,s); *id=get64(r+8); return JOURNAL_OK;
        }
    }
    return JOURNAL_NOT_FOUND;
}
