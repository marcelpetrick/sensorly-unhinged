# SPDX-FileCopyrightText: 2026 Marcel Petrick <mail@marcelpetrick.it>
# SPDX-License-Identifier: GPL-3.0-or-later
idf_component_register(SRCS "main.c" "sample.c" INCLUDE_DIRS "."
    REQUIRES esp_driver_gpio esp_driver_i2c esp_adc esp_timer esp_app_format esp_hw_support json)
