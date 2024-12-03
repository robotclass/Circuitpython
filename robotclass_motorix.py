# SPDX-FileCopyrightText: 2023 Oleg Evsegneev for RobotClass
#
# SPDX-License-Identifier: MIT

# RobotClass Motorix CircuitPython Driver
"""
`robotclass_motorix`
====================================================

Драйвер модуля Моторикс от RobotClass

Исходный код
https://github.com/robotclass/Circuitpython

Реализация
--------------------

**Аппаратная часть:**

* `Модуль моторикс
  <https://shop.robotclass.ru/item/3953>`_

**Зависимости:**

* Библиотека Adafruit's Bus Device: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

__version__ = "0.1"

FREQ = 8000000

MOTOR_A = const(0)
MOTOR_B = const(1)

CMD_CONFIG = const(0xA0)
CMD_SET_DIR = const(0xA5)
CMD_SET_PWM = const(0xA6)
CMD_SET_LED = const(0xA7)

class RobotClass_Motorix:
    def __init__(self, i2c: I2C, address: int = 0x50) -> None:
        from adafruit_bus_device import (  # pylint: disable=import-outside-toplevel
            i2c_device,
        )

        self._i2c = i2c_device.I2CDevice(i2c, address)

    # настройка ШИМ
    # freq - частота
    # res - разрешение как степени двойки: 1..16
    def configPwm(self, freq: int, res: int):
        if freq * res > FREQ:
            raise "Bad config"
        with self._i2c as i2c:
            i2c.write(bytes([CMD_CONFIG, freq & 0xFF, (freq >> 8) & 0xFF, res]))

    # вращение
    # motor - индекс мотора: 0,1
    # pwm - коэфф. заполнения от 0 до разрешения
    def setPwm(self, motor: int, pwm: int):
        with self._i2c as i2c:
            i2c.write(bytes([CMD_SET_PWM, motor, pwm & 0xFF, (pwm >> 8) & 0xFF]))


    # направление вращения
    # motor - индекс мотора: 0,1
    # in1, in2 - биты состояния мотора в стандартной схеме IN1/IN2
    def setDir(self, motor: int, in1: int, in2: int):
        v = 0
        if in1:
            v = 0b01
        if in2:
            v = 0b10
        with self._i2c as i2c:
            i2c.write(bytes([CMD_SET_DIR, motor, v, 0x00]))

    # изменение состояния встроенного светодиода
    # state - состояние: 0,1
    def setLed(self, mode: int):
        with self._i2c as i2c:
            i2c.write(bytes([CMD_SET_LED, mode, 0x00, 0x00]))
