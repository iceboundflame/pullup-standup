#!/usr/bin/env python

import simplejson as json
import attr
import datetime


@attr.attributes
class PullupRecord(object):
    created_at = attr.attr(default=attr.Factory(lambda: datetime.datetime.utcnow().isoformat()))
    pullups = attr.attr(default=0)
    time_in_set = attr.attr(default=0.0)


@attr.attributes
class User(object):
    username = attr.attr()
    name = attr.attr()
    badge_codes = attr.attr(default=attr.Factory(list))
    records = attr.attr(
        default=[],
        convert=lambda vals: [PullupRecord(**v) for v in vals]
    )

    @property
    def jsonable(self):
        ## FIXME SECURITY: Need to exclude badge codes when returning to web?
        return attr.asdict(self)


@attr.attributes
class UserStore(object):
    filename = attr.attr()
    users = attr.attr(default={})

    def get_user(self, username):
        return self.users.get(username)

    def lookup_badge_code(self, badge_code):
        for u in self.users.values():
            if any(c == badge_code for c in u.badge_codes):
                return u
        return

    def save_user(self, user):
        self.users[user.username] = user
        self.save()

    def load(self):
        try:
            with open(self.filename) as fh:
                self.users = {k: User(**u) for k, u in json.load(fh).items()}
        except Exception as e:
            print "Couldn't open", self.filename, e

    def save(self):
        with open(self.filename, "w") as fh:
            json.dump({k: u.jsonable for k, u in self.users.items()}, fh)
