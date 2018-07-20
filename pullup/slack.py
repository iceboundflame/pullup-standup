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


CHANNEL = "#pullups"


def refresh_user_from_slack(user):
    try:
        sc = SlackClient(SLACK_TOKEN)

        # unfortunately we have to get ALL users to find the user with this username
        resp = sc.api_call("users.list")
        slack_users_by_name = {u['name'].lower(): u for u in resp['members'] if not u['deleted']}
        slack_user = slack_users_by_name[user.username.lower()]

        user.name = slack_user['profile']['real_name']
        user.pfpic = slack_user['profile']['image_512']
        user.slackid = slack_user['id']

    except:
        print "Couldn't refresh user %s from Slack:" % (user.name)
        traceback.print_exc()


def post_set(user, record):
    try:
        sc = SlackClient(SLACK_TOKEN)

        sc.api_call(
            "chat.postMessage",
            channel=CHANNEL,
            text=":muscle: :rightmuscle: *{}* just did *{} pullups*!".format(
                "<@{}>".format(user.slackid) if user.slackid else user.name,
                record.pullups)
        )
    except:
        print "Couldn't post to Slack:"
        traceback.print_exc()
