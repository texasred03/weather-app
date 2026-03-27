"""
helpers.py — shared constants, formatting helpers, and demo data generators.
"""

import time
import math
import random
import datetime

# ─────────────────────────────────────────────
#  RETRO COLOR PALETTE  (classic Weather Channel)
# ─────────────────────────────────────────────
COLORS = {
    "bg_dark":      "#0a0f1e",
    "bg_mid":       "#0d1a2e",
    "bg_panel":     "#0f2040",
    "accent_blue":  "#1a6ab5",
    "accent_cyan":  "#00d4ff",
    "accent_teal":  "#00b4b4",
    "accent_gold":  "#f0b429",
    "accent_red":   "#e63946",
    "accent_green": "#2ecc71",
    "text_white":   "#f0f4ff",
    "text_dim":     "#7a9bbf",
    "text_bright":  "#ffffff",
    "temp_hot":     "#ff6b35",
    "temp_warm":    "#f0b429",
    "temp_cool":    "#4fc3f7",
    "temp_cold":    "#7c9cbf",
    "alert_bg":     "#8b0000",
    "alert_text":   "#ffcc00",
    "ticker_bg":    "#001a40",
    "ticker_text":  "#00d4ff",
    "ticker_news":  "#f0f4ff",
    "ticker_label": "#f0b429",
    "ticker_alert": "#ffcc00",
    "grid_line":    "#1a3050",
    "scanline":     "#050a14",
}

# ─────────────────────────────────────────────
#  FORMATTING HELPERS
# ─────────────────────────────────────────────
def temp_color(f):
    if f >= 90: return COLORS["temp_hot"]
    if f >= 70: return COLORS["temp_warm"]
    if f >= 50: return COLORS["temp_cool"]
    return COLORS["temp_cold"]

def wind_dir_label(deg):
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE",
            "S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return dirs[int((deg + 11.25) / 22.5) % 16]

def baro_trend(val):
    if val > 30.10: return "▲ HIGH"
    if val > 29.80: return "— STEADY"
    return "▼ LOW"

# ─────────────────────────────────────────────
#  SAFE STATION VALUE
#  WU can return None for sensors not yet reported.
# ─────────────────────────────────────────────
STATION_DEFAULTS = {
    "tempf":          60.0,
    "feelslike":      60.0,
    "dewpoint":       50.0,
    "humidity":       50.0,
    "baromrelin":     29.92,
    "windspeedmph":   0.0,
    "windgustmph":    0.0,
    "winddir":        0,
    "raintoday":      0.0,
    "uv":             0,
    "solarradiation": 0.0,
}

def sval(station_data, key):
    """Return station value, substituting the safe default if None or missing."""
    v = station_data.get(key)
    if v is None:
        return STATION_DEFAULTS.get(key, 0)
    return v

# ─────────────────────────────────────────────
#  TICKER SEGMENT BUILDER
#  Shared by both Tkinter app and Flask server.
# ─────────────────────────────────────────────
def build_ticker_segments(data, location_name):
    """
    Build ticker as a list of (type, text) segments.
    Types: 'weather', 'label', 'news', 'alert', 'sep'
    """
    
    al   = data["alerts"]
    news = data.get("rss", [])
    sep  = ("sep", " · ")
    
    segs = []
    
    if al:
        for alert in al:
            segs += [
                ("alert", f"  *** ALERT: {alert['event']}  "),
                ("alert", f"{alert['headline']}  ***  "),
                sep,
            ]
    elif news:
        segs.append(("weather", "  -- IN THE NEWS --  "))
        segs.append(sep)
        for label, headline in news:
            segs += [("label", f"  {label} ▸ "), ("news", f"{headline}  "), sep]

    return segs

# ─────────────────────────────────────────────
#  DEMO / MOCK DATA
# ─────────────────────────────────────────────
def get_demo_station_data():
    t = time.time()
    return {
        "tempf":          68.4 + 2 * math.sin(t / 3600),
        "humidity":       62 + 5 * math.sin(t / 1800),
        "baromrelin":     29.92 + 0.1 * math.sin(t / 7200),
        "windspeedmph":   max(0, 8 + 4 * math.sin(t / 600) + random.uniform(-1, 1)),
        "windgustmph":    max(0, 14 + 3 * math.sin(t / 400)),
        "winddir":        int((180 + 90 * math.sin(t / 900)) % 360),
        "raintoday":      0.12,
        "uv":             3,
        "solarradiation": 420,
        "feelslike":      66.1,
        "dewpoint":       52.3,
        "lastRain":       "2h ago",
    }

def get_demo_forecast():
    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    icons        = ["SUNNY", "P.CLOUDY", "RAIN", "P.CLOUDY", "SUNNY"]
    descriptions = ["Sunny", "Partly Cloudy", "Rain Showers", "Mostly Cloudy", "Clear"]
    highs  = [72, 68, 61, 65, 74]
    lows   = [55, 52, 50, 48, 53]
    precip = [5, 20, 75, 35, 10]
    today  = datetime.date.today()
    result = []
    for i in range(5):
        d = today + datetime.timedelta(days=i)
        result.append({
            "day":         "TODAY" if i == 0 else days[d.weekday()],
            "date":        d.strftime("%b %d"),
            "icon":        icons[i],
            "description": descriptions[i],
            "high":        highs[i],
            "low":         lows[i],
            "precip":      precip[i],
        })
    return result

def get_demo_alerts():
    return []

def get_demo_almanac():
    return {
        "sunrise":           "6:42 AM",
        "sunset":            "7:28 PM",
        "moonphase":         "First Quarter",
        "high_record":       85,
        "high_record_year":  1998,
        "low_record":        28,
        "low_record_year":   1967,
        "avg_high":          71,
        "avg_low":           52,
        "avg_precip":        0.14,
    }
