"""
data_manager.py — fetches station, forecast, and alert data. Runs in a background thread.
"""

import threading
import time
import datetime

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from config import CONFIG
from helpers import (
    get_demo_station_data, get_demo_forecast,
    get_demo_alerts, get_demo_almanac,
)


class WeatherDataManager:

    def __init__(self, rss_mgr=None):
        self.station_data = get_demo_station_data()
        self.forecast     = get_demo_forecast()
        self.alerts       = get_demo_alerts()
        self.almanac      = get_demo_almanac()
        self.last_update  = datetime.datetime.now()
        self.lock         = threading.Lock()
        self._running     = True
        self.rss_mgr      = rss_mgr

    def start(self):
        t = threading.Thread(target=self._update_loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    def get(self):
        with self.lock:
            return {
                "station":     self.station_data.copy(),
                "forecast":    list(self.forecast),
                "alerts":      list(self.alerts),
                "almanac":     self.almanac.copy(),
                "last_update": self.last_update,
                "rss":         self.rss_mgr.get_ticker_segments() if self.rss_mgr else [],
            }

    # ── Private ────────────────────────────────
    def _update_loop(self):
        while self._running:
            self._fetch_all()
            time.sleep(60)

    def _fetch_all(self):
        self._fetch_station()
        self._fetch_forecast()
        self._fetch_alerts()

    def _fetch_station(self):
        if CONFIG["demo_mode"] or not HAS_REQUESTS:
            data = get_demo_station_data()
        else:
            try:
                url = (
                    f"https://api.weather.com/v2/pws/observations/current"
                    f"?stationId={CONFIG['wu_station_id']}"
                    f"&format=json&units=e&apiKey={CONFIG['wu_api_key']}"
                    f"&numericPrecision=decimal"
                )
                r   = requests.get(url, timeout=10, headers={"User-Agent": "WeatherPi/1.0"})
                r.raise_for_status()
                obs = r.json()["observations"][0]
                imp = obs.get("imperial", {})
                data = {
                    "tempf":          imp.get("temp"),
                    "feelslike":      imp.get("heatIndex") or imp.get("windChill") or imp.get("temp"),
                    "dewpoint":       imp.get("dewpt"),
                    "humidity":       obs.get("humidity"),
                    "baromrelin":     imp.get("pressure"),
                    "windspeedmph":   imp.get("windSpeed"),
                    "windgustmph":    imp.get("windGust"),
                    "winddir":        obs.get("winddir"),
                    "raintoday":      imp.get("precipTotal"),
                    "uv":             obs.get("uv"),
                    "solarradiation": obs.get("solarRadiation"),
                }
                print(f"WU: temp={data['tempf']}°F  "
                      f"wind={data['windspeedmph']}mph  "
                      f"humidity={data['humidity']}%")
            except Exception as e:
                print(f"WU station fetch error: {e}")
                return

        with self.lock:
            self.station_data = data
            self.last_update  = datetime.datetime.now()

    def _fetch_forecast(self):
        if CONFIG["demo_mode"] or not HAS_REQUESTS:
            with self.lock:
                self.forecast = get_demo_forecast()
            return
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={CONFIG['latitude']}&longitude={CONFIG['longitude']}"
                f"&daily=temperature_2m_max,temperature_2m_min,"
                f"precipitation_probability_max,weathercode"
                f"&temperature_unit=fahrenheit"
                f"&timezone={CONFIG['timezone']}&forecast_days=5"
            )
            r = requests.get(url, timeout=10)
            d = r.json()["daily"]

            wmo_icons = {
                0:"SUNNY",    1:"SUNNY",    2:"P.CLOUDY", 3:"CLOUDY",
                45:"FOGGY",   48:"ICY FOG",
                51:"DRIZZLE", 53:"DRIZZLE", 55:"DRIZZLE",
                61:"RAIN",    63:"RAIN",    65:"RAIN",
                71:"SNOW",    73:"SNOW",    75:"SNOW",
                80:"SHOWERS", 81:"SHOWERS", 82:"SHOWERS",
                95:"T-STORM", 96:"T-STORM", 99:"T-STORM",
            }
            wmo_desc = {
                0:"Clear",        1:"Mainly Clear",   2:"Partly Cloudy",  3:"Overcast",
                45:"Foggy",       48:"Icy Fog",
                51:"Lt Drizzle",  53:"Drizzle",       55:"Hvy Drizzle",
                61:"Lt Rain",     63:"Rain",           65:"Hvy Rain",
                71:"Lt Snow",     73:"Snow",           75:"Hvy Snow",
                80:"Showers",     81:"Hvy Showers",    82:"Violent Showers",
                95:"Thunderstorm",96:"Hail Storm",     99:"Hvy Hail",
            }
            day_names = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
            forecast  = []
            for i in range(5):
                dt = datetime.date.fromisoformat(d["time"][i])
                wc = d["weathercode"][i]
                forecast.append({
                    "day":         "TODAY" if i == 0 else day_names[dt.weekday()],
                    "date":        dt.strftime("%b %d"),
                    "icon":        wmo_icons.get(wc, "VAR"),
                    "description": wmo_desc.get(wc, "Variable"),
                    "high":        round(d["temperature_2m_max"][i]),
                    "low":         round(d["temperature_2m_min"][i]),
                    "precip":      d["precipitation_probability_max"][i],
                })
            with self.lock:
                self.forecast = forecast
        except Exception as e:
            print(f"Forecast fetch error: {e}")

    def _fetch_alerts(self):
        if CONFIG["demo_mode"] or not HAS_REQUESTS:
            return
        try:
            url = f"https://api.weather.gov/alerts/active/zone/{CONFIG['nws_zone']}"
            r   = requests.get(url, timeout=10, headers={"User-Agent": "WeatherPi/1.0"})
            alerts = []
            for f in r.json().get("features", [])[:3]:
                p = f["properties"]
                alerts.append({
                    "event":       p.get("event", "ALERT"),
                    "headline":    p.get("headline", ""),
                    "description": p.get("description", "")[:200],
                })
            with self.lock:
                self.alerts = alerts
        except Exception as e:
            print(f"Alerts fetch error: {e}")
