# SPDX-FileCopyrightText: 2023 Oleg Evsegneev for RobotClass
#
# SPDX-License-Identifier: MIT

# RobotClass Photon display CircuitPython Driver
"""
`robotclass_photon`
====================================================

Драйвер дисплея Фотон от RobotClass

Исходный код
https://github.com/robotclass/Circuitpython

Реализация
--------------------

**Аппаратная часть:**

* `Дисплей Фотон
  <https://shop.robotclass.ru/item/3441>`_

**Зависимости:**

* Библиотека Adafruit's Bus Device: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

__version__ = "0.2"

import struct

CMD_RESET = const(0xF0)

CMD_ACK = const(0xA0)
CMD_EVENT_PUSH = const(0xA1)
CMD_EVENT_POP = const(0xA2)
CMD_PAGE = const(0xA3)
CMD_VERSION = const(0xA4)
CMD_ERR_PAGE_N = const(0xB0)
CMD_ERR_ITEM_N = const(0xB1)
CMD_SET_INT = const(0xC0)
CMD_SET_FLOAT = const(0xC1)
CMD_SET_STR = const(0xC2)
CMD_SET_PAGE = const(0xC3)
CMD_GET_VERSION = const(0xD0)
CMD_GET_PAGE = const(0xD1)


class RobotClass_Photon:
    def __init__(self, i2c: I2C, address: int = 0x25) -> None:
        from adafruit_bus_device import (  # pylint: disable=import-outside-toplevel
            i2c_device,
        )

        self._i2c = i2c_device.I2CDevice(i2c, address)

    def setValue(self, idx: int, v, width: int = 4, precision: int = 2):
        if isinstance(v, int):
            buf = v.to_bytes(4, "little", signed=True)
            with self._i2c as i2c:
                i2c.write(bytes([CMD_SET_INT, idx]) + buf)
        elif isinstance(v, float):
            buf = bytearray(struct.pack("f", v))
            with self._i2c as i2c:
                i2c.write(bytes([CMD_SET_FLOAT, idx, width, precision]) + buf)
        elif isinstance(v, str):
            buf = bytes(v, "UTF-8")
            with self._i2c as i2c:
                i2c.write(bytes([CMD_SET_STR, idx]) + buf)

    def setPage(self, idx: int):
        with self._i2c as i2c:
            i2c.write(bytes([CMD_SET_PAGE, idx]))

    def getVersion(self) -> int:
        with self._i2c as i2c:
            i2c.write(bytes([CMD_GET_VERSION]))
            buffer = bytearray(2)
            i2c.readinto(buffer)
        return buffer[0] | (buffer[1]<<8)

    def getPage(self) -> int:
        with self._i2c as i2c:
            i2c.write(bytes([CMD_GET_PAGE]))
            buffer = bytearray(2)
            i2c.readinto(buffer)
        return buffer[0] | (buffer[1]<<8)

    def reset(self):
        with self._i2c as i2c:
            i2c.write(bytes([CMD_RESET]))