import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import io
import time

def extract_locations_from_html(html_content, css_selector):
    """Extract location data from HTML using BeautifulSoup"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Convert CSS selector to BeautifulSoup format
        # Remove document.querySelector() wrapper if present
        if 'document.querySelector' in css_selector:
            # Extract the CSS selector from JavaScript
            match = re.search(r'querySelector\(["\']([^"\']+)["\']', css_selector)
            if match:
                css_selector = match.group(1)
        
        # Find the target element
        target_element = soup.select_one(css_selector)
        
        if not target_element:
            st.warning(f"Could not find element with selector: {css_selector}")
            return []
        
        locations = []
        
        # Get all child elements that might contain location data
        children = target_element.find_all(['div', 'li', 'article', 'section'], recursive=True)
        
        if not children:
            children = [target_element]
        
        for i, element in enumerate(children):
            text = element.get_text(strip=True)
            
            if len(text) < 20:  # Skip elements with too little text
                continue
            
            # Extract store name
            store_name = ""
            name_elements = element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b'])
            if name_elements:
                store_name = name_elements[0].get_text(strip=True)
            else:
                # Try to find store name patterns
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if any(keyword in line.upper() for keyword in ['#', "'S", 'STORE', 'MART', 'SHOP', 'MARKET']):
                        store_name = line
                        break
                if not store_name and lines:
                    store_name = lines[0]
            
            # Extract address
            address = ""
            address_match = re.search(r'\d+[^,\n]*(?:HIGHWAY|HWY|STREET|ST|AVENUE|AVE|ROAD|RD|DRIVE|DR|LANE|LN|BOULEVARD|BLVD)[^,\n]*', text, re.IGNORECASE)
            if address_match:
                address = address_match.group(0).strip()
            
            # Extract city, state, zip
            city, state, zip_code = "", "", ""
            city_state_zip_match = re.search(r'([A-Z\s]+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', text)
            if city_state_zip_match:
                city = city_state_zip_match.group(1).strip()
                state = city_state_zip_match.group(2).strip()
                zip_code = city_state_zip_match.group(3).strip()
            
            # Extract phone
            phone = ""
            phone_match = re.search(r'$$?\d{3}$$?[-.\s]?\d{3}[-.\s]?\d{4}', text)
            if phone_match:
                phone = phone_match.group(0)
            
            # Extract hours
            hours = ""
            hours_match = re.search(r'(?:hours?|open|closed)[^,\n]*(?:am|pm|24)', text, re.IGNORECASE)
            if hours_match:
                hours = hours_match.group(0)
            
            # Only add if we have meaningful data
            if store_name or address or (city and state):
                locations.append({
                    'storeName': store_name or 'Unknown Store',
                    'address': address or '',
                    'city': city or '',
                    'state': state or '',
                    'zipCode': zip_code or '',
                    'phone': phone or '',
                    'hours': hours or '',
                    'fullText': text[:300] if len(text) > 300 else text,
                    'elementIndex': i
                })
        
        return locations
        
    except Exception as e:
        st.error(f"Error extracting locations: {str(e)}")
        return []

def fetch_page_content(url):
    """Fetch page content using requests"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        return response.text
        
    except requests.RequestException as e:
        st.error(f"Error fetching page: {str(e)}")
        return None

def scrape_static_content(url, css_selector):
    """Scrape static content from a webpage"""
    st.info(f"🌐 Fetching content from: {url}")
    
    html_content = fetch_page_content(url)
    if not html_content:
        return None
    
    st.info(f"📊 Extracting data using selector: {css_selector}")
    
    locations = extract_locations_from_html(html_content, css_selector)
    
    return locations

def main():
    st.set_page_config(
        page_title="Simple Location Scraper",
        page_icon="🎯",
        layout="wide"
    )
    
    st.title("🎯 Simple Location Scraper")
    st.markdown("Extract location data from websites using CSS selectors (Static Content Only)")
    
    # Warning about limitations
    st.warning("""
    ⚠️ **Important**: This version only works with static HTML content. 
    For dynamic content (JavaScript-loaded), you'll need to install Selenium.
    
    To install Selenium: `pip install selenium webdriver-manager`
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
        
        # Advanced options
        with st.expander("🔧 Advanced Options"):
            max_locations = st.number_input("Max Locations to Extract", min_value=10, max_value=50000, value=10000)
            include_raw_text = st.checkbox("Include Raw Text", value=False, help="Include the raw text content for debugging")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📊 Extraction Results")
        
        if st.button("🚀 Start Scraping", type="primary", use_container_width=True):
            if not url or not css_selector:
                st.error("Please provide both URL and CSS selector")
                return
            
            with st.spinner("Scraping in progress..."):
                locations = scrape_static_content(url, css_selector)
            
            if locations:
                st.success(f"✅ Successfully extracted {len(locations)} locations!")
                
                # Convert to DataFrame
                df = pd.DataFrame(locations)
                
                # Remove raw text column if not requested
                if not include_raw_text and 'fullText' in df.columns:
                    df = df.drop('fullText', axis=1)
                
                # Display results
                st.dataframe(df, use_container_width=True, height=400)
                
                # Statistics
                col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)
                
                with col_stats1:
                    st.metric("Total Locations", len(locations))
                
                with col_stats2:
                    unique_states = df['state'].nunique() if 'state' in df.columns else 0
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
                    sample_size = min(5, len(locations))
                    
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
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False)
                    csv_data = csv_buffer.getvalue()
                    
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
                st.error("❌ No locations were extracted. This might be because:")
                st.markdown("""
                - The website loads content dynamically with JavaScript
                - The CSS selector is incorrect
                - The website blocks automated requests
                
                **Solution**: Install Selenium for dynamic content scraping:
                ```bash
                pip install selenium webdriver-manager
