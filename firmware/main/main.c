// SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
// SPDX-License-Identifier: GPL-3.0-or-later
// Engineering bring-up only. No charging, USB500, provisioning, OTA or radio.
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include "cJSON.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_app_desc.h"
#include "esp_mac.h"
#include "esp_sleep.h"
#include "esp_system.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "sample.h"

#if !CONFIG_IDF_TARGET_ESP32C6 || !CONFIG_ESP_TASK_WDT_INIT || !CONFIG_ESP_TASK_WDT_PANIC
#error "Bring-up requires ESP32-C6 and a resetting task watchdog"
#endif
_Static_assert(CONFIG_ESP_TASK_WDT_TIMEOUT_S == 5, "Review watchdog policy before changing timeout");

// EDS §2.1; both layouts share this pin mapping.
enum { BTN_PROV = 1, USB_EN2 = 14, SDA = 6, SCL = 7, CHARGE_ENABLE = 18, LED_N = 19, TEST_MODE = 20,
       USB_ISEL = 21, PG_N = 22, CHG_N = 23 };
// Bring-up policy choices, not measured energy or safety limits. See docs/72.
enum { I2C_TIMEOUT_MS = 50, SAMPLE_INTERVAL_S = 300, FACTORY_WINDOW_MS = 3000 };

static void safe_outputs(void) {
    // Charge disabled, EN1=EN2=1 standby (TI Table 7-2; ADR-001).
    // No active USB-current mode is authorized in this image.
    ESP_ERROR_CHECK(gpio_set_level(CHARGE_ENABLE, 0));
    ESP_ERROR_CHECK(gpio_set_level(USB_ISEL, 1));
    ESP_ERROR_CHECK(gpio_set_level(USB_EN2, 1));
    // Preload safe latches before releasing any hold left by an earlier image.
    ESP_ERROR_CHECK(gpio_hold_dis(CHARGE_ENABLE));
    ESP_ERROR_CHECK(gpio_hold_dis(USB_ISEL));
    ESP_ERROR_CHECK(gpio_hold_dis(USB_EN2));
    gpio_config_t outputs = {
        .pin_bit_mask = (1ULL << CHARGE_ENABLE) | (1ULL << USB_ISEL) | (1ULL << USB_EN2),
        .mode = GPIO_MODE_OUTPUT,
    };
    ESP_ERROR_CHECK(gpio_config(&outputs));
}

static esp_err_t acquire(double *temperature_c, double *humidity_rh) {
    i2c_master_bus_handle_t bus = NULL;
    i2c_master_dev_handle_t sensor = NULL;
    const i2c_master_bus_config_t bus_cfg = {
        .i2c_port = I2C_NUM_0, .sda_io_num = SDA, .scl_io_num = SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT, .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = false, // R3/R4 are external 10 kohm.
    };
    const i2c_device_config_t dev_cfg = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7, .device_address = 0x44,
        .scl_speed_hz = 100000, // conservative bring-up bus rate
    };
    esp_err_t err = i2c_new_master_bus(&bus_cfg, &bus);
    if (err != ESP_OK) return err;
    err = i2c_master_bus_add_device(bus, &dev_cfg, &sensor);
    if (err == ESP_OK) {
        // Sensirion's SHT4x reference driver: 0xfd, then wait 10 ms.
        const uint8_t command = 0xfd;
        uint8_t frame[6];
        err = i2c_master_transmit(sensor, &command, 1, I2C_TIMEOUT_MS);
        if (err == ESP_OK) {
            vTaskDelay(pdMS_TO_TICKS(10));
            err = i2c_master_receive(sensor, frame, sizeof(frame), I2C_TIMEOUT_MS);
            if (err == ESP_OK && !sensorly_decode(frame, temperature_c, humidity_rh))
                err = ESP_ERR_INVALID_CRC;
        }
        i2c_master_bus_rm_device(sensor);
    }
    i2c_del_master_bus(bus);
    return err;
}

