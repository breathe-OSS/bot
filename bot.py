import discord
from discord.ext import commands
import aiohttp
import asyncio
import difflib
import os
import json
import urllib.parse
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
BREATHE_API_URL = "https://api.breatheoss.app/aqi/{zone_id}"

# Load zone data from JSON
with open('zones.json', 'r', encoding='utf-8') as f:
    ZONE_DATA = json.load(f)

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

class LocationSelect(discord.ui.Select):
    def __init__(self, zones_chunk, placeholder="Select a region..."):
        options = [
            discord.SelectOption(label=zone["name"], value=zone["id"], emoji=zone["emoji"])
            for zone in zones_chunk
        ]
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        zone_id = self.values[0]
        await interaction.response.defer()

        try:
            data = await fetch_aqi_data(zone_id)
            if data:
                embed = await create_aqi_embed(data)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("⚠️ Could not fetch data for this location")
        except Exception as e:
            await interaction.followup.send(f"⚠️ Error fetching data: {e}")

class DropdownView(discord.ui.View):
    def __init__(self):
        super().__init__()
        chunk_size = 25
        chunks = [ZONE_DATA[i:i + chunk_size] for i in range(0, len(ZONE_DATA), chunk_size)]
        
        for chunk in chunks:
            if len(chunks) == 1:
                placeholder = "Select a region..."
            else:
                first_name = chunk[0]["name"]
                last_name = chunk[-1]["name"]
                placeholder = f"Select a region ({first_name} - {last_name})..."
            
            self.add_item(LocationSelect(chunk, placeholder=placeholder))

class BreatheBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session: aiohttp.ClientSession | None = None

    async def setup_hook(self):
        # Persistent HTTP session with a 5 second timeout for requests
        timeout = aiohttp.ClientTimeout(total=5)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
        await super().close()

intents = discord.Intents.default()
intents.message_content = True
bot = BreatheBot(command_prefix=".", intents=intents)

async def fetch_aqi_data(zone_id):
    """Fetch AQI data for a specific zone using persistent session and timeout"""
    url = BREATHE_API_URL.format(zone_id=zone_id)
    session = bot.session
    try:
        if session and not session.closed:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                return await response.json()
        else:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as temp_session:
                async with temp_session.get(url) as response:
                    if response.status != 200:
                        return None
                    return await response.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None

async def fetch_sensor_info():
    """Fetch all sensor hardware information using persistent session and timeout"""
    url = "https://api.breatheoss.app/sensor-info"
    session = bot.session
    try:
        if session and not session.closed:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                return await response.json()
        else:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as temp_session:
                async with temp_session.get(url) as response:
                    if response.status != 200:
                        return None
                    return await response.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return None

class MoreInfoView(discord.ui.View):
    def __init__(self, zone_names):
        super().__init__(timeout=None)
        self.zone_names = [z.lower() for z in zone_names]

    @discord.ui.button(label="Sensor Information", style=discord.ButtonStyle.secondary, emoji="📊")
    async def more_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        data = await fetch_sensor_info()
        
        if not data or "sensors" not in data:
            await interaction.followup.send("⚠️ Could not fetch sensor information.", ephemeral=True)
            return
            
        matching_sensors = [s for s in data["sensors"] if s.get("zone", "").lower() in self.zone_names]
        
        if not matching_sensors:
            await interaction.followup.send("No detailed hardware info available for these locations.", ephemeral=True)
            return
            
        embed = discord.Embed(title="📊 Sensor Hardware Details", color=0x3498db)
        
        for s in matching_sensors:
            name = s.get("name", "Unknown Node")
            provider = s.get("provider", "N/A")
            model = s.get("model", "N/A")
            date = s.get("installation_date", "N/A")
            embed.add_field(name=f"📍 {name}", value=f"**Provider:** {provider}\n**Model:** {model}\n**Installed:** {date}", inline=False)
            
        await interaction.followup.send(embed=embed, ephemeral=True)

def get_us_aqi_category(us_aqi):
    """Generate US AQI category label"""
    if not isinstance(us_aqi, int):
        return "N/A"
    
    if us_aqi <= 50:
        return "Good"
    elif us_aqi <= 100:
        return "Moderate"
    elif us_aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    elif us_aqi <= 200:
        return "Unhealthy"
    elif us_aqi <= 300:
        return "Very Unhealthy"
    else:
        return "Hazardous"

