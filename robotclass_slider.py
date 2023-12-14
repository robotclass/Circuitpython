# SPDX-FileCopyrightText: 2023 Oleg Evsegneev for RobotClass
#
# SPDX-License-Identifier: MIT

# RobotClass Joystick-Slider CircuitPython Driver
"""
`robotclass_slider`
====================================================

Драйвер скользящего джойстика (джойстик-слайдера) I2C от RobotClass

Исходный код
https://github.com/robotclass/Circuitpython

Реализация
--------------------

**Аппаратная часть:**

* `Джойстик-слайдер QIIC
  <https://shop.robotclass.ru/item/3439>`_

**Зависимости:**

* Библиотека Adafruit's Bus Device: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

__version__ = "0.2"

_REGISTER_GET_SENSOR = const(0xBA)

class RobotClass_Slider:
    i2c = None

    def __init__(self, i2c: I2C, address: int = 0x20) -> None:
        from adafruit_bus_device import (  # pylint: disable=import-outside-toplevel
            i2c_device,
        )
        self._i2c = i2c_device.I2CDevice(i2c, address)

    def getXY(self):
        data = self._read_register(_REGISTER_GET_SENSOR, 4);
        x = data[0] | (data[1]<<8)
        y = data[2] | (data[3]<<8)
        return (x,y)

    def _read_register(self, register: int, length: int) -> bytearray:
        """Low level register reading over I2C, returns a list of values"""
        with self._i2c:
            self._i2c.write(bytes([register & 0xFF]))
            result = bytearray(length)
            self._i2c.readinto(result)
            return result

    def _write_register_byte(self, register: int, value: int) -> None:
        """Low level register writing over I2C, writes one 8-bit value"""
        with self._i2c:
            self._i2c.write(bytes([register & 0xFF, value & 0xFF]))
