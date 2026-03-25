"""
icon_loader.py — loads weather icon PNGs from the icons/ directory.

Expected icon files (PNG, any size — will be resized automatically):
    icons/sunny.png
    icons/partly_cloudy.png
    icons/cloudy.png
    icons/rain.png
    icons/drizzle.png
    icons/showers.png
    icons/snow.png
    icons/tstorm.png
    icons/foggy.png
    icons/windy.png
    icons/clear.png          (same as sunny, or use a night variant)
    icons/unknown.png        (fallback for unrecognised conditions)

Condition strings from data_manager/helpers map to filenames via ICON_MAP below.
Add or rename entries here if your filenames differ.

Requires Pillow:  pip install Pillow
"""

import os
from PIL import Image, ImageTk

# ── Where to look for icons ──────────────────────────────────────────────────
# Searches next to this file, then cwd.
def _icons_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in [os.path.join(here, "icons"), os.path.join(os.getcwd(), "icons")]:
        if os.path.isdir(candidate):
            return candidate
    return None


# ── Condition string → filename (without extension) ─────────────────────────
ICON_MAP = {
    "SUNNY":      "sunny",
    "CLEAR":      "sunny",
    "M.CLEAR":    "sunny",
    "P.CLOUDY":   "partly_cloudy",
    "CLOUDY":     "cloudy",
    "OVERCAST":   "cloudy",
    "RAIN":       "rain",
    "DRIZZLE":    "drizzle",
    "SHOWERS":    "showers",
    "SNOW":       "snow",
    "T-STORM":    "tstorm",
    "FOGGY":      "foggy",
    "ICY FOG":    "foggy",
    "WINDY":      "windy",
    "VAR":        "partly_cloudy",
}

# ── Caches ───────────────────────────────────────────────────────────────────
_pil_cache = {}   # filename → PIL Image
_tk_cache  = {}   # "filename_SIZE" → ImageTk.PhotoImage  (must stay alive)

_icons_available = None   # None = not yet checked


def is_available() -> bool:
    """Return True if Pillow is installed and the icons/ directory exists."""
    global _icons_available
    if _icons_available is None:
        try:
            from PIL import Image, ImageTk
            _icons_available = _icons_dir() is not None
            if not _icons_available:
                print("icon_loader: icons/ directory not found — falling back to text labels")
        except ImportError:
            _icons_available = False
            print("icon_loader: Pillow not installed — falling back to text labels")
    return _icons_available


def get_icon(condition, size=64, master=None):
    """
    Return a Tkinter-compatible PhotoImage for the given condition string,
    or None if icons are unavailable.

    The caller MUST hold a reference to the returned object to prevent
    Tkinter's garbage collector from destroying it.

    Args:
        condition:  condition string, e.g. "SUNNY", "RAIN", "P.CLOUDY"
        size:       pixel size (width = height). Default 64.
        master:     Tkinter root window — must be passed before mainloop starts
    """
    if not is_available():
        return None

    cond     = condition.upper().strip()
    filename = ICON_MAP.get(cond, "unknown")
    tk_key   = f"{filename}_{size}"

    if tk_key in _tk_cache:
        return _tk_cache[tk_key]

    icons_dir = _icons_dir()
    if icons_dir is None:
        return None

    # Load PIL image (cached at original size)
    if filename not in _pil_cache:
        path = os.path.join(icons_dir, f"{filename}.png")
        if not os.path.exists(path):
            path = os.path.join(icons_dir, "unknown.png")
        if not os.path.exists(path):
            print(f"icon_loader: missing {filename}.png (and no unknown.png fallback)")
            _pil_cache[filename] = None
        else:
            try:
                _pil_cache[filename] = Image.open(path).convert("RGBA")
            except Exception as e:
                print(f"icon_loader: could not load {path}: {e}")
                _pil_cache[filename] = None

    pil_img = _pil_cache.get(filename)
    if pil_img is None:
        return None

    resized = pil_img.resize((size, size), Image.LANCZOS) if pil_img.size != (size, size) else pil_img.copy()

    try:
        tk_img = ImageTk.PhotoImage(resized, master=master)
        _tk_cache[tk_key] = tk_img
        return tk_img
    except Exception as e:
        print(f"icon_loader: ImageTk failed for {filename}: {e}")
        return None


def preload_all(size=64, master=None):
    """Pre-load all mapped icons at startup to avoid first-draw lag."""
    if not is_available():
        return
    loaded = 0
    for cond in ICON_MAP:
        img = get_icon(cond, size, master=master)
        if img:
            loaded += 1
    print(f"icon_loader: preloaded {loaded} icons at {size}px")


def list_expected_files():
    """Return the list of PNG filenames the loader expects in icons/."""
    return sorted(set(f"{v}.png" for v in ICON_MAP.values())) + ["unknown.png"]
