import discord
import asyncio
import aiohttp
import os
import re

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1438035018747478016  # channel where bot sends d #1 etc.
# https://discord.com/channels/1414290618972373042/1438035018747478016

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ---------- HELPERS ---------- #
async def download_image(url, name):
    os.makedirs("pokemon_images", exist_ok=True)
    img_path = f"pokemon_images/{name}.png"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                with open(img_path, "wb") as f:
                    f.write(await resp.read())
                print(f"Saved image: {img_path}")
            else:
                print(f"Failed to download image for {name}")

async def save_embed_text(eng_name, text):
    os.makedirs("pokemon_texts", exist_ok=True)
    path = f"pokemon_texts/{eng_name}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Saved embed text: {path}")

# ---------- MAIN LISTENER ---------- #
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.channel.id != CHANNEL_ID or not message.author.bot:
        return

    if not message.embeds:
        return

    embed = message.embeds[0]

    # ---------------- Parse English Name ---------------- #
    if embed.title and "—" in embed.title:
        eng_name = embed.title.split("—")[1].strip()
    else:
        print("No valid title found")
        return

    # ---------------- Download Image ---------------- #
    if embed.image and embed.image.url:
        await download_image(embed.image.url, eng_name)
    else:
        print(f"No image found for {eng_name}")

    # ---------------- Save Entire Embed Content ---------------- #
    full_text = ""
    if embed.title:
        full_text += embed.title + "\n"
    for field in embed.fields:
        if field.name == "Names":
            full_text += f"{field.value}\n\n"

    await save_embed_text(eng_name, full_text.strip())

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    print("Bot is ready and listening for Pokétwo messages!")

client.run(TOKEN)
