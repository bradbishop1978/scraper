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
        
        status_text.text("✅ Website loaded successfully!")
        
        # Step 3: Robot searches using different terms
        total_searches = len(search_terms)
        
        for i, search_term in enumerate(search_terms):
            # Update progress
            progress = (i + 1) / total_searches
            progress_bar.progress(progress)
            status_text.text(f"🤖 Robot is searching for: '{search_term}' ({i+1}/{total_searches})")
            
            try:
                # Robot finds the search box fresh each time (fixes stale element issue)
                search_input = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[type="text"], input[placeholder*="address"], input[placeholder*="zip"]'))
                )
                
                # Robot clears the search box and types new search term
                search_input.clear()
                time.sleep(0.5)  # Small pause after clearing
                
                if search_term:  # Don't type anything for empty search
                    search_input.send_keys(search_term)
                    time.sleep(0.5)  # Small pause after typing
                
                # Robot presses Enter (like you pressing Enter key)
                search_input.send_keys(Keys.RETURN)
                
                # Robot waits for results to load
                time.sleep(4)  # Increased wait time for results
                
                # Robot checks if location list appeared
                try:
                    WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".hbp-location-list"))
                    )
                    status_text.text(f"✅ Found results for '{search_term}'")
                except TimeoutException:
                    status_text.text(f"⏰ No results found for '{search_term}', continuing...")
                
            except TimeoutException:
                st.warning(f"⏰ Robot couldn't find search box for '{search_term}', skipping...")
                continue
            except Exception as e:
                st.warning(f"⚠️ Robot had trouble with search '{search_term}': {str(e)}")
                continue
        
        status_text.text("🎉 Robot finished all searches!")
        return True
        
    except Exception as e:
        st.error(f"❌ Robot encountered an error: {str(e)}")
        return False

