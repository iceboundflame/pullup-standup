#!/usr/bin/env python

# BCM 12 = Data 0
# BCM 13 = Data 1
# BCM 5 = Beeper
# BCM 6 = Green LED
import simplejson as json
import os
import time

import Adafruit_ADS1x15
import pigpio
from autobahn.twisted import ApplicationSession
from autobahn.twisted.wamp import ApplicationRunner
from enum import Enum
from twisted.internet import reactor
from twisted.internet import task

import wiegand
from store import UserStore, User


class MyComponent(ApplicationSession):
    def onJoin(self, details):
        self.pullup_tracker = PullupTracker(Adafruit_ADS1x15.ADS1115())
        self.rfid = RfidReader(pigpio.pi(), self.badge_read_unsafe)

        print "Joined Crossbar"
        self.register(self.get_leaders, 'pusu.get_leaders')
        self.register(self.get_state, 'pusu.get_state')
        task.LoopingCall(self.publisher).start(0.5)
        task.LoopingCall(self.updater).start(0.0)

    def badge_read_unsafe(self, bits, code):
        # Will be running off-reactor thread.
        reactor.callFromThread(self.badge_read, bits, code)

    def badge_read(self, bits, code):
        print "{}_{}".format(bits, code)

    def get_leaders(self):
        return ["Leaderboard"]

    def get_state(self):
        return self.pullup_tracker.jsonable
        return {
            "pullup": self.pullup_tracker.jsonable,
            "auth": self.auth_handler.jsonable,
            "leaders": self.leaderboard.jsonable,
        }

    def publisher(self):
        self.publish('pusu.pullup', self.pullup_tracker.jsonable)

    def updater(self):
        result = self.pullup_tracker._sample()

        if result:
            print "Pullup"
            self.publish('pusu.pullup', self.pullup_tracker.jsonable)

        if self.pullup_tracker.idle_time > 5:
            self.pullup_tracker.reset()


class State(Enum):
    IDLE = 0
    UP = 1
    DOWN = 2


class AuthHandler(object):
    def __init__(self, user_store):
        pass

    def badge_swiped(self, bits, code):
        pass

    def jsonable(self):
        return {
            # "badge_id":

        }



class PullupTracker(object):
    ADC_CHANNEL = 0
    ADC_SAMPLES_PER_SEC = 8
    # 1 = +/-4.096V
    # 2 = +/-2.048V
    ADC_GAIN = 1

    THRESHOLD_DOWN = 500
    THRESHOLD_UP = 10000

    def __init__(self, adc):
        self.adc = adc
        self.raw_value = 0
        self.reset()

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

        if self.state == State.UP:
            if self.raw_value < self.THRESHOLD_DOWN:
                self.state = State.DOWN
        else:
            if self.raw_value > self.THRESHOLD_UP:
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

    @is_green.setter
    def is_green(self, on):
        self.pi.write(self.GREEN_PIN, 0 if on else 1)

    def beep_for(self, secs):
        self.pi.write(self.BEEPER_PIN, 0)
        time.sleep(secs)
        self.pi.write(self.BEEPER_PIN, 1)


if __name__ == '__main__':
    runner = ApplicationRunner(
        os.environ.get("AUTOBAHN_DEMO_ROUTER", u"ws://127.0.0.1:8080/ws"),
        u"realm1"
        # u"crossbardemo",
    )
    runner.run(MyComponent)
