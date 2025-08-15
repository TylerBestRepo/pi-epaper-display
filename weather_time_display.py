#!/usr/bin/env python3
import sys
import os
import time
import requests
from datetime import datetime

# Add the waveshare library to path
sys.path.append('lib')

from waveshare_epd import epd2in13_V3  # Use whichever version worked for you
from PIL import Image, ImageDraw, ImageFont

def get_weather():
    """Get weather data from OpenMeteo API (free, no API key needed)"""
    try:
        # Melbourne coordinates (change to your city's coordinates)
        lat = -37.8136
        lon = 144.9631
        
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            current = data['current_weather']
            
            # Convert weather code to description
            weather_codes = {
                0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle",
                55: "Heavy drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
                71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Rain showers",
                81: "Rain showers", 82: "Heavy showers", 95: "Thunderstorm"
            }
            
            weather_info = {
                'temp': round(current['temperature']),
                'description': weather_codes.get(current['weathercode'], 'Unknown'),
                'wind_speed': round(current['windspeed']),
                'city': 'Melbourne'  # You can customize this
            }
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
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%a, %b %d")
        
        # Get weather
        weather = get_weather()
        
        print(f"Displaying: {date_str} {time_str}")
        if weather:
            print(f"Weather: {weather['temp']}°C, {weather['description']}")
        
        # Create image
        image = Image.new('1', (epd.height, epd.width), 255)
        draw = ImageDraw.Draw(image)
        
        # Fonts
        try:
            font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
            font_medium = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
            font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 10)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw content
        y_pos = 8
        
        # Time (large)
        draw.text((10, y_pos), time_str, font=font_large, fill=0)
        y_pos += 20
        
        # Date
        draw.text((10, y_pos), date_str, font=font_medium, fill=0)
        y_pos += 18
        
        # Weather section
        if weather:
            # Temperature
            temp_text = f"{weather['temp']}°C"
            draw.text((10, y_pos), temp_text, font=font_medium, fill=0)
            y_pos += 15
            
            # Weather description
            desc = weather['description']
            if len(desc) > 20:
                desc = desc[:17] + "..."
            draw.text((10, y_pos), desc, font=font_small, fill=0)
            y_pos += 12
            
            # City and wind
            draw.text((10, y_pos), f"{weather['city']}", font=font_small, fill=0)
            draw.text((10, y_pos + 10), f"Wind: {weather['wind_speed']} km/h", font=font_small, fill=0)
        else:
            draw.text((10, y_pos), "Weather unavailable", font=font_small, fill=0)
        
        # Border
        draw.rectangle([(2, 2), (epd.height-2, epd.width-2)], outline=0, width=1)
        
        # Display
        epd.display(epd.getbuffer(image))
        print("Display updated successfully!")
        
        epd.sleep()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    display_time_and_weather()