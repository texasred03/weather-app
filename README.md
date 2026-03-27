# 🌤️ Retro Weather Channel Station
### Raspberry Pi 3B+ + WS2000 + Touchscreen

A Python-based weather display with a classic late-90s Weather Channel aesthetic. Runs in demo mode out of the box — configure `config.json` to go live. Also serves a full web dashboard accessible from any browser on your network.

---

## Hardware

**Required**
- Raspberry Pi
- Personal Weather Station registered on Weather Underground

**Recommended (Optional) display setup**
- **Touchscreen** -- Project will work as a web service, but a touchscreen is a nice touch ;)
- **Wall Mount** -- Somehow to mount the screen.  I repurposed a vivint security system display (more to come on that later)

---

## File Structure

```
weather_station/
├── config.json          # Your settings — edit this, not the Python files
├── requirements.txt     # Required python packages
├── main.py              # Entry point — run this
├── config.py            # Loads config.json, exposes CONFIG dict
├── helpers.py           # Colors, formatting helpers, demo data, ticker builder
├── rss_manager.py       # RSS news feed fetching (background thread)
├── data_manager.py      # WU station, forecast, and alerts fetching
├── tkinter_app.py       # Touchscreen UI — all 5 pages
├── flask_server.py      # Web dashboard — HTML template + Flask routes
├── icon_loader.py       # Loads weather icons from icons/ directory
└── icons/               # Your PNG weather icons go here
    ├── sunny.png
    ├── partly_cloudy.png
    ├── cloudy.png
    ├── rain.png
    ├── drizzle.png
    ├── showers.png
    ├── snow.png
    ├── tstorm.png
    ├── foggy.png
    ├── windy.png
    └── unknown.png      ← fallback for unrecognised conditions
```

**Rule of thumb for changes:**
- Touchscreen UI → edit `tkinter_app.py`
- Web dashboard → edit `flask_server.py`
- Colors, formatting → edit `helpers.py`
- Data sources → edit `data_manager.py`
- News feeds → edit `rss_manager.py`
- Your location, keys, settings → edit `config.json` only

---

## Installation

### 1. Set up a virtual environment
```bash
cd /opt/weather-app
python3 -m venv venv --system-site-packages
source venv/bin/activate
```

> `--system-site-packages` is required so the venv can access `python3-tk`, which is a system package.

### 2. Install system dependencies
```bash
sudo apt update
sudo apt install python3-tk -y
```

### 3. Install Python packages
```bash
pip install -r requirements.txt
```

> `requirements.txt` covers `requests`, `flask`, and `Pillow`. Tkinter is not listed — it is a system package handled by the `--system-site-packages` flag above.

