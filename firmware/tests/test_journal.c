// SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
#include "journal.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { uint8_t flash[2*JOURNAL_BANK_SIZE]; int fail_at; int writes; int erases; bool report_after; uint32_t fail_read_at; bool fail_read_once; uint32_t corrupt_read_at; int corrupt_read_nth, corrupt_read_count; bool partial_erase_once; } mem_t;
static bool rd(void *v,uint32_t at,void *p,size_t n) {
    mem_t *m=v; if((uint64_t)at+n>sizeof(m->flash)) return false;
    if(m->fail_read_once && at==m->fail_read_at) { m->fail_read_once=false; return false; }
    memcpy(p,m->flash+at,n);
    if(m->corrupt_read_nth && at==m->corrupt_read_at &&
       ++m->corrupt_read_count==m->corrupt_read_nth) ((uint8_t *)p)[70]^=1;
    return true;
}
static bool wr(void *v,uint32_t at,const void *p,size_t n) {
    mem_t *m=v; if((uint64_t)at+n>sizeof(m->flash)) return false;
    m->writes++;
    size_t done=n;
    if(m->fail_at==m->writes) done=m->report_after?n:n/2;
    const uint8_t *in=p;
    for(size_t i=0;i<done;i++) {
        assert((m->flash[at+i]&in[i])==in[i]); // NOR flash cannot set a programmed bit.
        m->flash[at+i]&=in[i];
    }
    return m->fail_at!=m->writes;
}
static bool er(void *v,uint32_t at,size_t n) {
    mem_t *m=v; if(at%JOURNAL_ERASE_SIZE||n%JOURNAL_ERASE_SIZE||
                   (uint64_t)at+n>sizeof(m->flash)) return false;
    m->erases++;
    if(m->partial_erase_once) {
        m->partial_erase_once=false;
        memset(m->flash+at,0xff,16); // interrupted first erase unit, commit word still zero
        return false;
    }
    memset(m->flash+at,0xff,n); return true;
}
static void fresh(mem_t *m) {
    memset(m,0,sizeof(*m));
    memset(m->flash,0xff,sizeof(m->flash));
}
static journal_io_t io(mem_t *m) { journal_io_t x={m,rd,wr,er}; return x; }
static journal_sample_t sample(uint64_t n) {
    journal_sample_t s={0}; s.boot_id=17; s.uptime_us=n; s.mac[5]=42;
    s.temperature_milli_c=21000+(int32_t)n; s.humidity_milli_rh=44000;
    s.battery_mv=3000; s.firmware_sha256[0]=0xa5; return s;
}
static void basic(void) {
    mem_t *m=malloc(sizeof(*m)); assert(m); fresh(m);
    journal_t j; assert(journal_open(&j,io(m))==JOURNAL_OK);
    for(uint64_t n=1;n<=500;n++) { journal_sample_t s=sample(n); uint64_t id=0;
        assert(journal_append(&j,&s,&id)==JOURNAL_OK&&id==n); }
    assert(j.live==500);
    for(uint64_t n=1;n<=250;n++) assert(journal_ack(&j,n)==JOURNAL_OK);
    for(uint64_t n=501;n<=750;n++) { journal_sample_t s=sample(n); uint64_t id=0;
        assert(journal_append(&j,&s,&id)==JOURNAL_OK&&id==n); }
    assert(j.live==500);
    journal_sample_t next=sample(751); uint64_t id=0;
    assert(journal_append(&j,&next,&id)==JOURNAL_OVERFLOW&&j.overflow==1);
    assert(journal_open(&j,io(m))==JOURNAL_OK&&j.live==500&&j.overflow==1);
    journal_sample_t old; assert(journal_oldest(&j,&old,&id)==JOURNAL_OK&&id==251&&old.uptime_us==251);
    for(uint64_t n=752;n<=1000;n++) { journal_sample_t s=sample(n);
        assert(journal_append(&j,&s,&id)==JOURNAL_OVERFLOW); }
    assert(j.overflow==250); // overflow events force compaction, carrying the counter.
    assert(journal_open(&j,io(m))==JOURNAL_OK&&j.overflow==250&&j.live==500);
    for(uint64_t n=251;n<=750;n++) assert(journal_ack(&j,n)==JOURNAL_OK);
    journal_sample_t last=sample(1001); assert(journal_append(&j,&last,&id)==JOURNAL_OK&&id==751);
    assert(journal_open(&j,io(m))==JOURNAL_OK&&j.live==1&&j.highwater==751);
    free(m);
}
static void faults(void) {
    for(int cut=1;cut<=2;cut++) for(int after=0;after<=1;after++) {
        mem_t *m=malloc(sizeof(*m)); assert(m); fresh(m);
        journal_t j; assert(journal_open(&j,io(m))==JOURNAL_OK);
        journal_sample_t s=sample(1); uint64_t id=0;
        m->writes=0; m->fail_at=cut; m->report_after=after;
        journal_result_t r=journal_append(&j,&s,&id);
        m->fail_at=0;
        assert(journal_open(&j,io(m))==JOURNAL_OK);
        if(cut==2&&after) assert(r==JOURNAL_OK&&j.live==1&&id==1);
        else if(cut==1&&after) assert(j.live==0 || j.live==1);
        else assert(j.live==0);
        assert(journal_append(&j,&s,&id)==JOURNAL_OK&&id==1);
        assert(j.live==1);
        journal_sample_t conflict=s; conflict.temperature_milli_c++;
        assert(journal_append(&j,&conflict,&id)==JOURNAL_CORRUPT);
        free(m);
    }
}
static void torn_ack_and_corruption(void) {
    mem_t *m=malloc(sizeof(*m)); assert(m); fresh(m);
    journal_t j; assert(journal_open(&j,io(m))==JOURNAL_OK);
    journal_sample_t s=sample(1); uint64_t id=0;
    assert(journal_append(&j,&s,&id)==JOURNAL_OK);
    m->writes=0; m->fail_at=1; m->report_after=false;
    assert(journal_ack(&j,id)==JOURNAL_IO_ERROR);
    m->fail_at=0;
    assert(journal_open(&j,io(m))==JOURNAL_OK&&j.live==1);
    assert(journal_ack(&j,id)==JOURNAL_OK&&j.live==0);
    assert(journal_open(&j,io(m))==JOURNAL_OK&&j.live==0);
    // Corruption in a committed payload is reported, never skipped.
    m->flash[64+70]^=1;
    assert(journal_open(&j,io(m))==JOURNAL_CORRUPT);
    free(m);
}
static void first_header_fault(void) {
    for(int cut=1;cut<=2;cut++) {
        mem_t *m=malloc(sizeof(*m)); assert(m); fresh(m);
        m->writes=0; m->fail_at=cut; m->report_after=false;
        journal_t j; assert(journal_open(&j,io(m))==JOURNAL_IO_ERROR);
        m->fail_at=0;
        assert(journal_open(&j,io(m))==JOURNAL_OK);
        journal_sample_t s=sample(1); uint64_t id=0;
        assert(journal_append(&j,&s,&id)==JOURNAL_OK&&id==1);
        free(m);
    }
}
static void ambiguous_overflow(void) {
    mem_t *m=malloc(sizeof(*m)); assert(m); fresh(m);
    journal_t j; assert(journal_open(&j,io(m))==JOURNAL_OK);
    for(uint64_t n=1;n<=500;n++) { journal_sample_t s=sample(n); uint64_t id=0;
        assert(journal_append(&j,&s,&id)==JOURNAL_OK); }
    journal_sample_t s=sample(501); uint64_t id=0;
    m->writes=0; m->fail_at=2; m->report_after=true;
    assert(journal_append(&j,&s,&id)==JOURNAL_OVERFLOW);
    m->fail_at=0;
    assert(journal_open(&j,io(m))==JOURNAL_OK&&j.overflow==1);
    assert(journal_append(&j,&s,&id)==JOURNAL_OVERFLOW&&j.overflow==1);
    free(m);
}
static void compaction_faults(void) {
    mem_t *base=malloc(sizeof(*base)); assert(base); fresh(base);
    journal_t j; assert(journal_open(&j,io(base))==JOURNAL_OK);
    for(uint64_t n=1;n<=500;n++) { journal_sample_t s=sample(n); uint64_t id=0;
        assert(journal_append(&j,&s,&id)==JOURNAL_OK); }
    for(uint64_t n=1;n<=155;n++) assert(journal_ack(&j,n)==JOURNAL_OK);
    for(uint64_t n=501;n<=654;n++) { journal_sample_t s=sample(n); uint64_t id=0;
        assert(journal_append(&j,&s,&id)==JOURNAL_OK); }
    // 654 slots, 499 live: next append must switch banks.
    assert(j.slots==654&&j.live==499);
    for(int cut=1;cut<=503;cut+= (cut==1?248:cut==249?250:1)) for(int after=0;after<=1;after++) {
        mem_t *m=malloc(sizeof(*m)); assert(m); memcpy(m,base,sizeof(*m));
        journal_t x; assert(journal_open(&x,io(m))==JOURNAL_OK);
        journal_sample_t s=sample(655); uint64_t id=0;
        m->writes=0; m->fail_at=cut; m->report_after=after;
        (void)journal_append(&x,&s,&id);
        m->fail_at=0;
        assert(journal_open(&x,io(m))==JOURNAL_OK);
        assert(x.live==499||x.live==500);
        assert(journal_append(&x,&s,&id)==JOURNAL_OK&&id==655);
        assert(x.live==500);
        journal_sample_t old; assert(journal_oldest(&x,&old,&id)==JOURNAL_OK&&id==156);
        free(m);
    }
    free(base);
}
static void committed_header_faults(void) {
    mem_t *base=malloc(sizeof(*base)); assert(base); fresh(base);
    base->fail_read_once=false;
    journal_t j; assert(journal_open(&j,io(base))==JOURNAL_OK);
    for(uint64_t n=1;n<=500;n++) { journal_sample_t s=sample(n); uint64_t id=0;
        assert(journal_append(&j,&s,&id)==JOURNAL_OK&&id==n); }
    for(uint64_t n=1;n<=155;n++) assert(journal_ack(&j,n)==JOURNAL_OK);
    for(uint64_t n=501;n<=655;n++) { journal_sample_t s=sample(n); uint64_t id=0;
        assert(journal_append(&j,&s,&id)==JOURNAL_OK&&id==n); }
    assert(j.bank==1&&j.generation==2&&j.highwater==655);
    for(int fault=0;fault<2;fault++) {
        mem_t *m=malloc(sizeof(*m)); assert(m); memcpy(m,base,sizeof(*m));
        journal_t x; assert(journal_open(&x,io(m))==JOURNAL_OK);
        if(fault==0) { m->fail_read_at=JOURNAL_BANK_SIZE; m->fail_read_once=true; }
        else m->flash[JOURNAL_BANK_SIZE+12]^=1; // committed newer header, CRC now invalid
        int writes=m->writes;
        journal_sample_t s=sample(656); uint64_t id=0;
        assert(journal_append(&x,&s,&id)==(fault==0?JOURNAL_IO_ERROR:JOURNAL_CORRUPT));
        assert(m->writes==writes); // Never erase the authoritative bank or reuse ID 655.
        if(fault==0) {
            assert(journal_open(&x,io(m))==JOURNAL_OK&&x.highwater==655);
            assert(journal_ack(&x,156)==JOURNAL_OK);
            assert(journal_append(&x,&s,&id)==JOURNAL_OK&&id==656);
        } else assert(journal_open(&x,io(m))==JOURNAL_CORRUPT);
        free(m);
    }
    free(base);
}
static void factory_read_fault(void) {
    mem_t *m=malloc(sizeof(*m)); assert(m); fresh(m);
    m->writes=0;
    m->fail_read_at=64; m->fail_read_once=true;
    journal_t j; assert(journal_open(&j,io(m))==JOURNAL_IO_ERROR);
    assert(m->writes==0); // Factory read failure must not initialize a header.
    free(m);
}
static void factory_requires_both_banks_empty(void) {
    for(int fault=0;fault<2;fault++) {
        mem_t *m=malloc(sizeof(*m)); assert(m); fresh(m);
        if(fault==0) m->flash[JOURNAL_BANK_SIZE+64]=0x53;
        else { m->fail_read_at=JOURNAL_BANK_SIZE+64; m->fail_read_once=true; }
        uint8_t *before=malloc(sizeof(m->flash)); assert(before);
        memcpy(before,m->flash,sizeof(m->flash));
        journal_t j;
        assert(journal_open(&j,io(m))==(fault==0?JOURNAL_CORRUPT:JOURNAL_IO_ERROR));
        assert(m->writes==0&&m->erases==0);
        assert(memcmp(before,m->flash,sizeof(m->flash))==0);
        free(before); free(m);
    }
}
static void corruption_between_scan_and_compaction(void) {
    mem_t *m=malloc(sizeof(*m)); assert(m); fresh(m);
    journal_t j; assert(journal_open(&j,io(m))==JOURNAL_OK);
    for(uint64_t n=1;n<=500;n++) { journal_sample_t s=sample(n); uint64_t id=0;
        assert(journal_append(&j,&s,&id)==JOURNAL_OK); }
    for(uint64_t n=1;n<=155;n++) assert(journal_ack(&j,n)==JOURNAL_OK);
    for(uint64_t n=501;n<=654;n++) { journal_sample_t s=sample(n); uint64_t id=0;
        assert(journal_append(&j,&s,&id)==JOURNAL_OK); }
    assert(j.slots==654&&j.live==499&&j.bank==0);
    m->corrupt_read_at=64+155*JOURNAL_RECORD_SIZE; // first unacknowledged record
    m->corrupt_read_count=0; m->corrupt_read_nth=3; // scan, token lookup, copy
    journal_sample_t s=sample(655); uint64_t id=0;
    assert(journal_append(&j,&s,&id)==JOURNAL_CORRUPT);
    assert(m->corrupt_read_count>=3);
    m->corrupt_read_nth=0;
    assert(journal_open(&j,io(m))==JOURNAL_OK&&j.bank==0&&j.highwater==654&&j.live==499);
    journal_sample_t oldest;
    assert(journal_oldest(&j,&oldest,&id)==JOURNAL_OK&&id==156);
    assert(journal_append(&j,&s,&id)==JOURNAL_OK&&id==655);
    free(m);
}
static void partial_erase_fails_closed(void) {
    mem_t *m=malloc(sizeof(*m)); assert(m); fresh(m);
    journal_t j; assert(journal_open(&j,io(m))==JOURNAL_OK);
    for(uint64_t n=1;n<=500;n++) { journal_sample_t s=sample(n); uint64_t id=0;
        assert(journal_append(&j,&s,&id)==JOURNAL_OK); }
    for(uint64_t n=1;n<=155;n++) assert(journal_ack(&j,n)==JOURNAL_OK);
    for(uint64_t n=501;n<=655;n++) { journal_sample_t s=sample(n); uint64_t id=0;
        assert(journal_append(&j,&s,&id)==JOURNAL_OK); }
    assert(j.bank==1&&j.live==500&&j.slots==500);
    for(uint64_t n=656;n<=809;n++) { journal_sample_t s=sample(n); uint64_t id=0;
        assert(journal_append(&j,&s,&id)==JOURNAL_OVERFLOW); }
    assert(j.slots==654&&j.overflow==154);
    uint8_t *active=malloc(JOURNAL_BANK_SIZE); assert(active);
    memcpy(active,m->flash+JOURNAL_BANK_SIZE,JOURNAL_BANK_SIZE);
    m->partial_erase_once=true;
    journal_sample_t s=sample(810); uint64_t id=0;
    assert(journal_append(&j,&s,&id)==JOURNAL_CORRUPT);
    assert(journal_open(&j,io(m))==JOURNAL_CORRUPT);
    assert(memcmp(active,m->flash+JOURNAL_BANK_SIZE,JOURNAL_BANK_SIZE)==0);
    free(active);
    // No bank is chosen while the stale bank's committed header is damaged.
    free(m);
}
static void unopened_api_is_safe(void) {
    journal_t j={0}; journal_sample_t s=sample(1); uint64_t id=0;
    assert(journal_append(&j,&s,&id)==JOURNAL_IO_ERROR);
    assert(journal_ack(&j,1)==JOURNAL_IO_ERROR);
    assert(journal_oldest(&j,&s,&id)==JOURNAL_IO_ERROR);
}
int main(void) { basic(); faults(); torn_ack_and_corruption(); first_header_fault(); ambiguous_overflow(); compaction_faults(); committed_header_faults(); factory_read_fault(); factory_requires_both_banks_empty(); corruption_between_scan_and_compaction(); partial_erase_fails_closed(); unopened_api_is_safe(); puts("journal host tests passed"); }
