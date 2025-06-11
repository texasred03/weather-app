from flask import Flask, render_template, jsonify
import requests
from config import API_KEY, APPLICATION_KEY, LATITUDE, LONGITUDE
# from music_routes import music_bp  # Import the music Blueprint

app = Flask(__name__)

# Register the music Blueprint
# app.register_blueprint(music_bp) # commented out

# Function to fetch weather data from Ambient Weather API
def fetch_weather_data():
    try:
        # API URL to get the device data
        url = f"https://api.ambientweather.net/v1/devices?apiKey={API_KEY}&applicationKey={APPLICATION_KEY}"
        response = requests.get(url)
        weather_data = response.json()

        # Check if data is received successfully
        if weather_data:
            print("Weather data fetched successfully")
            # print(json.dumps(weather_data, indent=4))
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
        
        weather_station_id = weather_data[0]['info']['name']

        temp = weather_data[0]['lastData']['tempf']
        feelsLike = weather_data[0]['lastData']['feelsLike']
        humidity = weather_data[0]['lastData']['humidity']  
        wind_speed = weather_data[0]['lastData']['windspeedmph'] 
        pressure = weather_data[0]['lastData']['baromrelin']

        lat = weather_data[0]['info']['coords']['coords']['lat']
        long = weather_data[0]['info']['coords']['coords']['lon']

        city = weather_data[0]['info']['coords']['address_components'][2]['long_name']
        state =  weather_data[0]['info']['coords']['address_components'][4]['long_name']
        county =  weather_data[0]['info']['coords']['address_components'][3]['long_name']

        # Fetch weather alert
        alert = fetch_weather_alerts(lat, long)

        # Pass data to the template
        return render_template('index.html', weather_station_id = weather_station_id, temp=temp, feelsLike = feelsLike, pressure = pressure,
                                humidity=humidity, wind_speed=wind_speed, alert=alert, city=city, state=state, county=county)
    else:
        return "Weather data not available"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
