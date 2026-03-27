"""
flask_server.py — Flask web dashboard, runs in a daemon thread.
"""

import threading
import datetime

try:
    from flask import Flask, jsonify, render_template_string
    import logging as _logging
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

from config import CONFIG
from helpers import (
    sval, wind_dir_label, baro_trend,
    build_ticker_segments,
)

# ─────────────────────────────────────────────
#  WEB HELPERS
# ─────────────────────────────────────────────
def _web_temp_class(f):
    if f >= 90: return "t-hot"
    if f >= 70: return "t-warm"
    if f >= 50: return "t-cool"
    return "t-cold"

def _web_condition_icon(st):
    if sval(st, "raintoday") > 0.1:        return "🌧️"
    if sval(st, "solarradiation") > 600:   return "☀️"
    if sval(st, "solarradiation") > 200:   return "⛅"
    if sval(st, "windspeedmph") > 20:      return "💨"
    return "🌤️"

# ─────────────────────────────────────────────
#  HTML TEMPLATE
# ─────────────────────────────────────────────
WEB_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="60">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<title>{{ location }} — Weather Station</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&display=swap');

  :root {
    --bg-dark:     #0a0f1e;
    --bg-mid:      #0d1a2e;
    --bg-panel:    #0f2040;
    --blue:        #1a6ab5;
    --cyan:        #00d4ff;
    --teal:        #00b4b4;
    --gold:        #f0b429;
    --red:         #e63946;
    --green:       #2ecc71;
    --dim:         #7a9bbf;
    --white:       #f0f4ff;
    --hot:         #ff6b35;
    --warm:        #f0b429;
    --cool:        #4fc3f7;
    --cold:        #7c9cbf;
    --grid:        #1a3050;
    --alert-bg:    #8b0000;
    --alert-text:  #ffcc00;
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg-dark);
    color: var(--white);
    font-family: 'Share Tech Mono', monospace,"Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji";
    min-height: 100vh;
    overflow-x: hidden;
  }

  body::before {
    content: '';
    position: fixed; inset: 0;
    background: repeating-linear-gradient(
      to bottom,
      transparent 0px, transparent 3px,
      rgba(0,0,0,0.18) 3px, rgba(0,0,0,0.18) 4px
    );
    pointer-events: none;
    z-index: 999;
  }

  header {
    background: var(--blue);
    border-bottom: 3px solid var(--cyan);
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  header .logo { font-family: 'Orbitron', monospace; font-size: 1.1rem; font-weight: 700; color: #fff; }
  header .logo span { color: var(--cyan); }
  header .clock { font-size: 0.85rem; color: var(--gold); text-align: right; }

  .alert-banner {
    background: var(--alert-bg);
    border-bottom: 2px solid var(--red);
    padding: 10px 20px;
    color: var(--alert-text);
    font-weight: bold;
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }
  .alert-banner .alert-event { white-space: nowrap; font-family: 'Orbitron', monospace; font-size: 0.8rem; }
  .alert-banner .alert-body  { font-size: 0.85rem; line-height: 1.4; }

  .ticker-wrap {
    background: #001a40;
    border-bottom: 1px solid var(--grid);
    overflow: hidden;
    height: 32px;
    display: flex;
    align-items: center;
  }
  .ticker-wrap.alert-mode { background: #5a0000; }
  .ticker-label {
    background: var(--blue);
    color: var(--gold);
    font-family: 'Orbitron', monospace;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0 10px;
    height: 100%;
    display: flex;
    align-items: center;
    white-space: nowrap;
    flex-shrink: 0;
    border-right: 2px solid var(--cyan);
  }
  .ticker-track {
    display: flex;
    white-space: nowrap;
    animation: ticker-scroll 60s linear infinite;
    font-size: 0.8rem;
    padding-left: 20px;
  }
  .ticker-track:hover { animation-play-state: paused; }
  .ticker-weather { color: var(--cyan); }
  .ticker-source  { color: var(--gold); }
  .ticker-news    { color: var(--white); }
  .ticker-alert-t { color: var(--alert-text); }
  .ticker-sep     { color: var(--dim); padding: 0 8px; }
  @keyframes ticker-scroll {
    from { transform: translateX(0); }
    to   { transform: translateX(-50%); }
  }

  main {
    padding: 16px;
    display: grid;
    gap: 14px;
    grid-template-columns: 1fr 1fr;
    grid-template-areas:
      "current  current"
      "forecast forecast"
      "radar    radar"
      "almanac  news";
    max-width: 1100px;
    margin: 0 auto;
  }
  @media (max-width: 700px) {
    main { grid-template-columns: 1fr; grid-template-areas: "current" "forecast" "radar" "almanac" "news"; }
  }

  .panel {
    background: var(--bg-panel);
    border: 1px solid var(--grid);
    border-radius: 4px;
    padding: 14px 16px;
  }
  .panel-title {
    font-family: 'Orbitron', monospace;
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--cyan);
    letter-spacing: 0.12em;
    border-bottom: 1px solid var(--grid);
    padding-bottom: 8px;
    margin-bottom: 12px;
  }

  .current-panel { grid-area: current; }
  .current-grid {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 16px;
  }
  @media (max-width: 500px) { .current-grid { grid-template-columns: 1fr; } }
  .big-temp    { font-family: 'Orbitron', monospace; font-size: 4.5rem; font-weight: 900; line-height: 1; }
  .feels-like  { font-size: 0.8rem; color: var(--dim); margin-top: 4px; }
  .condition-icon { font-size: 3rem; margin: 10px 0 6px; }
  .dew-hum     { font-size: 0.8rem; color: var(--dim); line-height: 1.8; }
  .metrics-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
  .metric { padding: 8px 10px; border-bottom: 1px solid var(--grid); border-right: 1px solid var(--grid); }
  .metric:nth-child(even) { border-right: none; }
  .metric-label { font-size: 0.65rem; color: var(--dim); text-transform: uppercase; }
  .metric-value { font-size: 0.95rem; color: var(--cyan); margin-top: 2px; }
  .updated { font-size: 0.65rem; color: var(--dim); text-align: right; margin-top: 10px; }

  .forecast-panel { grid-area: forecast; }
  .forecast-grid  { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
  @media (max-width: 600px) { .forecast-grid { grid-template-columns: repeat(3, 1fr); } }
  .forecast-day { background: var(--bg-mid); border: 1px solid var(--grid); border-radius: 3px; padding: 10px 6px; text-align: center; }
  .forecast-day.today { border-color: var(--gold); }
  .fc-dayname { font-family: 'Orbitron', monospace; font-size: 0.65rem; color: var(--gold); }
  .fc-date    { font-size: 0.65rem; color: var(--dim); margin-bottom: 6px; }
  .fc-icon    { font-size: 1.8rem; margin: 4px 0; }
  .fc-desc    { font-size: 0.62rem; color: var(--white); margin-bottom: 6px; min-height: 28px; line-height: 1.3; }
  .fc-high    { font-size: 1.1rem; font-weight: bold; }
  .fc-low     { font-size: 0.8rem; margin-top: 2px; }
  .fc-precip  { margin-top: 8px; font-size: 0.65rem; color: var(--teal); }
  .precip-bar-wrap { background: var(--bg-dark); border: 1px solid var(--grid); height: 6px; border-radius: 3px; margin: 3px 0; overflow: hidden; }
  .precip-bar { height: 100%; background: var(--teal); border-radius: 3px; }

  .radar-panel { grid-area: radar; }
  #radar-map { width: 100%; height: 420px; border: 1px solid var(--grid); border-radius: 3px; background: #060d18; }
  .radar-meta { margin-top: 8px; font-size: 0.65rem; color: var(--dim); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; }
  .radar-meta a { color: var(--teal); text-decoration: none; }
  .radar-meta a:hover { text-decoration: underline; }
  #radar-frame-time { color: var(--gold); font-family: 'Orbitron', monospace; font-size: 0.65rem; }
  .radar-controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .radar-btn { background: var(--bg-mid); border: 1px solid var(--grid); color: var(--dim); font-family: 'Orbitron', monospace; font-size: 0.6rem; padding: 4px 10px; border-radius: 2px; cursor: pointer; transition: all 0.15s; }
  .radar-btn:hover, .radar-btn.active { background: var(--blue); border-color: var(--cyan); color: #fff; }
  .leaflet-container { background: #060d18 !important; }
  .leaflet-control-zoom a { background: var(--bg-panel) !important; color: var(--cyan) !important; border-color: var(--grid) !important; }
  .leaflet-control-attribution { background: rgba(6,13,24,0.8) !important; color: var(--dim) !important; font-size: 0.55rem !important; }
  .leaflet-control-attribution a { color: var(--teal) !important; }

  .almanac-panel { grid-area: almanac; }
  .sun-row { display: flex; justify-content: space-around; margin-bottom: 14px; text-align: center; }
  .sun-label { font-size: 0.65rem; color: var(--cyan); text-transform: uppercase; }
  .sun-value { font-family: 'Orbitron', monospace; font-size: 1.1rem; color: var(--gold); margin-top: 2px; }
  .moon-row  { text-align: center; font-size: 0.85rem; color: var(--white); margin-bottom: 14px; }
  .rec-table { width: 100%; border-collapse: collapse; font-size: 0.78rem; }
  .rec-table td { padding: 5px 8px; border-bottom: 1px solid var(--grid); }
  .rec-table td:first-child { color: var(--dim); }
  .rec-table td:last-child  { text-align: right; font-family: 'Orbitron', monospace; font-size: 0.75rem; }

  .news-panel { grid-area: news; }
  .news-item  { padding: 8px 0; border-bottom: 1px solid var(--grid); font-size: 0.78rem; line-height: 1.4; }
  .news-item:last-child { border-bottom: none; }
  .news-source   { font-size: 0.62rem; color: var(--gold); text-transform: uppercase; margin-bottom: 2px; }
  .news-headline { color: var(--white); }

  footer { text-align: center; padding: 14px; font-size: 0.65rem; color: var(--dim); border-top: 1px solid var(--grid); margin-top: 6px; }
  footer a { color: var(--teal); text-decoration: none; }

  .t-hot  { color: #ff6b35; }
  .t-warm { color: #f0b429; }
  .t-cool { color: #4fc3f7; }
  .t-cold { color: #7c9cbf; }
</style>
</head>
<body>

<header>
  <div class="logo">⛅ THE <span>WEATHER</span> CHANNEL</div>
  <div class="clock">
    <div id="clock-time">{{ now_time }}</div>
    <div>{{ now_date }}</div>
  </div>
</header>

{% if alerts %}
{% for alert in alerts %}
<div class="alert-banner">
  <div class="alert-event">⚠ {{ alert.event }}</div>
  <div class="alert-body">{{ alert.headline }}</div>
</div>
{% endfor %}
{% endif %}

<div class="ticker-wrap {% if alerts %}alert-mode{% endif %}">
  <div class="ticker-track">
    {% for seg in ticker_segments %}{% if seg[0] == 'alert' %}<span class="ticker-alert-t">{{ seg[1] }}</span>{% elif seg[0] == 'label' %}<span class="ticker-source">{{ seg[1] }}</span>{% elif seg[0] == 'news' %}<span class="ticker-news">{{ seg[1] }}</span>{% elif seg[0] == 'weather' %}<span class="ticker-weather">{{ seg[1] }}</span>{% else %}<span class="ticker-sep">·</span>{% endif %}{% endfor %}
    {% for seg in ticker_segments %}{% if seg[0] == 'alert' %}<span class="ticker-alert-t">{{ seg[1] }}</span>{% elif seg[0] == 'label' %}<span class="ticker-source">{{ seg[1] }}</span>{% elif seg[0] == 'news' %}<span class="ticker-news">{{ seg[1] }}</span>{% elif seg[0] == 'weather' %}<span class="ticker-weather">{{ seg[1] }}</span>{% else %}<span class="ticker-sep">·</span>{% endif %}{% endfor %}
  </div>
</div>

<main>

  <section class="panel current-panel">
    <div class="panel-title">📍 {{ location }} — Current Conditions</div>
    <div class="current-grid">
      <div>
        <div class="big-temp {{ temp_class }}">{{ temp }}°</div>
        <div class="feels-like">FEELS LIKE {{ feels_like }}°F</div>
        <div class="condition-icon">{{ condition_icon }}</div>
        <div class="dew-hum">DEW POINT &nbsp; {{ dewpoint }}°F<br>HUMIDITY &nbsp;&nbsp; {{ humidity }}%</div>
      </div>
      <div class="metrics-grid">
        <div class="metric"><div class="metric-label">Wind Speed</div><div class="metric-value">{{ wind_speed }} MPH</div></div>
        <div class="metric"><div class="metric-label">Wind Gust</div><div class="metric-value">{{ wind_gust }} MPH</div></div>
        <div class="metric"><div class="metric-label">Direction</div><div class="metric-value">{{ wind_dir_label }} {{ wind_dir }}°</div></div>
        <div class="metric"><div class="metric-label">Barometer</div><div class="metric-value">{{ baro }}" {{ baro_trend }}</div></div>
        <div class="metric"><div class="metric-label">Rain Today</div><div class="metric-value">{{ rain }}"</div></div>
        <div class="metric"><div class="metric-label">UV Index</div><div class="metric-value">{{ uv }}</div></div>
        <div class="metric"><div class="metric-label">Solar Rad</div><div class="metric-value">{{ solar }} W/m²</div></div>
        <div class="metric"><div class="metric-label">Station</div><div class="metric-value" style="color:var(--green)">LIVE</div></div>
      </div>
    </div>
    <div class="updated">UPDATED {{ updated }}</div>
  </section>

  <section class="panel forecast-panel">
    <div class="panel-title">📅 5-Day Forecast</div>
    <div class="forecast-grid">
      {% for day in forecast %}
      <div class="forecast-day {% if day.day == 'TODAY' %}today{% endif %}">
        <div class="fc-dayname">{{ day.day }}</div>
        <div class="fc-date">{{ day.date }}</div>
        <div class="fc-icon">{{ day.icon }}</div>
        <div class="fc-desc">{{ day.description }}</div>
        <div class="fc-high {{ day.high_class }}">{{ day.high }}°</div>
        <div class="fc-low {{ day.low_class }}">{{ day.low }}°</div>
        <div class="fc-precip">
          <div class="precip-bar-wrap"><div class="precip-bar" style="width:{{ day.precip }}%"></div></div>
          💧 {{ day.precip }}%
        </div>
      </div>
      {% endfor %}
    </div>
  </section>

  <section class="panel radar-panel">
    <div class="panel-title">📡 Live Radar — {{ location }}</div>
    <div id="radar-map"></div>
    <div class="radar-meta">
      <div class="radar-controls">
        <button class="radar-btn active" id="btn-play" onclick="radarPlayStop()">⏸ PAUSE</button>
        <button class="radar-btn" onclick="radarStep(-1)">◀ PREV</button>
        <button class="radar-btn" onclick="radarStep(1)">NEXT ▶</button>
      </div>
      <div id="radar-frame-time">LOADING RADAR...</div>
      <span>
        <a href="https://www.rainviewer.com/" target="_blank">RainViewer</a>
        &nbsp;·&nbsp;
        <a href="https://radar.weather.gov/" target="_blank">NWS Radar ↗</a>
      </span>
    </div>
  </section>

  <section class="panel almanac-panel">
    <div class="panel-title">📖 Almanac — {{ today_str }}</div>
    <div class="sun-row">
      <div><div class="sun-label">🌅 Sunrise</div><div class="sun-value">{{ sunrise }}</div></div>
      <div><div class="sun-label">🌇 Sunset</div><div class="sun-value">{{ sunset }}</div></div>
    </div>
    <div class="moon-row">🌙 {{ moonphase }}</div>
    <table class="rec-table">
      <tr><td>Record High</td><td class="t-hot">{{ rec_high }}°F <span style="color:var(--dim)">({{ rec_high_yr }})</span></td></tr>
      <tr><td>Record Low</td><td class="t-cold">{{ rec_low }}°F <span style="color:var(--dim)">({{ rec_low_yr }})</span></td></tr>
      <tr><td>Avg High</td><td class="t-warm">{{ avg_high }}°F</td></tr>
      <tr><td>Avg Low</td><td class="t-cool">{{ avg_low }}°F</td></tr>
      <tr><td>Avg Precip</td><td style="color:var(--teal)">{{ avg_precip }}"</td></tr>
    </table>
  </section>

  <section class="panel news-panel">
    <div class="panel-title">📰 In The News</div>
    {% if news %}
      {% for source, headline in news %}
      <div class="news-item">
        <div class="news-source">{{ source }}</div>
        <div class="news-headline">{{ headline.title() }}</div>
      </div>
      {% endfor %}
    {% else %}
      <div style="color:var(--dim); font-size:0.8rem; margin-top:8px;">News feeds loading...</div>
    {% endif %}
  </section>

</main>

<footer>
  AUTO-REFRESH EVERY 60s &nbsp;·&nbsp;
  <a href="/api/data">JSON API</a> &nbsp;·&nbsp;
  DATA: WEATHER UNDERGROUND + OPEN-METEO + NWS
</footer>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
  function updateClock() {
    const now = new Date();
    const t = now.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
    const el = document.getElementById('clock-time');
    if (el) el.textContent = t;
  }
  setInterval(updateClock, 1000);
  updateClock();

  const RADAR_LAT = {{ latitude }};
  const RADAR_LON = {{ longitude }};

  const map = L.map('radar-map', { center: [RADAR_LAT, RADAR_LON], zoom: 7 });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OSM</a> © <a href="https://carto.com/">CARTO</a>',
    subdomains: 'abcd', maxZoom: 19,
  }).addTo(map);

  L.circleMarker([RADAR_LAT, RADAR_LON], {
    radius: 6, fillColor: '#f0b429', color: '#fff', weight: 1.5, fillOpacity: 1,
  }).addTo(map).bindTooltip('{{ location }}');

  let radarFrames = [], radarLayers = {}, animPosition = 0;
  let animTimer = null, isPlaying = true;
  const ANIM_SPEED = 600;

  async function loadRadarFrames() {
    try {
      const res  = await fetch('https://api.rainviewer.com/public/weather-maps.json');
      const data = await res.json();
      radarFrames = (data.radar.past || []).slice(-12);
      if (data.radar.nowcast) radarFrames = radarFrames.concat(data.radar.nowcast.slice(0,2));
      Object.values(radarLayers).forEach(l => map.removeLayer(l));
      radarLayers = {};
      radarFrames.forEach(frame => {
        const url = `${data.host}${frame.path}/256/{z}/{x}/{y}/2/1_1.png`;
        radarLayers[frame.time] = L.tileLayer(url, {opacity: 0, zIndex: 10, attribution: 'RainViewer'});
        radarLayers[frame.time].addTo(map);
      });
      showFrame(radarFrames.length - 1);
      if (isPlaying) startAnimation();
    } catch(e) {
      document.getElementById('radar-frame-time').textContent = '⚠ RADAR UNAVAILABLE';
    }
  }

  function showFrame(idx) {
    if (!radarFrames.length) return;
    idx = Math.max(0, Math.min(idx, radarFrames.length - 1));
    if (radarFrames[animPosition]) {
      const prev = radarLayers[radarFrames[animPosition].time];
      if (prev) prev.setOpacity(0);
    }
    animPosition = idx;
    const layer = radarLayers[radarFrames[idx].time];
    if (layer) layer.setOpacity(0.75);
    const d   = new Date(radarFrames[idx].time * 1000);
    const lbl = d.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'})
              + '  ' + d.toLocaleDateString('en-US', {month:'short', day:'numeric'});
    document.getElementById('radar-frame-time').textContent = lbl;
  }

  function startAnimation() {
    if (animTimer) clearInterval(animTimer);
    animTimer = setInterval(() => showFrame((animPosition + 1) % radarFrames.length), ANIM_SPEED);
    document.getElementById('btn-play').textContent = '⏸ PAUSE';
    document.getElementById('btn-play').classList.add('active');
  }

  function stopAnimation() {
    if (animTimer) { clearInterval(animTimer); animTimer = null; }
    document.getElementById('btn-play').textContent = '▶ PLAY';
    document.getElementById('btn-play').classList.remove('active');
  }

  function radarPlayStop() { isPlaying = !isPlaying; isPlaying ? startAnimation() : stopAnimation(); }
  function radarStep(dir)  { stopAnimation(); isPlaying = false; showFrame(animPosition + dir); }

  loadRadarFrames();
  setInterval(loadRadarFrames, 600000);
</script>
</body>
</html>"""


# ─────────────────────────────────────────────
#  FLASK SERVER
# ─────────────────────────────────────────────
class FlaskServer:
    """Runs a Flask web server in a daemon thread."""

    def __init__(self, data_mgr):
        if not HAS_FLASK:
            raise RuntimeError("Flask is not installed.")
        self.data_mgr = data_mgr
        self.app      = Flask(__name__)
        _logging.getLogger("werkzeug").setLevel(_logging.WARNING)
        self._register_routes()

    def _register_routes(self):
        app = self.app

        @app.route("/")
        def index():
            data = self.data_mgr.get()
            st   = data["station"]
            al   = data["almanac"]
            now  = datetime.datetime.now()

            fc = []
            for day in data["forecast"]:
                d = dict(day)
                d["high_class"] = _web_temp_class(day["high"])
                d["low_class"]  = _web_temp_class(day["low"])
                fc.append(d)

            ticker = build_ticker_segments(data, CONFIG["location_name"])

            ctx = dict(
                location       = CONFIG["location_name"],
                now_time       = now.strftime("%I:%M:%S %p"),
                now_date       = now.strftime("%A, %B %d %Y"),
                today_str      = now.strftime("%B %d").upper(),
                temp           = f"{sval(st,'tempf'):.1f}",
                temp_class     = _web_temp_class(sval(st, "tempf")),
                feels_like     = f"{sval(st,'feelslike'):.1f}",
                condition_icon = _web_condition_icon(st),
                humidity       = f"{sval(st,'humidity'):.0f}",
                dewpoint       = f"{sval(st,'dewpoint'):.1f}",
                wind_speed     = f"{sval(st,'windspeedmph'):.1f}",
                wind_gust      = f"{sval(st,'windgustmph'):.1f}",
                wind_dir       = f"{sval(st,'winddir'):.0f}",
                wind_dir_label = wind_dir_label(sval(st, "winddir")),
                baro           = f"{sval(st,'baromrelin'):.2f}",
                baro_trend     = baro_trend(sval(st, "baromrelin")),
                rain           = f"{sval(st,'raintoday'):.2f}",
                uv             = int(sval(st, "uv")),
                solar          = f"{sval(st,'solarradiation'):.0f}",
                updated        = data["last_update"].strftime("%I:%M %p"),
                forecast       = fc,
                alerts         = data["alerts"],
                sunrise        = al["sunrise"],
                sunset         = al["sunset"],
                moonphase      = al["moonphase"],
                rec_high       = al["high_record"],
                rec_high_yr    = al["high_record_year"],
                rec_low        = al["low_record"],
                rec_low_yr     = al["low_record_year"],
                avg_high       = al["avg_high"],
                avg_low        = al["avg_low"],
                avg_precip     = al["avg_precip"],
                news           = data.get("rss", []),
                ticker_segments = ticker,
                wu_station_id  = CONFIG.get("wu_station_id", "—"),
                latitude       = CONFIG.get("latitude", 40.0),
                longitude      = CONFIG.get("longitude", -98.0),
            )
            return render_template_string(WEB_TEMPLATE, **ctx)

        @app.route("/api/data")
        def api_data():
            data = self.data_mgr.get()
            data["last_update"] = data["last_update"].isoformat()
            return jsonify(data)

    def start(self):
        port = CONFIG.get("web_port", 5000)
        t = threading.Thread(
            target=lambda: self.app.run(host="0.0.0.0", port=port, use_reloader=False),
            daemon=True,
            name="FlaskThread",
        )
        t.start()
        print(f"Web server started → http://0.0.0.0:{port}")
