# SPDX-FileCopyrightText: 2024 Oleg Evsegneev for RobotClass
#
# SPDX-License-Identifier: MIT

# RobotClass CircuitPython driver for keyboard switch matrix
"""
`robotclass_keypad`
====================================================

Драйвер клавиатуры МехМод 3X4 от RobotClass

Исходный код
https://github.com/robotclass/Circuitpython

Реализация
--------------------

**Аппаратная часть:**

* `Модуль моторикс
  <https://shop.robotclass.ru/item/3954>`_

**Зависимости:**

* Библиотека Adafruit's Bus Device: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

__version__ = "0.1"

_REGISTER_GET_STATE = const(0xA0)
_REGISTER_SET_LED = const(0xB0)

class RobotClass_KeyPad:
    i2c = None

    # address - адрес в шине I2C
    # cols - число колонок
    # rows - число строк
    def __init__(self, i2c: I2C, address: int = 0x22, cols: int = 3, rows: int = 4) -> None:
        from adafruit_bus_device import (  # pylint: disable=import-outside-toplevel
            i2c_device,
        )
        self.rows = rows
        self.cols = cols
        self._i2c = i2c_device.I2CDevice(i2c, address)

    # получение состояния клавиш
    # результат: двухбайтное целое, где биты - состояния клавиш
    def getStateRaw(self):
        data = self._read_register(_REGISTER_GET_STATE, 2);
        v = data[0] | (data[1]<<8)
        return v

    # получение состояния клавиш
    # результат: список пар координат x,y
    def getState(self):
        data = self._read_register(_REGISTER_GET_STATE, 2);
        v = data[0] | (data[1]<<8)
        
        state = []
        b = 0
        for y in range(self.rows):
            for x in range(self.cols):
                if v & (1<<b): # если b-й бит включён
                    state.append([x,y])
                b += 1

        return state

    # изменение состояния встроенного светодиода
    # state - состояние: 0,1
    def setLed(self, state: int):
        self._write_register_byte(_REGISTER_SET_LED, state)

    def _read_register(self, register: int, length: int) -> bytearray:
        """Low level register reading over I2C, returns a list of values"""
        with self._i2c:
            self._i2c.write(bytes([register & 0xFF, 0x00, 0x00]))
            time.sleep(0.001)
            result = bytearray(length)
            self._i2c.readinto(result)
            return result

    def _write_register_byte(self, register: int, value: int) -> None:
        """Low level register writing over I2C, writes one 8-bit value"""
        with self._i2c:
            self._i2c.write(bytes([register & 0xFF, value & 0xFF, 0x00]))