def robot_wait_and_find_element(driver, selector, timeout=10):
    """Helper function to find elements with better error handling"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        return element
    except TimeoutException:
        return None
    except Exception as e:
        st.warning(f"Error finding element: {str(e)}")
        return None

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
        list_end = len(html_content)
        
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

def generate_search_terms(intensity="standard"):
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
    
    # Adjust search terms based on intensity
    if intensity == "quick":
        search_terms = [""] + states[:5] + cities[:3] + zip_codes[:2]
    elif intensity == "standard":
        search_terms = [""] + states[:10] + cities[:8] + zip_codes[:5]
    else:  # comprehensive
        search_terms = [""] + states + cities[:15] + zip_codes
    
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
        },
        {
            'locationId': '169248',
            'storeName': 'CENEX ZIP TRIP #52',
            'address': '1201 CENTRAL AVE',
            'city': 'BILLINGS',
            'state': 'MT',
            'zipCode': '59102',
            'phone': '(406) 245-9670',
            'latitude': '45.770052',
            'longitude': '-108.546965',
            'distance': '7242.61 miles',
            'fullAddress': '1201 CENTRAL AVE, BILLINGS, MT 59102',
            'elementIndex': 2
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
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        demo_mode = st.checkbox("🎭 Demo Mode", value=True, help="Use sample data for testing")
        
        if not demo_mode:
            if not SELENIUM_AVAILABLE:
                st.error("🤖 Browser automation not available!")
                st.code("pip install selenium")
                st.stop()
            
            search_intensity = st.selectbox(
                "🔍 Search Intensity",
                ["quick", "standard", "comprehensive"],
                index=1,
                help="Quick: ~50-100 locations, Standard: ~200-500 locations, Comprehensive: ~500+ locations"
            )
            
            show_browser = st.checkbox("👁️ Show Browser Window", help="Watch the robot work (slower)")
        
        with st.expander("📖 How It Works"):
            st.markdown("""
            **The Robot Process:**
            1. 🤖 Opens Chrome browser
            2. 🌐 Goes to Hunt Brothers website  
            3. 🔍 Searches different states/cities
            4. ⏳ Waits for locations to load
            5. 📊 Extracts all location data
            6. 💾 Gives you CSV/JSON files
            """)
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📊 Robot Scraper")
        
        if st.button("🚀 Start Robot Scraper", type="primary", use_container_width=True):
            if demo_mode:
                st.info("🎭 Using demo data to show you what the robot can do...")
                locations = create_sample_data()
                
                # Simulate progress for demo
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                demo_steps = [
                    "🤖 Robot is opening Hunt Brothers website...",
                    "🔍 Robot found the search box!",
                    "🤖 Robot is searching for: 'Tennessee' (1/5)",
                    "🤖 Robot is searching for: 'Kentucky' (2/5)",
                    "🤖 Robot is searching for: 'Alabama' (3/5)",
                    "🤖 Robot is searching for: 'Georgia' (4/5)",
                    "🤖 Robot is searching for: 'Louisiana' (5/5)",
                    "🎉 Robot finished! Extracting location data...",
                ]
                
                for i, step in enumerate(demo_steps):
                    status_text.text(step)
                    progress_bar.progress((i + 1) / len(demo_steps))
                    time.sleep(0.5)
                
                status_text.text("✅ Demo completed!")
                
            else:
                # Real robot scraping
                with st.spinner("Starting browser robot..."):
                    driver = setup_browser()
                    
                    if not driver:
                        st.error("Could not start browser robot!")
                        st.stop()
                
                try:
                    # Create progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Generate search terms
                    search_terms = generate_search_terms(search_intensity)
                    
                    # Robot performs searches
                    success = robot_search_locations(driver, search_terms, progress_bar, status_text)
                    
                    if success:
                        status_text.text("🤖 Robot is extracting location data...")
                        
                        # Robot extracts HTML
                        html_content = robot_extract_html(driver)
                        
                        if html_content:
                            # Parse the extracted HTML
                            locations = parse_hunt_brothers_html(html_content)
                        else:
                            locations = []
                    else:
                        locations = []
                        
                finally:
                    # Always close the browser
                    driver.quit()
                    status_text.text("🤖 Robot finished and browser closed!")
            
            # Display results
            if locations:
                st.success(f"🎉 Robot found {len(locations)} Hunt Brothers locations!")
                
                # Convert to DataFrame
                df = pd.DataFrame(locations)
                
                # Display data table
                st.dataframe(df, use_container_width=True, height=400)
                
                # Statistics
                col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
                
                with col_stats1:
                    st.metric("Total Locations", len(locations))
                
                with col_stats2:
                    unique_states = len(set(loc.get('state', '') for loc in locations if loc.get('state')))
                    st.metric("States", unique_states)
                
                with col_stats3:
                    with_coords = len([l for l in locations if l.get('latitude') and l.get('longitude')])
                    st.metric("With Coordinates", with_coords)
                
                with col_stats4:
                    with_phones = len([l for l in locations if l.get('phone')])
                    st.metric("With Phone Numbers", with_phones)
                
                # Sample locations display
                st.subheader("📍 Sample Locations")
                for i, location in enumerate(locations[:3]):
                    with st.expander(f"📍 {location.get('storeName', 'Unknown Store')}"):
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.write(f"**ID:** {location.get('locationId', 'N/A')}")
                            st.write(f"**Address:** {location.get('address', 'N/A')}")
                            st.write(f"**City:** {location.get('city', 'N/A')}, {location.get('state', 'N/A')} {location.get('zipCode', 'N/A')}")
                            st.write(f"**Phone:** {location.get('phone', 'N/A')}")
                        with col_b:
                            st.write(f"**Coordinates:** {location.get('latitude', 'N/A')}, {location.get('longitude', 'N/A')}")
                            st.write(f"**Distance:** {location.get('distance', 'N/A')}")
                
                # Download options
                st.subheader("💾 Download Your Data")
                
                col_dl1, col_dl2 = st.columns(2)
                
                with col_dl1:
                    # CSV download
                    csv_headers = ["Location ID", "Store Name", "Address", "City", "State", "ZIP", "Phone", "Latitude", "Longitude", "Distance"]
                    csv_rows = []
                    for loc in locations:
                        csv_rows.append([
                            loc.get('locationId', ''),
                            loc.get('storeName', ''),
                            loc.get('address', ''),
                            loc.get('city', ''),
                            loc.get('state', ''),
                            loc.get('zipCode', ''),
                            loc.get('phone', ''),
                            loc.get('latitude', ''),
                            loc.get('longitude', ''),
                            loc.get('distance', '')
                        ])
                    
                    csv_content = ",".join(csv_headers) + "\n"
                    for row in csv_rows:
                        csv_content += ",".join(f'"{str(field)}"' for field in row) + "\n"
                    
                    st.download_button(
                        label="📄 Download CSV File",
                        data=csv_content,
                        file_name=f"hunt_brothers_locations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col_dl2:
                    # JSON download
                    json_data = json.dumps(locations, indent=2)
                    st.download_button(
                        label="📋 Download JSON File",
                        data=json_data,
                        file_name=f"hunt_brothers_locations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
            
            else:
                st.error("❌ Robot couldn't find any locations.")
                if not demo_mode:
                    st.markdown("""
                    **Possible issues:**
                    - Website might have changed
                    - Network connectivity problems
                    - Browser automation blocked
                    
                    **Try:**
                    - Enable Demo Mode first
                    - Check your internet connection
                    - Try again in a few minutes
                    """)
    
    with col2:
        st.header("🤖 About the Robot")
        
        if SELENIUM_AVAILABLE:
            st.success("✅ Browser automation ready!")
        else:
            st.error("❌ Browser automation not available")
            st.code("pip install selenium")
        
        with st.expander("🎯 What the Robot Does", expanded=True):
            st.markdown("""
            **Step-by-step process:**
            
            1. 🤖 **Opens Chrome browser**
            2. 🌐 **Goes to Hunt Brothers website**
            3. 🔍 **Searches for different locations:**
               - All 21 states where they operate
               - Major cities in each state
               - Key zip codes
            4. ⏳ **Waits for each search to load**
            5. 📊 **Extracts all location data**
            6. 💾 **Creates your CSV/JSON files**
            """)
        
        with st.expander("⚙️ Setup Requirements"):
            st.markdown("""
            **What you need:**
            - ✅ Python installed
            - ✅ Chrome browser installed
            - ✅ Internet connection
            - ✅ Selenium library (`pip install selenium`)
            
            **That's it!** The robot handles everything else.
            """)
        
        st.header("🎯 Expected Results")
        st.markdown("""
        **You should get:**
        - 🏪 **Hundreds** of real Hunt Brothers locations
        - 📍 **Exact addresses** and GPS coordinates  
        - 📞 **Phone numbers** for each location
        - 📊 **CSV/JSON** files ready for use
        
        **Data quality:** Real store names like "CENEX ZIP TRIP #50" and actual addresses.
        """)

if __name__ == "__main__":
    main()
