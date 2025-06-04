import discord
from discord.ext import commands
import aiohttp
import os
from dotenv import load_dotenv
import urllib.parse

# Load the .env file
load_dotenv()

# Get secrets from environment
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
COC_API_TOKEN = os.getenv("COC_API_TOKEN")
CLAN_TAG = os.getenv("CLAN_TAG")
encoded_clan_tag = urllib.parse.quote(CLAN_TAG)

headers = {
    "Authorization": f"Bearer {COC_API_TOKEN}"
}

bot = commands.Bot(command_prefix='!')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command()
async def claninfo(ctx):
    async with aiohttp.ClientSession() as session:
        url = f"https://api.clashofclans.com/v1/clans/{encoded_clan_tag}"
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                clan_data = await response.json()
                members = clan_data.get('memberList', [])

                description = '\n'.join([
                    f"{m['name']} ({m['role']}) - {m['trophies']}🏆"
                    for m in members
                ])

                embed = discord.Embed(
                    title=clan_data['name'],
                    description=description or "No members found.",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Clan tag: {CLAN_TAG}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to fetch clan info. Check your API key and tag.")

bot.run(DISCORD_BOT_TOKEN)