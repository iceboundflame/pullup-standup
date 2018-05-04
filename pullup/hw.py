#!/usr/bin/env python

# BCM 12 = Data 0
# BCM 13 = Data 1
# BCM 5 = Beeper
# BCM 6 = Green LED
import time

import Adafruit_ADS1x15
import attr
import pigpio
from enum import Enum

import pullup.wiegand as wiegand


class State(Enum):
    IDLE = 0
    UP = 1
    DOWN = 2


@attr.attrs
class PullupTracker(object):
    adc = attr.attr(default=attr.Factory(lambda: Adafruit_ADS1x15.ADS1115()))
    adc_channel = attr.attr(default=0)
    # 1 = +/-4.096V
    # 2 = +/-2.048V
    adc_gain = attr.attr(default=1)
    adc_samples_per_sec = attr.attr(default=16)

    threshold_up = attr.attr(default=9000)
    threshold_down = attr.attr(default=1200)
    idle_timeout = attr.attr(default=20.0)

    raw_value = attr.attr(default=0)
    pullups = attr.attr(default=0)
    state = attr.attr(default=State.IDLE)
    start_time = attr.attr(default=None)
    last_pullup_time = attr.attr(default=None)

    def __attrs_post_init__(self):
        self.reset()

    def reset(self):
        self.pullups = 0
        self.state = State.IDLE
        self.start_time = None
        self.last_pullup_time = None

    @property
    def time_since_start(self):
        if not self.start_time:
            return 0

        return time.time() - self.start_time

    @property
    def time_in_set(self):
        if not self.start_time or not self.last_pullup_time:
            return 0

        return self.last_pullup_time - self.start_time

    @property
    def idle_time(self):
        if not self.last_pullup_time:
            return 0

        return time.time() - self.last_pullup_time

    # def start(self, reactor):
    #     self.lp = task.LoopingCall(self._sample)
    #     self.lp.start(0.1)

    # def stop(self):
    #     if self.lp:
    #         self.lp.stop()

    def _sample(self):
        value = self.adc.read_adc(
                self.adc_channel,
                gain=self.adc_gain,
                data_rate=self.adc_samples_per_sec)

        self.raw_value = value

        old_state = self.state

        if self.state == State.UP:
            if self.raw_value < self.threshold_down:
                self.state = State.DOWN
        else:
            if self.raw_value > self.threshold_up:
                self.last_pullup_time = time.time()
                if self.state == State.IDLE:
                    # New set started.
                    self.pullups = 1
                    self.start_time = self.last_pullup_time
                    print "new set"
                else:
                    self.pullups += 1
                self.state = State.UP

            if self.idle_time > self.idle_timeout:
                self.state = State.IDLE

        if self.state != old_state:
            return self.state  # Alert caller of state change
        return None

    @property
    def jsonable(self):
        return {
            "pullups": self.pullups,
            "time_since_start": self.time_since_start,
            "time_in_set": self.time_in_set,
            "idle_time": self.idle_time,
            "idle_time_percent": self.idle_time / self.idle_timeout,
            "state": self.state.name,
            "raw_value": self.raw_value,
        }


class RfidReader(object): # Note: all pins are active LOW.
    BEEPER_PIN = 5
    GREEN_PIN = 6
    DATA_0_PIN = 12
    DATA_1_PIN = 13

    def __init__(self, pi, *callbacks):
        self.callbacks = callbacks
        self.pi = pi

        self.pi.set_mode(self.BEEPER_PIN, pigpio.OUTPUT)
        self.pi.set_mode(self.GREEN_PIN, pigpio.OUTPUT)
        self.pi.write(self.BEEPER_PIN, 1)
        self.pi.write(self.GREEN_PIN, 1)

        def callback(bits, code):
            for cb in self.callbacks:
                cb(bits, code)
        self.w = wiegand.decoder(self.pi, self.DATA_0_PIN, self.DATA_1_PIN, callback)

        # self.w.cancel()
        # self.pi.stop()

    @property
    def is_green(self):
        return not self.pi.read(self.GREEN_PIN)

    @is_green.setter
    def is_green(self, on):
        self.pi.write(self.GREEN_PIN, 0 if on else 1)

    def beep_for(self, secs):
        self.pi.write(self.BEEPER_PIN, 0)
        time.sleep(secs)
        self.pi.write(self.BEEPER_PIN, 1)