static esp_err_t battery_mv(int *millivolts) {
    adc_oneshot_unit_handle_t adc = NULL;
    adc_cali_handle_t calibration = NULL;
    const adc_oneshot_unit_init_cfg_t unit = {.unit_id = ADC_UNIT_1};
    const adc_oneshot_chan_cfg_t channel = {
        .atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    const adc_cali_curve_fitting_config_t curve = {
        .unit_id = ADC_UNIT_1, .chan = ADC_CHANNEL_2,
        .atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    esp_err_t err = adc_oneshot_new_unit(&unit, &adc);
    if (err != ESP_OK) return err;
    err = adc_oneshot_config_channel(adc, ADC_CHANNEL_2, &channel);
    if (err == ESP_OK) err = adc_cali_create_scheme_curve_fitting(&curve, &calibration);
    int raw = 0, mv = 0;
    if (err == ESP_OK) err = adc_oneshot_read(adc, ADC_CHANNEL_2, &raw);
    if (err == ESP_OK) err = adc_cali_raw_to_voltage(calibration, raw, &mv);
    if (err == ESP_OK) *millivolts = 2 * mv; // EDS §6: equal 2M2 divider.
    if (calibration) adc_cali_delete_scheme_curve_fitting(calibration);
    adc_oneshot_del_unit(adc);
    return err;
}

void app_main(void) {
    safe_outputs();
    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
    // Open-drain charger outputs already have R9/R10 external pull-ups.
    gpio_config_t charger_inputs = {
        .pin_bit_mask = (1ULL << PG_N) | (1ULL << CHG_N),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE, .pull_down_en = GPIO_PULLDOWN_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&charger_inputs));
    gpio_config_t factory_input = {
        .pin_bit_mask = 1ULL << TEST_MODE, .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE, .pull_down_en = GPIO_PULLDOWN_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&factory_input));
    ESP_ERROR_CHECK(gpio_set_level(LED_N, 1));
    ESP_ERROR_CHECK(gpio_set_direction(LED_N, GPIO_MODE_OUTPUT));
    gpio_config_t button = {.pin_bit_mask = 1ULL << BTN_PROV, .mode = GPIO_MODE_INPUT};
    ESP_ERROR_CHECK(gpio_config(&button));
    // No Wi-Fi/BLE init is linked from this application. Sensor precedes ADC
    // and console activity; no stale reading is substituted on any failure.
    vTaskDelay(pdMS_TO_TICKS(10)); // sensor power-up margin; docs/72
    double temperature = 0, humidity = 0;
    int64_t acquired_us = esp_timer_get_time();
    esp_err_t sensor_err = acquire(&temperature, &humidity);
    vTaskDelay(pdMS_TO_TICKS(550)); // EDS §6: 5 * 1.1 Mohm * 100 nF.
    int vbat_mv = 0;
    esp_err_t adc_err = battery_mv(&vbat_mv);
    bool usb_present = !gpio_get_level(PG_N);
    bool charging = !gpio_get_level(CHG_N);
    bool factory_mode = !gpio_get_level(TEST_MODE);
    uint8_t mac[6];
    ESP_ERROR_CHECK(esp_read_mac(mac, ESP_MAC_WIFI_STA));
    char chip_id[13], image_hash[65];
    snprintf(chip_id, sizeof(chip_id), "%02x%02x%02x%02x%02x%02x",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    esp_app_get_elf_sha256(image_hash, sizeof(image_hash));
    cJSON *record = cJSON_CreateObject();
    if (record) {
        cJSON_AddNumberToObject(record, "schema", 1);
        cJSON_AddStringToObject(record, "kind", "sensorly-bringup");
        cJSON_AddStringToObject(record, "chip_id", chip_id);
        cJSON_AddStringToObject(record, "firmware_sha256", image_hash);
        cJSON_AddNumberToObject(record, "reset_reason", esp_reset_reason());
        cJSON_AddNumberToObject(record, "wake_reason", esp_sleep_get_wakeup_cause());
        cJSON_AddNumberToObject(record, "uptime_us", acquired_us);
        cJSON_AddNullToObject(record, "acquired_at_utc");
        cJSON_AddBoolToObject(record, "clock_valid", false);
        cJSON_AddBoolToObject(record, "factory_mode", factory_mode);
        cJSON_AddBoolToObject(record, "radio_started", false);
        cJSON_AddBoolToObject(record, "charge_enabled", false);
        cJSON_AddStringToObject(record, "input_mode", "STANDBY");
        cJSON_AddBoolToObject(record, "usb_present", usb_present);
        cJSON_AddBoolToObject(record, "charging", charging);
        cJSON_AddStringToObject(record, "sensor_status", esp_err_to_name(sensor_err));
        cJSON_AddStringToObject(record, "adc_status", esp_err_to_name(adc_err));
        if (sensor_err == ESP_OK) {
            cJSON_AddNumberToObject(record, "temperature_c", temperature);
            cJSON_AddNumberToObject(record, "humidity_rh", humidity);
        } else {
            cJSON_AddNullToObject(record, "temperature_c");
            cJSON_AddNullToObject(record, "humidity_rh");
        }
        if (adc_err == ESP_OK) cJSON_AddNumberToObject(record, "battery_mv", vbat_mv);
        else cJSON_AddNullToObject(record, "battery_mv");
        cJSON *flags = cJSON_AddArrayToObject(record, "quality_flags");
        cJSON_AddItemToArray(flags, cJSON_CreateString("engineering_unqualified"));
        cJSON_AddItemToArray(flags, cJSON_CreateString("battery_meter_check_pending"));
        cJSON_AddItemToArray(flags, cJSON_CreateString("cooldown_unqualified"));
        if (usb_present) cJSON_AddItemToArray(flags, cJSON_CreateString("usb_thermal_bias"));
        if (charging) cJSON_AddItemToArray(flags, cJSON_CreateString("unexpected_charge_status"));
        char *json = cJSON_PrintUnformatted(record);
        if (json) { puts(json); free(json); }
        cJSON_Delete(record);
    }
    // Factory fixture has a bounded receive window; no endless test loop.
    if (factory_mode) vTaskDelay(pdMS_TO_TICKS(FACTORY_WINDOW_MS));
    safe_outputs();
    ESP_ERROR_CHECK(esp_task_wdt_reset());
    ESP_ERROR_CHECK(esp_sleep_enable_timer_wakeup((uint64_t)SAMPLE_INTERVAL_S * 1000000));
    // A held button must not cause an immediate repeated deep-sleep reset loop.
    // Timer wake remains armed; release the button to arm EXT1 on the next cycle.
    if (gpio_get_level(BTN_PROV))
        ESP_ERROR_CHECK(esp_sleep_enable_ext1_wakeup_io(1ULL << BTN_PROV, ESP_EXT1_WAKEUP_ANY_LOW));
    // Release the EN outputs to external R8/R20 pull-ups before digital power-off.
    gpio_config_t standby = {.pin_bit_mask = (1ULL << USB_ISEL) | (1ULL << USB_EN2),
                             .mode = GPIO_MODE_INPUT};
    ESP_ERROR_CHECK(gpio_config(&standby));
    esp_deep_sleep_start();
}
