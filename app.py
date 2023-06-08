import discord
import requests
from aiohttp import web
import os
# twitch
from twitchAPI.twitch import Twitch
from twitchAPI.helper import first
from twitchAPI.eventsub import EventSub
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.types import AuthScope
import asyncio

from dotenv import load_dotenv
load_dotenv()

# twitch
TARGET_USERNAME = "nightsea324"
EVENTSUB_URL = os.getenv("TWITCH_CALLBACK_URL")
APP_ID = os.getenv("TWITCH_CLIENT_ID")
APP_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TARGET_SCOPES = [AuthScope.MODERATOR_READ_FOLLOWERS]


# twitch
async def on_follow(data: dict):
    # our event happend, lets do things with the data we got!
    print(data)


async def eventsub_example():
    # create the api instance and get the ID of the target user
    twitch = await Twitch(APP_ID, APP_SECRET)
    user = await first(twitch.get_users(logins=TARGET_USERNAME))

    # the user has to authenticate once using the bot with our intended scope.
    # since we do not need the resulting token after this authentication, we just discard the result we get from authenticate()
    # Please read up the UserAuthenticator documentation to get a full view of how this process works
    auth = UserAuthenticator(twitch, TARGET_SCOPES, force_verify=False)
    await auth.authenticate()

    # basic setup, will run on port 8080 and a reverse proxy takes care of the https and certificate
    event_sub = EventSub(EVENTSUB_URL, APP_ID, 8080, twitch)

    # unsubscribe from all old events that might still be there
    # this will ensure we have a clean slate
    await event_sub.unsubscribe_all()
    # start the eventsub client
    event_sub.start()
    # subscribing to the desired eventsub hook for our user
    # the given function (in this example on_follow) will be called every time this event is triggered
    # the broadcaster is a moderator in their own channel by default so specifying both as the same works in this example
    # await event_sub.listen_channel_follow_v2(user.id, user.id, on_follow)
    print('start')
    await event_sub.listen_stream_online(user.id, on_follow)
    print('sub')

    # eventsub will run in its own process
    # so lets just wait for user input before shutting it all down again
    try:
        input('press Enter to shut down...')
    finally:
        # stopping both eventsub as well as gracefully closing the connection to the API
        await event_sub.stop()
        await twitch.close()
    print('done')


# lets run our example
asyncio.run(eventsub_example())

# discord
# TOKEN = os.getenv("DISCORD_TOKEN")
# DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
#
# intents = discord.Intents.default()
# intents.message_content = True
#
# client = discord.Client(intents=intents)
# app = web.Application()
#
#
# @client.event
# async def on_ready():
#     print("Logged in as {0.user}".format(client))
#
#
# client.run(TOKEN)
