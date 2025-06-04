from discord import app_commands, Interaction
from discord.ext import commands
import discord
import aiohttp
import os
from dotenv import load_dotenv
import urllib.parse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load the .env file
load_dotenv()

# Get secrets from environment
COC_API_TOKEN = os.getenv("COC_API_TOKEN")
CLAN_TAG = os.getenv("CLAN_TAG")
encoded_clan_tag = urllib.parse.quote(CLAN_TAG)

headers = {
    "Authorization": f"Bearer {COC_API_TOKEN}"
}

class ClashBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @app_commands.command(name='claninfo', description='Shows Clan Info')
    async def claninfo(self, interaction: Interaction):
        logger.info(f"/claninfo invoked by {interaction.user} ({interaction.user.id}) in {interaction.guild.name}")
        await interaction.response.defer()
        
        url = f"https://api.clashofclans.com/v1/clans/{encoded_clan_tag}"
        headers = {"Authorization": f"Bearer {COC_API_TOKEN}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error("Failed to fetch clan data: HTTP %d", response.status)
                    await interaction.followup.send(f"Error fetching clan data: {response.status}")
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
            role = member.get('role', 'N/A').capitalize().replace('Admin', 'Elder')
            level = member.get('expLevel', 0)
            trophies = member.get('trophies', 0)
            donations = member.get('donations', 0)
            donations_rcv = member.get('donationsReceived', 0)

            embed.add_field(
                name=f"{name} ({role})",
                value=f"Level: {level} | \U0001F3C6 {trophies}\n\U0001F4E4 {donations} | \U0001F4E5 {donations_rcv}",
                inline=False
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name='nic', description='shows a juicy pic of nic')
    async def clanlogo(self, interaction: Interaction):
        embed = discord.Embed(
            title="nic",
            description="Here is our clan's glorious emblem!",
            color=discord.Color.gold()
        )
        embed.set_image(url="https://i.imgur.com/9ythM6n.png")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cwlstats", description="Displays CWL war statistics")
    async def cwlstats(self, interaction: Interaction):
        logger.info(f"/cwlstats invoked by {interaction.user} ({interaction.user.id}) in {interaction.guild.name}")
        await interaction.response.defer()
        
        BASE_URL = "https://api.clashofclans.com/v1"
        headers = {"Authorization": f"Bearer {COC_API_TOKEN}"}

        async with aiohttp.ClientSession() as session:
            league_url = f"{BASE_URL}/clans/{encoded_clan_tag}/currentwar/leaguegroup"
            async with session.get(league_url, headers=headers) as resp:
                if resp.status != 200:
                    logger.error("Failed to fetch CWL group data. Status: %s", resp.status)
                    await interaction.followup.send(f"Failed to fetch CWL group data. Status: {resp.status}")
                    return
                group_data = await resp.json()
                logger.info("Fetched CWL league group data")

            rounds = group_data.get("rounds", [])
            active_war_data = None
            active_war_tag = None

            for round_info in reversed(rounds):
                for tag in round_info.get("warTags", []):
                    if tag == "#0":
                        continue
                    encoded_tag = urllib.parse.quote(tag)
                    war_url = f"{BASE_URL}/clanwarleagues/wars/{encoded_tag}"
                    async with session.get(war_url, headers=headers) as war_resp:
                        if war_resp.status != 200:
                            logger.warning("Failed to fetch war data for tag %s. Status: %s", tag, war_resp.status)
                            continue
                        war_data = await war_resp.json()
                        if war_data.get("state") == "inWar" and war_data.get("clan", {}).get("tag") == CLAN_TAG:
                            active_war_data = war_data
                            active_war_tag = tag
                            logger.info("Active CWL war found: %s", tag)
                            break
                if active_war_data:
                    break

            if not active_war_data:
                logger.warning("No active CWL war found")
                await interaction.followup.send("No active CWL war found.")
                return

            clan_name = active_war_data["clan"]["name"]
            opponent_name = active_war_data["opponent"]["name"]
            clan_stars = active_war_data["clan"].get("stars", 0)
            opponent_stars = active_war_data["opponent"].get("stars", 0)
            clan_destruction = round(active_war_data["clan"].get("destructionPercentage", 0), 2)
            opponent_destruction = round(active_war_data["opponent"].get("destructionPercentage", 0), 2)
            war_end_time = int((parse_sc_time(active_war_data["endTime"]).timestamp()))
            
            embed = discord.Embed(
                title=f"CWL War: {clan_name} **{clan_stars}⭐ ({clan_destruction}%)** vs {opponent_name} **{opponent_stars}⭐({opponent_destruction}%)**",
                description=f"**War End Time:** <t:{war_end_time}:F> • __<t:{war_end_time}:R>__\n\n",
                color=discord.Color.dark_gold()
            )
            
            total_members = len(active_war_data["clan"].get("members", []))
            attacks_made = sum(1 for member in active_war_data["clan"]["members"] if "attacks" in member and member["attacks"])
            attacks_left = total_members - attacks_made
            
            embed.add_field(
                name="🗡️ Attacks Remaining",
                value=f"{attacks_left} / {total_members}",
                inline=False
)
            # Sort opponent members by mapPosition descending
            opponent_members = [
                m for m in active_war_data["opponent"]["members"]
                if "mapPosition" in m and "tag" in m
            ]
            
            # Sort descending: highest mapPosition = strongest base = #1
            opponent_sorted = reversed(sorted(opponent_members, key=lambda m: m["mapPosition"], reverse=True))

            # Create a map: tag → (name, rank)
            opponent_map = {
                member["tag"]: (member.get("name", "Unknown"), idx + 1)
                for idx, member in enumerate(opponent_sorted)
            }
                        
            # Step 3: Build attack summary with mapped defenders
            all_attacks = []
            for member in active_war_data["clan"].get("members", []):
                name = member.get("name", "Unknown")
                attacks = member.get("attacks",[])

                if not attacks:
                    embed.add_field(name=name, value="❌ Has not attacked yet", inline=False)
                    continue
                
                attacks[0]["name"] = name
                all_attacks.append(attacks[0])
            
            sorted_attacks = sorted(all_attacks, key=lambda a: (a["stars"],a["destructionPercentage"]), reverse=True)
            
            for attack in sorted_attacks:
                name = attack.get("name","Unknown")
                stars = attack.get("stars", 0)
                defender_tag = attack.get("defenderTag", "")
                destruction_percent = attack.get("destructionPercentage", 0)
                opp_name, opp_rank = opponent_map.get(defender_tag, ("Unknown", "??"))
                value = f"{'⭐' * stars} {stars} Stars [{destruction_percent}%] on {opp_name} (#{opp_rank})\n"
                embed.add_field(name=name, value=value, inline=False)

            await interaction.followup.send(embed=embed)

    @app_commands.command(name="cwlattacks", description="Lists which members have attacked in CWL")
    async def cwlattacks(self, interaction: Interaction):
        logger.info(f"/cwlattacks invoked by {interaction.user} ({interaction.user.id}) in {interaction.guild.name}")
        await interaction.response.defer()
        base_url = "https://api.clashofclans.com/v1"
        headers = {"Authorization": f"Bearer {COC_API_TOKEN}"}

        try:
            async with aiohttp.ClientSession() as session:
                league_url = f"{base_url}/clans/{encoded_clan_tag}/currentwar/leaguegroup"
                async with session.get(league_url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch CWL group data. Status: {response.status}")
                        await interaction.followup.send("Error fetching CWL group data.")
                        return
                    league_data = await response.json()

                rounds = league_data.get("rounds", [])
                valid_war_tags = []
                for round_info in reversed(rounds):
                    war_tags = round_info.get("warTags", [])
                    valid_tags = [tag for tag in war_tags if tag != "#0"]
                    if valid_tags:
                        valid_war_tags.append(valid_tags)

                if not valid_war_tags:
                    logger.warning("No valid CWL war tags found.")
                    await interaction.followup.send("No active war tags found.")
                    return

                active_war_tags = []
                for round in valid_war_tags:
                    war_tag = urllib.parse.quote(round[-1])
                    war_url = f"{base_url}/clanwarleagues/wars/{war_tag}"
                    async with session.get(war_url, headers=headers) as response:
                        if response.status != 200:
                            continue
                        war_data = await response.json()
                        if war_data.get("state") == "inWar":
                            active_war_tags = round
                            break

                active_war_data = []
                for war_tag in active_war_tags:
                    war_url = f"{base_url}/clanwarleagues/wars/{urllib.parse.quote(war_tag)}"
                    async with session.get(war_url, headers=headers) as response:
                        if response.status != 200:
                            continue
                        war_data = await response.json()
                        active_war_data.append(war_data)

                our_clan, enemy_clan = None, None
                for active_war in active_war_data:
                    for side in ["clan", "opponent"]:
                        if active_war.get(side, {}).get("tag") == CLAN_TAG:
                            our_clan = active_war[side]
                            enemy_clan = active_war["opponent" if side == "clan" else "clan"]
                            break
                    if our_clan:
                        break

                if not our_clan:
                    logger.warning("Could not find clan in active war data.")
                    await interaction.followup.send("Could not find your clan in the active wars.")
                    return

                attacked = []
                not_attacked = []
                for member in our_clan.get("members", []):
                    name = member["name"]
                    if member.get("attacks"):
                        attacked.append(name)
                    else:
                        not_attacked.append(name)

                logger.info(f"CWL attack status: {len(attacked)} attacked, {len(not_attacked)} not attacked")

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

                await interaction.followup.send(embed=embed)
                logger.info("CWL attack report sent successfully.")

        except Exception as e:
            logger.exception("Exception in /cwlattacks command:")
            await interaction.followup.send("An unexpected error occurred while processing the command.")

    @app_commands.command(name="cwlstandings", description="Displays current standings of all clans in the CWL group")
    async def cwlstandings(self, interaction: discord.Interaction):
        await interaction.response.defer()

        base_url = "https://api.clashofclans.com/v1"
        league_url = f"{base_url}/clans/{encoded_clan_tag}/currentwar/leaguegroup"
        headers = {"Authorization": f"Bearer {COC_API_TOKEN}"}

        async with aiohttp.ClientSession() as session:
            # Fetch league group
            async with session.get(league_url, headers=headers) as response:
                if response.status != 200:
                    await interaction.followup.send("Failed to fetch CWL group data.")
                    return
                group_data = await response.json()

            clan_stats = {clan["tag"]: {
                "name": clan["name"],
                "stars": 0,
                "destruction": 0,
                "wins": 0,
                "losses": 0,
                "battles": 0
            } for clan in group_data.get("clans", [])}

            # Go through rounds and wars
            for round_data in group_data.get("rounds", []):
                for war_tag in round_data.get("warTags", []):
                    if war_tag == "#0":
                        continue
                    encoded_tag = urllib.parse.quote(war_tag)
                    war_url = f"{base_url}/clanwarleagues/wars/{encoded_tag}"

                    async with session.get(war_url, headers=headers) as war_resp:
                        if war_resp.status != 200:
                            continue
                        war_data = await war_resp.json()

                        for side in ["clan", "opponent"]:
                            tag = war_data[side]["tag"]
                            if tag in clan_stats:
                                stats = clan_stats[tag]
                                stats["stars"] += war_data[side].get("stars", 0)
                                for member in war_data[side].get("members", []):
                                    for attack in member.get("attacks", []):
                                        stats["destruction"] += attack.get("destructionPercentage", 0)
                                if war_data.get("state") == "warEnded":
                                    stats["battles"] += 1
                                    
                        if war_data.get("state") != "warEnded":
                            continue

                        # Determine winner
                        clan = war_data["clan"]
                        opp = war_data["opponent"]
                        if clan["stars"] > opp["stars"] or (
                            clan["stars"] == opp["stars"] and clan["destructionPercentage"] > opp["destructionPercentage"]
                        ):
                            clan_stats[clan["tag"]]["wins"] += 1
                            clan_stats[opp["tag"]]["losses"] += 1
                        else:
                            clan_stats[opp["tag"]]["wins"] += 1
                            clan_stats[clan["tag"]]["losses"] += 1

            # Calculate average destruction and sort
            stats["destruction"] = round(stats["destruction"], 2)

            sorted_clans = sorted(clan_stats.values(), key=lambda c: (c["wins"], c["stars"], c["destruction"]), reverse=True)

            embed = discord.Embed(
                title="🏆 CWL Standings",
                description="Current League Rankings",
                color=discord.Color.blue()
            )

            for i, clan in enumerate(sorted_clans, 1):
                embed.add_field(
                    name=f"{i}. {clan['name']}",
                    value=(
                        f"✅ Wins: {clan['wins']} | ❌ Losses: {clan['losses']} | 🔄 Wars: {clan['battles']}\n"
                        f"⭐ Stars: {clan['stars']} | 💥 Destruction: {clan['destruction']}%"
                    ),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
    
def parse_sc_time(sc_time: str):
    return datetime.strptime(sc_time, "%Y%m%dT%H%M%S.%fZ")

async def setup(bot):
    await bot.add_cog(ClashBot(bot))