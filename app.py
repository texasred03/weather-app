import os
import requests
from flask import Flask, render_template,jsonify
import json
import threading
import pygame
import time
import random
from config import API_KEY, APPLICATION_KEY, DEVICE_ID, LATITUDE, LONGITUDE

app = Flask(__name__)

# Directory for music files
MUSIC_DIR = 'static/music/'

# List of available music files
music_files = ['music1.mp3', 'music2.mp3', 'music3.mp3']

# Function to fetch weather data from Ambient Weather API
def fetch_weather_data():
    try:
        # API URL to get the device data
        url = f"https://api.ambientweather.net/v1/devices?apiKey={API_KEY}&applicationKey={APPLICATION_KEY}"
        response = requests.get(url)
        weather_data = response.json()

        # Check if data is received successfully
        if weather_data:
            print("Weather data fetched successfully:", json.dumps(weather_data, indent=4))
            return weather_data
        else:
            print("No weather data returned.")
            return None
    except Exception as e:
        print("Error fetching weather data:", e)
        return None

def fetch_weather_alerts(lat, lon):
    nws_url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
    try:
        response = requests.get(nws_url, timeout=5)
        data = response.json()
        
        if "features" in data and data["features"]:
            return data["features"][0]["properties"]["headline"]
        else:
            return "No active weather alerts."
    except Exception as e:
        print(f"Error fetching alerts: {e}")
        return "Could not fetch alerts."

# Function to play music if available
def play_music():
    pygame.mixer.init()
    while True:
        # Randomly select a music file from the list
        music_file = random.choice(music_files)

        # Check if the music file exists
        music_path = os.path.join(MUSIC_DIR, music_file)
        if os.path.exists(music_path):
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play(-1)  # Play on loop
        else:
            print(f"Music file {music_file} not found, skipping...")

        time.sleep(300)  # Play music every 5 minutes

# Start music playback in a separate thread
music_thread = threading.Thread(target=play_music)
music_thread.daemon = True  # Allows the thread to exit when the main program exits
music_thread.start()

@app.route('/weather')
def get_weather():
    weather_data = fetch_weather_data()  # Ensure this function exists
    return jsonify(weather_data)

@app.route('/alerts')
def get_alerts():
    alert = fetch_weather_alerts(LATITUDE, LONGITUDE)
    return jsonify({"alert": alert})

@app.route('/')
def index():
    weather_data = fetch_weather_data()
    if weather_data:
        # Extract relevant data from the response
        temp = weather_data[0]['lastData']['tempf']  # Example for temperature
        humidity = weather_data[0]['lastData']['humidity']  # Example for humidity
        wind_speed = weather_data[0]['lastData']['windspeedmph']  # Example for wind speed

        # Fetch weather alert
        alert = fetch_weather_alerts(LATITUDE, LONGITUDE)

        # Log the values to check if they are being extracted properly
        print(f"Temperature: {temp}°F")
        print(f"Humidity: {humidity}%")
        print(f"Wind Speed: {wind_speed} mph")

        # Pass data to the template
        return render_template('index.html', temp=temp, humidity=humidity, wind_speed=wind_speed, alert=alert)
    else:
        return "Weather data not available"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
