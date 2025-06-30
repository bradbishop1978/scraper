import streamlit as st
import pandas as pd
import json
from datetime import datetime
import io
import re
import urllib.request
import urllib.parse
import html

def extract_locations_from_html(html_content, css_selector):
    """Extract location data from HTML using basic string parsing"""
    try:
        # Simple HTML parsing without BeautifulSoup
        locations = []
        
        # Convert CSS selector to a simple search pattern
        if '#' in css_selector:
            # Extract ID from selector like "#hbp-location-search > div.hbp-location-list"
            id_match = re.search(r'#([a-zA-Z0-9_-]+)', css_selector)
            if id_match:
                target_id = id_match.group(1)
                
                # Find the element with this ID
                id_pattern = f'id="{target_id}"'
                id_start = html_content.find(id_pattern)
                
                if id_start != -1:
                    # Find the opening tag
                    tag_start = html_content.rfind('<', 0, id_start)
                    if tag_start != -1:
                        # Extract tag name
                        tag_match = re.search(r'<(\w+)', html_content[tag_start:])
                        if tag_match:
                            tag_name = tag_match.group(1)
                            
                            # Find the closing tag
                            closing_tag = f'</{tag_name}>'
                            tag_end = html_content.find(closing_tag, id_start)
                            
                            if tag_end != -1:
                                element_content = html_content[tag_start:tag_end + len(closing_tag)]
                                locations = parse_location_content(element_content)
        
        # If no locations found with ID, try searching for location patterns in entire content
        if not locations:
            locations = parse_location_content(html_content)
        
        return locations
        
    except Exception as e:
        st.error(f"Error extracting locations: {str(e)}")
        return []

def parse_location_content(content):
    """Parse location data from HTML content"""
    locations = []
    
    # Remove HTML tags for text analysis
    text_content = re.sub(r'<[^>]+>', ' ', content)
    text_content = html.unescape(text_content)
    
    # Split into potential location blocks
    lines = text_content.split('\n')
    current_location = {}
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue
        
        # Look for store name patterns
        if any(keyword in line.upper() for keyword in ['#', "'S", 'STORE', 'MART', 'SHOP', 'MARKET', 'PIZZA']):
            if current_location:  # Save previous location
                if current_location.get('storeName') or current_location.get('address'):
                    locations.append(current_location)
            current_location = {'storeName': line}
        
        # Look for address patterns
        elif re.search(r'\d+[^,\n]*(?:HIGHWAY|HWY|STREET|ST|AVENUE|AVE|ROAD|RD|DRIVE|DR|LANE|LN|BOULEVARD|BLVD)', line, re.IGNORECASE):
            current_location['address'] = line
        
        # Look for city, state, zip patterns
        elif re.search(r'[A-Z\s]+,\s*[A-Z]{2}\s+\d{5}', line):
            city_state_zip = re.search(r'([A-Z\s]+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', line)
            if city_state_zip:
                current_location['city'] = city_state_zip.group(1).strip()
                current_location['state'] = city_state_zip.group(2).strip()
                current_location['zipCode'] = city_state_zip.group(3).strip()
        
        # Look for phone patterns
        elif re.search(r'$$?\d{3}$$?[-.\s]?\d{3}[-.\s]?\d{4}', line):
            phone_match = re.search(r'$$?\d{3}$$?[-.\s]?\d{3}[-.\s]?\d{4}', line)
            if phone_match:
                current_location['phone'] = phone_match.group(0)
        
        # Look for hours patterns
        elif re.search(r'(?:hours?|open|closed)[^,\n]*(?:am|pm|24)', line, re.IGNORECASE):
            current_location['hours'] = line
    
    # Don't forget the last location
    if current_location and (current_location.get('storeName') or current_location.get('address')):
        locations.append(current_location)
    
    # Clean up locations and add missing fields
    cleaned_locations = []
    for i, loc in enumerate(locations):
        cleaned_loc = {
            'storeName': loc.get('storeName', f'Location {i+1}'),
            'address': loc.get('address', ''),
            'city': loc.get('city', ''),
            'state': loc.get('state', ''),
            'zipCode': loc.get('zipCode', ''),
            'phone': loc.get('phone', ''),
            'hours': loc.get('hours', ''),
            'elementIndex': i
        }
        cleaned_locations.append(cleaned_loc)
    
    return cleaned_locations

