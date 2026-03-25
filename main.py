#!/usr/bin/env python3
"""
main.py — Retro Weather Channel Station entry point.

Usage:
    python3 main.py                          # touchscreen + web
    python3 main.py --web-only               # web server only (no display)
    python3 main.py --config /path/to/cfg    # use specific config file
"""

import argparse
import time
import sys

from config import CONFIG, reload_config
from rss_manager import RSSFeedManager
from data_manager import WeatherDataManager

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from flask_server import FlaskServer
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


def main():
    parser = argparse.ArgumentParser(description="Retro Weather Station")
    parser.add_argument("--web-only", action="store_true",
                        help="Run web server only (no Tkinter display)")
    parser.add_argument("--config", metavar="PATH",
                        help="Path to config.json (overrides auto-discovery)")
    args = parser.parse_args()

    if args.config:
        reload_config(args.config)

    print("Starting Retro Weather Station...")
    print(f"Demo mode:  {CONFIG['demo_mode']}")
    print(f"Location:   {CONFIG['location_name']}")
    print(f"Web port:   {CONFIG['web_port']}")
    if args.web_only:
        print("Mode:       web only")

    # Start background data managers
    rss_mgr = RSSFeedManager()
    rss_mgr.start()

    mgr = WeatherDataManager(rss_mgr=rss_mgr)
    mgr.start()

    # Start Flask web server
    if HAS_FLASK and CONFIG.get("web_enabled", True):
        flask_srv = FlaskServer(mgr)
        flask_srv.start()
    elif not HAS_FLASK:
        print("Warning: Flask not installed — web UI disabled.")

    # Start Tkinter display or block in web-only mode
    if args.web_only:
        print(f"Web UI at http://0.0.0.0:{CONFIG.get('web_port', 5000)}")
        print("Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            mgr.stop()
            rss_mgr.stop()
            print("Weather station stopped.")
    else:
        try:
            from tkinter_app import RetroWeatherApp
        except Exception as e:
            print(f"Error loading Tkinter display: {e}")
            print("Try running with --web-only if no display is attached.")
            sys.exit(1)

        app = RetroWeatherApp(mgr)
        app.start_ticker()
        try:
            app.mainloop()
        finally:
            mgr.stop()
            rss_mgr.stop()
            print("Weather station stopped.")


if __name__ == "__main__":
    main()
