# SPDX-FileCopyrightText: 2026 Oleg Evsegneev for RobotClass
#
# SPDX-License-Identifier: MIT

# RobotClass QTR optical sensor CircuitPython driver
"""
`robotclass_qtr`
====================================================

Драйвер датчиков отражения QTR от RobotClass

Исходный код
https://github.com/robotclass/Circuitpython

Реализация
--------------------

**Аппаратная часть:**

* `Датчик отражения QTR11
  <https://shop.robotclass.ru/item/4331>`_
"""

__version__ = "0.1"

import time
import board
import digitalio
import analogio
import microcontroller

# --- Enums as simple constants ---

# QTRReadMode
OFF = 0
ON = 1
ON_AND_OFF = 2
ODD_EVEN = 3
ODD_EVEN_AND_OFF = 4
MANUAL = 5

# QTRType
UNDEFINED = 0
RC = 1
ANALOG = 2

# QTREmitters
ALL = 0
ODD = 1
EVEN = 2
NONE = 3

QTR_NO_EMITTER_PIN = 255
QTR_RC_DEFAULT_TIMEOUT = 2500       # microseconds
QTR_MAX_SENSORS = 31


class CalibrationData:
    __slots__ = ("initialized", "minimum", "maximum")
    def __init__(self):
        self.initialized = False
        self.minimum = None
        self.maximum = None


