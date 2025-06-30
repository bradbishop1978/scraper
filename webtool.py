import streamlit as st
import pandas as pd
import json
from datetime import datetime
import io
import re
import urllib.request
import urllib.parse

def parse_hunt_brothers_html(html_content):
    """Parse Hunt Brothers location data from the specific HTML structure"""
    locations = []
    
    try:
        # Find the hbp-location-list div
        list_start = html_content.find('<div class="hbp-location-list">')
        if list_start == -1:
            st.warning("Could not find hbp-location-list container")
            return []
        
        # Find the end of the container
        list_end = html_content.find('</div>', list_start)
        # Find the actual end by counting div tags
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
        
        if list_end == -1:
            list_end = len(html_content)
        
        container_html = html_content[list_start:list_end]
        
        # Find all listed-location divs
        location_pattern = r'<div class="listed-location"[^>]*>(.*?)</div>\s*</div>\s*</div>'
        location_matches = re.findall(location_pattern, container_html, re.DOTALL)
        
        st.info(f"Found {len(location_matches)} location blocks")
        
        for i, location_html in enumerate(location_matches):
            try:
                location_data = parse_single_location(location_html, i)
                if location_data:
                    locations.append(location_data)
            except Exception as e:
                st.warning(f"Error parsing location {i}: {str(e)}")
                continue
        
        return locations
        
    except Exception as e:
        st.error(f"Error parsing HTML: {str(e)}")
        return []

def parse_single_location(location_html, index):
    """Parse a single location from its HTML"""
    try:
        # Extract coordinates from data attributes
        lat_match = re.search(r'data-lat="([^"]*)"', location_html)
        lng_match = re.search(r'data-lng="([^"]*)"', location_html)
        
        latitude = lat_match.group(1) if lat_match else ""
        longitude = lng_match.group(1) if lng_match else ""
        
        # Extract distance
        distance_match = re.search(r'<span class="distance">([^<]*)</span>', location_html)
        distance = distance_match.group(1).strip() if distance_match else ""
        
        # Extract store name from h3 tag
        name_match = re.search(r'<h3><a[^>]*>([^<]*)</a></h3>', location_html)
        store_name = name_match.group(1).strip() if name_match else ""
        
        # Extract location ID from href
        id_match = re.search(r'/location-details/(\d+)', location_html)
        location_id = id_match.group(1) if id_match else ""
        
        # Extract address from the address tag
        address_match = re.search(r'<address class="address">.*?<i[^>]*></i>\s*([^<]*)<br>([^<]*)</a>', location_html, re.DOTALL)
        
        street_address = ""
        city_state_zip = ""
        city = ""
        state = ""
        zip_code = ""
        
        if address_match:
            street_address = address_match.group(1).strip()
            city_state_zip = address_match.group(2).strip()
            
            # Parse city, state, zip
            city_state_zip_pattern = r'([^,]+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)'
            csz_match = re.search(city_state_zip_pattern, city_state_zip)
            if csz_match:
                city = csz_match.group(1).strip()
                state = csz_match.group(2).strip()
                zip_code = csz_match.group(3).strip()
        
        # Extract phone number
        phone_match = re.search(r'<a href="tel:([^"]*)"[^>]*><i[^>]*></i>\s*([^<]*)</a>', location_html)
        phone = phone_match.group(2).strip() if phone_match else ""
        
        # Extract Google Maps URL for directions
        directions_match = re.search(r'<a[^>]*href="(https://www\.google\.com/maps/[^"]*)"[^>]*target="_blank"', location_html)
        directions_url = directions_match.group(1) if directions_match else ""
        
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
            'directionsUrl': directions_url,
            'fullAddress': f"{street_address}, {city_state_zip}" if street_address and city_state_zip else "",
            'elementIndex': index
        }
        
    except Exception as e:
        st.warning(f"Error parsing single location: {str(e)}")
        return None

