#!/usr/bin/env python

import simplejson as json


class PullupRecord(object):
    def __init__(self, created_at, pullups, time_in_set):
        self.created_at = created_at
        self.pullups = pullups
        self.time_in_set = time_in_set

    def to_jsonable(self):
        return self.__dict__

    @staticmethod
    def from_jsonable(jsonable):
        return PullupRecord(**jsonable)
        #     jsonable['created_at'],
        #     jsonable['pullups'],
        #     jsonable['time_in_set']
        # )


class User(object):
    def __init__(self, username, name, records):
        self.username = username
        self.name = name
        self.records = records

    @staticmethod
    def from_jsonable(jsonable):
        j = dict(jsonable)
        j['records'] = [PullupRecord.from_jsonable(r) for r in j['records']]
        return User(**j)

    def to_jsonable(self):
        j = dict(self.__dict__)
        j['records'] = [r.to_jsonable() for r in self.records]
        return j


class UserStore(object):
    def __init__(self, filename):
        self.filename = filename
        self.users = {}
        self.load()

    def get_user(self, username):
        return self.users[username]

    def save_user(self, user):
        self.users[user.username] = user
        self.save()

    def load(self):
        with open(self.filename) as fh:
            self.users = {k: User.from_jsonable(u) for k, u in json.load(fh).items()}

    def save(self):
        with open(self.filename, "w") as fh:
            json.dump(fh, {k: u.to_jsonable() for k, u in self.users.items()})
