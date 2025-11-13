import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image
import torch
import clip
from torchvision import transforms
import io, aiohttp, os, asyncio

TOKEN = os.getenv("DISCORD_TOKEN")

# 🧠 Load CLIP model for image comparison
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# 📂 Preload all Pokémon images and encode once
pokemon_dir = "pokemon"
pokemon_features = []
pokemon_names = []
POKEMON_INFO_FILE = "pkdex.txt"
pokemon_info = {}

with open(POKEMON_INFO_FILE, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            parts = line.strip().split(" ", 1)
            if len(parts) > 1:
                name = parts[1].split("#")[0].strip().lower()
                pokemon_info[name] = line.strip()

for fname in os.listdir(pokemon_dir):
    if fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        name = os.path.splitext(fname)[0]
        image = preprocess(Image.open(os.path.join(pokemon_dir, fname)).convert("RGB")).unsqueeze(0).to(device)
        with torch.no_grad():
            feature = model.encode_image(image)
            feature /= feature.norm(dim=-1, keepdim=True)
        pokemon_features.append(feature)
        pokemon_names.append(name)

pokemon_features = torch.cat(pokemon_features, dim=0)

# ⚙️ Bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix=None, intents=intents)

@bot.event
async def on_ready():
    bot.session = aiohttp.ClientSession()
    try:
        await bot.tree.sync()
        print(" Commands synced")
    except Exception as e:
        print("Sync error:", e)
    print(f" Logged in as {bot.user}")

@bot.tree.context_menu(name="aaaaa000ik0")
async def identify_pokemon(interaction: discord.Interaction, message: discord.Message):
    """Right-click an image message and select 'Identify Pokémon'."""
    image_url = None

    # attachments
    if message.attachments:
        att = message.attachments[0]
        if att.content_type and att.content_type.startswith("image"):
            image_url = att.url

    # embeds (Pokétwo)
    if not image_url and message.embeds:
        embed = message.embeds[0]
        if embed.image and embed.image.url:
            image_url = embed.image.url

    if not image_url:
        await interaction.response.send_message("❌ No image found!", ephemeral=True)
        return

    async with bot.session.get(image_url) as resp:
        if resp.status != 200:
            await interaction.response.send_message("⚠️ Could not download image!", ephemeral=True)
            return
        data = await resp.read()

    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        input_tensor = preprocess(img).unsqueeze(0).to(device)
        with torch.no_grad():
            input_feature = model.encode_image(input_tensor)
            input_feature /= input_feature.norm(dim=-1, keepdim=True)

        # cosine similarity
        similarities = (input_feature @ pokemon_features.T).squeeze(0)
        best_idx = similarities.argmax().item()
        best_score = similarities[best_idx].item()
        best_name = pokemon_names[best_idx]
        

        if best_score > 0.85:
            info_line = pokemon_info.get(best_name, f"@Pokétwo#8236 c {best_name}")
            # send the Pokémon image from your local database
            img_path = os.path.join(pokemon_dir, f"{best_name}.png")
            if os.path.exists(img_path):
                file = discord.File(img_path, filename=f"{best_name}.png")
                await interaction.response.send_message(file=file, content=info_line, ephemeral=True)

        else:
            await interaction.response.send_message(
                "❓ I couldn’t confidently identify this Pokémon.",
                ephemeral=True
            )

    except Exception as e:
        await interaction.response.send_message(f"Error: {e}", ephemeral=True)

@bot.event
async def on_close():
    await bot.session.close()

bot.run(TOKEN)