async def create_aqi_embed(data):
    """Create an embed from AQI data"""
    zone_name = data.get('zone_name', 'Unknown Location')
    aqi = data.get('aqi', 'N/A')
    us_aqi = data.get('us_aqi', 'N/A')
    pollutant = format_pollutant(data.get('main_pollutant', 'N/A'))
    
    us_units = data.get('concentrations_us_units', {})
    
    # Get latest temp and humidity from history
    history = data.get('history', [])
    if history and len(history) > 0:
        latest = history[-1]
        temp = latest.get('temp', 'N/A')
        humidity = latest.get('humidity', 'N/A')
    else:
        temp = 'N/A'
        humidity = 'N/A'
    
    pm2_5 = us_units.get('pm2_5')
    pm10 = us_units.get('pm10')
    no2 = us_units.get('no2')
    so2 = us_units.get('so2')
    co = us_units.get('co')
    ch4 = us_units.get('ch4')

    # Color based on US AQI
    if isinstance(us_aqi, int):
        if us_aqi <= 50: color = 0x00e400
        elif us_aqi <= 100: color = 0xffff00
        elif us_aqi <= 150: color = 0xff7e00
        elif us_aqi <= 200: color = 0xff0000
        elif us_aqi <= 300: color = 0x8f3f97
        else: color = 0x7e0023
    else:
        color = 0x808080

    embed = discord.Embed(title=f"Breathe AQI: {zone_name}", url="https://breatheoss.app", color=color)
    
    embed.add_field(name="NAQI", value=f"**{aqi}**", inline=True)
    embed.add_field(name="US AQI", value=f"**{us_aqi}**", inline=True)
    embed.add_field(name="Primary Pollutant", value=f"**{pollutant}**", inline=True)
    
    # Add AQI category
    category = get_us_aqi_category(us_aqi)
    if category != "N/A":
        embed.add_field(name=category, value="*Label based on US AQI*", inline=False)
    
    concentrations = []
    if pm2_5 is not None:
        concentrations.append(f"**PM₂.₅**: `{pm2_5:.1f}` µg/m³")
    if pm10 is not None:
        concentrations.append(f"**PM₁₀**: `{pm10:.1f}` µg/m³")
    if no2 is not None:
        concentrations.append(f"**NO₂**: `{no2 * 1.88:.1f}` µg/m³")
    if so2 is not None:
        concentrations.append(f"**SO₂**: `{so2 * 2.62:.1f}` µg/m³")
    if co is not None:
        concentrations.append(f"**CO**: `{co * 1.145:.2f}` mg/m³")
    if ch4 is not None:
        concentrations.append(f"**CH₄**: `{ch4 * 0.654:.2f}` mg/m³")
    
    if concentrations:
        embed.add_field(name="Pollutant Concentrations", value="\n".join(concentrations), inline=False)
    
    # Calculate cigarette equivalence
    pm2_5_24h = data.get('averages_24h', {}).get('pm2_5')
    cig_pm2_5 = pm2_5_24h if pm2_5_24h is not None else pm2_5
    
    if cig_pm2_5 is not None:
        cigarettes = cig_pm2_5 / 22
        embed.add_field(
            name="Equivalent PM₂.₅ inhalation today", 
            value=f"🚬 **≈ {cigarettes:.2f}** cigarettes", 
            inline=False
        )
    
    if isinstance(temp, float):
        embed.add_field(name="Temperature", value=f"{temp:.1f}°C", inline=True)
    if isinstance(humidity, (int, float)):
        embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
    
    nodes = data.get('nodes', {})
    if nodes:
        for node_name, node_data in nodes.items():
            node_aqi = node_data.get('aqi', 'N/A')
            node_us_aqi = node_data.get('us_aqi', 'N/A')
            node_pm25 = node_data.get('pm2_5', 'N/A')
            node_pm10 = node_data.get('pm10', 'N/A')
            
            pm25_str = f"{node_pm25:.1f}" if isinstance(node_pm25, (int, float)) else str(node_pm25)
            pm10_str = f"{node_pm10:.1f}" if isinstance(node_pm10, (int, float)) else str(node_pm10)
            
            node_text = f"NAQI: **{node_aqi}** • US AQI: **{node_us_aqi}**\nPM₂.₅: `{pm25_str}` µg/m³ • PM₁₀: `{pm10_str}` µg/m³"
            embed.add_field(name=f"📍 {node_name}", value=node_text, inline=False)

    # Add last updated timestamp in IST
    timestamp = data.get('timestamp_unix')
    if timestamp:
        # Convert to IST
        ist = timezone(timedelta(hours=5, minutes=30))
        dt_ist = datetime.fromtimestamp(timestamp, tz=ist)
        time_str = dt_ist.strftime('%I:%M:%S %p')
        date_str = dt_ist.strftime('%d %b %Y')
        embed.add_field(name="Last Updated", value=f"{date_str}\n{time_str} IST", inline=True)

    chart_url = await fetch_quickchart_url(data)
    if chart_url:
        embed.set_image(url=chart_url)

    embed.set_footer(text="Visit breatheoss.app for more info")
    
    return embed

