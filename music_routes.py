import os
from flask import Flask, Blueprint, jsonify, send_from_directory

# Define a Blueprint for music
music_bp = Blueprint("music", __name__)

# Directory for music files
MUSIC_DIR = "static/music"

@music_bp.route("/music/<path:filename>")
def serve_music(filename):
    """Serve music files from the static directory."""
    return send_from_directory(MUSIC_DIR, filename)

@music_bp.route("/music")
def get_music():
    """Return a list of available music files."""
    try:
        music_files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(".mp3")]
        return jsonify({"music_files": music_files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
