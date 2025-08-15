#!/usr/bin/env python3
import sys
import os
import time
from datetime import datetime

# Add the waveshare library to path
sys.path.append('lib')

from waveshare_epd import epd2in13_V3  # Use whichever version worked for you
from PIL import Image, ImageDraw, ImageFont

def display_time():
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
        date_str = now.strftime("%A")  # Day of week
        date_num = now.strftime("%B %d, %Y")  # Month Day, Year
        time_str = now.strftime("%I:%M %p")  # Time in 12-hour format
        
        print(f"Displaying: {date_str}, {date_num} at {time_str}")
        
        # Create image
        image = Image.new('1', (epd.height, epd.width), 255)  # 255: clear/white
        draw = ImageDraw.Draw(image)
        
        # Try to use a default font, fallback to basic if not available
        try:
            font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
            font_medium = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
            font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw text on image
        y_pos = 10
        draw.text((10, y_pos), date_str, font=font_medium, fill=0)
        y_pos += 25
        draw.text((10, y_pos), date_num, font=font_small, fill=0)
        y_pos += 25
        draw.text((10, y_pos), time_str, font=font_large, fill=0)
        
        # Add a simple border
        draw.rectangle([(5, 5), (epd.height-5, epd.width-5)], outline=0, width=2)
        
        # Display the image
        epd.display(epd.getbuffer(image))
        print("Time displayed successfully!")
        
        # Put display to sleep to save power
        epd.sleep()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    display_time()