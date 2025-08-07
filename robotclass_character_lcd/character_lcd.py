# SPDX-FileCopyrightText: 2025 Oleg Evsegneev for RobotClass
#
# SPDX-License-Identifier: MIT

# Драйвер для дисплеев LCD1602/2004 с параллельным интерфейсом
"""
`character_lcd`
====================================================

Драйвер для монохромных символьных дисплеев LCD1602/2004 с параллельным интерфейсом

Исходный код
https://github.com/robotclass/Circuitpython

**Пример**
lcd_columns = 16
lcd_rows = 2

lcd_rs = digitalio.DigitalInOut(board.D7)
lcd_en = digitalio.DigitalInOut(board.D8)
lcd_d7 = digitalio.DigitalInOut(board.D12)
lcd_d6 = digitalio.DigitalInOut(board.D11)
lcd_d5 = digitalio.DigitalInOut(board.D10)
lcd_d4 = digitalio.DigitalInOut(board.D9)
lcd_backlight = digitalio.DigitalInOut(board.D13)

lcd = RobotClass_LCD_Mono(
    lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows, lcd_backlight
)
lcd.message = "Как дела?"

Реализация
--------------------

**Аппаратная часть:**

* `Дисплей ЖК 16х2 (1602A) с кириллицей, RobotClass
  <https://shop.robotclass.ru/item/2713>
  <https://shop.robotclass.ru/item/3911>
  <https://shop.robotclass.ru/item/3886>`_

**Зависимости:**

* Библиотека Adafruit CircuitPython CharLCD: https://github.com/adafruit/Adafruit_CircuitPython_CharLCD
"""
import digitalio

from adafruit_character_lcd.character_lcd import Character_LCD

_LCD_ENTRYLEFT = const(0x02)

def utf8rus(source: int) -> int:
    """
    Преобразует байты utf-8 в байты для cp1251.
    
    Args:
        source: байты в utf-8
        
    Returns:
        байты в cp1251
    """
    target = []
    i = 0
    k = len(source)
    
    while i < k:
        n = source[i]
        i += 1
        
        if n >= 0xC0:
            if n == 0xD0:
                if i < k:
                    next_char = source[i]
                    i += 1
                    if next_char == 0x81:  # Ё
                        n = 0xA8
                    elif 0x90 <= next_char <= 0xBF:  # А-я (кроме Ё)
                        n = next_char + 0x30
            elif n == 0xD1:
                if i < k:
                    next_char = source[i]
                    i += 1
                    if next_char == 0x91:  # ё
                        n = 0xB8
                    elif 0x80 <= next_char <= 0x8F:  # а-п (кроме ё)
                        n = next_char + 0x70
        
        target.append(n)
    
    return target

def getCharCyr(ch: int) -> int:
    """
    Преобразует символ кириллицы в соответствующий код для дисплея.
    
    Args:
        ch: Код символа в кодировке исходного текста (0x00-0xFF)
        
    Returns:
        Преобразованный код символа для дисплея
    """
    conversion_map = {
        # Первый блок (0xC0-0xCF)
        0xC0: 0x41, 0xC1: 0xA0, 0xC2: 0x42, 0xC3: 0xA1,
        0xC4: 0xE0, 0xC5: 0x45, 0xC6: 0xA3, 0xC7: 0xA4,
        0xC8: 0xA5, 0xC9: 0xA6, 0xCA: 0x4B, 0xCB: 0xA7,
        0xCC: 0x4D, 0xCD: 0x48, 0xCE: 0x4F, 0xCF: 0xA8,
        
        # Второй блок (0xD0-0xDF)
        0xD0: 0x50, 0xD1: 0x43, 0xD2: 0x54, 0xD3: 0xA9,
        0xD4: 0xAA, 0xD5: 0x58, 0xD6: 0xE1, 0xD7: 0xAB,
        0xD8: 0xAC, 0xD9: 0xE2, 0xDA: 0xAD, 0xDB: 0xAE,
        0xDC: 0x62, 0xDD: 0xAF, 0xDE: 0xB0, 0xDF: 0xB1,
        
        # Третий блок (0xE0-0xEF)
        0xE0: 0x61, 0xE1: 0xB2, 0xE2: 0xB3, 0xE3: 0xB4,
        0xE4: 0xE3, 0xE5: 0x65, 0xE6: 0xB6, 0xE7: 0xB7,
        0xE8: 0xB8, 0xE9: 0xB9, 0xEA: 0xBA, 0xEB: 0xBB,
        0xEC: 0xBC, 0xED: 0xBD, 0xEE: 0x6F, 0xEF: 0xBE,
        
        # Четвертый блок (0xF0-0xFF)
        0xF0: 0x70, 0xF1: 0x63, 0xF2: 0xBF, 0xF3: 0x79,
        0xF4: 0xE4, 0xF5: 0x78, 0xF6: 0xE5, 0xF7: 0xC0,
        0xF8: 0xC1, 0xF9: 0xE6, 0xFA: 0xC2, 0xFB: 0xC3,
        0xFC: 0xC4, 0xFD: 0xC5, 0xFE: 0xC6, 0xFF: 0xC7,
        
        # Особые символы
        0xA8: 0xA2, 0xB8: 0xB5
    }
    
    return conversion_map.get(ch, ch)

