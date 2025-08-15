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

def get_pi_power():
    """Get Pi's power consumption"""
    try:
        # Try multiple possible locations for voltage reading
        voltage_paths = [
            '/sys/class/hwmon/hwmon0/in1_input',
            '/sys/class/hwmon/hwmon1/in1_input', 
            '/sys/firmware/devicetree/base/chosen/power/regulator-min-microvolt',
            '/proc/device-tree/chosen/power/regulator-min-microvolt'
        ]
        
        voltage = None
        for path in voltage_paths:
            try:
                with open(path, 'r') as f:
                    value = float(f.read().strip())
                    if path.endswith('in1_input'):
                        voltage = value / 1000  # Convert to volts
                    else:
                        voltage = value / 1000000  # Convert from microvolts
                    print(f"Found voltage at {path}: {voltage}V")
                    break
            except:
                continue
        
        if voltage is None:
            # Try reading from vcgencmd (Raspberry Pi specific)
            import subprocess
            result = subprocess.run(['vcgencmd', 'measure_volts', 'core'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                # Output format: "volt=1.2000V"
                voltage_str = result.stdout.strip().split('=')[1].replace('V', '')
                voltage = float(voltage_str)
                print(f"Found voltage via vcgencmd: {voltage}V")
        
        if voltage:
            # Estimate current based on Pi model (Zero 2W typically draws 0.4-0.8A)
            estimated_current = 0.6  # Amps
            power_watts = voltage * estimated_current
            
            return {
                'voltage': round(voltage, 1),
                'power': round(power_watts, 1),
                'current': estimated_current
            }
        else:
            print("Could not find voltage reading")
            return None
            
    except Exception as e:
        print(f"Power monitoring error: {e}")
        return None

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
        # lat = -37.8136
        # lon = 144.9631

        # Import coordinates from config
        try:
            from config import LATITUDE, LONGITUDE, CITY
            lat = LATITUDE
            lon = LONGITUDE
            city_name = CITY
        except ImportError:
            print("Config file not found, using default Melbourne coordinates")
            lat = -37.8136
            lon = 144.9631
            city_name = "Melbourne"
        
        # Enhanced URL with more data
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&daily=temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max&hourly=apparent_temperature&timezone=auto"
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
            sunrise_time = datetime.fromisoformat(sunrise_str).strftime("%H:%M")
            sunset_time = datetime.fromisoformat(sunset_str).strftime("%H:%M")
            
            weather_info = {
                'temp': round(current['temperature']),
                'feels_like': round(hourly['apparent_temperature'][current_hour]) if current_hour < len(hourly['apparent_temperature']) else round(current['temperature']),
                'temp_max': round(daily['temperature_2m_max'][0]),
                'temp_min': round(daily['temperature_2m_min'][0]),
                'description': weather_codes.get(current['weathercode'], 'Unknown'),
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
        
        # Create image (remember: height and width are swapped for landscape)
        image = Image.new('1', (epd.height, epd.width), 255)
        draw = ImageDraw.Draw(image)
        
        # Get actual display dimensions
        width = epd.height  # 250
        height = epd.width  # 122
        
        # Fonts
        try:
            font_huge = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 28)
            font_xlarge = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
            font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 14)
            font_medium = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
            font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 10)
        except:
            font_huge = ImageFont.load_default()
            font_xlarge = ImageFont.load_default()
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        if weather:
            # Top section - Time and Temperature side by side
            y_top = 8
            
            # Time on the left
            draw.text((15, y_top), time_str, font=font_huge, fill=0)
            
            # Temperature on the right
            temp_text = f"{weather['temp']}°"
            temp_bbox = draw.textbbox((0, 0), temp_text, font=font_huge)
            temp_width = temp_bbox[2] - temp_bbox[0]
            temp_x = width - temp_width - 15  # Right aligned with margin
            draw.text((temp_x, y_top), temp_text, font=font_huge, fill=0)
            
            # Weather description - centered under the TEMPERATURE (not the whole section)
            desc = weather['description']
            if len(desc) > 18:
                desc = desc[:16] + ".."
            desc_bbox = draw.textbbox((0, 0), desc, font=font_medium)
            desc_width = desc_bbox[2] - desc_bbox[0]
            # Center the description under the temperature
            desc_x = temp_x + (temp_width - desc_width) // 2
            draw.text((desc_x, y_top + 35), desc, font=font_medium, fill=0)
            
            # Bottom row - grouped information in three sections
            y_bottom = 68
            
            # Left section - Date and Power
            draw.text((8, y_bottom), date_str, font=font_large, fill=0)

            # Get and display power info
            power_info = get_pi_power()
            if power_info:
                power_text = f"{power_info['power']}W {power_info['voltage']}V"
                draw.text((8, y_bottom + 16), power_text, font=font_small, fill=0)
            else:
                draw.text((8, y_bottom + 16), "Power: N/A", font=font_small, fill=0)
            
            # Middle section - Temperature details
            middle_x = 110
            feels_text = f"Feels {weather['feels_like']}°"
            draw.text((middle_x, y_bottom), feels_text, font=font_small, fill=0)
            
            range_text = f"{weather['temp_min']}° - {weather['temp_max']}°"
            draw.text((middle_x, y_bottom + 12), range_text, font=font_small, fill=0)
            
            # Right section - Sun & UV
            right_x = 170
            sun_text = f"☀{weather['sunrise']}"
            draw.text((right_x, y_bottom), sun_text, font=font_small, fill=0)
            
            moon_text = f"◐{weather['sunset']}"  # Half moon symbol
            draw.text((right_x, y_bottom + 12), moon_text, font=font_small, fill=0)
            
            # UV at bottom right
            uv = weather['uv_index']
            if uv <= 2:
                uv_level = "Low"
            elif uv <= 5:
                uv_level = "Mod"
            elif uv <= 7:
                uv_level = "High"
            else:
                uv_level = "V.High"
            
            uv_text = f"UV{uv} {uv_level}"
            draw.text((right_x, y_bottom + 24), uv_text, font=font_small, fill=0)
            
            # Separator line above bottom section
            draw.line([(10, y_bottom - 4), (width - 10, y_bottom - 4)], fill=0, width=1)
            
        else:
            # Fallback if no weather - still show time prominently
            draw.text((15, 15), time_str, font=font_huge, fill=0)
            
            no_weather_text = "Weather Unavailable"
            bbox = draw.textbbox((0, 0), no_weather_text, font=font_medium)
            text_width = bbox[2] - bbox[0]
            text_x = (width - text_width) // 2
            draw.text((text_x, 50), no_weather_text, font=font_medium, fill=0)
            
            # Date below
            draw.text((15, 70), date_str, font=font_large, fill=0)
        
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