def fetch_hunt_brothers_page(url="https://www.huntbrotherspizza.com/locations/"):
    """Fetch the Hunt Brothers locations page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
            
            # Handle gzip encoding
            if response.info().get('Content-Encoding') == 'gzip':
                import gzip
                content = gzip.decompress(content)
            
            return content.decode('utf-8')
        
    except Exception as e:
        st.error(f"Error fetching page: {str(e)}")
        return None

def create_sample_hunt_brothers_data():
    """Create sample data based on the HTML structure you provided"""
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
            'directionsUrl': 'https://www.google.com/maps/?daddr=11+HWY+10+E%0APARK+CITY%2C+MT+59063',
            'fullAddress': '11 HWY 10 E, PARK CITY, MT 59063',
            'elementIndex': 0
        },
        {
            'locationId': '84094',
            'storeName': 'CENEX ZIP TRIP #74',
            'address': '902 N BROADWAY',
            'city': 'RED LODGE',
            'state': 'MT',
            'zipCode': '59068',
            'phone': '(406) 446-0338',
            'latitude': '45.195916',
            'longitude': '-109.246596',
            'distance': '7242.35 miles',
            'directionsUrl': 'https://www.google.com/maps/?daddr=902+N+BROADWAY%0ARED+LODGE%2C+MT+59068',
            'fullAddress': '902 N BROADWAY, RED LODGE, MT 59068',
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
            'directionsUrl': 'https://www.google.com/maps/?daddr=1201+CENTRAL+AVE%0ABILLINGS%2C+MT+59102',
            'fullAddress': '1201 CENTRAL AVE, BILLINGS, MT 59102',
            'elementIndex': 2
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
            'directionsUrl': 'https://www.google.com/maps/?daddr=2205+HWY+47%0AHARDIN%2C+MT+59034',
            'fullAddress': '2205 HWY 47, HARDIN, MT 59034',
            'elementIndex': 3
        }
    ]

def main():
    st.set_page_config(
        page_title="Hunt Brothers Pizza Scraper",
        page_icon="🍕",
        layout="wide"
    )
    
    st.title("🍕 Hunt Brothers Pizza Location Scraper")
    st.markdown("Specialized parser for Hunt Brothers Pizza location data")
    
    # Sidebar for options
    with st.sidebar:
        st.header("⚙️ Options")
        
        url = st.text_input(
            "🌐 Website URL",
            value="https://www.huntbrotherspizza.com/locations/",
            help="Hunt Brothers locations page URL"
        )
        
        demo_mode = st.checkbox("🎭 Demo Mode", value=True, help="Use sample data for testing")
        
        if not demo_mode:
            st.warning("⚠️ Live scraping may not work due to dynamic content loading. The website likely requires JavaScript to populate the location list.")
        
        with st.expander("📋 Data Fields"):
            st.markdown("""
            **Extracted Fields:**
            - Store Name (e.g., "CENEX ZIP TRIP #50")
            - Street Address
            - City, State, ZIP
            - Phone Number
            - Latitude/Longitude
            - Distance from search point
            - Google Maps directions URL
            - Location ID
            """)
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📊 Extraction Results")
        
        if st.button("🚀 Extract Locations", type="primary", use_container_width=True):
            if demo_mode:
                st.info("🎭 Using sample Hunt Brothers data...")
                locations = create_sample_hunt_brothers_data()
            else:
                with st.spinner("Fetching Hunt Brothers locations..."):
                    html_content = fetch_hunt_brothers_page(url)
                    
                    if html_content:
                        st.info(f"📄 Page loaded ({len(html_content):,} characters)")
                        locations = parse_hunt_brothers_html(html_content)
                    else:
                        locations = []
            
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
                    with_coords = len([l for l in locations if l.get('latitude') and l.get('longitude')])
                    st.metric("With Coordinates", with_coords)
                
                with col_stats4:
                    with_phones = len([l for l in locations if l.get('phone')])
                    st.metric("With Phone Numbers", with_phones)
                
                # Sample locations
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
                            if location.get('directionsUrl'):
                                st.markdown(f"[🗺️ Get Directions]({location.get('directionsUrl')})")
                
                # Download options
                st.subheader("💾 Download Options")
                
                col_dl1, col_dl2, col_dl3 = st.columns(3)
                
                with col_dl1:
                    # CSV download
                    csv_headers = ["Location ID", "Store Name", "Address", "City", "State", "ZIP", "Phone", "Latitude", "Longitude", "Distance", "Directions URL"]
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
                            loc.get('distance', ''),
                            loc.get('directionsUrl', '')
                        ])
                    
                    csv_content = ",".join(csv_headers) + "\n"
                    for row in csv_rows:
                        csv_content += ",".join(f'"{str(field)}"' for field in row) + "\n"
                    
                    st.download_button(
                        label="📄 Download CSV",
                        data=csv_content,
                        file_name=f"hunt_brothers_locations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col_dl2:
                    # JSON download
                    json_data = json.dumps(locations, indent=2)
                    st.download_button(
                        label="📋 Download JSON",
                        data=json_data,
                        file_name=f"hunt_brothers_locations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                with col_dl3:
                    # KML download for Google Earth
                    kml_content = generate_kml(locations)
                    st.download_button(
                        label="🗺️ Download KML",
                        data=kml_content,
                        file_name=f"hunt_brothers_locations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.kml",
                        mime="application/vnd.google-earth.kml+xml",
                        use_container_width=True
                    )
                
            else:
                st.error("❌ No locations were extracted.")
                st.markdown("""
                **Possible reasons:**
                - The website loads content dynamically with JavaScript
                - No search has been performed on the page
                - The page structure has changed
                
                **Try:**
                - Enable Demo Mode to test the interface
                - The website likely requires user interaction to load locations
                """)
    
    with col2:
        st.header("📖 About This Parser")
        
        with st.expander("🎯 How It Works", expanded=True):
            st.markdown("""
            This parser is specifically designed for Hunt Brothers Pizza's HTML structure:
            
            1. **Finds** the `hbp-location-list` container
            2. **Extracts** each `listed-location` div
            3. **Parses** store names, addresses, coordinates
            4. **Includes** phone numbers and directions
            """)
        
        with st.expander("📊 Data Quality"):
            st.markdown("""
            **High Quality Data:**
            - ✅ Real store names (CENEX ZIP TRIP #50)
            - ✅ Actual addresses (11 HWY 10 E)
            - ✅ GPS coordinates
            - ✅ Phone numbers
            - ✅ Google Maps integration
            """)
        
        with st.expander("⚠️ Limitations"):
            st.markdown("""
            - Only works with static HTML content
            - Hunt Brothers loads data dynamically
            - May need user interaction to populate list
            - Demo mode shows the expected data structure
            """)
        
        st.header("🎭 Demo Data")
        st.markdown("""
        The demo shows real Hunt Brothers locations from Montana and North Dakota, extracted from the HTML structure you provided.
        
        This demonstrates the exact data format and quality you can expect.
        """)

def generate_kml(locations):
    """Generate KML file for Google Earth"""
    kml_header = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
<name>Hunt Brothers Pizza Locations</name>
<description>Hunt Brothers Pizza store locations</description>
'''
    
    kml_footer = '''</Document>
</kml>'''
    
    placemarks = ""
    for location in locations:
        if location.get('latitude') and location.get('longitude'):
            placemarks += f'''
<Placemark>
<name>{location.get('storeName', 'Unknown Store')}</name>
<description>
Address: {location.get('fullAddress', 'N/A')}
Phone: {location.get('phone', 'N/A')}
Distance: {location.get('distance', 'N/A')}
</description>
<Point>
<coordinates>{location.get('longitude')},{location.get('latitude')},0</coordinates>
</Point>
</Placemark>'''
    
    return kml_header + placemarks + kml_footer

if __name__ == "__main__":
    main()
