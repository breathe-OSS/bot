# Breathe (Discord Bot)

> _"Breathe, breathe in the air. Don't be afraid to care."_ - **Pink Floyd**, _The Dark Side of the Moon_

<p align="center">
  <img src="https://breatheoss.app/assets/images/logo.png" alt="App Icon" width="128"/>
</p>

> **Note:** This repository contains the **Discord bot** for Breathe. Live web version is at [breatheoss.app](https://breatheoss.app). Check out our [Web](https://github.com/breathe-OSS/site), [Android](https://github.com/breathe-OSS/breathe), and [iOS](https://github.com/breathe-OSS/breathe-ios) repositories.

**Breathe Discord Bot** is a modern Discord bot designed to bring real-time Air Quality Index (AQI) monitoring across J&K & Ladakh directly into Discord servers. Built with **Python** and **discord.py**, it provides instant access to air quality data, interactive paginated location selectors, smart location fuzzy matching, and 24-hour multi-line trend graphs.

- Check the [**breathe api**](https://github.com/breathe-OSS/api?tab=readme-ov-file#how-the-aqi-is-calculated) repo to know how the AQI is calculated.

---

## Features

- **Slash Command Support & Autocomplete** (`/aqi`, `/zones`)
- **Prefix Command Support** (`.aqi`, `.aqi jammu srinagar`, `.aqi zones`)
- **Interactive Paginated Dropdowns** (Scales dynamically into multiple select menus past Discord's 25-option limit)
- **Fuzzy & Substring Location Matching** (Handles shorthands like `.aqi srina` or typos like `.aqi srinagr` using `difflib`)
- **24-Hour Multi-Line Trend Graphs** (Powered by QuickChart.io, rendering overall zone averages alongside individual sensor nodes)
- **US & Indian NAQI Standards Support** (Calculates NAQI, US AQI, and pollutant concentrations for PM₂.₅, PM₁₀, NO₂, SO₂, CO, CH₄)
- **Cigarette Equivalence Calculation** (Displays equivalent daily PM₂.₅ inhalation in cigarettes)
- **Detailed Hardware Info Modal** (View provider, model, and installation date for AirGradient sensor nodes)
- **High-Performance Architecture** (Persistent `aiohttp.ClientSession` with 5-second request timeouts and fallback handling)

---

## Tech Stack

- **Language:** Python 3.10+
- **Library:** `discord.py` 2.x
- **Networking:** `aiohttp` (Async HTTP Client)
- **Visualization:** QuickChart.io (Serverless Chart.js PNG rendering)
- **Fuzzy Matching:** `difflib`

---

## Project Structure

```breathe-discord/
├── bot.py             # Main application entry point & bot commands
├── zones.json         # Region mappings, zone IDs, and emojis
├── requirements.txt   # Python dependencies
└── .env               # Discord Bot Token configuration
```

---

## Build and Deploy Locally

### Prerequisites

- Python 3.10 or newer
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))
- A running instance of the **Breathe API** (`https://api.breatheoss.app`)

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/breathe-OSS/bot && cd bot
   ```

2. **Set up a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the project root:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

5. **Run the bot:**
   ```bash
   python3 bot.py
   ```

---

## AQI Data Providers

### Why this exists

Publicly available AQI data for the J&K & Ladakh region is currently unreliable. Most standardized sources rely on sparse sensor networks or algorithmic modeling that does not accurately reflect ground-level realities. This results in widely varying values across different platforms. **Google**, for example, shows values that are insanely **low**, but they are usually off by a huge margin.

**Breathe** aims to solve this by strictly curating sources and building a ground-truth network.

---

## Current Data Sources

### Open-Meteo

Used for all pollutant values for **most regions** in J&K & Ladakh.
Open-Meteo's satellite-based air quality model provides stable and consistent values that generally fall within the expected range of nearby ground measurements.

- Air quality & pollutant data: [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api)
- Weather forecasts & historical data: [Open-Meteo](https://open-meteo.com)

### AirGradient

Used for regions where physical ground sensors are deployed in real time.

- Their website: [AirGradient](https://www.airgradient.com/)

This provides accurate values of PM₁₀ and PM₂.₅. Other values are fetched from Open-Meteo (like O₃ and NO₂).

---

## Call for Contributors (Hardware)

The limitation of our current project is that we do not have ground sensors in every region and are mostly relying on satellite data, so the data is **not 100%** accurate.

We are actively working to deploy custom physical sensors to improve data density. If you are interested in hosting a sensor node, please contact us at: [contact@breatheoss.app](mailto:contact@breatheoss.app)

We have deployed **AirGradient** sensors in Jammu, Srinagar, Leh, Rajouri, Doda, Samba, Udhampur & Bandipora which provide an accurate measurement of PM₁₀ and PM₂.₅ values. We are working to deploy them in all other regions.

---

## Credits & Developers

This project is fully Free & Open Source Software (FOSS).

1. [sidharthify](https://github.com/sidharthify) (Lead Dev)
2. [Flashwreck](https://github.com/Flashwreck) (Lead dev and devops maintainer)
3. [SleeperOfSaturn](https://github.com/SleeperOfSaturn) (iOS app co-lead)
4. [Lostless1907](https://github.com/Lostless1907) (Contributor and developer)
5. [suveshmoza](https://github.com/suveshmoza) (Contributor and developer)
6. [empirea9](https://github.com/empirea9) (Contributor)
