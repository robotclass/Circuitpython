# SPDX-FileCopyrightText: 2023 Oleg Evsegneev for RobotClass
#
# SPDX-License-Identifier: MIT

# RobotClass LED gauge Omicron-16 CircuitPython Driver
"""
`robotclass_gauge`
====================================================

Драйвер светодиодного индикатора Омикрон-16 от RobotClass

Исходный код
https://github.com/robotclass/Circuitpython

Реализация
--------------------

**Аппаратная часть:**

* `Светодиодный индикатор Омикрон-16
  <https://shop.robotclass.ru/item/3476>`_

**Зависимости:**

* Библиотека Adafruit's Bus Device: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

__version__ = "0.1"

import time

CMD_GET_VERSION = const(0xB0)  # версия прошивки
CMD_GET_SRC = const(0xB1)  # получение источника сигнала
CMD_GET_STATE = const(0xB2)  # получение позиции энкодера 0..15
CMD_SET_MODE = const(0xC0)  # установка режима
CMD_SET_COLOR = const(0xC1)  # установка цвета RGB 0..255,0..255,0..255
CMD_SET_BRIGHTNESS = const(0xC2)  # установка яркости 0..31
CMD_SET_POT_LPF = const(0xC3)  # установка коэффициента ФНЧ для потенциометра 1..15
CMD_SET_ENC_LIMIT = const(0xC4)  # установка предела энкодера
CMD_SET_ENC_MAX = const(0xC5)  # установка диапазона энкодера
CMD_INIT = const(0xE0)  # инициализация (сброс+обнуление настроек)
CMD_RESET = const(0xE1)  # сброс счётчика
CMD_RUN_TEST = const(0xE2)  # запуск теста

ENC_LIMIT_1 = const(0)
ENC_LIMIT_2 = const(1)
ENC_LIMIT_4 = const(2)
ENC_LIMIT_8 = const(3)
ENC_LIMIT_16 = const(4)
ENC_LIMIT_32 = const(5)
ENC_LIMIT_64 = const(6)

MODE_FLOOD = 0
MODE_LEVEL = 1
MODE_POINT = 2

SRC_ENC = 0
SRC_POT = 1

class RobotClass_LedGauge:
    i2c = None
    source = None

    def __init__(self, i2c: I2C, address: int = 0x30, ) -> None:
        from adafruit_bus_device import (  # pylint: disable=import-outside-toplevel
            i2c_device,
        )
        self._i2c = i2c_device.I2CDevice(i2c, address)
        self._write_register(CMD_INIT, 1)
        self.source = self._read_register(CMD_GET_SRC, 1)[0]

    def test(self):
        self._write_register(CMD_RUN_TEST, 1)

    def reset(self):
        self._write_register(CMD_RESET, 1)

    def getVersion(self):
        data = self._read_register(CMD_GET_VERSION, 1)[0]
        return data

    def getState(self):
        data = self._read_register(CMD_GET_STATE, 3)
        pos = data[0] | (data[1]<<8)

        if self.source == SRC_ENC:
            btn = data[2]
        else:
            btn = None

        return {'position':pos,'button':btn}

    def setMode(self, mode: int):
        self._write_register(CMD_SET_MODE, mode)

    def setColor(self, r: int, g: int, b: int):
        self._write_register_buf(CMD_SET_COLOR, [r, g, b])

    def setBrightness(self, brightness: int):
        if value < 0 or value > 31:
            raise "Bad brightness value"
        self._write_register(CMD_SET_BRIGHTNESS, brightness)

    def setEncLimit(self, value: bool):
        self._write_register(CMD_SET_ENC_LIMIT, value)

    def setEncMax(self, value: int):
        if value < 0 or value > 14:
            raise "Bad encoder max value"
        self._write_register(CMD_SET_ENC_MAX, value)

    def setPotLPF(self, value: int):
        if value < 1 or value > 16:
            raise "Bad potentiometer LPF"
        self._write_register(CMD_SET_POT_LPF, value)

    def _read_register(self, register: int, length: int) -> bytearray:
        """Чтение из шины I2C массива байт"""
        with self._i2c:
            self._i2c.write(bytes([register & 0xFF, 0x00, 0x00, 0x00]))
            result = bytearray(length)
            self._i2c.readinto(result)
        return result

    def _write_register(self, register: int, value: int) -> None:
        """Запись в шину I2C одного байта"""
        with self._i2c:
            self._i2c.write(bytes([register & 0xFF, value & 0xFF, 0x00, 0x00]))
        time.sleep(0.001)

    def _write_register_buf(self, register: int, values: list) -> None:
        """Запись в шину I2C массива байт"""
        buf = [register & 0xFF] + values
        with self._i2c:
            self._i2c.write(bytes(buf))
        time.sleep(0.001)