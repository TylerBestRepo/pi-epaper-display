#!/usr/bin/env python3
import sys
import os
import time
import requests
from datetime import datetime, timedelta
import json

# Add the waveshare library to path
sys.path.append('lib')

from waveshare_epd import epd2in13_V3  # Use whichever version worked for you
from PIL import Image, ImageDraw, ImageFont

# Cache file for weather data
WEATHER_CACHE_FILE = 'weather_cache.json'
WEATHER_UPDATE_INTERVAL = 3600  # 60 minutes in seconds

def load_weather_cache():
    """Load cached weather data if it exists and is recent"""
    try:
        if os.path.exists(WEATHER_CACHE_FILE):
            with open(WEATHER_CACHE_FILE, 'r') as f:
                cache = json.load(f)
                cache_time = datetime.fromisoformat(cache['timestamp'])
                
                # Check if cache is less than 60 minutes old
                if datetime.now() - cache_time < timedelta(seconds=WEATHER_UPDATE_INTERVAL):
                    print("Using cached weather data")
                    return cache['weather_data']
        return None
    except Exception as e:
        print(f"Error loading cache: {e}")
        return None

def save_weather_cache(weather_data):
    """Save weather data to cache with timestamp"""
    try:
        cache = {
            'timestamp': datetime.now().isoformat(),
            'weather_data': weather_data
        }
        with open(WEATHER_CACHE_FILE, 'w') as f:
            json.dump(cache, f)
        print("Weather data cached")
    except Exception as e:
        print(f"Error saving cache: {e}")

def get_weather():
    """Get weather data from cache or fetch new data if needed"""
    # Try to load from cache first
    cached_weather = load_weather_cache()
    if cached_weather:
        return cached_weather
    
    # Fetch new weather data
    try:
        print("Fetching fresh weather data...")
        # Melbourne coordinates (change to your city's coordinates)
        lat = -37.91806
        lon = 145.03544

        # Enhanced URL with more data including UV index, sunrise/sunset, and apparent temperature
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max&hourly=apparent_temperature,uv_index&timezone=auto"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            current = data['current_weather']
            daily = data['daily']
            hourly = data['hourly']
            
            # Get current hour index for hourly data
            current_time = datetime.fromisoformat(current['time'])
            current_hour = current_time.hour
            
            # Convert weather code to description
            weather_codes = {
                0: "Clear", 1: "Mostly Clear", 2: "Partly Cloudy", 3: "Overcast",
                45: "Fog", 48: "Rime Fog", 51: "Light Drizzle", 53: "Drizzle",
                55: "Heavy Drizzle", 61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
                71: "Light Snow", 73: "Snow", 75: "Heavy Snow", 80: "Rain Showers",
                81: "Rain Showers", 82: "Heavy Showers", 95: "Thunderstorm"
            }
            
            # Parse sunrise/sunset times
            sunrise_str = daily['sunrise'][0]
            sunset_str = daily['sunset'][0]
            sunrise_time = datetime.fromisoformat(sunrise_str).strftime("%I:%M").lstrip('0')
            sunset_time = datetime.fromisoformat(sunset_str).strftime("%I:%M").lstrip('0')
            
            weather_info = {
                'temp': round(current['temperature']),
                'feels_like': round(hourly['apparent_temperature'][current_hour]),
                'temp_max': round(daily['temperature_2m_max'][0]),
                'temp_min': round(daily['temperature_2m_min'][0]),
                'description': weather_codes.get(current['weathercode'], 'Unknown'),
                'wind_speed': round(current['windspeed']),
                'uv_index': round(daily['uv_index_max'][0]),
                'sunrise': sunrise_time,
                'sunset': sunset_time,
                'city': 'Melbourne'
            }
            
            # Save to cache
            save_weather_cache(weather_info)
            return weather_info
        else:
            print(f"Weather API error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Weather error: {e}")
        return None

