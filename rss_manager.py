"""
rss_manager.py — fetches news headlines from RSS feeds in a background thread.
"""

import threading
import time
import html
import re
import xml.etree.ElementTree as ET

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from config import CONFIG


def _clean_headline(text):
    """Strip HTML entities, tags, and extra whitespace. Uppercase for ticker feel."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.upper()


class RSSFeedManager:
    """Fetches headlines from configured RSS feeds in a background thread."""

    def __init__(self):
        self.headlines   = []   # list of (source_label, headline_text)
        self.lock        = threading.Lock()
        self._running    = True

    def start(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    def _loop(self):
        time.sleep(5)   # stagger so app UI loads first
        self._fetch_all()
        while self._running:
            self._fetch_all()
            time.sleep(CONFIG["rss_refresh_sec"])

    def _fetch_all(self):
        if not HAS_REQUESTS:
            return
        all_headlines = []
        for label, url in CONFIG.get("rss_feeds", []):
            #print(f"DEBUG: Fetching RSS url: {url}")
            try:
                r    = requests.get(url, timeout=10, headers={"User-Agent": "WeatherPi/1.0"})
                root = ET.fromstring(r.content)
                ns   = {"atom": "http://www.w3.org/2005/Atom"}

                items = root.findall(".//item")
                if not items:
                    items = root.findall(".//item") or root.findall(".//atom:entry", ns)
                
                count = 0
                for item in items:
                    if count >= CONFIG["rss_max_per_feed"]:
                        break
                    
                    title_el = item.find("title")
                    if title_el is None:
                        titel_el = item.find("{http://www.w3.org/2005/Atom}/title")

                    if title_el is None or not title_el.text:
                        continue

                    headline = _clean_headline(title_el.text)
                    if headline:
                        all_headlines.append((label.upper(), headline))
                        count += 1
                print(f"RSS [{label}]: fetched {count} headlines")
            except Exception as e:
                print(f"RSS fetch error [{label}]: {e}")

        if all_headlines:
            with self.lock:
                self.headlines = all_headlines

    def get_ticker_segments(self):
        """Return list of (label, headline) tuples, thread-safe."""
        with self.lock:
            return list(self.headlines)
