from digitalio import Direction
from adafruit_bus_device import i2c_device

# адрес PCA9536
_PCA9536_ADDRESS = 0x41

# регистры PCA9536
_PCA9536_REGISTER_INPUT_PORT = 0x00
_PCA9536_REGISTER_OUTPUT_PORT = 0x01
_PCA9536_REGISTER_POLARITY_INVERSION = 0x02
_PCA9536_REGISTER_CONFIGURATION = 0x03
_PCA9536_REGISTER_INVALID = 0x04

# PCA9536 has four GPIO pins: 0-3
_PCA9536_MAX_GPIO = 3

class PCAChannel:
    _mode = Direction.OUTPUT
    _inverted = False
    _pca = None
    _index = 0

    def __init__(self, pca: "PCA9536", index: int):
        self._pca = pca
        self._index = index
        
        self.direction = Direction.OUTPUT

    @property
    def inverted(self):
        return self._inverted

    @inverted.setter
    def inverted(self, inverted: int) -> None:
        self._inverted = inverted
        
        invertRegister = self._pca._read_register_byte(_PCA9536_REGISTER_POLARITY_INVERSION)

        # TODO: Break out of here if it's already set correctly
        invertRegister &= ~(1 << pin)  # Clear pin bit
        if(inverted):  # Set the bit if it's being set to inverted
            invertRegister |= (1 << pin)

        self._pca._write_register_byte(_PCA9536_REGISTER_POLARITY_INVERSION, invertRegister)

    @property
    def direction(self):
        return self._mode

    @direction.setter
    def direction(self, mode: int) -> None:
        self._mode = mode

        cfgRegister = self._pca._read_register_byte(_PCA9536_REGISTER_CONFIGURATION)

        cfgRegister &= ~(1 << self._index)  # убираем бит
        if(mode == Direction.INPUT):
            cfgRegister |= (1 << self._index)
            
        self._pca._write_register_byte(_PCA9536_REGISTER_CONFIGURATION, cfgRegister)

    def read(self, value) -> None:
        inputRegister = self._pca._read_register_byte(_PCA9536_REGISTER_INPUT_PORT)

        return (inputRegister & (1 << self._index)) >> self._index

    def write(self, value):
        outputRegister = self._pca._read_register_byte(_PCA9536_REGISTER_OUTPUT_PORT)

        # TODO: Break out of here if it's already set correctly
        outputRegister &= ~(1 << self._index)  # Clear pin bit
        if(value == True):  # Set the bit if it's being set to HIGH (opposite of Arduino)
            outputRegister |= (1 << self._index)

        self._pca._write_register_byte(_PCA9536_REGISTER_OUTPUT_PORT, outputRegister)
        
    value = property(read, write)
    
class PCAChannels:
    def __init__(self, pca: "PCA9536") -> None:
        self._pca = pca
        self._channels = [None] * len(self)

    def __len__(self) -> int:
        return 4

    def __getitem__(self, index: int) -> PCAChannel:
        if not self._channels[index]:
            self._channels[index] = PCAChannel(self._pca, index)
        return self._channels[index]
        
class PCA9536:
    _i2c = None

    def __init__(self, i2c: I2C, address: int = _PCA9536_ADDRESS):
        self._i2c = i2c_device.I2CDevice(i2c, address)

        self.channels = PCAChannels(self)

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