#!/usr/bin/env python

import attr
import datetime
import dateutil.parser
import dateutil.relativedelta
import pytz
import simplejson as json
import tzlocal


@attr.attrs
class PullupRecord(object):
    created_at = attr.attr(default=attr.Factory(
        lambda: datetime.datetime.now(pytz.utc).isoformat()))
    pullups = attr.attr(default=0)
    time_in_set = attr.attr(default=0.0)

    @property
    def created_at_dt(self):
        return dateutil.parser.parse(self.created_at)


def this_week_start():
    """Get local Sunday midnight."""
    weekstart = (datetime.date.today() +  # N.B. today() is local date.
                 dateutil.relativedelta.relativedelta(weekday=dateutil.relativedelta.SU(-1)))
    weekstart = datetime.datetime.combine(weekstart, datetime.time(0, 0))
    weekstart = tzlocal.get_localzone().localize(weekstart)
    # print "This week started", weekstart.isoformat()
    return weekstart


@attr.attrs
class User(object):
    username = attr.attr()
    name = attr.attr()
    pfpic = attr.attr(default=None)
    badge_codes = attr.attr(default=attr.Factory(list))
    records = attr.attr(
        default=[],
        convert=lambda vals: [PullupRecord(**v) for v in vals]
    )

    @property
    def total_lifetime(self):
        return self.total_since(None)

    @property
    def total_7d(self):
        return self.total_since(datetime.datetime.now(pytz.utc) - datetime.timedelta(days=7))

    @property
    def total_this_week(self):
        return self.total_since(this_week_start())

    @property
    def best_lifetime(self):
        return self.best_since(None)

    @property
    def best_7d(self):
        return self.best_since(datetime.datetime.now(pytz.utc) - datetime.timedelta(days=7))

    @property
    def best_this_week(self):
        return self.best_since(this_week_start())

    def stats_since(self, start):
        best, total = 0, 0
        for r in self.records:
            if not start or r.created_at_dt > start:
                best = max(best, r.pullups)
                total += r.pullups
        return best, total

    def best_since(self, start):
        return self.stats_since(start)[0]

    def total_since(self, start):
        return self.stats_since(start)[1]

    @property
    def jsonable(self):
        # For Web use only. Not for storage.
        return {
            "username": self.username,
            "name": self.name,
            "pfpic": self.pfpic,
            "records": [attr.asdict(r) for r in self.records],
            "best_lifetime": self.best_lifetime,
            "best_7d": self.best_7d,
            "best_this_week": self.best_this_week,
            "total_lifetime": self.total_lifetime,
            "total_7d": self.total_7d,
            "total_this_week": self.total_this_week,
        }


@attr.attrs
class UserStore(object):
    filename = attr.attr()
    users = attr.attr(default={})

    threshold_up = attr.attr(default=9000)
    threshold_down = attr.attr(default=1200)

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
                obj = json.load(fh)
                self.users = {k: User(**u) for k, u in obj.get('users').items()}
                self.threshold_up = obj.get('threshold_up')
                self.threshold_down = obj.get('threshold_down')
        except Exception as e:
            print "Couldn't open", self.filename, e
            # raise

    def save(self):
        with open(self.filename, "w") as fh:
            json.dump(self.jsonable, fh)

    @property
    def jsonable(self):
        return {
            'users': {k: attr.asdict(u) for k, u in self.users.items()},
            'threshold_up': self.threshold_up,
            'threshold_down': self.threshold_down,
        }

    def compute_leaders(self, top_n=8):
        leaders_objs = list(sorted(self.users.values(), key=lambda u: u.total_7d, reverse=True)[:top_n])
        leaders_objs = filter(lambda u: u.total_7d > 0, leaders_objs)
        return {
            'leaders': map(lambda u: u.jsonable, leaders_objs),
        }

#
# user_id =>
#  lifetime_total
#  record
#  r
#  record.ts  # blob of raw time series
#
