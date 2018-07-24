#!/usr/bin/env python

import os

from slackclient import SlackClient
import traceback

SLACK_TOKEN = os.environ.get("SLACK_API_TOKEN")
SLACK_TOKEN_FILE = os.path.expanduser('~/SLACK_API_TOKEN')
if not SLACK_TOKEN:
    try:
        SLACK_TOKEN = open(SLACK_TOKEN_FILE).read().strip()
    except:
        print "SLACK_API_TOKEN not set and couldn't read it from", SLACK_TOKEN_FILE
        traceback.print_exc()


USERNAME = "Pullup Bar"
CHANNEL = "#pullups"


def get_slack_users():
    sc = SlackClient(SLACK_TOKEN)
    resp = sc.api_call("users.list")
    slack_users_by_name = {u['name'].lower(): u for u in resp['members']}
    return slack_users_by_name


def refresh_user_from_slack_internal(slack_users_by_name, user):
    slack_user = slack_users_by_name[user.username.lower()]

    user.name = slack_user['profile']['real_name']
    user.pfpic = slack_user['profile']['image_512']
    user.slackid = slack_user['id']


def refresh_user_from_slack(user):
    try:
        # unfortunately we have to get ALL users to find the user with this username
        print "REFRESH USER: Getting All Slack Users"
        slack_users_by_name = get_slack_users()
        print "REFRESH USER: Got Slack Users"
        refresh_user_from_slack_internal(slack_users_by_name, user)

    except:
        print "Couldn't refresh user %s from Slack:" % (user.name)
        traceback.print_exc()


def post_set(store, user, record):
    try:
        sc = SlackClient(SLACK_TOKEN)

        sc.api_call(
            "chat.postMessage",
            channel=CHANNEL,
            username=USERNAME,
            text=":muscle: :rightmuscle: *{}* just did *{} {}*!".format(
                "<@{}>".format(user.slackid) if user.slackid else user.name,
                record.pullups,
                "pullup" if record.pullups == 1 else "pullups")
        )

    except:
        print "Couldn't post to Slack:"
        traceback.print_exc()


def post_leaderboard(store):
    try:
        sc = SlackClient(SLACK_TOKEN)

        leaderboard = ""
        for u in store.compute_leaders(top_n=10, json=False):
            leaderboard += "{:30} {:4d} total, {:4d} best\n".format(u.name, u.total_this_week, u.best_this_week)
        sc.api_call(
            "chat.postMessage",
            channel=CHANNEL,
            username=USERNAME,
            text="This Week's Leaderboard:\n```{}```".format(leaderboard)
        )

    except:
        print "Couldn't post to Slack:"
        traceback.print_exc()
