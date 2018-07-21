#!/usr/bin/env python

# BCM 12 = Data 0
# BCM 13 = Data 1
# BCM 5 = Beeper
# BCM 6 = Green LED
import os

import pigpio
import sys
from autobahn.twisted import ApplicationSession
from autobahn.twisted.wamp import ApplicationRunner
from twisted.internet import reactor
from twisted.internet import task, threads

from pullup.hw import PullupTracker, RfidReader, State
from pullup.store import UserStore, User, PullupRecord
from pullup import slack


class MyComponent(ApplicationSession):

    def __init__(self, config=None):
        super(MyComponent, self).__init__(config)
        self.pullup_tracker = PullupTracker()
        self.rfid = RfidReader(pigpio.pi(), self.badge_read_unsafe)

        self.current_user = None
        self.enrolling_code = None

        self.store = UserStore(filename="users.json")
        self.store.load()

        self.pullup_tracker.threshold_up = self.store.threshold_up
        self.pullup_tracker.threshold_down = self.store.threshold_down
        print "Thresholds:", \
            self.pullup_tracker.threshold_up, \
            self.pullup_tracker.threshold_down

    def onClose(self, wasClean):
        print "Lost Crossbar connection"
        reactor.stop()

    def onJoin(self, details):
        print "Joined Crossbar"
        self.register(self.get_state, 'pusu.get_state')
        self.register(self.enroll, 'pusu.enroll')
        self.register(self.end_set, 'pusu.end_set')
        self.register(self.signout, 'pusu.signout')
        self.register(self.refresh_user_profile, 'pusu.refresh_user_profile')
        self.register(self.set_username, 'pusu.set_username')
        self.register(self.set_threshold, 'pusu.set_threshold')
        self.register(self.get_leaders, 'pusu.get_leaders')
        task.LoopingCall(self.publish_state).start(0.5)
        task.LoopingCall(self.updater).start(0.0)

        # slack.post_leaderboard(self.store)

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

    def refresh_user_profile(self):
        # WARNING: This really lags because it's loading ALL slack users. Even though it's deferred to a thread,
        # it causes the pullup tracker to refresh a lot less frequently and possibly miss pullups.
        # Avoid calling this, except on enrollment and when user requests a refresh (taps image).

        if self.current_user:
            def cb(result):
                print "REFRESH USER: Saving Refreshed User"
                self.store.save_user(self.current_user)
                print "REFRESH USER: Done"
                self.publish_state()

            d = threads.deferToThread(slack.refresh_user_from_slack, self.current_user)
            d.addCallback(cb)

    def set_username(self, new_username):
        # UNTESTED
        if self.current_user and self.current_user.username != new_username:
            if self.store.get_user(new_username):
                raise ValueError("Username already exists")

            old_username = self.current_user.username
            self.current_user.username = new_username
            del self.store.users[old_username]
            self.store.save_user(self.current_user)

            self.publish_state()
            self.refresh_user_profile()

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
            self.current_user = User(username, username)
            print "Creating new user", self.current_user
        self.current_user.badge_codes.append(self.enrolling_code)
        self.store.save_user(self.current_user)

        self.refresh_user_profile()

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

    def end_set(self):
        if self.pullup_tracker.state != State.IDLE:
            self.pullup_tracker.state = State.IDLE
            self.record_pullup_set()

    def updater(self):
        result = self.pullup_tracker._sample()

        if self.current_user:
            if result:
                if result == State.UP:
                    print "Pullup"
                    self.rfid.beep_for(0.015)
                elif result == State.DOWN:
                    print "Down"
                    self.rfid.beep_for(0.070)
                elif result == State.IDLE:
                    print "Set timed out"
                    self.record_pullup_set()

        self.publish_pullup_state()

    def record_pullup_set(self):
        if self.current_user:
            record = PullupRecord(
                    pullups=self.pullup_tracker.pullups,
                    time_in_set=self.pullup_tracker.time_in_set)
            self.current_user.records.append(record)
            self.store.save_user(self.current_user)

            def post():
                slack.post_set(self.store, self.current_user, record)
                slack.post_leaderboard(self.store)
            reactor.callInThread(post)

            # self.rfid.beep_for(0.250)

        # User records updated
        self.publish_state()

    def set_threshold(self, up, down):
        self.pullup_tracker.threshold_up = up
        self.pullup_tracker.threshold_down = down

        self.store.threshold_up = up
        self.store.threshold_down = down
        self.store.save()

    def get_leaders(self):
        return threads.deferToThread(self.store.compute_leaders)


if __name__ == '__main__':
    runner = ApplicationRunner(
        os.environ.get("AUTOBAHN_ROUTER", u"ws://127.0.0.1:8080/ws"),
        u"realm1"
    )
    runner.run(MyComponent)
