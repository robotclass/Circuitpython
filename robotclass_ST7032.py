# SPDX-FileCopyrightText: 2024 Oleg Evsegneev for RobotClass
#
# SPDX-License-Identifier: MIT

# RobotClass LED gauge Omicron-16 CircuitPython Driver
"""
`robotclass_ST7032`
====================================================

Драйвер дисплея на микросхеме ST7032

Исходный код
https://github.com/robotclass/Circuitpython

Оригинальный код для micropython
https://github.com/combs/Python-ST7032

**Пример**
from robotclass_ST7032 import RobotClass_ST7032

i2c = board.I2C()
device = RobotClass_ST7032(i2c)

device.setContrast(35)
device.clear()
device.write("Hello World!")
device.setCursor(0,1)
device.write("Goodbye")

Реализация
--------------------

**Аппаратная часть:**

* `FSTN дисплей 1602 ST7032
  <https://shop.robotclass.ru/item/3476>`_

**Зависимости:**

* Библиотека Adafruit's Bus Device: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""

__version__ = "0.1"

import time

ST7032_I2C_DEFAULT_ADDR     = const(0x3E)

# commands
LCD_CLEARDISPLAY        = const(0x01)
LCD_RETURNHOME          = const(0x02)
LCD_ENTRYMODESET        = const(0x04)
LCD_DISPLAYCONTROL      = const(0x08)
LCD_CURSORSHIFT         = const(0x10)
LCD_FUNCTIONSET         = const(0x20)
LCD_SETCGRAMADDR        = const(0x40)
LCD_SETDDRAMADDR        = const(0x80)

LCD_EX_SETBIASOSC       = const(0x10)        # Bias selection / Internal OSC frequency adjust
LCD_EX_SETICONRAMADDR   = const(0x40)        # Set ICON RAM address
LCD_EX_POWICONCONTRASTH = const(0x50)        # Power / ICON control / Contrast set(high byte)
LCD_EX_FOLLOWERCONTROL  = const(0x60)        # Follower control
LCD_EX_CONTRASTSETL     = const(0x70)        # Contrast set(low byte)

# flags for display entry mode
LCD_ENTRYRIGHT          = const(0x00)
LCD_ENTRYLEFT           = const(0x02)
LCD_ENTRYSHIFTINCREMENT = const(0x01)
LCD_ENTRYSHIFTDECREMENT = const(0x00)

# flags for display on/off control
LCD_DISPLAYON           = const(0x04)
LCD_DISPLAYOFF          = const(0x00)
LCD_CURSORON            = const(0x02)
LCD_CURSOROFF           = const(0x00)
LCD_BLINKON             = const(0x01)
LCD_BLINKOFF            = const(0x00)

# flags for display/cursor shift
LCD_DISPLAYMOVE         = const(0x08)
LCD_CURSORMOVE          = const(0x00)
LCD_MOVERIGHT           = const(0x04)
LCD_MOVELEFT            = const(0x00)

# flags for function set
LCD_8BITMODE            = const(0x10)
LCD_4BITMODE            = const(0x00)
LCD_2LINE               = const(0x08)
LCD_1LINE               = const(0x00)
LCD_5x10DOTS            = const(0x04)
LCD_5x8DOTS             = const(0x00)
LCD_EX_INSTRUCTION      = const(0x01)        # IS: instruction table select

# flags for Bias selection
LCD_BIAS_1_4            = const(0x08)        # bias will be 1/4
LCD_BIAS_1_5            = const(0x00)        # bias will be 1/5

# flags Power / ICON control / Contrast set(high byte)
LCD_ICON_ON             = const(0x08)        # ICON display on
LCD_ICON_OFF            = const(0x00)        # ICON display off
LCD_BOOST_ON            = const(0x04)        # booster circuit is turn on
LCD_BOOST_OFF           = const(0x00)        # booster circuit is turn off
LCD_OSC_122HZ           = const(0x00)        # 122Hz@3.0V
LCD_OSC_131HZ           = const(0x01)        # 131Hz@3.0V
LCD_OSC_144HZ           = const(0x02)        # 144Hz@3.0V
LCD_OSC_161HZ           = const(0x03)        # 161Hz@3.0V
LCD_OSC_183HZ           = const(0x04)        # 183Hz@3.0V
LCD_OSC_221HZ           = const(0x05)        # 221Hz@3.0V
LCD_OSC_274HZ           = const(0x06)        # 274Hz@3.0V
LCD_OSC_347HZ           = const(0x07)        # 347Hz@3.0V

# flags Follower control
LCD_FOLLOWER_ON         = const(0x08)        # internal follower circuit is turn on
LCD_FOLLOWER_OFF        = const(0x00)        # internal follower circuit is turn off
LCD_RAB_1_00            = const(0x00)        # 1+(Rb/Ra)=1.00
LCD_RAB_1_25            = const(0x01)        # 1+(Rb/Ra)=1.25
LCD_RAB_1_50            = const(0x02)        # 1+(Rb/Ra)=1.50
LCD_RAB_1_80            = const(0x03)        # 1+(Rb/Ra)=1.80
LCD_RAB_2_00            = const(0x04)        # 1+(Rb/Ra)=2.00
LCD_RAB_2_50            = const(0x05)        # 1+(Rb/Ra)=2.50
LCD_RAB_3_00            = const(0x06)        # 1+(Rb/Ra)=3.00
LCD_RAB_3_75            = const(0x07)        # 1+(Rb/Ra)=3.75

class RobotClass_ST7032:

    busnum = 0
    _displaycontrol = 0
    _displaymode = 0
    _displayfunction = 0
    lines = 2
    dotsize=0
    _numlines = 1
    _currline = 0


    def __del__(self):
        # self.smbus.close()
        pass

    def __init__(self, i2c: I2C, address: int = ST7032_I2C_DEFAULT_ADDR) -> None:
        from adafruit_bus_device import (  # pylint: disable=import-outside-toplevel
            i2c_device,
        )
        self._i2c = i2c_device.I2CDevice(i2c, address)

        self._displayfunction  = LCD_8BITMODE | LCD_1LINE | LCD_5x8DOTS

        if (self.lines > 1) :
            self._displayfunction |= LCD_2LINE

        self._numlines = self.lines
        self._currline = 0
        # for some 1 line displays you can select a 10 pixel high font
        if ((self.dotsize != 0) and (self.lines == 1)) :
            self._displayfunction |= LCD_5x10DOTS

        # finally, set # lines, font size, etc.
        self.normalFunctionSet()

        self.extendFunctionSet()
        self.command(LCD_EX_SETBIASOSC | LCD_BIAS_1_4 | LCD_OSC_347HZ)          # 1/5bias, OSC=183Hz@3.0V
        self.command(LCD_EX_FOLLOWERCONTROL | LCD_FOLLOWER_ON | LCD_RAB_2_00)     # internal follower circuit is turn on
        time.sleep(0.2)                                 # Wait time >200ms (for power stable)
        self.normalFunctionSet()

        # turn the display on with no cursor or blinking default
        #  display()
        self._displaycontrol  = 0x00 #LCD_DISPLAYON | LCD_CURSOROFF | LCD_BLINKOFF
        self.setDisplayControl(LCD_DISPLAYON | LCD_CURSOROFF | LCD_BLINKOFF)

        # self.clear it off
        self.clear()

        # Initialize to default text direction (for romance languages)
        #  self.command(LCD_ENTRYMODESET | self._displaymode)
        self._displaymode      = 0x00#LCD_ENTRYLEFT | LCD_ENTRYSHIFTDECREMENT
        self.setEntryMode(LCD_ENTRYLEFT | LCD_ENTRYSHIFTDECREMENT)

    def setDisplayControl(self,setBit) :
        self._displaycontrol |= setBit
        self.command(LCD_DISPLAYCONTROL | self._displaycontrol)


    def resetDisplayControl(self,resetBit) :
        self._displaycontrol &= ~resetBit
        self.command(LCD_DISPLAYCONTROL | self._displaycontrol)


    def setEntryMode(self,setBit) :
        self._displaymode |= setBit
        self.command(LCD_ENTRYMODESET | self._displaymode)


    def resetEntryMode(self,resetBit) :
        self._displaymode &= ~resetBit
        self.command(LCD_ENTRYMODESET | self._displaymode)


    def normalFunctionSet(self) :
        self.command(LCD_FUNCTIONSET | self._displayfunction)


    def extendFunctionSet(self) :
        self.command(LCD_FUNCTIONSET | self._displayfunction | LCD_EX_INSTRUCTION)

    def setContrast(self,cont):
        self.extendFunctionSet()
        self.command(LCD_EX_CONTRASTSETL | (cont & 0x0f))                 # Contrast set
        self.command(LCD_EX_POWICONCONTRASTH | LCD_ICON_ON | LCD_BOOST_ON | ((cont >> 4) & 0x03)) # Power, ICON, Contrast control
        self.normalFunctionSet()

    def setIcon(self,addr, bit) :
        self.extendFunctionSet()
        self.command(LCD_EX_SETICONRAMADDR | (addr & 0x0f))                   # ICON address
        write(bit)
        self.normalFunctionSet()

    # /********** high level commands, for the user! */
    def clear(self):
        self.command(LCD_CLEARDISPLAY)  # self.clear display, set cursor position to zero
        time.sleep(0.002)  # this command takes a long time!

    def home(self):
        self.command(LCD_RETURNHOME)  # set cursor position to zero
        time.sleep(0.002)  # this command takes a long time!

    def setCursor(self,col,row):
        row_offsets = [ 0x00, 0x40, 0x14, 0x54 ]

        if ( row > self._numlines ) :
            row = self._numlines-1    # we count rows starting w/0


        self.command(LCD_SETDDRAMADDR | (col + row_offsets[row]))


    # Turn the display on/off (quickly)
    def noDisplay(self) :
        self.resetDisplayControl(LCD_DISPLAYON)

    def display(self) :
        self.setDisplayControl(LCD_DISPLAYON)


    # Turns the underline cursor on/off
    def noCursor(self) :
        self.resetDisplayControl(LCD_CURSORON)

    def cursor(self) :
        self.setDisplayControl(LCD_CURSORON)


    # Turn on and off the blinking cursor
    def noBlink(self) :
        self.resetDisplayControl(LCD_BLINKON)

    def blink(self) :
        self.setDisplayControl(LCD_BLINKON)


    # These commands scroll the display without changing the RAM
    def scrollDisplayLeft(self) :
        self.command(LCD_CURSORSHIFT | LCD_DISPLAYMOVE | LCD_MOVELEFT)


    def scrollDisplayRight(self) :
        self.command(LCD_CURSORSHIFT | LCD_DISPLAYMOVE | LCD_MOVERIGHT)


    # This is for text that flows Left to Right
    def leftToRight(self) :
        self.setEntryMode(LCD_ENTRYLEFT)


    # This is for text that flows Right to Left
    def rightToLeft(self) :
        self.resetEntryMode(LCD_ENTRYLEFT)


    # This will 'right justify' text from the cursor
    def autoscroll(self) :
        self.setEntryMode(LCD_ENTRYSHIFTINCREMENT)


    # This will 'left justify' text from the cursor
    def noAutoscroll(self) :
        self.resetEntryMode(LCD_ENTRYSHIFTINCREMENT)


    # Allows us to fill the first 8 CGRAM locations
    # with custom characters
    def createChar(self,location, charmap) :
        location &= 0x7 # we only have 8 locations 0-7
        self.command(LCD_SETCGRAMADDR | (location << 3))
        for i in range(0,7):
            self.writeData(charmap[i])



    # /*********** mid level commands, for sending data/cmds */

    def command(self, value) :
        with self._i2c:
            self._i2c.write(bytes([0x00, value & 0xFF]))
            
    def writeData(self, value) :
        with self._i2c:
            self._i2c.write(bytes([0x40, value & 0xFF]))

    def write(self, value):
        for character in value:
            self.writeData(ord(character))

    def println(self, value):
        for character in value:
            self.writeData(ord(character))
        self.writeData(0)