def display_time_and_weather():
    try:
        print("Initializing e-paper display...")
        epd = epd2in13_V3.EPD()
        
        # Initialize display
        try:
            epd.init()
        except:
            try:
                epd.init(epd.FULL_UPDATE)
            except:
                epd.init(0)
        
        # Get current time
        now = datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip('0')  # Remove leading zero
        date_str = now.strftime("%a, %b %d")
        
        # Get weather (from cache or fresh)
        weather = get_weather()
        
        print(f"Displaying: {date_str} {time_str}")
        if weather:
            print(f"Weather: {weather['temp']}°C (feels {weather['feels_like']}°C), {weather['description']}")
            print(f"Sun: {weather['sunrise']} - {weather['sunset']}, UV: {weather['uv_index']}")
        
        # Create image (remember: height and width are swapped for landscape)
        image = Image.new('1', (epd.height, epd.width), 255)
        draw = ImageDraw.Draw(image)
        
        # Get actual display dimensions
        width = epd.height  # 250
        height = epd.width  # 122
        
        # Fonts
        try:
            font_xlarge = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
            font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
            font_medium = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
            font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 10)
            font_tiny = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 9)
        except:
            font_xlarge = ImageFont.load_default()
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_tiny = ImageFont.load_default()
        
        # Layout: Three columns
        left_col = 8
        middle_col = 85
        right_col = 170
        
        # Left column - Time and Date
        y_pos = 12
        
        # Time (large, centered in left area)
        time_bbox = draw.textbbox((0, 0), time_str, font=font_large)
        time_width = time_bbox[2] - time_bbox[0]
        time_x = left_col + (75 - time_width) // 2  # Center in left column
        draw.text((time_x, y_pos), time_str, font=font_large, fill=0)
        y_pos += 28
        
        # Date (centered under time)
        date_bbox = draw.textbbox((0, 0), date_str, font=font_small)
        date_width = date_bbox[2] - date_bbox[0]
        date_x = left_col + (75 - date_width) // 2
        draw.text((date_x, y_pos), date_str, font=font_small, fill=0)
        y_pos += 20
        
        # Sunrise/Sunset
        if weather:
            sun_text = f"☀ {weather['sunrise']}"
            draw.text((left_col, y_pos), sun_text, font=font_tiny, fill=0)
            y_pos += 12
            moon_text = f"🌙 {weather['sunset']}"
            draw.text((left_col, y_pos), moon_text, font=font_tiny, fill=0)
        
        # Middle column - Temperature
        if weather:
            y_pos = 12
            
            # Current temperature (large)
            temp_text = f"{weather['temp']}°"
            draw.text((middle_col, y_pos), temp_text, font=font_large, fill=0)
            y_pos += 22
            
            # Feels like
            feels_text = f"Feels {weather['feels_like']}°"
            draw.text((middle_col, y_pos), feels_text, font=font_tiny, fill=0)
            y_pos += 12
            
            # Min/Max temperatures
            minmax_text = f"{weather['temp_min']}° - {weather['temp_max']}°"
            draw.text((middle_col, y_pos), minmax_text, font=font_small, fill=0)
            y_pos += 15
            
            # Weather description
            desc = weather['description']
            if len(desc) > 10:
                desc = desc[:8] + ".."
            draw.text((middle_col, y_pos), desc, font=font_small, fill=0)
        
        # Right column - Additional info
        if weather:
            y_pos = 12
            
            # UV Index with warning level
            uv = weather['uv_index']
            if uv <= 2:
                uv_level = "Low"
            elif uv <= 5:
                uv_level = "Mod"
            elif uv <= 7:
                uv_level = "High"
            elif uv <= 10:
                uv_level = "V.High"
            else:
                uv_level = "Extreme"
            
            uv_text = f"UV {uv}"
            draw.text((right_col, y_pos), uv_text, font=font_small, fill=0)
            y_pos += 12
            draw.text((right_col, y_pos), uv_level, font=font_tiny, fill=0)
            y_pos += 15
            
            # Wind speed
            wind_text = f"Wind"
            draw.text((right_col, y_pos), wind_text, font=font_small, fill=0)
            y_pos += 12
            wind_speed_text = f"{weather['wind_speed']} km/h"
            draw.text((right_col, y_pos), wind_speed_text, font=font_tiny, fill=0)
        else:
            draw.text((middle_col, 20), "Weather", font=font_small, fill=0)
            draw.text((middle_col, 35), "unavailable", font=font_small, fill=0)
        
        # Vertical divider lines
        draw.line([(82, 8), (82, height-8)], fill=0, width=1)
        draw.line([(167, 8), (167, height-8)], fill=0, width=1)
        
        # Border
        draw.rectangle([(2, 2), (width-2, height-2)], outline=0, width=2)
        
        # Display
        epd.display(epd.getbuffer(image))
        print("Display updated successfully!")
        
        epd.sleep()
        
    except Exception as e:
        print(f"Error: {e}")

def run_continuous():
    """Run the display update in a continuous loop"""
    print("Starting continuous display updates...")
    print("Time updates every minute, weather updates every 60 minutes")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            display_time_and_weather()
            
            # Wait until the next minute
            now = datetime.now()
            seconds_until_next_minute = 60 - now.second
            print(f"Waiting {seconds_until_next_minute} seconds until next update...")
            time.sleep(seconds_until_next_minute)
            
    except KeyboardInterrupt:
        print("\nStopping display updates...")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        run_continuous()
    else:
        display_time_and_weather()