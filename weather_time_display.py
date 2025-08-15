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
            daily = data['daily']
            
            # Convert weather code to description
            weather_codes = {
                0: "Clear", 1: "Mostly Clear", 2: "Partly Cloudy", 3: "Overcast",
                45: "Fog", 48: "Rime Fog", 51: "Light Drizzle", 53: "Drizzle",
                55: "Heavy Drizzle", 61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
                71: "Light Snow", 73: "Snow", 75: "Heavy Snow", 80: "Rain Showers",
                81: "Rain Showers", 82: "Heavy Showers", 95: "Thunderstorm"
            }
            
            weather_info = {
                'temp': round(current['temperature']),
                'temp_max': round(daily['temperature_2m_max'][0]),
                'temp_min': round(daily['temperature_2m_min'][0]),
                'description': weather_codes.get(current['weathercode'], 'Unknown'),
                'wind_speed': round(current['windspeed']),
                'city': 'Melbourne'
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
        time_str = now.strftime("%I:%M %p").lstrip('0')  # Remove leading zero
        date_str = now.strftime("%a, %b %d")
        
        # Get weather
        weather = get_weather()
        
        print(f"Displaying: {date_str} {time_str}")
        if weather:
            print(f"Weather: {weather['temp']}°C ({weather['temp_min']}-{weather['temp_max']}°C), {weather['description']}")
        
        # Create image (remember: height and width are swapped for landscape)
        image = Image.new('1', (epd.height, epd.width), 255)
        draw = ImageDraw.Draw(image)
        
        # Get actual display dimensions
        width = epd.height  # 250
        height = epd.width  # 122
        
        # Fonts
        try:
            font_xlarge = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24)
            font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
            font_medium = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
            font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
        except:
            font_xlarge = ImageFont.load_default()
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Layout: Two columns
        left_col = 10
        right_col = 130
        
        # Left column - Time and Date
        y_pos = 15
        
        # Time (large, centered in left area)
        time_bbox = draw.textbbox((0, 0), time_str, font=font_xlarge)
        time_width = time_bbox[2] - time_bbox[0]
        time_x = left_col + (110 - time_width) // 2  # Center in left column
        draw.text((time_x, y_pos), time_str, font=font_xlarge, fill=0)
        y_pos += 35
        
        # Date (centered under time)
        date_bbox = draw.textbbox((0, 0), date_str, font=font_medium)
        date_width = date_bbox[2] - date_bbox[0]
        date_x = left_col + (110 - date_width) // 2
        draw.text((date_x, y_pos), date_str, font=font_medium, fill=0)
        
        # Right column - Weather
        if weather:
            y_pos = 15
            
            # Current temperature (large)
            temp_text = f"{weather['temp']}°"
            draw.text((right_col, y_pos), temp_text, font=font_large, fill=0)
            y_pos += 25
            
            # Min/Max temperatures
            minmax_text = f"{weather['temp_min']}° - {weather['temp_max']}°"
            draw.text((right_col, y_pos), minmax_text, font=font_small, fill=0)
            y_pos += 18
            
            # Weather description
            desc = weather['description']
            if len(desc) > 12:  # Adjust for smaller space
                desc = desc[:10] + ".."
            draw.text((right_col, y_pos), desc, font=font_small, fill=0)
            y_pos += 15
            
            # Wind speed
            wind_text = f"{weather['wind_speed']} km/h"
            draw.text((right_col, y_pos), wind_text, font=font_small, fill=0)
        else:
            draw.text((right_col, 20), "Weather", font=font_small, fill=0)
            draw.text((right_col, 35), "unavailable", font=font_small, fill=0)
        
        # Vertical divider line
        draw.line([(125, 10), (125, height-10)], fill=0, width=1)
        
        # Border
        draw.rectangle([(2, 2), (width-2, height-2)], outline=0, width=2)
        
        # Display
        epd.display(epd.getbuffer(image))
        print("Display updated successfully!")
        
        epd.sleep()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    display_time_and_weather()