### 4. Configure config.json
Edit `config.json` with your details — see the [config.json reference](#configjson-reference) below.

> **JSON rules:** no comments, no trailing commas, `true`/`false` lowercase, arrays use `[...]` not `(...)`.
> Validate anytime with: `python3 -m json.tool config.json`

### 5. Add weather icons
Create an `icons/` folder and add your PNG files. This repo contains a set of free to use icons:
```bash
mkdir /opt/weather-app/icons
```
Drop your PNGs in using the filenames listed in the file structure above. Any size PNG works — they are auto-resized to 64px for the current conditions page and 48px for the forecast page. Missing icons fall back to `unknown.png`, and if that's also missing, text labels are shown instead.

### 6. Run
```bash
# Web only (no screen attached)
python3 main.py --web-only

# With touchscreen (must be booted to desktop)
DISPLAY=:0 python3 main.py

# Point at a config file elsewhere
python3 main.py --web-only --config /path/to/config.json
```

Then open `http://<pi-ip>:5000` from any browser on your network.

---

## Configuration

### Getting your Weather Underground credentials
1. Register your weather station (if not already) at [wunderground.com](https://www.wunderground.com) → My Profile → My Devices → Add New Device
2. Get a free API key at [wunderground.com/member/api-keys](https://www.wunderground.com/member/api-keys)
3. Your Station ID is on your PWS dashboard (e.g. `KTXAMAR123`)

### Finding your NWS zone
1. Go to [weather.gov](https://www.weather.gov) and enter your city or ZIP code
2. On your local forecast page, look at the URL — it will contain your 3-letter office code (e.g. `AMX` for Amarillo)
3. Alternatively, go directly to [alerts.weather.gov/cap/us.php?x=0](https://alerts.weather.gov/cap/us.php?x=0), find your state, and look up your county zone code (format: 2-letter state + `Z` + 3 digits, e.g. `TXZ042`)

### Finding your NWS radar station
Go to [radar.weather.gov](https://radar.weather.gov), click your area — the 4-letter station ID (e.g. `KAMA` for Amarillo) appears in the URL.

### config.json reference

| Key | Default | Description |
|-----|---------|-------------|
| `wu_api_key` | `""` | Weather Underground API key |
| `wu_station_id` | `""` | Your PWS station ID (e.g. `KTXAMAR123`) |
| `latitude` | `40.7128` | Your latitude — used for forecast + web radar center |
| `longitude` | `-74.006` | Your longitude |
| `location_name` | `"YOUR CITY"` | Display name shown on screen and web UI |
| `timezone` | `"America/New_York"` | [TZ identifier](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) |
| `nws_zone` | `"NYZ072"` | NWS alert zone code |
| `nws_radar_station` | `"OKX"` | 4-letter NWS radar station ID (e.g. `KAMA`) |
| `fullscreen` | `false` | Set `true` for Pi touchscreen deployment |
| `screen_width` | `800` | Tkinter window width in pixels |
| `screen_height` | `480` | Tkinter window height in pixels |
| `demo_mode` | `true` | Use simulated data — set `false` once keys are entered |
| `web_enabled` | `true` | Enable Flask web server |
| `web_port` | `5000` | Web server port |
| `rss_feeds` | AP/Reuters/NPR/BBC/NASA | List of `["Label", "URL"]` pairs |
| `rss_max_per_feed` | `3` | Max headlines pulled per feed |
| `rss_refresh_sec` | `600` | RSS refresh interval in seconds (600 = 10 min) |

---

## Features

### Touchscreen (Tkinter) — `tkinter_app.py`

| Page | Description |
|------|-------------|
| **CURRENT** | Live station data — temp, humidity, wind, barometer, UV, solar radiation. Weather condition icon from your `icons/` folder. |
| **FORECAST** | 5-day forecast with condition icons and precipitation bars via Open-Meteo |
| **RADAR** | Live NWS radar image for your station, auto-refreshes every 2 minutes |
| **NEWS / ALERTS** | Live NWS weather alerts when active; otherwise shows latest RSS news headlines |
| **ALMANAC** | Sunrise/sunset, moon phase, historical records |

- Scrolling ticker shows live conditions, forecast, and RSS news headlines
- Alerts turn the ticker bar red and push alert text to the front
- Pages auto-rotate every 10 seconds; stops after manual tap
- Tap main area → advance to next page
- Tap nav bar → jump directly to that page
- `overrideredirect(True)` removes window chrome for clean kiosk display
- Weather icons loaded from `icons/` directory via `icon_loader.py` using Pillow

### Web Dashboard — `flask_server.py`

Accessible at `http://<pi-ip>:5000` from any device on your network.

- Current conditions with emoji weather icons
- 5-day forecast with precipitation bars
- **Live animated radar** — RainViewer tile map, 2-hour loop with play/pause/step controls, centered on your coordinates
- Weather alerts displayed as red banners when active
- Almanac — sunrise, sunset, moon phase, historical records
- News headlines panel
- Scrolling ticker with alert/weather/news priority logic
- Auto-refreshes every 60 seconds; live clock updates every second in JS
- **JSON API** at `/api/data` — raw data snapshot for integrations

---

## Autostart on Boot

### Web-only / headless Pi
```bash
sudo nano /etc/systemd/system/weather.service
```

```ini
[Unit]
Description=Retro Weather Station
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/opt/weather-app/venv/bin/python /opt/weather-app/main.py --web-only
WorkingDirectory=/opt/weather-app
Restart=always
RestartSec=10
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable weather.service
sudo systemctl start weather.service
sudo systemctl status weather.service
```

### With touchscreen (booted to desktop)
```ini
[Unit]
Description=Retro Weather Station
After=graphical.target

[Service]
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStart=/opt/weather-app/venv/bin/python /opt/weather-app/main.py
WorkingDirectory=/opt/weather-app
Restart=always
RestartSec=10
User=pi

[Install]
WantedBy=graphical.target
```

---

## Touchscreen Hardware Setup

### Waveshare 7" (HDMI — alternative)
Add to `/boot/config.txt`:
```
hdmi_group=2
hdmi_mode=87
hdmi_cvt=1024 600 60 6 0 0 0
hdmi_drive=1
```

Update `config.json`:
```json
"fullscreen":    true,
"screen_width":  1024,
"screen_height": 600
```

If the display renders as a small window in the corner despite correct resolution, the window manager may be interfering. The app uses `overrideredirect(True)` and `geometry("{W}x{H}+0+0")` to force exact placement — ensure your Pi is booted to desktop and the `DISPLAY` variable is set correctly.

---

## Customization

- **Colors** — edit the `COLORS` dict in `helpers.py`
- **Page rotation speed** — change `self.rotate_sec` in `RetroWeatherApp.__init__()` in `tkinter_app.py`
- **Ticker scroll speed** — change the `2` in `self.ticker_x -= 2` in `_tick_scroll()` in `tkinter_app.py`
- **Celsius** — change `temperature_unit=fahrenheit` to `celsius` in `_fetch_forecast()` in `data_manager.py`
- **Forecast days** — change `forecast_days=5` in `_fetch_forecast()` in `data_manager.py`
- **Add a page** — extend `PAGES` in `tkinter_app.py` and add a `_draw_yourpage()` method
- **Weather icons** — replace any PNG in `icons/` with your own; any size works, auto-resized on load

---

## Python Version Note

This project requires **Python 3.7+**. Raspberry Pi OS Buster ships with Python 3.7 — all code is compatible. The `venv` must be created with `--system-site-packages` to access the system `tkinter` package.

---

## APIs Used

| API | Key Required | Cost | Used For |
|-----|-------------|------|----------|
| Weather Underground PWS | Yes (free) | Free | Live station data |
| Open-Meteo | No | Free | 5-day forecast |
| NWS Weather.gov | No | Free | Weather alerts |
| NWS RIDGE2 | No | Free | Touchscreen radar image |
| RainViewer | No | Free (personal use) | Web radar animated map |
| RSS feeds | No | Free | News ticker |
| CartoDB | No | Free | Web radar map basemap |

---

*Built with Python 3.7+ · Tkinter · Flask · Pillow · Requests · Leaflet.js*
*Retro aesthetic inspired by The Weather Channel, circa 1998.*
