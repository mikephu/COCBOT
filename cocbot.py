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

intents = discord.Intents.default()
intents.message_content = True  # Required to read message content for commands

headers = {
    "Authorization": f"Bearer {COC_API_TOKEN}"
}

bot = commands.Bot(command_prefix='!',intents=intents)

@bot.command(name='claninfo')
async def claninfo(ctx):
    url = f"https://api.clashofclans.com/v1/clans/{encoded_clan_tag}"
    headers = {
        "Authorization": f"Bearer {COC_API_TOKEN}"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                await ctx.send(f"Error fetching clan data: {response.status}")
                return
            data = await response.json()

    members = data.get('memberList', [])
    clan_name = data.get('name', 'Unknown')
    embed = discord.Embed(
        title=f"{clan_name} — Members",
        description=f"Total Members: {len(members)}",
        color=discord.Color.green()
    )

    for member in members:
        name = member.get('name', 'Unknown')
        role = member.get('role', 'N/A').capitalize()
        level = member.get('expLevel', 0)
        trophies = member.get('trophies', 0)
        donations = member.get('donations', 0)
        donations_rcv = member.get('donationsReceived', 0)

        embed.add_field(
            name=f"{name} ({role})",
            value=f"Level: {level} | 🏆 {trophies}\n📤 {donations} | 📥 {donations_rcv}",
            inline=False
        )

    await ctx.send(embed=embed)

@bot.command(name='clanlogo')
async def clanlogo(ctx):
    embed = discord.Embed(
        title="Clan Logo",
        description="Here is our clan's glorious emblem!",
        color=discord.Color.gold()
    )
    embed.set_image(url="https://i.imgur.com/9ythM6n.png")

    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user.name}")
    
@bot.command(name='cwlattacks')
async def cwlattacks(ctx):
    await ctx.send("Fetching CWL war attack info, please wait...")

    base_url = "https://api.clashofclans.com/v1"
    headers = {
        "Authorization": f"Bearer {COC_API_TOKEN}"
    }

    async with aiohttp.ClientSession() as session:
        # Step 1: Get league group info
        league_url = f"{base_url}/clans/{encoded_clan_tag}/currentwar/leaguegroup"
        async with session.get(league_url, headers=headers) as response:
            if response.status != 200:
                await ctx.send("Error fetching CWL group data.")
                return
            league_data = await response.json()
        # Step 2: Get the latest round war tag
        rounds = league_data.get("rounds", [])
        if not rounds:
            await ctx.send("No CWL rounds found.")
            return

        
        # Get all non-#0 rounds
        valid_war_tags = []
        for round_info in reversed(rounds):
            war_tags = round_info.get("warTags", [])
            valid_war_tag = [tag for tag in war_tags if tag != "#0"]
            if valid_war_tag:   
                valid_war_tags.append(valid_war_tag)
            
        if not valid_war_tags:
            await ctx.send("No active war tags found.")
            return
        
        # Step 3: Check to see which war is currently active "inWar"        
        for round in valid_war_tags:
            war_tag = urllib.parse.quote(round[-1])
            war_url = f"{base_url}/clanwarleagues/wars/{war_tag}"
            async with session.get(war_url, headers=headers) as response:
                if response.status != 200:
                    await ctx.send("Error fetching current CWL war data.")
                    return
                war_data = await response.json()
                if war_data.get("state") == "inWar":
                    active_war_tags = round
                    break

        active_war_data = []
        for round in active_war_tags:
            war_tag = urllib.parse.quote(round)
            war_url = f"{base_url}/clanwarleagues/wars/{war_tag}"
            async with session.get(war_url, headers=headers) as response:
                if response.status != 200:
                    await ctx.send("Error fetching current CWL war data.")
                    return
                war_data = await response.json()
                active_war_data.append(war_data)
        
        
        # Step 4: Find our clan
        our_clan = None
        enemy_clan = None
        for active_war in active_war_data:
            our_clan = None
            enemy_clan = None
            for clan in ["clan", "opponent"]:
                if active_war.get(clan, {}).get("tag") == CLAN_TAG:
                    our_clan = active_war.get(clan)
                    enemy_clan = active_war.get("opponent" if clan == "clan" else "clan")
                    break
            if our_clan:
                break
            
        # Step 5: Process attack info
        attacked = []
        not_attacked = []

        for member in our_clan.get("members", []):
            name = member["name"]
            attacks = member.get("attacks", [])
            if attacks:
                attacked.append(name)
            else:
                not_attacked.append(name)

        # Step 6: Send embed
        embed = discord.Embed(
            title=f"CWL Attacks - {our_clan['name']} vs {enemy_clan['name']}",
            color=discord.Color.red()
        )

        embed.add_field(
            name="✅ Attacked",
            value="\n".join(attacked) if attacked else "None",
            inline=False
        )
        embed.add_field(
            name="❌ Not Yet Attacked",
            value="\n".join(not_attacked) if not_attacked else "None",
            inline=False
        )

        await ctx.send(embed=embed)

bot.run(DISCORD_BOT_TOKEN)