#!/usr/bin/env python

# BCM 12 = Data 0
# BCM 13 = Data 1
# BCM 5 = Beeper
# BCM 6 = Green LED

import os
import time

import Adafruit_ADS1x15
import pigpio
from enum import Enum
from twisted.internet import reactor

import wiegand


class MyComponent(ApplicationSession):
    def __init__(self):
        self.pullup_tracker = PullupTracker(Adafruit_ADS1x15.ADS1115())
        self.rfid = RfidReader(pigpio.pi(), self.badge_read)

    def badge_read(self):
        # ??? Will be running off-reactor thread.
        # self.???
        reactor.callFromThread(asdf)

    @inlineCallbacks
    def on_join(self, details):
        print "Joined Crossbar"

        def get_leaders():
            return ["Leaderboard"]
        self.register(get_leaders, 'pusu.get_leaders');

        while True:
            result = self.pullup_tracker._sample()
            yield sleep(0.1)

            if result:
                self.publish('pusu.pullup', self.pullup_tracker.jsonable)

            if self.pullup_tracker.idle_time > 5:
                self.pullup_tracker.reset()

        # res = yield self.call('com.myapp.add2', 2, 3)
        # print("Got result: {}".format(res))


class State(Enum):
    IDLE = 0
    UP = 1
    DOWN = 2


class PullupTracker(object):
    ADC_CHANNEL = 0
    ADC_SAMPLES_PER_SEC = 8
    # 1 = +/-4.096V
    # 2 = +/-2.048V
    ADC_GAIN = 1

    THRESHOLD_DOWN = 10000
    THRESHOLD_UP = 20000

    def __init__(self, adc):
        self.adc = adc
        self.raw_value = 0

    def reset(self):
        self.pullups = 0
        self.state = State.IDLE
        self.start_time = None
        self.last_pullup_time = None

    @property
    def time_in_set(self):
        if not self.start_time:
            return 0

        return time.time() - self.start_time

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
                self.ADC_CHANNEL,
                gain=self.ADC_GAIN,
                data_rate=self.ADC_SAMPLES_PER_SEC)

        self.raw_value = value

        print value
        time.sleep(0.1)

        if self.state == State.UP and self.raw_value < self.THRESHOLD_DOWN:
            self.state = State.DOWN
        elif self.raw_value > self.THRESHOLD_UP:
            self.state = State.UP
            if self.pullups == 0:
                self.start_time = time.time()
            self.pullups += 1
            self.last_pullup_time = time.time()
            return True

        return False

    @property
    def jsonable(self):
        return {
            "pullups": self.pullups,
            "time_in_set": self.time_in_set,
            "idle_time": self.idle_time,
            # "raw_value": self.raw_value,
        }


class RfidReader(object):
    # Note: all pins are active LOW.
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

    @property
    def is_green(self, on):
        self.pi.write(self.GREEN_PIN, 0 if on else 1)

    def beep_for(self, secs):
        self.pi.write(self.BEEPER_PIN, 0)
        time.sleep(secs)
        self.pi.write(self.BEEPER_PIN, 1)


if __name__ == '__main__':
    runner = ApplicationRunner(
        os.environ.get("AUTOBAHN_DEMO_ROUTER", u"ws://127.0.0.1:8080/ws"),
        u"crossbardemo",
    )
    runner.run(MyComponent)
