import os
import datetime
import pytz
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
LOOPTIME = int(os.getenv("LOOP_TIME"))


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
            stream[username]["status"] = "new"
            notification.append(stream[username])
            online_users[username] = True
        elif username in online_users and username not in stream:
            notification.append({"user_login": username, "status": "delete",
                                "info": user_list[username]})
            online_users.pop(username)
        elif username in online_users and username in stream:
            stream[username]["status"] = "update"
            stream[username]["info"] = user_list[username]
            notification.append(stream[username])

    return notification


# discord
@ bot.command()
async def ping(ctx):
    await ctx.send("pong")

posted_message = {}


@loop(seconds=LOOPTIME)
async def notification():
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if not channel:
        return

    notification = get_notification()
    for message in notification:

        if message["status"] == "new" and message["user_login"] not in posted_message:
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

            started_at = (datetime.datetime.strptime(message["started_at"], "%Y-%m-%dT%H:%M:%SZ"))
            started_at = started_at .replace(tzinfo=pytz.utc).astimezone(
                pytz.timezone("Asia/Taipei")
            ).strftime("%Y-%m-%d %H:%M")
            embed.set_footer(text="Started streaming：{}" .format(started_at))
            # message
            message_text = "**{}** 開台啦".format(message["user_name"])

            thumbnail_url = "{}{}".format(
                message["thumbnail_url"].format(width=1920, height=1080),
                "?" + str(datetime.datetime.now().timestamp())
            )
            embed.set_image(url="{}".format(thumbnail_url))

            res = await channel.send(message_text, embed=embed)

            posted_message[message["user_login"]] = {
                "id": res.id,
                "updatedAt": datetime.datetime.now(),
                "thumbnail_url": thumbnail_url,
                "embed": embed
            }

        elif message["status"] == "update" and message["user_login"] in posted_message:
            if check_is_need_refresh(posted_message[message["user_login"]]["updatedAt"]):
                posted_message[message["user_login"]]['updatedAt'] = datetime.datetime.now()
                posted_message[message["user_login"]]["thumbnail_url"] = "{}{}".format(
                    message["thumbnail_url"].format(width=1920, height=1080),
                    "?" + str(datetime.datetime.now().timestamp())
                )
            embed = posted_message[message["user_login"]]["embed"]
            embed.set_image(url="{}".format(
                posted_message[message["user_login"]]["thumbnail_url"]))
            res = await channel.fetch_message(posted_message[message["user_login"]]["id"])
            await res.edit(embed=embed)

        elif message["status"] == "delete" and message["user_login"] in posted_message:
            embed = posted_message[message["user_login"]]["embed"]
            embed.set_image(url="{}".format(message["info"]["offline_image_url"]))

            res = await channel.fetch_message(posted_message[message["user_login"]]["id"])
            await res.edit(embed=embed)

            posted_message[message["user_login"]] = None


def check_is_need_refresh(datetime_):
    return datetime_ + datetime.timedelta(minutes=5) < datetime.datetime.now()


@ bot.event
async def on_ready():
    notification.start()
    print("Logged in as {0.user}".format(bot))


bot.run(TOKEN)
