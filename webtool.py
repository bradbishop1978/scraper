import streamlit as st
import pandas as pd
import json
from datetime import datetime
import io
import re
import time

# Try to import Selenium (the browser automation tool)
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

def setup_browser():
    """Set up the robot browser (Chrome)"""
    if not SELENIUM_AVAILABLE:
        st.error("🤖 Browser automation not available. Please install Selenium first!")
        st.code("pip install selenium")
        return None
    
    try:
        # Configure the robot browser
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # You can make the browser visible by commenting out this line:
        chrome_options.add_argument("--headless")  # Remove this to see the browser working
        
        # Start the robot browser
        driver = webdriver.Chrome(options=chrome_options)
        return driver
        
    except Exception as e:
        st.error(f"❌ Could not start browser robot: {str(e)}")
        st.info("💡 Make sure Chrome browser is installed on your computer")
        return None

def robot_search_locations(driver, search_terms, progress_bar, status_text):
    """Make the robot search for locations using different terms"""
    
    try:
        # Step 1: Robot goes to Hunt Brothers website
        status_text.text("🤖 Robot is opening Hunt Brothers website...")
        driver.get("https://www.huntbrotherspizza.com/locations/")
        
        # Step 2: Robot waits for page to load (like waiting for a slow website)
        status_text.text("⏳ Robot is waiting for website to load...")
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)  # Extra wait for dynamic content
        
        # Step 3: Robot looks for the search box
        status_text.text("🔍 Robot is looking for the search box...")
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="text"], input[placeholder*="address"], input[placeholder*="zip"]'))
        )
        
        status_text.text("✅ Robot found the search box!")
        
        # Step 4: Robot searches using different terms
        total_searches = len(search_terms)
        
        for i, search_term in enumerate(search_terms):
            # Update progress
            progress = (i + 1) / total_searches
            progress_bar.progress(progress)
            status_text.text(f"🤖 Robot is searching for: '{search_term}' ({i+1}/{total_searches})")
            
            try:
                # Robot clears the search box and types new search term
                search_input.clear()
                if search_term:  # Don't type anything for empty search
                    search_input.send_keys(search_term)
                
                # Robot presses Enter (like you pressing Enter key)
                search_input.send_keys(Keys.RETURN)
                
                # Robot waits for results to load
                time.sleep(3)
                
                # Robot checks if location list appeared
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".hbp-location-list"))
                    )
                except TimeoutException:
                    pass  # Continue even if specific element not found
                
            except Exception as e:
                st.warning(f"⚠️ Robot had trouble with search '{search_term}': {str(e)}")
                continue
        
        status_text.text("🎉 Robot finished all searches!")
        return True
        
    except Exception as e:
        st.error(f"❌ Robot encountered an error: {str(e)}")
        return False

def robot_extract_html(driver):
    """Robot copies all the location data from the website"""
    try:
        # Robot gets the entire webpage content
        html_content = driver.page_source
        return html_content
    except Exception as e:
        st.error(f"❌ Robot couldn't copy the webpage: {str(e)}")
        return None

def parse_hunt_brothers_html(html_content):
    """Parse the location data from HTML (same as before)"""
    locations = []
    
    try:
        # Find the location list container
        list_start = html_content.find('<div class="hbp-location-list">')
        if list_start == -1:
            st.warning("Could not find location list in the webpage")
            return []
        
        # Find the end of the container by counting div tags
        div_count = 1
        search_pos = list_start + len('<div class="hbp-location-list">')
        
        while div_count > 0 and search_pos < len(html_content):
            next_open = html_content.find('<div', search_pos)
            next_close = html_content.find('</div>', search_pos)
            
            if next_close == -1:
                break
            
            if next_open != -1 and next_open < next_close:
                div_count += 1
                search_pos = next_open + 4
            else:
                div_count -= 1
                search_pos = next_close + 6
                if div_count == 0:
                    list_end = next_close + 6
                    break
        
        container_html = html_content[list_start:list_end]
        
        # Find all individual location blocks
        location_pattern = r'<div class="listed-location"[^>]*data-lat="([^"]*)"[^>]*data-lng="([^"]*)"[^>]*>(.*?)</div>\s*</div>\s*</div>'
        location_matches = re.findall(location_pattern, container_html, re.DOTALL)
        
        st.info(f"📍 Found {len(location_matches)} locations in the webpage!")
        
        for i, (lat, lng, location_html) in enumerate(location_matches):
            try:
                location_data = parse_single_location(location_html, lat, lng, i)
                if location_data:
                    locations.append(location_data)
            except Exception as e:
                continue
        
        return locations
        
    except Exception as e:
        st.error(f"Error parsing location data: {str(e)}")
        return []

