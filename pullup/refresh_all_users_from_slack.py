#!/usr/bin/env python
import traceback

from pullup import slack
from pullup.store import UserStore

if __name__ == '__main__':
    store = UserStore(filename="users.json")
    store.load()

    slack_users_by_name = slack.get_slack_users()
    for user in store.users.values():
        print user.username
        try:
            slack.refresh_user_from_slack_internal(slack_users_by_name, user)
            print "\t\t=>", user.name
            store.save_user(user)
        except:
            traceback.print_exc()
