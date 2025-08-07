# SPDX-FileCopyrightText: 2025 Oleg Evsegneev for RobotClass
#
# SPDX-License-Identifier: MIT

# Драйвер для дисплеев LCD1602/2004 с I2C интерфейсом на основе PCA9534
"""
`character_lcd_i2c`
====================================================

Драйвер для монохромных символьных дисплеев LCD1602/2004 с I2C интерфейсом на базе PCA9534

Исходный код
https://github.com/robotclass/Circuitpython

**Пример**
i2c = board.I2C()

lcd = RobotClass_LCD_I2C(i2c, 16, 2)
lcd.message = "Как дела?"

Реализация
--------------------

**Аппаратная часть:**

* `Интерфейс I2C для ЖК дисплея 1602/2004, RobotClass
  <https://shop.robotclass.ru/item/4087>`_

**Зависимости:**

* Библиотека Adafruit's Bus Device: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Библиотека Adafruit CircuitPython CharLCD: https://github.com/adafruit/Adafruit_CircuitPython_CharLCD
"""

import time

from robotclass_pca9534 import PCA9534

from robotclass_character_lcd.character_lcd import Character_LCD_Mono

class Character_LCD_I2C(Character_LCD_Mono):
    def __init__(
        self,
        i2c: board.I2C,
        columns: int,
        lines: int,
        address: Optional[int] = None,
        backlight_inverted: bool = False
    ) -> None:

        if address:
            self.pca = PCA9534(i2c, address=address)
        else:
            self.pca = PCA9534(i2c)

        self.pca.channels[1].value = 0

        super().__init__(
            self.pca.channels[0],  # reset
            self.pca.channels[2],  # enable
            self.pca.channels[4],  # data line 4
            self.pca.channels[5],  # data line 5
            self.pca.channels[6],  # data line 6
            self.pca.channels[7],  # data line 7
            columns,
            lines,
            backlight_pin=self.pca.channels[3],
            backlight_inverted=backlight_inverted,
        )

    def _write8(self, value: int, char_mode: bool = False) -> None:
        time.sleep(0.001)
        
        # bits are, MSB (7) to LSB (0)
        # backlight:   bit 3
        # data line 7: bit 7
        # data line 6: bit 6
        # data line 5: bit 5
        # data line 4: bit 4
        # enable:      bit 2
        # reset:       bit 0

        reset_bit = int(char_mode)
        backlight_bit = int(self.backlight ^ self.backlight_inverted) << 3

        self.pca.output = reset_bit | backlight_bit | (value & 0xF0)

        self._pulse_enable()

        self.pca.output = reset_bit | backlight_bit | ((value & 0x0F) << 4)

        self._pulse_enable()