def parse_single_location(location_html, latitude, longitude, index):
    """Parse individual location data"""
    try:
        # Extract distance
        distance_match = re.search(r'<span class="distance">([^<]*)</span>', location_html)
        distance = distance_match.group(1).strip() if distance_match else ""
        
        # Extract store name
        name_match = re.search(r'<h3><a[^>]*>([^<]*)</a></h3>', location_html)
        store_name = name_match.group(1).strip() if name_match else ""
        
        # Extract location ID
        id_match = re.search(r'/location-details/(\d+)', location_html)
        location_id = id_match.group(1) if id_match else ""
        
        # Extract address
        address_match = re.search(r'<i[^>]*></i>\s*([^<]*)<br>([^<]*)</a>', location_html, re.DOTALL)
        
        street_address = ""
        city_state_zip = ""
        city = ""
        state = ""
        zip_code = ""
        
        if address_match:
            street_address = address_match.group(1).strip()
            city_state_zip = address_match.group(2).strip()
            
            # Parse city, state, zip
            csz_match = re.search(r'([^,]+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', city_state_zip)
            if csz_match:
                city = csz_match.group(1).strip()
                state = csz_match.group(2).strip()
                zip_code = csz_match.group(3).strip()
        
        # Extract phone number
        phone_match = re.search(r'<a href="tel:[^"]*"[^>]*><i[^>]*></i>\s*([^<]*)</a>', location_html)
        phone = phone_match.group(1).strip() if phone_match else ""
        
        return {
            'locationId': location_id,
            'storeName': store_name,
            'address': street_address,
            'city': city,
            'state': state,
            'zipCode': zip_code,
            'phone': phone,
            'latitude': latitude,
            'longitude': longitude,
            'distance': distance,
            'fullAddress': f"{street_address}, {city_state_zip}" if street_address and city_state_zip else "",
            'elementIndex': index
        }
        
    except Exception as e:
        return None

def generate_search_terms():
    """Create a list of search terms to find all locations"""
    
    # States where Hunt Brothers operates
    states = [
        "AL", "AR", "FL", "GA", "IL", "IN", "IA", "KS", "KY", "LA", 
        "MS", "MO", "NE", "NC", "OH", "OK", "SC", "TN", "TX", "VA", "WV"
    ]
    
    # Major cities in Hunt Brothers territory
    cities = [
        "Nashville", "Memphis", "Knoxville", "Chattanooga", "Birmingham", 
        "Montgomery", "Louisville", "Lexington", "Atlanta", "Augusta", 
        "Jackson", "Gulfport", "Little Rock", "Fort Smith", "St. Louis", 
        "Kansas City", "Charlotte", "Raleigh", "Columbia", "Charleston",
        "Richmond", "Norfolk", "Huntington", "Columbus", "Indianapolis"
    ]
    
    # Some zip codes to try
    zip_codes = [
        "37201", "38103", "35203", "40202", "30301", "39201", 
        "72201", "63101", "27601", "29201", "23219", "25301"
    ]
    
    # Combine all search terms
    search_terms = [""] + states + cities[:10] + zip_codes[:5]  # Limit for efficiency
    
    return search_terms

def create_sample_data():
    """Sample data for demo mode"""
    return [
        {
            'locationId': '81626',
            'storeName': 'CENEX ZIP TRIP #50',
            'address': '11 HWY 10 E',
            'city': 'PARK CITY',
            'state': 'MT',
            'zipCode': '59063',
            'phone': '(406) 633-2359',
            'latitude': '45.634266',
            'longitude': '-108.918157',
            'distance': '7235.05 miles',
            'fullAddress': '11 HWY 10 E, PARK CITY, MT 59063',
            'elementIndex': 0
        },
        {
            'locationId': '185656',
            'storeName': 'HARDIN KOA',
            'address': '2205 HWY 47',
            'city': 'HARDIN',
            'state': 'MT',
            'zipCode': '59034',
            'phone': '(406) 665-1635',
            'latitude': '45.820352',
            'longitude': '-107.611961',
            'distance': '7274.34 miles',
            'fullAddress': '2205 HWY 47, HARDIN, MT 59034',
            'elementIndex': 1
        }
    ]

def main():
    st.set_page_config(
        page_title="Hunt Brothers Complete Scraper",
        page_icon="🍕",
        layout="wide"
    )
    
    st.title("🍕 Hunt Brothers Pizza - Complete Location Scraper")
    st.markdown("**With Browser Automation** - Extracts ALL locations automatically!")
    
    # Check if Selenium is available
    if not SELENIUM_AVAILABLE:
        st.error("🤖 **Browser Automation Not Available**")
        st.markdown("""
        To use the complete scraper with browser automation, you need to install Selenium:
        
        ```bash
        pip install selenium