class QTRSensors:
    def __init__(self):
        self._type = UNDEFINED
        self._sensor_pins = []          # list of microcontroller.Pin
        self._sensor_pins_io = []       # list of DigitalInOut objects (RC mode)
        self._sensor_pins_analog = []   # list of AnalogIn objects (Analog mode)
        self._sensor_count = 0

        self._timeout = QTR_RC_DEFAULT_TIMEOUT
        self._max_value = QTR_RC_DEFAULT_TIMEOUT
        self._samples_per_sensor = 4

        self._odd_emitter_pin = None
        self._even_emitter_pin = None
        self._odd_emitter_io = None
        self._even_emitter_io = None
        self._emitter_pin_count = 0

        self._dimmable = True
        self._dimming_level = 0

        self._last_position = 0

        self.calibration_on = CalibrationData()
        self.calibration_off = CalibrationData()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def set_type_rc(self):
        self._type = RC
        self._max_value = self._timeout

    def set_type_analog(self):
        self._type = ANALOG
        self._max_value = 65535  # CircuitPython analogin is 16-bit

    def get_type(self):
        return self._type

    def get_size(self):
        return self._sensor_count

    def set_sensor_pins(self, pins, sensor_count=None):
        """pins: list of microcontroller.Pin (or a tuple)."""
        if sensor_count is None:
            sensor_count = len(pins)
        if sensor_count > QTR_MAX_SENSORS:
            sensor_count = QTR_MAX_SENSORS

        self._sensor_pins = list(pins[:sensor_count])
        self._sensor_count = sensor_count

        # Pre-build IO objects for RC mode (DigitalInOut) and Analog mode.
        self._sensor_pins_io = []
        self._sensor_pins_analog = []

        if self._type == RC:
            for p in self._sensor_pins:
                dio = digitalio.DigitalInOut(p)
                dio.direction = digitalio.Direction.INPUT
                dio.pull = None
                self._sensor_pins_io.append(dio)
        elif self._type == ANALOG:
            for p in self._sensor_pins:
                self._sensor_pins_analog.append(analogio.AnalogIn(p))

        # Invalidate calibration
        self.calibration_on.initialized = False
        self.calibration_off.initialized = False

    def set_timeout(self, timeout):
        if timeout > 32767:
            timeout = 32767
        self._timeout = timeout
        if self._type == RC:
            self._max_value = timeout

    def get_timeout(self):
        return self._timeout

    def set_samples_per_sensor(self, samples):
        if samples > 64:
            samples = 64
        self._samples_per_sensor = samples

    def get_samples_per_sensor(self):
        return self._samples_per_sensor

    # ------------------------------------------------------------------
    # Emitter control
    # ------------------------------------------------------------------

    def set_emitter_pin(self, emitter_pin):
        self.release_emitter_pins()
        self._odd_emitter_pin = emitter_pin
        dio = digitalio.DigitalInOut(emitter_pin)
        dio.direction = digitalio.Direction.OUTPUT
        dio.value = False
        self._odd_emitter_io = dio
        self._emitter_pin_count = 1

    def set_emitter_pins(self, odd_emitter_pin, even_emitter_pin):
        self.release_emitter_pins()
        self._odd_emitter_pin = odd_emitter_pin
        self._even_emitter_pin = even_emitter_pin

        dio_odd = digitalio.DigitalInOut(odd_emitter_pin)
        dio_odd.direction = digitalio.Direction.OUTPUT
        dio_odd.value = False
        self._odd_emitter_io = dio_odd

        dio_even = digitalio.DigitalInOut(even_emitter_pin)
        dio_even.direction = digitalio.Direction.OUTPUT
        dio_even.value = False
        self._even_emitter_io = dio_even

        self._emitter_pin_count = 2

    def release_emitter_pins(self):
        if self._odd_emitter_io is not None:
            try:
                self._odd_emitter_io.deinit()
            except Exception:
                pass
            self._odd_emitter_io = None
            self._odd_emitter_pin = None

        if self._even_emitter_io is not None:
            try:
                self._even_emitter_io.deinit()
            except Exception:
                pass
            self._even_emitter_io = None
            self._even_emitter_pin = None

        self._emitter_pin_count = 0

    def get_emitter_pin_count(self):
        return self._emitter_pin_count

    def get_emitter_pin(self):
        return self._odd_emitter_pin if self._odd_emitter_pin is not None else QTR_NO_EMITTER_PIN

    def get_odd_emitter_pin(self):
        return self._odd_emitter_pin if self._odd_emitter_pin is not None else QTR_NO_EMITTER_PIN

    def get_even_emitter_pin(self):
        return self._even_emitter_pin if self._even_emitter_pin is not None else QTR_NO_EMITTER_PIN

    def set_dimmable(self):
        self._dimmable = True

    def set_non_dimmable(self):
        self._dimmable = False

    def get_dimmable(self):
        return self._dimmable

    def set_dimming_level(self, dimming_level):
        if dimming_level > 31:
            dimming_level = 31
        self._dimming_level = dimming_level

    def get_dimming_level(self):
        return self._dimming_level

    def emitters_off(self, emitters=ALL, wait=True):
        pin_changed = False

        if emitters == ALL or (self._emitter_pin_count == 2 and emitters == ODD):
            if self._odd_emitter_io is not None and self._odd_emitter_io.value:
                self._odd_emitter_io.value = False
                pin_changed = True

        if self._emitter_pin_count == 2 and (emitters == ALL or emitters == EVEN):
            if self._even_emitter_io is not None and self._even_emitter_io.value:
                self._even_emitter_io.value = False
                pin_changed = True

        if wait and pin_changed:
            if self._dimmable:
                time.sleep(0.0012)   # 1200 us
            else:
                time.sleep(0.0002)   # 200 us

    def emitters_on(self, emitters=ALL, wait=True):
        pin_changed = False
        emitters_on_start_ns = 0

        if emitters == ALL or (self._emitter_pin_count == 2 and emitters == ODD):
            if self._odd_emitter_io is not None:
                if self._dimmable or (not self._odd_emitter_io.value):
                    emitters_on_start_ns = self._emitters_on_with_pin(self._odd_emitter_io)
                    pin_changed = True

        if self._emitter_pin_count == 2 and (emitters == ALL or emitters == EVEN):
            if self._even_emitter_io is not None:
                if self._dimmable or (not self._even_emitter_io.value):
                    emitters_on_start_ns = self._emitters_on_with_pin(self._even_emitter_io)
                    pin_changed = True

        if wait and pin_changed:
            if self._dimmable:
                # Wait until at least 300 us since first set high
                while (time.monotonic_ns() - emitters_on_start_ns) < 300_000:
                    time.sleep(0.00001)
            else:
                time.sleep(0.0002)  # 200 us

    def _emitters_on_with_pin(self, dio):
        if self._dimmable and dio.value:
            dio.value = False
            time.sleep(0.0012)  # 1200 us

        dio.value = True
        emitters_on_start_ns = time.monotonic_ns()

        if self._dimmable and self._dimming_level > 0:
            # Dimming: pulse the pin low/high at 1us intervals.
            # CircuitPython timing is much looser than AVR; we approximate.
            for _ in range(self._dimming_level):
                time.sleep(0.000001)
                dio.value = False
                time.sleep(0.000001)
                dio.value = True

        return emitters_on_start_ns

    def emitters_select(self, emitters):
        if emitters == ODD:
            off_emitters = EVEN
        elif emitters == EVEN:
            off_emitters = ODD
        elif emitters == ALL:
            self.emitters_on()
            return
        elif emitters == NONE:
            self.emitters_off()
            return
        else:
            return

        self.emitters_off(off_emitters, False)
        turn_off_start_ns = time.monotonic_ns()

        self.emitters_on(emitters)

        if self._dimmable:
            while (time.monotonic_ns() - turn_off_start_ns) < 1_200_000:
                time.sleep(0.00001)

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def reset_calibration(self):
        for i in range(self._sensor_count):
            if self.calibration_on.maximum is not None:
                self.calibration_on.maximum[i] = 0
            if self.calibration_off.maximum is not None:
                self.calibration_off.maximum[i] = 0
            if self.calibration_on.minimum is not None:
                self.calibration_on.minimum[i] = self._max_value
            if self.calibration_off.minimum is not None:
                self.calibration_off.minimum[i] = self._max_value

    def calibrate(self, mode=ON):
        if mode == MANUAL:
            return

        if mode in (ON, ON_AND_OFF):
            self._calibrate_on_or_off(self.calibration_on, ON)
        elif mode in (ODD_EVEN, ODD_EVEN_AND_OFF):
            self._calibrate_on_or_off(self.calibration_on, ODD_EVEN)

        if mode in (ON_AND_OFF, ODD_EVEN_AND_OFF, OFF):
            self._calibrate_on_or_off(self.calibration_off, OFF)

    def _calibrate_on_or_off(self, calibration, mode):
        n = self._sensor_count
        if n == 0:
            return

        sensor_values = [0] * n
        max_sensor_values = [0] * n
        min_sensor_values = [0] * n

        if not calibration.initialized:
            calibration.maximum = [0] * n
            calibration.minimum = [self._max_value] * n
            calibration.initialized = True

        for j in range(10):
            self.read(sensor_values, mode)
            for i in range(n):
                if j == 0 or sensor_values[i] > max_sensor_values[i]:
                    max_sensor_values[i] = sensor_values[i]
                if j == 0 or sensor_values[i] < min_sensor_values[i]:
                    min_sensor_values[i] = sensor_values[i]

        for i in range(n):
            if min_sensor_values[i] > calibration.maximum[i]:
                calibration.maximum[i] = min_sensor_values[i]
            if max_sensor_values[i] < calibration.minimum[i]:
                calibration.minimum[i] = max_sensor_values[i]

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------

    def read(self, sensor_values, mode=ON):
        if mode == OFF:
            self.emitters_off()
            self._read_private(sensor_values)
            return
        elif mode == MANUAL:
            self._read_private(sensor_values)
            return
        elif mode in (ON, ON_AND_OFF):
            self.emitters_on()
            self._read_private(sensor_values)
            self.emitters_off()
        elif mode in (ODD_EVEN, ODD_EVEN_AND_OFF):
            self.emitters_select(ODD)
            self._read_private(sensor_values, 0, 2)

            self.emitters_select(EVEN)
            self._read_private(sensor_values, 1, 2)

            self.emitters_off()
        else:
            return

        if mode in (ON_AND_OFF, ODD_EVEN_AND_OFF):
            off_values = [0] * self._sensor_count
            self._read_private(off_values)
            for i in range(self._sensor_count):
                sensor_values[i] += self._max_value - off_values[i]
                if sensor_values[i] > self._max_value:
                    sensor_values[i] = self._max_value

    def read_calibrated(self, sensor_values, mode=ON):
        if mode == MANUAL:
            return

        if mode in (ON, ON_AND_OFF, ODD_EVEN_AND_OFF):
            if not self.calibration_on.initialized:
                return
        if mode in (OFF, ON_AND_OFF, ODD_EVEN_AND_OFF):
            if not self.calibration_off.initialized:
                return

        self.read(sensor_values, mode)

        for i in range(self._sensor_count):
            if mode in (ON, ODD_EVEN):
                calmax = self.calibration_on.maximum[i]
                calmin = self.calibration_on.minimum[i]
            elif mode == OFF:
                calmax = self.calibration_off.maximum[i]
                calmin = self.calibration_off.minimum[i]
            else:
                # ON_AND_OFF / ODD_EVEN_AND_OFF
                if self.calibration_off.minimum[i] < self.calibration_on.minimum[i]:
                    calmin = self._max_value
                else:
                    calmin = (self.calibration_on.minimum[i]
                              + self._max_value
                              - self.calibration_off.minimum[i])

                if self.calibration_off.maximum[i] < self.calibration_on.maximum[i]:
                    calmax = self._max_value
                else:
                    calmax = (self.calibration_on.maximum[i]
                              + self._max_value
                              - self.calibration_off.maximum[i])

            denominator = calmax - calmin
            value = 0
            if denominator != 0:
                value = (sensor_values[i] - calmin) * 1000 // denominator

            if value < 0:
                value = 0
            elif value > 1000:
                value = 1000

            sensor_values[i] = value

    def read_line_black(self, sensor_values, mode=ON):
        return self._read_line_private(sensor_values, mode, False)

    def read_line_white(self, sensor_values, mode=ON):
        return self._read_line_private(sensor_values, mode, True)

    def _read_line_private(self, sensor_values, mode, invert_readings):
        if mode == MANUAL:
            return 0

        on_line = False
        avg = 0
        total = 0

        self.read_calibrated(sensor_values, mode)

        for i in range(self._sensor_count):
            value = sensor_values[i]
            if invert_readings:
                value = 1000 - value

            if value > 200:
                on_line = True

            if value > 50:
                avg += value * (i * 1000)
                total += value

        if not on_line:
            if self._last_position < (self._sensor_count - 1) * 1000 // 2:
                return 0
            else:
                return (self._sensor_count - 1) * 1000

        self._last_position = avg // total
        return self._last_position

    # ------------------------------------------------------------------
    # Low-level reading (the important part for RC mode)
    # ------------------------------------------------------------------

    def _read_private(self, sensor_values, start=0, step=1):
        if self._type == RC:
            self._read_private_rc(sensor_values, start, step)
        elif self._type == ANALOG:
            self._read_private_analog(sensor_values, start, step)

    def _read_private_rc(self, sensor_values, start, step):
        """
        RC mode: for each sensor pin, drive it HIGH briefly to charge the
        capacitor, then switch to INPUT (high-Z) and measure the time for the
        pin to fall back to LOW as the capacitor discharges through the
        phototransistor.

        Arduino uses noInterrupts() to get precise timing. CircuitPython
        cannot disable interrupts, so timing will be somewhat jittery, but
        this approach is the closest practical equivalent.
        """
        n = self._sensor_count
        if n == 0:
            return

        # 1) Charge each line: set as OUTPUT, drive HIGH.
        for i in range(start, n, step):
            dio = self._sensor_pins_io[i]
            dio.direction = digitalio.Direction.OUTPUT
            dio.value = True
            sensor_values[i] = self._max_value

        # Charge for 10 us (Arduino equivalent). In CircuitPython, sleep
        # resolution is coarse; ~10us is near the limit of sleep() but we
        # can use a short busy-wait.
        self._busy_wait_us(10)

        # 2) Switch each line to INPUT (high-Z). Record t0 right before the
        #    first switch to be as close as possible to Arduino behavior.
        t0 = time.monotonic_ns()

        for i in range(start, n, step):
            dio = self._sensor_pins_io[i]
            dio.direction = digitalio.Direction.INPUT

        # 3) Poll each pin until it reads LOW or the timeout expires.
        timeout_ns = self._max_value * 1000  # us -> ns
        deadline = t0 + timeout_ns

        # Track which sensors have already seen the transition.
        found = [False] * n

        while True:
            now = time.monotonic_ns()
            elapsed_ns = now - t0
            if elapsed_ns >= timeout_ns:
                break

            # Read all pins in this group
            for i in range(start, n, step):
                if not found[i]:
                    if not self._sensor_pins_io[i].value:
                        # Line went LOW: record elapsed time in microseconds
                        sensor_values[i] = elapsed_ns // 1000
                        found[i] = True

            # If all found, we can stop early
            all_found = True
            for i in range(start, n, step):
                if not found[i]:
                    all_found = False
                    break
            if all_found:
                break

        # Any pins that never went LOW keep the timeout value (_max_value),
        # which was pre-set above.

    def _read_private_analog(self, sensor_values, start, step):
        n = self._sensor_count
        if n == 0:
            return

        for i in range(start, n, step):
            sensor_values[i] = 0

        for _ in range(self._samples_per_sensor):
            for i in range(start, n, step):
                # AnalogIn.value is 0..65535 (16-bit)
                sensor_values[i] += self._sensor_pins_analog[i].value

        for i in range(start, n, step):
            sensor_values[i] = (sensor_values[i]
                                + (self._samples_per_sensor >> 1)) // self._samples_per_sensor

    @staticmethod
    def _busy_wait_us(us):
        """Busy-wait for approximately `us` microseconds."""
        end = time.monotonic_ns() + us * 1000
        while time.monotonic_ns() < end:
            pass

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def deinit(self):
        self.release_emitter_pins()
        for dio in self._sensor_pins_io:
            try:
                dio.deinit()
            except Exception:
                pass
        self._sensor_pins_io = []
        self._sensor_pins_analog = []