import os
import discord

from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print("Bot is ready")
    print("Client user : ", client.user)

    game = discord.Game("測試中")

    await client.change_presence(status=discord.Status.online, activity=game)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == "hello":
        await message.channel.send("Hello!")

    await message.channel.send(message.content)


token = os.getenv("TOKEN")
client.run(token)
