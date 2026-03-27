"""
config.py — loads config.json and exposes CONFIG dict.
All other modules import CONFIG from here.
"""

import json
import os

CONFIG_DEFAULTS = {
    "wu_api_key":        "",
    "wu_station_id":     "",
    "latitude":          40.7128,
    "longitude":        -74.0060,
    "location_name":     "YOUR CITY",
    "timezone":          "America/New_York",
    "nws_zone":          "NYZ072",
    "nws_zone_id":       "TXZ017",   # e.g. TXZ017 for Randall County TX
    "nws_radar_station": "OKX",
    "fullscreen":        False,
    "screen_width":      800,
    "screen_height":     480,
    "demo_mode":         True,
    "web_enabled":       True,
    "web_port":          5000,
    "rss_feeds": [
        ("AP NEWS", "https://feeds.apnews.com/rss/apf-topnews"),
        ("REUTERS", "https://feeds.reuters.com/reuters/topNews"),
        ("NPR",     "https://feeds.npr.org/1001/rss.xml"),
        ("BBC",     "https://feeds.bbci.co.uk/news/rss.xml"),
        ("NASA",    "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
    ],
    "rss_max_per_feed":  3,
    "rss_refresh_sec":   600,
}


def load_config(path=None):
    """
    Load config.json and merge with defaults.
    Searches next to this file, then cwd, unless path is given explicitly.
    Returns the merged CONFIG dict.
    """
    cfg = dict(CONFIG_DEFAULTS)

    if path:
        search = [path]
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        search = [
            os.path.join(here, "config.json"),
            os.path.join(os.getcwd(), "config.json"),
        ]

    for p in search:
        if os.path.exists(p):
            try:
                with open(p) as f:
                    data = json.load(f)
                user = {k: v for k, v in data.items() if not k.startswith("_")}
                if "rss_feeds" in user:
                    user["rss_feeds"] = [tuple(x) for x in user["rss_feeds"]]
                cfg.update(user)
                print(f"Config loaded from {p}")
            except Exception as e:
                print(f"Warning: could not read {p}: {e}")
            break
    else:
        print("Warning: config.json not found — using built-in defaults")

    return cfg


# Module-level CONFIG — imported by all other modules.
# main.py may call reload_config() after parsing --config arg.
CONFIG = load_config()


def reload_config(path):
    """Reload CONFIG in-place from a specific file path."""
    global CONFIG
    try:
        with open(path) as f:
            data = json.load(f)
        user = {k: v for k, v in data.items() if not k.startswith("_")}
        if "rss_feeds" in user:
            user["rss_feeds"] = [tuple(x) for x in user["rss_feeds"]]
        CONFIG.update(user)
        print(f"Config reloaded from {path}")
    except Exception as e:
        print(f"Error loading config from {path}: {e}")