NODE_COLORS = ["#e74c3c", "#2ecc71", "#f1c40f", "#9b59b6", "#e67e22", "#1abc9c", "#e84393"]

async def fetch_quickchart_url(data) -> str | None:
    history = data.get('history', [])
    if not history or len(history) < 2:
        return None

    ist = timezone(timedelta(hours=5, minutes=30))
    times = [datetime.fromtimestamp(h['ts'], tz=ist).strftime('%H:%M') for h in history]
    
    zone_name = data.get('zone_name', 'Location')
    zone_us_aqi = [h.get('us_aqi', 0) for h in history]
    source = data.get('source', '').lower()
    is_airgradient = 'airgradient' in source
    nodes = data.get('nodes', {})
    node_count = len(nodes) if isinstance(nodes, dict) else 0

    if is_airgradient:
        if node_count > 1:
            primary_label = "Overall Zone Avg"
        elif node_count == 1:
            primary_label = list(nodes.keys())[0]
        else:
            primary_label = zone_name
    else:
        primary_label = "Overall Zone Avg"

    has_multiple_nodes = is_airgradient and node_count > 1
    
    datasets = [{
        "label": primary_label,
        "data": zone_us_aqi,
        "borderColor": "#3498db",
        "backgroundColor": "rgba(52, 152, 219, 0.08)",
        "borderWidth": 4,
        "pointRadius": 0,
        "fill": True,
        "tension": 0.35
    }]

    if has_multiple_nodes:
        ts_map = {h['ts']: i for i, h in enumerate(history)}
        
        for idx, (node_name, node_info) in enumerate(nodes.items()):
            node_history = node_info.get('history', []) if isinstance(node_info, dict) else []
            if not node_history:
                continue
                
            node_data = [None] * len(history)
            for nh in node_history:
                ts = nh.get('ts')
                if ts in ts_map:
                    node_data[ts_map[ts]] = nh.get('us_aqi')
            
            color = NODE_COLORS[idx % len(NODE_COLORS)]
            datasets.append({
                "label": f"{node_name} Node",
                "data": node_data,
                "borderColor": color,
                "borderWidth": 2,
                "pointRadius": 2,
                "pointBackgroundColor": color,
                "fill": False,
                "tension": 0.35,
                "spanGaps": True
            })

    has_nodes = len(datasets) > 1

    chart_config = {
        "type": "line",
        "data": {
            "labels": times,
            "datasets": datasets
        },
        "options": {
            "title": {
                "display": True,
                "text": f"24-Hour US AQI Trend — {data.get('zone_name', 'Location')}",
                "fontColor": "#ffffff",
                "fontSize": 14
            },
            "legend": {
                "display": has_nodes,
                "position": "bottom",
                "labels": {
                    "fontColor": "#ffffff",
                    "fontSize": 11,
                    "boxWidth": 12
                }
            },
            "scales": {
                "xAxes": [{
                    "gridLines": {"color": "rgba(255, 255, 255, 0.1)"},
                    "ticks": {"fontColor": "#aaaaaa", "maxTicksLimit": 8}
                }],
                "yAxes": [{
                    "gridLines": {"color": "rgba(255, 255, 255, 0.1)"},
                    "ticks": {"fontColor": "#aaaaaa", "beginAtZero": True}
                }]
            }
        }
    }

    payload = {
        "backgroundColor": "#1e1f22",
        "width": 650,
        "height": 300,
        "format": "png",
        "chart": chart_config
    }

    session = bot.session
    try:
        if session and not session.closed:
            async with session.post("https://quickchart.io/chart/create", json=payload, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                if resp.status == 200:
                    res_data = await resp.json()
                    if res_data.get("success") and "url" in res_data:
                        return res_data["url"]
    except Exception:
        pass

    encoded_config = urllib.parse.quote(json.dumps(chart_config, separators=(',', ':')))
    fallback_url = f"https://quickchart.io/chart?c={encoded_config}&bg=1e1f22&w=650&h=300&v=2.9"
    if len(fallback_url) <= 2048:
        return fallback_url
    return None

def find_zone_by_name(location_name):
    """Find a zone by matching location name, ID using exact substring or fuzzy matching"""
    if not location_name:
        return None

    location_lower = location_name.strip().lower()

    for zone in ZONE_DATA:
        if zone["name"].lower() == location_lower or zone["id"].lower() == location_lower:
            return zone["id"]

    for zone in ZONE_DATA:
        zname = zone["name"].lower()
        zid = zone["id"].lower()
        if zname.startswith(location_lower) or zid.startswith(location_lower) or location_lower in zname or location_lower in zid:
            return zone["id"]

    zone_names_map = {zone["name"].lower(): zone["id"] for zone in ZONE_DATA}
    matches = difflib.get_close_matches(location_lower, zone_names_map.keys(), n=1, cutoff=0.6)
    if matches:
        return zone_names_map[matches[0]]

    return None

def create_zones_embed():
    """Create an embed showing all available zones"""
    embed = discord.Embed(
        title="🌍 Available Locations",
        url="https://breatheoss.app",
        description="List of all the locations you can check for air quality data:",
        color=0x3498db
    )
    
    zones_text = "\n".join([f"{zone['emoji']} **{zone['name']}**" for zone in ZONE_DATA])
    
    embed.add_field(name="Regions", value=zones_text, inline=False)
    embed.set_footer(text="Visit breatheoss.app for more info")
    
    return embed

@bot.command()
@commands.cooldown(15, 60, commands.BucketType.user)
async def aqi(ctx, *locations):
    """Check AQI for one or more locations. Usage: .aqi OR .aqi jammu srinagar OR .aqi zones"""
    if not locations:
        view = DropdownView()
        await ctx.send("Select a region to check the real-time air quality:", view=view)
    elif len(locations) == 1 and locations[0].lower() == "zones":
        embed = create_zones_embed()
        await ctx.send(embed=embed)
    else:
        if len(locations) > 3:
            await ctx.send("⚠️ You can only request up to 3 locations at a time.")
            return

        embeds = []
        zone_names_found = []
        has_ag = False
        not_found = False
        fetch_error = False

        for location in locations:
            zone_id = find_zone_by_name(location)
            
            if not zone_id:
                not_found = True
                continue
                
            zone_name = next((z["name"] for z in ZONE_DATA if z["id"] == zone_id), location)
            
            try:
                data = await fetch_aqi_data(zone_id)
                if data:
                    embeds.append(await create_aqi_embed(data))
                    zone_names_found.append(zone_name)
                    if "airgradient" in data.get("source", "").lower():
                        has_ag = True
                else:
                    fetch_error = True
            except Exception:
                fetch_error = True
                
        if embeds:
            view = MoreInfoView(zone_names_found) if has_ag else discord.utils.MISSING
            for i, embed in enumerate(embeds):
                if i == len(embeds) - 1:
                    await ctx.send(embed=embed, view=view)
                else:
                    await ctx.send(embed=embed)
            
        if not_found:
            await ctx.send("⚠️ One or more requested locations were not found. Please check the spelling or use the `/zones` command to see the available list.")
        elif fetch_error:
            await ctx.send("⚠️ Error fetching data for one or more locations.")

@aqi.error
async def aqi_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ **Slow down!** Please wait {error.retry_after:.1f} seconds before checking the AQI again.")

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
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.checks.cooldown(15, 60, key=lambda i: i.user.id)
async def aqi_slash(interaction: discord.Interaction, location: str = None):
    """Slash command to check AQI with autocomplete"""
    if not location:
        view = DropdownView()
        await interaction.response.send_message("Select a region to check the real-time air quality:", view=view)
    else:
        await interaction.response.defer()
        
        zone_id = find_zone_by_name(location)
        
        if not zone_id:
            await interaction.followup.send(f"⚠️ Location '{location}' not found. Please check the spelling or use the `/zones` command to see the available list.")
        else:
            try:
                data = await fetch_aqi_data(zone_id)
                if data:
                    embed = await create_aqi_embed(data)
                    zone_name = next((z["name"] for z in ZONE_DATA if z["id"] == zone_id), location)
                    view = MoreInfoView([zone_name]) if "airgradient" in data.get("source", "").lower() else discord.utils.MISSING
                    await interaction.followup.send(embed=embed, view=view)
                else:
                    await interaction.followup.send(f"⚠️ Could not fetch data for {location}")
            except Exception as e:
                await interaction.followup.send(f"⚠️ Error fetching data for {location}: {e}")

@aqi_slash.error
async def aqi_slash_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ **Slow down!** Please wait {error.retry_after:.1f} seconds before checking the AQI again.", ephemeral=True)

@bot.tree.command(name="zones", description="List all available locations for air quality monitoring")
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
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

if __name__ == "__main__":
    bot.run(TOKEN)