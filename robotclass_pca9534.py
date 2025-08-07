# SPDX-FileCopyrightText: 2025 Oleg Evsegneev for RobotClass
#
# SPDX-License-Identifier: MIT

# RobotClass PCA9534 CircuitPython Driver
"""
`robotclass_pca9534`
====================================================

Драйвер символьного расширителя GPIO PCA9534

Исходный код
https://github.com/robotclass/Circuitpython

**Пример**
i2c = board.I2C()
pca = PCA9534(i2c)

# вывод всего регистра
out = pca.output
print(f"output {out:b}")

# смена состояния 1-го контакта
pca.channels[1].value = 1

# смена направления для 1-го контакта
pca.channels[1].direction = Direction.INPUT

# вывод состояния 1-го контакта в цикле
while True:
    print(pca.channels[1].value)
    time.sleep(0.1)

Реализация
--------------------

**Аппаратная часть:**

* `Расширитель GPIO 8-канальный, QIIC, RobotClass
  <https://shop.robotclass.ru/item/4088>`_

**Зависимости:**

* Библиотека Adafruit's Bus Device: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

from digitalio import Direction
from adafruit_bus_device import i2c_device

# адрес PCA9534
_PCA9534_ADDRESS = 0x3F

# регистры PCA9536
_PCA9534_REGISTER_INPUT_PORT = 0x00
_PCA9534_REGISTER_OUTPUT_PORT = 0x01
_PCA9534_REGISTER_POLARITY_INVERSION = 0x02
_PCA9534_REGISTER_CONFIGURATION = 0x03
_PCA9534_REGISTER_INVALID = 0x04

# PCA9536 has eight GPIO pins: 0-7
_PCA9536_MAX_GPIO = 7

class PCAChannel:
    _mode = Direction.OUTPUT
    _inverted = False
    _pca = None
    _index = 0

    def __init__(self, pca: "PCA9534", index: int):
        self._pca = pca
        self._index = index
        
        self.direction = Direction.OUTPUT

    @property
    def inverted(self):
        return self._inverted

    @inverted.setter
    def inverted(self, inverted: int) -> None:
        self._inverted = inverted
        
        invertRegister = self._pca._read_register_byte(_PCA9534_REGISTER_POLARITY_INVERSION)

        # TODO: Break out of here if it's already set correctly
        invertRegister &= ~(1 << self._index)  # Clear pin bit
        if(inverted):  # Set the bit if it's being set to inverted
            invertRegister |= (1 << self._index)

        self._pca._write_register_byte(_PCA9534_REGISTER_POLARITY_INVERSION, invertRegister)

    @property
    def direction(self):
        return self._mode

    @direction.setter
    def direction(self, mode: int) -> None:
        self._mode = mode

        cfgRegister = self._pca._read_register_byte(_PCA9534_REGISTER_CONFIGURATION)

        cfgRegister &= ~(1 << self._index)  # убираем бит
        if(mode == Direction.INPUT):
            cfgRegister |= (1 << self._index)
            
        self._pca._write_register_byte(_PCA9534_REGISTER_CONFIGURATION, cfgRegister)

    def read(self) -> None:
        if self._mode == Direction.INPUT:
            inputRegister = self._pca._read_register_byte(_PCA9534_REGISTER_INPUT_PORT)
            return (inputRegister & (1 << self._index)) >> self._index
        else:
            outputRegister = self._pca._read_register_byte(_PCA9534_REGISTER_OUTPUT_PORT)
            return (outputRegister & (1 << self._index)) >> self._index

    def write(self, value):
        outputRegister = self._pca._read_register_byte(_PCA9534_REGISTER_OUTPUT_PORT)

        # TODO: Break out of here if it's already set correctly
        outputRegister &= ~(1 << self._index)  # Clear pin bit
        if(value == True):  # Set the bit if it's being set to HIGH (opposite of Arduino)
            outputRegister |= (1 << self._index)

        self._pca._write_register_byte(_PCA9534_REGISTER_OUTPUT_PORT, outputRegister)
        
    value = property(read, write)
    
class PCAChannels:
    def __init__(self, pca: "PCA9534") -> None:
        self._pca = pca
        self._channels = [None] * len(self)

    def __len__(self) -> int:
        return 8

    def __getitem__(self, index: int) -> PCAChannel:
        if not self._channels[index]:
            self._channels[index] = PCAChannel(self._pca, index)
        return self._channels[index]
        
class PCA9534:
    _i2c = None

    def __init__(self, i2c: I2C, address: int = _PCA9534_ADDRESS):
        self._i2c = i2c_device.I2CDevice(i2c, address)

        self.channels = PCAChannels(self)

    @property
    def inv(self) -> int:
        """ Регистр инверсии в исходном виде. Каждый бит отвечает
        за инверсию отдельного контакта. Если инвертирован - 1, если нет - 9.
        """
        return self._read_register_byte(_PCA9534_REGISTER_POLARITY_INVERSION)

    @inv.setter
    def inv(self, val: int) -> None:
        for i,ch in enumerate(self.channels):
            ch.inverted = (val & (1<<i)) >> i

        self._write_register_byte(_PCA9534_REGISTER_POLARITY_INVERSION, val)

    @property
    def dir(self) -> int:
        """ Регистр направления в исходном виде. Каждый бит отвечает
        за направление отдельного контакта. Если вход - 1, если выход - 9.
        """
        return self._read_register_byte(_PCA9534_REGISTER_CONFIGURATION)

    @dir.setter
    def dir(self, val: int) -> None:
        for i,ch in enumerate(self.channels):
            x = (val & (1<<i))
            ch.direction = (val & (1<<i)) and Direction.INPUT or Direction.OUTPUT

        self._write_register_byte(_PCA9534_REGISTER_CONFIGURATION, val)

    @property
    def output(self) -> int:
        """ Регистр состояния выхода (OUTPUT) в исходном виде. Каждый бит отвечает
        за состояние отдельного контакта.
        """
        return self._read_register_byte(_PCA9534_REGISTER_OUTPUT_PORT)

    @output.setter
    def output(self, val: int) -> None:
        self._write_register_byte(_PCA9534_REGISTER_OUTPUT_PORT, val)

    @property
    def input(self) -> int:
        """ Регистр состояния входа (INPUT) в исходном виде. Каждый бит отвечает
        за состояние отдельного контакта.
        """
        return self._read_register_byte(_PCA9534_REGISTER_INPUT_PORT)

    @input.setter
    def input(self, val: int) -> None:
        self._write_register_byte(_PCA9534_REGISTER_INPUT_PORT, val)

    def _read_register(self, register, length):
        with self._i2c as i2c:
            i2c.write(bytes([register & 0xFF]))
            buffer = bytearray(length)
            i2c.readinto(buffer)
            return buffer

    def _read_register_byte(self, register):
        return self._read_register(register, 1)[0]

    def _write_register_byte(self, register, value):
        buffer = bytearray(2)
        buffer[0] = register & 0xFF
        buffer[1] = value & 0xFF
        with self._i2c as i2c:
            i2c.write(buffer)