def fetch_page_content(url):
    """Fetch page content using urllib"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')
            return content
        
    except Exception as e:
        st.error(f"Error fetching page: {str(e)}")
        return None

def scrape_basic_content(url, css_selector):
    """Scrape content using basic Python libraries only"""
    st.info(f"🌐 Fetching content from: {url}")
    
    html_content = fetch_page_content(url)
    if not html_content:
        return None
    
    st.info(f"📄 Page content loaded ({len(html_content)} characters)")
    st.info(f"📊 Extracting data using selector: {css_selector}")
    
    locations = extract_locations_from_html(html_content, css_selector)
    
    return locations

def create_sample_data():
    """Create sample data for demonstration"""
    return [
        {
            'storeName': "LEEBO'S #1",
            'address': "1783 HIGHWAY 121",
            'city': "HINESTON",
            'state': "LA",
            'zipCode': "71309",
            'phone': "(318) 793-2400",
            'hours': "Mon-Sun: 6:00 AM - 11:00 PM",
            'elementIndex': 0
        },
        {
            'storeName': "CORNER STORE #2",
            'address': "456 MAIN STREET",
            'city': "MONROE",
            'state': "LA",
            'zipCode': "71201",
            'phone': "(318) 555-0123",
            'hours': "Daily: 24 Hours",
            'elementIndex': 1
        }
    ]

def main():
    st.set_page_config(
        page_title="Basic Location Scraper",
        page_icon="🎯",
        layout="wide"
    )
    
    st.title("🎯 Basic Location Scraper")
    st.markdown("Extract location data from websites using basic Python libraries only")
    
    # Info about limitations
    st.info("""
    ℹ️ **This version uses only built-in Python libraries** - no external dependencies like BeautifulSoup or Selenium.
    It works best with static HTML content and simple CSS selectors.
    """)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Website URL input
        url = st.text_input(
            "🌐 Website URL",
            value="https://www.huntbrotherspizza.com/locations/",
            help="Enter the full URL of the website to scrape"
        )
        
        # CSS selector input
        css_selector = st.text_area(
            "📍 CSS Selector",
            value="#hbp-location-search > div.hbp-location-list",
            help="Enter the CSS selector to find the location container",
            height=100
        )
        
        # Demo mode
        demo_mode = st.checkbox("🎭 Demo Mode", help="Use sample data for testing")
        
        # Advanced options
        with st.expander("🔧 Advanced Options"):
            include_raw_html = st.checkbox("Include Raw HTML", value=False, help="Show raw HTML content for debugging")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📊 Extraction Results")
        
        if st.button("🚀 Start Scraping", type="primary", use_container_width=True):
            if demo_mode:
                st.info("🎭 Using demo data...")
                locations = create_sample_data()
            else:
                if not url or not css_selector:
                    st.error("Please provide both URL and CSS selector")
                    return
                
                with st.spinner("Scraping in progress..."):
                    locations = scrape_basic_content(url, css_selector)
            
            if locations:
                st.success(f"✅ Successfully extracted {len(locations)} locations!")
                
                # Convert to DataFrame
                df = pd.DataFrame(locations)
                
                # Display results
                st.dataframe(df, use_container_width=True, height=400)
                
                # Statistics
                col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
                
                with col_stats1:
                    st.metric("Total Locations", len(locations))
                
                with col_stats2:
                    unique_states = len(set(loc.get('state', '') for loc in locations if loc.get('state')))
                    st.metric("States", unique_states)
                
                with col_stats3:
                    real_stores = len([l for l in locations if '#' in l.get('storeName', '') or "'S" in l.get('storeName', '')])
                    st.metric("Real Store Names", real_stores)
                
                with col_stats4:
                    with_phones = len([l for l in locations if l.get('phone', '')])
                    st.metric("With Phone Numbers", with_phones)
                
                # Sample locations
                if len(locations) > 0:
                    st.subheader("📍 Sample Locations")
                    sample_size = min(3, len(locations))
                    
                    for i in range(sample_size):
                        location = locations[i]
                        with st.expander(f"📍 {location.get('storeName', 'Unknown Store')}"):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.write(f"**Address:** {location.get('address', 'N/A')}")
                                st.write(f"**City:** {location.get('city', 'N/A')}")
                                st.write(f"**State:** {location.get('state', 'N/A')}")
                            with col_b:
                                st.write(f"**Zip Code:** {location.get('zipCode', 'N/A')}")
                                st.write(f"**Phone:** {location.get('phone', 'N/A')}")
                                st.write(f"**Hours:** {location.get('hours', 'N/A')}")
                
                # Download options
                st.subheader("💾 Download Options")
                
                col_dl1, col_dl2 = st.columns(2)
                
                with col_dl1:
                    # CSV download
                    csv_data = "Store Name,Address,City,State,Zip Code,Phone,Hours\n"
                    for location in locations:
                        csv_data += f'"{location.get("storeName", "")}","{location.get("address", "")}","{location.get("city", "")}","{location.get("state", "")}","{location.get("zipCode", "")}","{location.get("phone", "")}","{location.get("hours", "")}"\n'
                    
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv_data,
                        file_name=f"locations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col_dl2:
                    # JSON download
                    json_data = json.dumps(locations, indent=2)
                    st.download_button(
                        label="📋 Download JSON",
                        data=json_data,
                        file_name=f"locations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
            else:
                st.error("❌ No locations were extracted.")
                st.markdown("""
                **Possible reasons:**
                - The website loads content dynamically with JavaScript
                - The CSS selector is incorrect
                - The website blocks automated requests
                - Content is not in the expected format
                
                **Try:**
                - Enable Demo Mode to test the interface
                - Check the CSS selector in browser developer tools
                - Try a simpler selector like `#main` or `.content`
                """)
    
    with col2:
        st.header("📖 Instructions")
        
        with st.expander("🎯 How to Use", expanded=True):
            st.markdown("""
            1. **Enter Website URL**: Full URL of the page with locations
            2. **CSS Selector**: The element containing location data
            3. **Demo Mode**: Test with sample data first
            4. **Click Start Scraping**: Begin extraction
            5. **Download Results**: Get CSV or JSON files
            """)
        
        with st.expander("💡 Tips"):
            st.markdown("""
            - Try Demo Mode first to test the interface
            - Use simple CSS selectors like `#content` or `.main`
            - This version works best with static HTML
            - For dynamic content, you'd need Selenium
            """)
        
        with st.expander("🔧 CSS Selector Examples"):
            st.code('#locations-list')
            st.code('.store-results')
            st.code('#main-content')
            st.code('div[class*="location"]')
        
        st.header("🎭 Demo Mode")
        st.markdown("""
        **Enable Demo Mode** to test the interface with sample Hunt Brothers data:
        - LEEBO'S #1 - Hineston, LA
        - CORNER STORE #2 - Monroe, LA
        
        This lets you test CSV/JSON export without scraping.
        """)

if __name__ == "__main__":
    main()
