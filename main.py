#!/usr/bin/env python

# BCM 12 = Data 0
# BCM 13 = Data 1
# BCM 5 = Beeper
# BCM 6 = Green LED
import attr
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
from store import UserStore, User, PullupRecord


class MyComponent(ApplicationSession):
    def onJoin(self, details):
        self.pullup_tracker = PullupTracker()
        self.rfid = RfidReader(pigpio.pi(), self.badge_read_unsafe)

        self.current_user = None
        self.enrolling_code = None

        self.store = UserStore(filename="users.json")
        self.store.load()

        print "Joined Crossbar"
        self.register(self.get_state, 'pusu.get_state')
        self.register(self.enroll, 'pusu.enroll')
        self.register(self.signout, 'pusu.signout')
        task.LoopingCall(self.publish_state).start(0.5)
        task.LoopingCall(self.updater).start(0.0)

    #
    # Authentication
    #

    def badge_read_unsafe(self, bits, raw_code):
        # Will be running off-reactor thread. Reschedule on-thread.
        reactor.callFromThread(self.badge_read, bits, raw_code)

    def badge_read(self, bits, raw_code):
        self.signout()

        badge_code = "{}_{}".format(bits, raw_code)
        self.current_user = self.store.lookup_badge_code(badge_code)
        if self.current_user:
            print "Signed in user", self.current_user
            self.rfid.is_green = True
        else:
            print "Couldn't find user, enroll", badge_code
            self.enrolling_code = badge_code

        self.publish_state()

    def enroll(self, username):
        if not self.enrolling_code:
            return

        if not username:
            self.signout()
            return

        self.current_user = self.store.get_user(username)
        if self.current_user:
            print "Adding badge code to user", self.current_user
        else:
            self.current_user = User(username, "User " + username)
            print "Creating new user", self.current_user

        self.current_user.badge_codes.append(self.enrolling_code)
        self.store.save_user(self.current_user)

        self.rfid.is_green = True
        self.publish_state()

    def signout(self):
        if self.pullup_tracker.state != State.IDLE:
            self.record_pullup_set()
        self.pullup_tracker.reset()
        self.rfid.is_green = False
        self.current_user = None
        self.enrolling_code = None
        self.publish_state()

    #
    # State
    #

    def get_state(self):
        return {
            "pullup": self.pullup_tracker.jsonable,
            "current_user": self.current_user.jsonable if self.current_user else None,
            "enroll_mode": self.enrolling_code is not None,
        }

    def publish_state(self):
        self.publish('pusu.state', self.get_state())

    def publish_pullup_state(self):
        self.publish('pusu.state', {"pullup": self.pullup_tracker.jsonable})

    #
    # Pullups
    #

    def updater(self):
        if self.current_user:
            result = self.pullup_tracker._sample()

            if result:
                if result == State.UP:
                    print "Pullup"
                    # self.rfid.beep_for(0.015)
                elif result == State.DOWN:
                    print "Down"
                    # self.rfid.beep_for(0.070)
                elif result == State.IDLE:
                    print "Set timed out"
                    self.record_pullup_set()
                    # self.rfid.beep_for(0.250)

            self.publish_pullup_state()

    def record_pullup_set(self):
        if self.current_user:
            self.current_user.records.append(
                PullupRecord(
                    pullups=self.pullup_tracker.pullups,
                    time_in_set=self.pullup_tracker.time_in_set))
            self.store.save_user(self.current_user)

        # User records updated
        self.publish_state()


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

    threshold_down = attr.attr(default=500)
    threshold_up = attr.attr(default=10000)
    idle_timeout = attr.attr(default=5.0)

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
            "state": self.state.name,
            "raw_value": self.raw_value,
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
