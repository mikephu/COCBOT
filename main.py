from discord.ext import commands
import discord
import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  

bot = commands.Bot(command_prefix='!',intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot connected as {bot.user.name}")
    
async def main():
     async with bot:
        await bot.load_extension("slash_command_bot")
        await bot.start(DISCORD_BOT_TOKEN)
        
import asyncio
asyncio.run(main())