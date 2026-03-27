"""
tkinter_app.py — Retro Weather Channel touchscreen display (Tkinter).
"""

import tkinter as tk
from tkinter import font as tkfont
import time
import datetime
import threading
import io

from config import CONFIG
from helpers import (
    COLORS, temp_color, wind_dir_label, baro_trend,
    sval, build_ticker_segments,
)
import icon_loader

try:
    import requests
    from PIL import Image, ImageTk
    HAS_RADAR = True
except ImportError:
    HAS_RADAR = False


class RetroWeatherApp(tk.Tk):
    PAGES = ["current", "forecast", "radar_placeholder", "alerts", "almanac"]

    def __init__(self, data_mgr):
        super().__init__()
        self.data_mgr     = data_mgr
        self.page_index   = 0
        self.auto_rotate  = True
        self.rotate_sec   = 10
        self._last_rotate = time.time()

        self.title("Retro Weather Station")
        self.configure(bg=COLORS["bg_dark"])
        self.resizable(False, False)

        W = CONFIG["screen_width"]
        H = CONFIG["screen_height"]

        # Force window to exact size and position, remove decorations
        self.geometry(f"{W}x{H}+0+0")
        self.overrideredirect(True)   # removes title bar and window chrome

        if CONFIG["fullscreen"]:
            # Also try wm fullscreen as a fallback
            try:
                self.attributes("-fullscreen", True)
            except Exception:
                pass

        self._setup_fonts()
        icon_loader.preload_all(size=64, master=self)
        self._build_layout(W, H)
        
        # Radar state
        self._radar_image    = None   # current Tkinter PhotoImage
        self._radar_label    = None   # timestamp string
        self._radar_error    = None   # error message if fetch failed
        self._radar_fetching = False  # True while a fetch is in progress
        if HAS_RADAR:
            self._fetch_radar_async()
        self._update()

    # ── Fonts ───────────────────────────────────
    def _setup_fonts(self):
        self.f_huge   = tkfont.Font(family="Courier", size=48, weight="bold")
        self.f_large  = tkfont.Font(family="Courier", size=28, weight="bold")
        self.f_med    = tkfont.Font(family="Courier", size=16, weight="bold")
        self.f_small  = tkfont.Font(family="Courier", size=11)
        self.f_tiny   = tkfont.Font(family="Courier", size=9)
        self.f_label  = tkfont.Font(family="Courier", size=10, weight="bold")
        self.f_ticker = tkfont.Font(family="Courier", size=12, weight="bold")

    # ── Layout ──────────────────────────────────
    def _build_layout(self, W, H):
        HEADER_H = 40
        TICKER_H = 30
        NAV_H    = 36
        mid_h    = H - HEADER_H - TICKER_H - NAV_H

        self.header = tk.Canvas(self, width=W, height=HEADER_H,
                                bg=COLORS["accent_blue"], highlightthickness=0)
        self.header.place(x=0, y=0)
        self._draw_header()

        self.main = tk.Canvas(self, width=W, height=mid_h,
                              bg=COLORS["bg_dark"], highlightthickness=0)
        self.main.place(x=0, y=HEADER_H)
        self._draw_scanlines(W, mid_h)

        self.ticker_canvas = tk.Canvas(self, width=W, height=TICKER_H,
                                       bg=COLORS["ticker_bg"], highlightthickness=0)
        self.ticker_canvas.place(x=0, y=HEADER_H + mid_h)
        self.ticker_x            = W
        self._ticker_segments    = []
        self._ticker_total_width = W

        self.nav = tk.Canvas(self, width=W, height=NAV_H,
                             bg=COLORS["bg_mid"], highlightthickness=0)
        self.nav.place(x=0, y=H - NAV_H)
        self._draw_nav(W, NAV_H)

        self.W        = W
        self.H        = H
        self.mid_h    = mid_h
        self.HEADER_H = HEADER_H
        self.TICKER_H = TICKER_H
        self.NAV_H    = NAV_H

        for widget in [self.main, self.nav, self.header]:
            widget.bind("<Button-1>", self._on_click)

    def _draw_scanlines(self, W, H):
        for y in range(0, H, 4):
            self.main.create_line(0, y, W, y, fill=COLORS["scanline"], width=1)

    def _draw_header(self):
        c = self.header
        W = CONFIG["screen_width"]
        c.delete("all")
        c.create_rectangle(0, 0, W, 40, fill=COLORS["accent_blue"], outline="")
        c.create_rectangle(0, 36, W, 40, fill=COLORS["accent_cyan"], outline="")
        c.create_text(10, 20, text="* The Weather Channel *", anchor="w",
                      font=self.f_med, fill=COLORS["text_bright"])
        now = datetime.datetime.now().strftime("%I:%M %p  %a %b %d")
        c.create_text(W - 10, 20, text=now, anchor="e",
                      font=self.f_label, fill=COLORS["accent_gold"])

    def _draw_nav(self, W, H):
        c = self.nav
        c.delete("all")

        labels = ["CURRENT", "FORECAST", "RADAR", "NEWS / ALERTS", "ALMANAC"]
        btn_w  = W // len(labels)
        for i, label in enumerate(labels):
            x0     = i * btn_w
            x1     = x0 + btn_w
            active = (i == self.page_index)
            bg = COLORS["accent_blue"] if active else COLORS["bg_mid"]
            fg = COLORS["accent_gold"] if active else COLORS["text_dim"]
            c.create_rectangle(x0+1, 1, x1-1, H-1, fill=bg, outline=COLORS["grid_line"])
            c.create_text((x0+x1)//2, H//2, text=label, font=self.f_label, fill=fg)

    # ── Ticker ──────────────────────────────────
    def _tick_scroll(self):
        c = self.ticker_canvas
        c.delete("all")
        x = self.ticker_x
        for seg_type, text in self._ticker_segments:
            if seg_type == "alert":
                color = COLORS["ticker_alert"]
            elif seg_type == "label":
                color = COLORS["ticker_label"]
            elif seg_type == "news":
                color = COLORS["ticker_news"]
            else:
                color = COLORS["ticker_text"]
            c.create_text(x, 15, text=text, anchor="w", font=self.f_ticker, fill=color)

            text_id = c.create_text(x, 15, text=text, anchor="w", font=self.f_ticker, fill=color)
            bbox = c.bbox(text_id)
            text_width = bbox[2] - bbox[0]
            x += text_width + 20

        self.ticker_x -= 2
        if self.ticker_x < -self._ticker_total_width:
            self.ticker_x = self.W
        self.after(30, self._tick_scroll)

    def _refresh_ticker(self, data):
        segs = build_ticker_segments(data, CONFIG["location_name"])
        self._ticker_segments    = segs
        self._ticker_total_width = 0
        temp_x = 0

        for seg_type, text in segs:
            text_id = self.ticker_canvas.create_text(temp_x, 15, text=text,
							anchor="w", font=self.f_ticker)
            bbox = self.ticker_canvas.bbox(text_id)
            width = bbox[2] - bbox[0]
            self._ticker_total_width += width + 20
            self.ticker_canvas.delete(text_id)

        alert_mode = bool(data.get("alerts"))
        bg = COLORS["alert_bg"] if alert_mode else COLORS["ticker_bg"]
        self.ticker_canvas.configure(bg=bg)

    def start_ticker(self):
        self.ticker_x = self.W
        data = self.data_mgr.get()
        self._refresh_ticker(data)
        self._tick_scroll()

    # ── Page router ─────────────────────────────
    def _draw_page(self, data):
        page = self.PAGES[self.page_index]
        self.main.delete("content")
        dispatch = {
            "current":            self._draw_current,
            "forecast":           self._draw_forecast,
            "radar_placeholder":  self._draw_radar,
            "alerts":             self._draw_alerts,
            "almanac":            self._draw_almanac,
        }
        if page in dispatch:
            dispatch[page](data)
        #print("DEBUG Page: ", page)

    # ── PAGE: Current Conditions ─────────────────
    def _draw_current(self, data):
        c   = self.main
        st  = data["station"]
        W, H = self.W, self.mid_h
        tag = "content"

        c.create_rectangle(0, 0, W//2, H, fill=COLORS["bg_panel"],
                           outline=COLORS["grid_line"], tags=tag)

        tc = temp_color(sval(st, "tempf"))
        c.create_text(W//4, 20, text=CONFIG["location_name"].upper(),
                      font=self.f_label, fill=COLORS["accent_cyan"], tags=tag)
        c.create_text(W//4, 90,  text=f"{sval(st,'tempf'):.1f}°",
                      font=self.f_huge, fill=tc, tags=tag)
        c.create_text(W//4, 145, text=f"FEELS LIKE {sval(st,'feelslike'):.1f}°",
                      font=self.f_small, fill=COLORS["text_dim"], tags=tag)
        
        cond = self._condition_icon(st)
        icon = icon_loader.get_icon(cond, size=64)
        if icon:
            self._current_icon = icon   # hold ref to prevent GC
            c.create_image(W//4, 195, image=icon, tags=tag)
        else:
            c.create_text(W//4, 205, text=cond,
                          font=self.f_large, fill=COLORS["accent_teal"], tags=tag)
            
        c.create_text(W//4, 270, text=f"DEW PT  {sval(st,'dewpoint'):.1f}°F",
                      font=self.f_small, fill=COLORS["text_dim"], tags=tag)
        c.create_text(W//4, 292, text=f"HUMIDITY  {sval(st,'humidity'):.0f}%",
                      font=self.f_small, fill=COLORS["text_dim"], tags=tag)

        mx = W//2 + 10
        self._metric_row(c, mx, 10,  "WIND SPEED", f"{sval(st,'windspeedmph'):.1f} MPH", tag)
        self._metric_row(c, mx, 55,  "WIND GUST",  f"{sval(st,'windgustmph'):.1f} MPH", tag)
        self._metric_row(c, mx, 100, "DIRECTION",
                         f"{wind_dir_label(sval(st,'winddir'))}  {sval(st,'winddir'):.0f}°", tag)
        self._metric_row(c, mx, 145, "BAROMETER",
                         f"{sval(st,'baromrelin'):.2f}\"  {baro_trend(sval(st,'baromrelin'))}", tag)
        self._metric_row(c, mx, 190, "RAIN TODAY", f"{sval(st,'raintoday'):.2f}\"", tag)
        self._metric_row(c, mx, 235, "UV INDEX",   str(int(sval(st,'uv'))), tag)
        self._metric_row(c, mx, 280, "SOLAR RAD",  f"{sval(st,'solarradiation'):.0f} W/m²", tag)

        upd = data["last_update"].strftime("%I:%M %p")
        c.create_text(W - 8, H - 8, text=f"UPDATED {upd}", anchor="se",
                      font=self.f_tiny, fill=COLORS["text_dim"], tags=tag)

    def _metric_row(self, c, x, y, label, value, tag):
        c.create_text(x, y + 4,  text=label, anchor="nw",
                      font=self.f_tiny,  fill=COLORS["text_dim"],    tags=tag)
        c.create_text(x, y + 18, text=value, anchor="nw",
                      font=self.f_label, fill=COLORS["accent_cyan"], tags=tag)
        c.create_line(x, y + 38, x + 360, y + 38,
                      fill=COLORS["grid_line"], tags=tag)

    def _condition_icon(self, st):
        if sval(st, "raintoday") > 0.1:         return "RAIN"
        if sval(st, "solarradiation") > 600:    return "SUNNY"
        if sval(st, "solarradiation") > 200:    return "P.CLOUDY"
        if sval(st, "windspeedmph") > 20:       return "WINDY"
        return "M.CLEAR"

    # ── PAGE: Forecast ───────────────────────────
    def _draw_forecast(self, data):
        c    = self.main
        fc   = data["forecast"]
        W, H = self.W, self.mid_h
        tag  = "content"

        c.create_text(W//2, 14, text="5-DAY FORECAST",
                      font=self.f_med, fill=COLORS["accent_gold"], tags=tag)

        col_w = W // 5
        for i, day in enumerate(fc[:5]):
            x  = i * col_w + col_w // 2
            bg = COLORS["bg_panel"] if i % 2 == 0 else COLORS["bg_mid"]
            c.create_rectangle(i*col_w+2, 35, (i+1)*col_w-2, H-5,
                                fill=bg, outline=COLORS["grid_line"], tags=tag)

            fg = COLORS["accent_gold"] if day["day"] == "TODAY" else COLORS["accent_cyan"]
            c.create_text(x, 50, text=day["day"],  font=self.f_label, fill=fg, tags=tag)
            c.create_text(x, 68, text=day["date"], font=self.f_tiny,
                          fill=COLORS["text_dim"], tags=tag)
            
            fc_icon = icon_loader.get_icon(day["icon"], size=48)
            if fc_icon:
                if not hasattr(self, "_forecast_icons"):
                    self._forecast_icons = {}
                self._forecast_icons[i] = fc_icon   # hold ref
                c.create_image(x, 110, image=fc_icon, tags=tag)
            else:
                c.create_text(x, 110, text=day["icon"], font=self.f_small, tags=tag)

            words = day["description"].split()
            line1 = " ".join(words[:2])
            line2 = " ".join(words[2:]) if len(words) > 2 else ""
            c.create_text(x, 158, text=line1, font=self.f_tiny,
                          fill=COLORS["text_white"], tags=tag)
            if line2:
                c.create_text(x, 172, text=line2, font=self.f_tiny,
                              fill=COLORS["text_white"], tags=tag)

            c.create_text(x, 205, text=f"HI {day['high']}°",
                          font=self.f_med, fill=temp_color(day["high"]), tags=tag)
            c.create_text(x, 232, text=f"LO {day['low']}°",
                          font=self.f_small, fill=temp_color(day["low"]), tags=tag)

            bar_h  = int(day["precip"] * 0.7)
            bar_x0 = x - 18
            bar_y1 = H - 25
            c.create_rectangle(bar_x0, bar_y1-70, bar_x0+36, bar_y1,
                                fill=COLORS["bg_dark"], outline=COLORS["grid_line"], tags=tag)
            if bar_h > 0:
                c.create_rectangle(bar_x0, bar_y1-bar_h, bar_x0+36, bar_y1,
                                   fill=COLORS["accent_teal"], outline="", tags=tag)
            c.create_text(x, H-12, text=f"RAIN {day['precip']}%",
                          font=self.f_tiny, fill=COLORS["text_dim"], tags=tag)

    # ── PAGE: Radar ──────────────────────────────
    def _fetch_radar_async(self):
        """Fetch NWS radar GIF in a background thread, then store as TkImage."""
        if self._radar_fetching:
            return
        self._radar_fetching = True

        def _fetch():
            station = CONFIG.get("nws_radar_station", "KAMA").upper()
            url     = f"https://radar.weather.gov/ridge/standard/{station}_0.gif"
            try:
                r = requests.get(url, timeout=15,
                                 headers={"User-Agent": "WeatherPi/1.0"})
                r.raise_for_status()
                img = Image.open(io.BytesIO(r.content)).convert("RGBA")
                W_target = CONFIG["screen_width"]
                H_target = self.mid_h - 30
                img.thumbnail((W_target, H_target), Image.LANCZOS)
                self._radar_raw = img
                self.after(0, self._apply_radar_image)
                print(f"Radar fetched: {station}")
            except Exception as e:
                self._radar_error = f"RADAR UNAVAILABLE\n{e}"
                print(f"Radar fetch error: {e}")
            finally:
                self._radar_fetching = False

        threading.Thread(target=_fetch, daemon=True).start()

    def _apply_radar_image(self):
        """Called on main thread after background fetch completes."""
        if hasattr(self, "_radar_raw") and self._radar_raw:
            self._radar_image = ImageTk.PhotoImage(self._radar_raw)
            self._radar_label = datetime.datetime.now().strftime("%I:%M %p")
            self._radar_error = None

    def _draw_radar(self, data):
        c    = self.main
        W, H = self.W, self.mid_h
        tag  = "content"

        c.create_rectangle(0, 0, W, H, fill="#030810", outline="", tags=tag)
        c.create_text(W//2, 16, text="NWS RADAR",
                      font=self.f_med, fill=COLORS["accent_cyan"], tags=tag)

        if not HAS_RADAR:
            c.create_text(W//2, H//2 - 10,
                          text="INSTALL: pip install requests Pillow",
                          font=self.f_small, fill=COLORS["text_dim"], tags=tag)
            c.create_text(W//2, H//2 + 20,
                          text="SEE WEB UI FOR LIVE RADAR",
                          font=self.f_small, fill=COLORS["text_dim"], tags=tag)
            return

        if self._radar_error:
            c.create_text(W//2, H//2,
                          text=self._radar_error,
                          font=self.f_small, fill=COLORS["accent_red"], tags=tag)

        elif self._radar_image:
            # Center image on canvas
            c.create_image(W//2, H//2 + 10,
                           image=self._radar_image, tags=tag)
            station = CONFIG.get("nws_radar_station", "KAMA").upper()
            c.create_text(8, H - 8,
                          text=f"{station}  UPDATED {self._radar_label}",
                          anchor="sw", font=self.f_tiny,
                          fill=COLORS["accent_cyan"], tags=tag)
            c.create_text(W - 8, H - 8,
                          text="NWS RIDGE2",
                          anchor="se", font=self.f_tiny,
                          fill=COLORS["text_dim"], tags=tag)
        else:
            # Still loading
            c.create_text(W//2, H//2 - 10,
                          text="FETCHING RADAR...",
                          font=self.f_med, fill=COLORS["text_dim"], tags=tag)
            c.create_text(W//2, H//2 + 20,
                          text=CONFIG.get("nws_radar_station", "KAMA").upper(),
                          font=self.f_small, fill=COLORS["accent_cyan"], tags=tag)

    # ── PAGE: Alerts ─────────────────────────────
    def _draw_alerts(self, data):
        c      = self.main
        W, H   = self.W, self.mid_h
        tag    = "content"
        alerts = data["alerts"]

        if not alerts:
            c.create_text(W//2, 20, text="** LATEST HEADLINES **",
                          font=self.f_med, fill=COLORS["accent_cyan"], tags=tag)
            c.create_line(10, 38, W-10, 38, fill=COLORS["accent_teal"], width=1, tags=tag)

            headlines = data.get("rss", [])
            if not headlines:
                c.create_text(W//2, H//2,
                              text="NO HEADLINES AVAILABLE",
                              font=self.f_small, fill=COLORS["text_dim"], tags=tag)
                return

            y = 60
            for source, text in headlines[:6]:
                c.create_rectangle(10, y, W-10, y+60,
                                   fill=COLORS["bg_panel"], outline=COLORS["grid_line"], tags=tag)
                c.create_text(20, y+12, text=source,
                              anchor="w", font=self.f_label,
                              fill=COLORS["accent_gold"], tags=tag)
                c.create_text(20, y+32, text=text[:90],
                              anchor="w", font=self.f_tiny,
                              fill=COLORS["text_white"], tags=tag)
                y += 70
            return

        # ── Active alerts ────────────────────────────
        c.create_text(W//2, 16, text="** WEATHER ALERTS **",
                      font=self.f_med, fill=COLORS["alert_text"], tags=tag)
        c.create_line(10, 32, W-10, 32, fill=COLORS["accent_red"], width=2, tags=tag)

        # Show one alert at a time with full description
        # Cycle through alerts based on time so they each get screen time
        idx   = int(time.time() // 15) % len(alerts)
        alert = alerts[idx]

        # Alert count indicator
        if len(alerts) > 1:
            c.create_text(W - 12, 16,
                          text=f"{idx+1}/{len(alerts)}",
                          anchor="e", font=self.f_tiny,
                          fill=COLORS["text_dim"], tags=tag)

        # Event type header
        c.create_rectangle(10, 38, W-10, 68,
                           fill=COLORS["alert_bg"], outline=COLORS["accent_red"], tags=tag)
        c.create_text(W//2, 53, text=f"! {alert['event'].upper()} !",
                      font=self.f_label, fill=COLORS["alert_text"], tags=tag)

        # Headline
        headline = alert.get("headline", "")
        c.create_text(W//2, 82, text=headline,
                      font=self.f_tiny, fill=COLORS["text_white"],
                      width=W-30, tags=tag)

        # Description — word-wrapped to fill available space
        desc = alert.get("description", "")
        y = 108
        line_w = W - 30
        # Split on " | " (our cleaned separator) for natural breaks
        parts = desc.split(" | ")
        for part in parts:
            if y > H - 30:
                break
            c.create_text(16, y, text=part,
                          anchor="nw", font=self.f_tiny,
                          fill=COLORS["text_dim"],
                          width=line_w, tags=tag)
            # Estimate lines used: ~chars per line at tiny font on this width
            chars_per_line = line_w // 6
            lines = max(1, (len(part) + chars_per_line - 1) // chars_per_line)
            y += lines * 14 + 4

        # Instruction if there's room
        instruction = alert.get("instruction", "")
        if instruction and y < H - 40:
            c.create_line(10, y, W-10, y, fill=COLORS["grid_line"], tags=tag)
            y += 6
            c.create_text(16, y, text=instruction,
                          anchor="nw", font=self.f_tiny,
                          fill=COLORS["accent_gold"],
                          width=line_w, tags=tag)

    # ── PAGE: Almanac ────────────────────────────
    def _draw_almanac(self, data):
        c    = self.main
        W, H = self.W, self.mid_h
        tag  = "content"
        al   = data["almanac"]

        c.create_text(W//2, 18,
                      text=f"ALMANAC  —  {datetime.date.today().strftime('%B %d').upper()}",
                      font=self.f_med, fill=COLORS["accent_gold"], tags=tag)
        c.create_line(10, 36, W-10, 36, fill=COLORS["accent_teal"], width=1, tags=tag)

        col1x = W//4
        c.create_text(col1x, 60,  text="SUNRISE", font=self.f_label,
                      fill=COLORS["accent_cyan"], tags=tag)
        c.create_text(col1x, 84,  text=al["sunrise"],  font=self.f_large,
                      fill=COLORS["accent_gold"], tags=tag)
        c.create_text(col1x, 130, text="SUNSET", font=self.f_label,
                      fill=COLORS["accent_cyan"], tags=tag)
        c.create_text(col1x, 154, text=al["sunset"],   font=self.f_large,
                      fill=COLORS["temp_warm"], tags=tag)
        c.create_text(col1x, 205, text="MOON PHASE", font=self.f_label,
                      fill=COLORS["accent_cyan"], tags=tag)
        c.create_text(col1x, 228, text=al["moonphase"], font=self.f_med,
                      fill=COLORS["text_white"], tags=tag)

        c.create_line(W//2, 45, W//2, H-10,
                      fill=COLORS["grid_line"], dash=(4,4), tags=tag)

        col2x = W//2 + 20
        c.create_text(col2x, 55, text="HISTORICAL RECORDS", anchor="w",
                      font=self.f_label, fill=COLORS["accent_cyan"], tags=tag)
        c.create_line(col2x, 70, W-10, 70, fill=COLORS["grid_line"], tags=tag)

        y = 90
        for label, val, extra, vc in [
            ("REC HIGH", f"{al['high_record']}°F",  f"({al['high_record_year']})", COLORS["temp_hot"]),
            ("REC LOW",  f"{al['low_record']}°F",   f"({al['low_record_year']})",  COLORS["temp_cold"]),
            ("AVG HIGH", f"{al['avg_high']}°F",     "",                             COLORS["temp_warm"]),
            ("AVG LOW",  f"{al['avg_low']}°F",      "",                             COLORS["temp_cool"]),
            ("AVG PRECIP", f"{al['avg_precip']}\"", "",                             COLORS["accent_teal"]),
        ]:
            c.create_text(col2x,       y, text=label,          anchor="w",
                          font=self.f_tiny,  fill=COLORS["text_dim"], tags=tag)
            c.create_text(col2x + 200, y, text=f"{val} {extra}".strip(), anchor="w",
                          font=self.f_label, fill=vc,               tags=tag)
            y += 40

    # ── Event handling ───────────────────────────
    def _on_click(self, event):
        if event.widget == self.nav:
            idx = event.x // (self.W // len(self.PAGES))
            if 0 <= idx < len(self.PAGES):
                self.page_index  = idx
                self.auto_rotate = False
                self._draw_nav(self.W, self.NAV_H)
        else:
            self.page_index = (self.page_index + 1) % len(self.PAGES)
            self._draw_nav(self.W, self.NAV_H)

    # ── Main loop ────────────────────────────────
    def _update(self):
        if self.auto_rotate:
            if time.time() - self._last_rotate > self.rotate_sec:
                self.page_index   = (self.page_index + 1) % len(self.PAGES)
                self._last_rotate = time.time()
                self._draw_nav(self.W, self.NAV_H)

        data = self.data_mgr.get()
        self._draw_header()
        self._draw_page(data)
        self._refresh_ticker(data)

        # Refresh radar image every 2 minutes when on radar page
        if HAS_RADAR and self.PAGES[self.page_index] == "radar_placeholder":
            last = getattr(self, "_radar_last_refresh", 0)
            if time.time() - last > 120:
                self._radar_last_refresh = time.time()
                self._fetch_radar_async()

        self.after(1000, self._update)

