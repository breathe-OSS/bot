import discord
from discord.ext import commands
import aiohttp
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
BREATHE_API_URL = "https://api.breatheoss.app/aqi/{zone_id}"

def format_pollutant(pollutant):
    """Convert pollutant names to use Unicode subscript characters"""
    pollutant_upper = pollutant.upper()
    
    if 'PM2.5' in pollutant_upper:
        return pollutant_upper.replace('PM2.5', 'PM₂.₅')
    elif 'PM2_5' in pollutant_upper:
        return pollutant_upper.replace('PM2_5', 'PM₂.₅')
    elif 'PM10' in pollutant_upper:
        return pollutant_upper.replace('PM10', 'PM₁₀')
    elif 'NO2' in pollutant_upper:
        return pollutant_upper.replace('NO2', 'NO₂')
    elif 'SO2' in pollutant_upper:
        return pollutant_upper.replace('SO2', 'SO₂')
    elif 'CH4' in pollutant_upper:
        return pollutant_upper.replace('CH4', 'CH₄')
    else:
        return pollutant_upper

ZONE_DATA = [
    {"id": "anantnag_city", "name": "Anantnag", "emoji": "🏔️"},
    {"id": "bandipora_town", "name": "Bandipora", "emoji": "🏔️"},
    {"id": "baramulla_town", "name": "Baramulla", "emoji": "🏔️"},
    {"id": "doda_town", "name": "Doda", "emoji": "🏔️"},
    {"id": "ganderbal_town", "name": "Ganderbal", "emoji": "🏔️"},
    {"id": "handwara_town", "name": "Handwara", "emoji": "🏔️"},
    {"id": "jammu_city", "name": "Jammu", "emoji": "🏙️"},
    {"id": "kargil_town", "name": "Kargil", "emoji": "🏔️"},
    {"id": "katra_town", "name": "Katra", "emoji": "🏔️"},
    {"id": "kathua_town", "name": "Kathua", "emoji": "🏭"},
    {"id": "kishtwar_town", "name": "Kishtwar", "emoji": "🏔️"},
    {"id": "kulgam_town", "name": "Kulgam", "emoji": "🏔️"},
    {"id": "kupwara_town", "name": "Kupwara", "emoji": "🏔️"},
    {"id": "leh", "name": "Leh", "emoji": "🏙️"},
    {"id": "pahalgam_town", "name": "Pahalgam", "emoji": "🌲"},
    {"id": "poonch_town", "name": "Poonch", "emoji": "🏔️"},
    {"id": "pulwama_town", "name": "Pulwama", "emoji": "🏔️"},
    {"id": "rajouri_town", "name": "Rajouri", "emoji": "🏔️"},
    {"id": "ramban_town", "name": "Ramban", "emoji": "🏔️"},
    {"id": "reasi_town", "name": "Reasi", "emoji": "🏔️"},
    {"id": "samba_town", "name": "Samba", "emoji": "🏭"},
    {"id": "shopian_town", "name": "Shopian", "emoji": "🍎"},
    {"id": "sopore_town", "name": "Sopore", "emoji": "🏔️"},
    {"id": "srinagar", "name": "Srinagar", "emoji": "🏙️"},
    {"id": "udhampur_city", "name": "Udhampur", "emoji": "🏙️"}
]

class LocationSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=zone["name"], value=zone["id"], emoji=zone["emoji"])
            for zone in ZONE_DATA
        ]
        super().__init__(placeholder="Select a region...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        zone_id = self.values[0]
        await interaction.response.defer()

        try:
            data = await fetch_aqi_data(zone_id)
            if data:
                embed = create_aqi_embed(data)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("⚠️ Could not fetch data for this location")
        except Exception as e:
            await interaction.followup.send(f"⚠️ Error fetching data: {e}")

class DropdownView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(LocationSelect())

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

async def fetch_aqi_data(zone_id):
    """Fetch AQI data for a specific zone"""
    url = BREATHE_API_URL.format(zone_id=zone_id)
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            return await response.json()

def create_aqi_embed(data):
    """Create an embed from AQI data"""
    zone_name = data.get('zone_name', 'Unknown Location')
    aqi = data.get('aqi', 'N/A')
    us_aqi = data.get('us_aqi', 'N/A')
    pollutant = format_pollutant(data.get('main_pollutant', 'N/A'))
    
    raw_data = data.get('concentrations_raw_ugm3', {})
    temp = raw_data.get('temp', 'N/A')
    humidity = raw_data.get('humidity', 'N/A')
    
    pm2_5 = raw_data.get('pm2_5')
    pm10 = raw_data.get('pm10')
    no2 = raw_data.get('no2')
    so2 = raw_data.get('so2')
    co = raw_data.get('co')
    ch4 = raw_data.get('ch4')

    if isinstance(aqi, int):
        if aqi <= 50: color = 0x009966
        elif aqi <= 100: color = 0xffde33
        elif aqi <= 200: color = 0xff9933
        elif aqi <= 300: color = 0xcc0033
        elif aqi <= 400: color = 0x660099
        else: color = 0x7e0023
    else:
        color = 0x808080

    embed = discord.Embed(title=f"Breathe AQI: {zone_name}", color=color)
    
    embed.add_field(name="NAQI", value=f"**{aqi}**", inline=True)
    embed.add_field(name="US AQI", value=f"**{us_aqi}**", inline=True)
    embed.add_field(name="Primary Pollutant", value=f"**{pollutant}**", inline=True)
    
    concentrations = []
    if pm2_5 is not None:
        concentrations.append(f"**PM₂.₅**: `{pm2_5:.1f}` µg/m³")
    if pm10 is not None:
        concentrations.append(f"**PM₁₀**: `{pm10:.1f}` µg/m³")
    if no2 is not None:
        concentrations.append(f"**NO₂**: `{no2:.1f}` µg/m³")
    if so2 is not None:
        concentrations.append(f"**SO₂**: `{so2:.1f}` µg/m³")
    if co is not None:
        concentrations.append(f"**CO**: `{co/1000:.2f}` mg/m³")
    if ch4 is not None:
        concentrations.append(f"**CH₄**: `{ch4/1000:.2f}` mg/m³")
    
    if concentrations:
        embed.add_field(name="Pollutant Concentrations", value="\n".join(concentrations), inline=False)
    
    # Calculate cigarette equivalence
    if pm2_5 is not None:
        cigarettes = pm2_5 / 22
        embed.add_field(
            name="Equivalent PM₂.₅ inhalation today", 
            value=f"🚬 **{cigarettes:.2f}** cigarettes", 
            inline=False
        )
    
    if isinstance(temp, float):
        embed.add_field(name="Temperature", value=f"{temp:.1f}°C", inline=True)
    if isinstance(humidity, (int, float)):
        embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
    
    # Add last updated timestamp in IST
    timestamp = data.get('timestamp_unix')
    if timestamp:
        # Convert to IST
        ist = timezone(timedelta(hours=5, minutes=30))
        dt_ist = datetime.fromtimestamp(timestamp, tz=ist)
        time_str = dt_ist.strftime('%I:%M:%S %p')
        date_str = dt_ist.strftime('%d %b %Y')
        embed.add_field(name="Last Updated", value=f"{date_str}\n{time_str} IST", inline=True)

    source = data.get('source', 'Unknown Sensors')
    embed.set_footer(text=f"Data provided by {source}")
    
    return embed

def find_zone_by_name(location_name):
    """Find a zone by matching the location name (case insensitive)"""
    location_lower = location_name.lower()
    for zone in ZONE_DATA:
        if zone["name"].lower() == location_lower:
            return zone["id"]
    return None

def create_zones_embed():
    """Create an embed showing all available zones"""
    embed = discord.Embed(
        title="🌍 Available Locations",
        description="List of all the locations you can check for air quality data:",
        color=0x3498db
    )
    
    zones_text = "\n".join([f"{zone['emoji']} **{zone['name']}**" for zone in ZONE_DATA])
    
    embed.add_field(name="Regions", value=zones_text, inline=False)
    embed.set_footer(text=f"Total: {len(ZONE_DATA)} locations • Use /aqi or .aqi <location> to check air quality")
    
    return embed

@bot.command()
async def aqi(ctx, *locations):
    """Check AQI for one or more locations. Usage: .aqi OR .aqi jammu srinagar OR .aqi zones"""
    if not locations:
        view = DropdownView()
        await ctx.send("Select a region to check the real-time air quality:", view=view)
    elif len(locations) == 1 and locations[0].lower() == "zones":
        embed = create_zones_embed()
        await ctx.send(embed=embed)
    else:
        for location in locations:
            zone_id = find_zone_by_name(location)
            
            if not zone_id:
                await ctx.send(f"⚠️ Location '{location}' not found. Please check the spelling.")
                continue
            
            try:
                data = await fetch_aqi_data(zone_id)
                if data:
                    embed = create_aqi_embed(data)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"⚠️ Could not fetch data for {location}")
            except Exception as e:
                await ctx.send(f"⚠️ Error fetching data for {location}: {e}")

async def location_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[discord.app_commands.Choice[str]]:
    """Provide autocomplete suggestions for location names"""
    choices = [
        discord.app_commands.Choice(name=f"{zone['emoji']} {zone['name']}", value=zone['name'].lower())
        for zone in ZONE_DATA
        if current.lower() in zone['name'].lower()
    ]
    return choices[:25]

@bot.tree.command(name="aqi", description="Check real-time air quality for locations")
@discord.app_commands.describe(location="Select a location to check air quality")
@discord.app_commands.autocomplete(location=location_autocomplete)
async def aqi_slash(interaction: discord.Interaction, location: str = None):
    """Slash command to check AQI with autocomplete"""
    if not location:
        view = DropdownView()
        await interaction.response.send_message("Select a region to check the real-time air quality:", view=view)
    else:
        await interaction.response.defer()
        
        zone_id = find_zone_by_name(location)
        
        if not zone_id:
            await interaction.followup.send(f"⚠️ Location '{location}' not found. Please check the spelling.")
        else:
            try:
                data = await fetch_aqi_data(zone_id)
                if data:
                    embed = create_aqi_embed(data)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(f"⚠️ Could not fetch data for {location}")
            except Exception as e:
                await interaction.followup.send(f"⚠️ Error fetching data for {location}: {e}")

@bot.tree.command(name="zones", description="List all available locations for air quality monitoring")
async def zones_slash(interaction: discord.Interaction):
    """Slash command to show all available zones"""
    embed = create_zones_embed()
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"⚠️ Failed to sync commands: {e}")

bot.run(TOKEN)