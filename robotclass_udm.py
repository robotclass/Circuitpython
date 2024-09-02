# SPDX-FileCopyrightText: 2024 Oleg Evsegneev for RobotClass
#
# SPDX-License-Identifier: MIT

# RobotClass Ultrasonic ranger CircuitPython Driver
"""
`robotclass_udm`
====================================================

Драйвер ультразвукового дальномер УДМ40 от RobotClass

Исходный код
https://github.com/robotclass/Circuitpython

**Пример**
i2c = board.I2C()
sonic = RobotClass_UDM(i2c)

while True:
    data = sonic.getDistance()
    print("dist = %d" % data)
    time.sleep(0.1)

Реализация
--------------------

**Аппаратная часть:**

* `Ультразвуковой дальномер УДМ
  <https://shop.robotclass.ru/item/3851>`_

**Зависимости:**

* Библиотека Adafruit's Bus Device: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

__version__ = "0.1"

import time

_REGISTER_GET_SENSOR = const(0xB0)
_REGISTER_GET_VERSION = const(0xB1)
_REGISTER_SET_FILTER = const(0xC0)

class RobotClass_UDM:
    i2c = None

    def __init__(self, i2c: I2C, address: int = 0x34) -> None:
        from adafruit_bus_device import (  # pylint: disable=import-outside-toplevel
            i2c_device,
        )
        self._i2c = i2c_device.I2CDevice(i2c, address)

    def getDistance(self):
        data = self._read_register(_REGISTER_GET_SENSOR, 2);
        v = data[0] | (data[1]<<8)
        return  v

    def getVersion(self):
        data = self._read_register(_REGISTER_GET_VERSION, 2);
        v = data[0]
        return  v

    def filterSet(self):
        self._write_register_byte(_REGISTER_SET_FILTER, 1)

    def filterUnset(self, state: int):
        self._write_register_byte(_REGISTER_SET_FILTER, 0)

    def _read_register(self, register: int, length: int) -> bytearray:
        """Low level register reading over I2C, returns a list of values"""
        with self._i2c:
            self._i2c.write(bytes([register & 0xFF]))
            time.sleep(0.001)
            result = bytearray(length)
            self._i2c.readinto(result)
            return result

    def _write_register_byte(self, register: int, value: int) -> None:
        """Low level register writing over I2C, writes one 8-bit value"""
        with self._i2c:
            self._i2c.write(bytes([register & 0xFF, value & 0xFF]))
