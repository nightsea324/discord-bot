import os
# discord
import discord
from discord.ext import commands
from discord.ext.tasks import loop
# twitch
import requests

from dotenv import load_dotenv
load_dotenv()

# twitch
TARGET_USERNAME = os.getenv("TWITCH_USERNAME").split(",")
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
ACCESS_TOKEN = os.getenv("TWITCH_ACCESS_TOKEN")
# discord
TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# twitch
def get_app_access_token():
    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }

    response = requests.post("https://id.twitch.tv/oauth2/token", params=params)
    access_token = response.json()["access_token"]
    return access_token


user_list = {}


def get_user(username):
    params = {
        "login": username
    }
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": "Bearer {}".format(ACCESS_TOKEN)
    }

    response = requests.get("https://api.twitch.tv/helix/users", params=params, headers=headers)
    for entry in response.json()["data"]:
        user_list[entry["login"]] = entry
    return {entry["login"]: entry["id"] for entry in response.json()["data"]}


def get_stream(users):
    params = {
        "user_id": users.values()
    }
    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": "Bearer {}".format(ACCESS_TOKEN)
    }

    response = requests.get("https://api.twitch.tv/helix/streams", params=params, headers=headers)
    return {entry["user_login"]: entry for entry in response.json()["data"]}


online_users = {}


def get_notification():
    users = get_user(TARGET_USERNAME)
    stream = get_stream(users)

    notification = []
    for username in TARGET_USERNAME:
        if username not in online_users and username in stream:
            stream[username]["info"] = user_list[username]
            notification.append(stream[username])
            online_users[username] = True
        elif username in online_users and username not in stream:
            online_users.pop(username)

    return notification


# discord
@ bot.command()
async def ping(ctx):
    await ctx.send("pong")


@loop(seconds=30)
async def notification():
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if not channel:
        return

    notification = get_notification()
    for message in notification:
        # embed
        embed = discord.Embed(title="{}".format(message["title"]),
                              url="https://www.twitch.tv/{}".format(message["user_login"]),
                              description="{}".format(message["info"]["description"]),
                              color=discord.Color.dark_purple())
        embed.set_author(name="{}".format(message["user_name"]),
                         url="https://www.twitch.tv/{}".format(message["user_login"]),
                         icon_url="{}".format(message["info"]["profile_image_url"]))
        embed.set_thumbnail(url="{}".format(message["info"]["profile_image_url"]))
        embed.add_field(name="Game", value="{}".format(message["game_name"]), inline=True)
        embed.add_field(name="Viewers", value="{}".format(message["viewer_count"]), inline=True)
        embed.set_image(url="{}".format(message["thumbnail_url"].format(width=1920, height=1080)))
        embed.set_footer(text="Started streaming：{}" .format(message["started_at"]))

        await channel.send("**{}** 開台啦".format(message['user_name']), embed=embed)


@ bot.event
async def on_ready():
    notification.start()
    print("Logged in as {0.user}".format(bot))


bot.run(TOKEN)