class Character_LCD_Mono(Character_LCD):
    """Interfaces with monochromatic character LCDs.

    :param ~digitalio.DigitalInOut reset_dio: сброс RST
    :param ~digitalio.DigitalInOut enable_dio: линия EN
    :param ~digitalio.DigitalInOut d4_dio: линия данных 4
    :param ~digitalio.DigitalInOut d5_dio: линия данных 5
    :param ~digitalio.DigitalInOut d6_dio: линия данных 6
    :param ~digitalio.DigitalInOut d7_dio: линия данных 7
    :param int columns: столбцов
    :param int lines: строк
    :param ~digitalio.DigitalInOut backlight_pin: подсветка
    :param bool backlight_inverted: ``False`` инверсия подсветки.

    """

    def __init__(
        self,
        reset_dio: digitalio.DigitalInOut,
        enable_dio: digitalio.DigitalInOut,
        d4_dio: digitalio.DigitalInOut,
        d5_dio: digitalio.DigitalInOut,
        d6_dio: digitalio.DigitalInOut,
        d7_dio: digitalio.DigitalInOut,
        columns: int,
        lines: int,
        backlight_pin: Optional[digitalio.DigitalInOut] = None,
        backlight_inverted: bool = False,
    ):
        # Backlight pin and inversion
        self.backlight_pin = backlight_pin
        self.backlight_inverted = backlight_inverted

        #  Setup backlight
        if backlight_pin is not None:
            self.backlight_pin.direction = digitalio.Direction.OUTPUT
            self.backlight = True
        super().__init__(reset_dio, enable_dio, d4_dio, d5_dio, d6_dio, d7_dio, columns, lines)

    @property
    def backlight(self) -> Optional[bool]:
        return self._backlight_on

    @backlight.setter
    def backlight(self, enable):
        self._backlight_on = enable
        self.backlight_pin.value = enable ^ self.backlight_inverted

    @property
    def message(self) -> Optional[str]:
        return self._message

    @message.setter
    def message(self, message: str):
        cp1251_bytes = utf8rus(message.encode('utf-8'))
        cplcd_bytes = [getCharCyr(b) for b in cp1251_bytes]

        self._message = message

        line = self.row
        initial_character = 0

        for character in cplcd_bytes:
            if initial_character == 0:
                if self.displaymode & _LCD_ENTRYLEFT > 0:
                    col = self.column
                else:
                    col = self.columns - 1 - self.column
                self.cursor_position(col, line)
                initial_character += 1
            if character == ord("\n"):
                line += 1
                if self.displaymode & _LCD_ENTRYLEFT > 0:
                    col = self.column * self._column_align
                elif self._column_align:
                    col = self.column
                else:
                    col = self.columns - 1
                self.cursor_position(col, line)
            else:
                self._write8(character, True)

        self.column, self.row = 0, 0