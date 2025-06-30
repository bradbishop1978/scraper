import streamlit as st
import pandas as pd
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import json
from datetime import datetime
import io

def setup_driver(headless=True):
    """Setup Chrome WebDriver with options"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        return driver
    except Exception as e:
        st.error(f"Failed to setup Chrome driver: {str(e)}")
        return None

def extract_locations_from_element(driver, js_selector):
    """Extract location data from the specified DOM element"""
    try:
        # Execute JavaScript to get the element and its content
        script = f"""
        const element = {js_selector};
        if (!element) return null;
        
        const locations = [];
        const children = element.children || element.querySelectorAll('*');
        
        Array.from(children).forEach((child, index) => {{
            const text = child.textContent || child.innerText || '';
            const html = child.innerHTML || '';
            
            if (text.trim().length > 10) {{ // Only consider elements with substantial text
                // Extract store name (usually first line or in heading tags)
                let storeName = '';
                const headings = child.querySelectorAll('h1, h2, h3, h4, h5, h6, .name, .store-name, .title, strong, b');
                if (headings.length > 0) {{
                    storeName = headings[0].textContent.trim();
                }} else {{
                    const lines = text.split('\\n').map(line => line.trim()).filter(line => line);
                    if (lines.length > 0) {{
                        // Look for lines that look like store names
                        for (const line of lines) {{
                            if (line.includes('#') || line.includes("'S") || line.includes('STORE') || 
                                line.includes('MART') || line.includes('SHOP') || line.includes('MARKET')) {{
                                storeName = line;
                                break;
                            }}
                        }}
                        if (!storeName) storeName = lines[0];
                    }}
                }}
                
                // Extract address
                let address = '';
                const addressElements = child.querySelectorAll('.address, .street-address, .addr, .location-address');
                if (addressElements.length > 0) {{
                    address = addressElements[0].textContent.trim();
                }} else {{
                    const addressMatch = text.match(/\\d+[^,\\n]*(?:HIGHWAY|HWY|STREET|ST|AVENUE|AVE|ROAD|RD|DRIVE|DR|LANE|LN|BOULEVARD|BLVD)[^,\\n]*/i);
                    if (addressMatch) {{
                        address = addressMatch[0].trim();
                    }}
                }}
                
                // Extract city, state, zip
                let city = '', state = '', zipCode = '';
                const cityStateZipMatch = text.match(/([A-Z\\s]+),\\s*([A-Z]{{2}})\\s+(\\d{{5}}(?:-\\d{{4}})?)/g);
                if (cityStateZipMatch) {{
                    const parts = cityStateZipMatch[0].split(',');
                    if (parts.length >= 2) {{
                        city = parts[0].trim();
                        const stateZip = parts[1].trim().split(/\\s+/);
                        if (stateZip.length >= 2) {{
                            state = stateZip[0];
                            zipCode = stateZip[1];
                        }}
                    }}
                }}
                
                // Extract phone
                let phone = '';
                const phoneMatch = text.match(/\$$?\\d{{3}}\$$?[-\\.\\s]?\\d{{3}}[-\\.\\s]?\\d{{4}}/);
                if (phoneMatch) {{
                    phone = phoneMatch[0];
                }}
                
                // Extract hours
                let hours = '';
                const hoursMatch = text.match(/(?:hours?|open|closed)[^,\\n]*(?:am|pm|24)/gi);
                if (hoursMatch) {{
                    hours = hoursMatch[0];
                }}
                
                if (storeName || address || (city && state)) {{
                    locations.push({{
                        storeName: storeName || 'Unknown Store',
                        address: address || '',
                        city: city || '',
                        state: state || '',
                        zipCode: zipCode || '',
                        phone: phone || '',
                        hours: hours || '',
                        fullText: text.substring(0, 300),
                        elementIndex: index
                    }});
                }}
            }}
        }});
        
        return locations;
        """
        
        locations = driver.execute_script(script)
        return locations if locations else []
        
    except Exception as e:
        st.error(f"Error extracting locations: {str(e)}")
        return []

def perform_searches(driver, search_terms, progress_bar, status_text):
    """Perform multiple searches to populate the location list"""
    all_locations = {}
    
    try:
        # Find search input
        search_input = WebDriverWait(driver, 10).wait(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="text"], input[placeholder*="address"], input[placeholder*="zip"], input[placeholder*="search"]'))
        )
        
        total_searches = len(search_terms)
        
        for i, search_term in enumerate(search_terms):
            status_text.text(f"Searching: {search_term} ({i+1}/{total_searches})")
            progress_bar.progress((i + 1) / total_searches)
            
            try:
                # Clear and enter search term
                search_input.clear()
                if search_term:
                    search_input.send_keys(search_term)
                search_input.send_keys(Keys.RETURN)
                
                # Wait for results to load
                time.sleep(3)
                
                # Try to wait for the location list to populate
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#hbp-location-search > div.hbp-location-list"))
                    )
                except TimeoutException:
                    pass  # Continue even if specific element not found
                
            except Exception as e:
                st.warning(f"Error with search '{search_term}': {str(e)}")
                continue
                
        return True
        
    except Exception as e:
        st.error(f"Error performing searches: {str(e)}")
        return False

def generate_search_terms():
    """Generate comprehensive search terms"""
    states = ["AL", "AR", "FL", "GA", "IL", "IN", "IA", "KS", "KY", "LA", "MS", "MO", "NE", "NC", "OH", "OK", "SC", "TN", "TX", "VA", "WV"]
    
    cities = [
        "Nashville", "Memphis", "Knoxville", "Chattanooga", "Birmingham", "Montgomery", 
        "Louisville", "Lexington", "Atlanta", "Augusta", "Jackson", "Gulfport",
        "Little Rock", "Fort Smith", "St. Louis", "Kansas City", "Charlotte", "Raleigh",
        "Columbia", "Charleston", "Richmond", "Norfolk", "Huntington", "Columbus",
        "Indianapolis", "Chicago", "Houston", "Dallas", "Oklahoma City", "Tulsa"
    ]
    
    # Generate some zip codes
    zip_codes = []
    for i in range(30000, 40000, 500):  # Southern states zip range
        zip_codes.append(str(i))
    for i in range(70000, 73000, 500):  # Louisiana, Arkansas
        zip_codes.append(str(i))
    
    # Combine all search terms
    search_terms = ["", "*"] + states + cities + zip_codes[:20]  # Limit zip codes for efficiency
    
    return search_terms

def scrape_website(url, js_selector, search_strategy="comprehensive"):
    """Main scraping function"""
    driver = setup_driver(headless=True)
    if not driver:
        return None
    
    try:
        st.info(f"🌐 Navigating to: {url}")
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        time.sleep(3)  # Additional wait for dynamic content
        
        if search_strategy == "comprehensive":
            st.info("🔍 Performing comprehensive searches to populate location data...")
            
            # Create progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            search_terms = generate_search_terms()
            success = perform_searches(driver, search_terms, progress_bar, status_text)
            
            if not success:
                st.warning("Some searches failed, but continuing with extraction...")
        
        st.info(f"📊 Extracting data from DOM element: {js_selector}")
        
        # Extract locations from the specified DOM element
        locations = extract_locations_from_element(driver, js_selector)
        
        if not locations:
            st.warning("No locations found. Trying alternative extraction method...")
            
            # Alternative: get all text content and try to parse it
            try:
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Look for any elements that might contain location data
                potential_elements = soup.find_all(text=re.compile(r'\d{5}'))  # Find elements with zip codes
                
                st.info(f"Found {len(potential_elements)} elements with potential location data")
                
            except Exception as e:
                st.error(f"Alternative extraction failed: {str(e)}")
        
        return locations
        
    except Exception as e:
        st.error(f"Scraping failed: {str(e)}")
        return None
    finally:
        driver.quit()

def main():
    st.set_page_config(
        page_title="Universal Location Scraper",
        page_icon="🎯",
        layout="wide"
    )
    
    st.title("🎯 Universal Location Scraper")
    st.markdown("Extract location data from any website using JavaScript DOM selectors")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Website URL input
        url = st.text_input(
            "🌐 Website URL",
            value="https://www.huntbrotherspizza.com/locations/",
            help="Enter the full URL of the website to scrape"
        )
        
        # JavaScript selector input
        js_selector = st.text_area(
            "📍 JavaScript DOM Selector",
            value='document.querySelector("#hbp-location-search > div.hbp-location-list")',
            help="Enter the JavaScript code to select the DOM element containing locations",
            height=100
        )
        
        # Search strategy
        search_strategy = st.selectbox(
            "🔍 Search Strategy",
            ["comprehensive", "single_extraction"],
            help="Comprehensive: Perform multiple searches to populate data. Single: Extract current page content only."
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
            if not url or not js_selector:
                st.error("Please provide both URL and JavaScript selector")
                return
            
            with st.spinner("Scraping in progress..."):
                locations = scrape_website(url, js_selector, search_strategy)
            
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
                    real_stores = len([l for l in locations if l.get('storeName', '').find('#') != -1 or l.get('storeName', '').find("'S") != -1])
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
                
                col_dl1, col_dl2, col_dl3 = st.columns(3)
                
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
                
                with col_dl3:
                    # Excel download
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='Locations', index=False)
                    excel_data = excel_buffer.getvalue()
                    
                    st.download_button(
                        label="📊 Download Excel",
                        data=excel_data,
                        file_name=f"locations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
            else:
                st.error("❌ No locations were extracted. Please check your URL and JavaScript selector.")
    
    with col2:
        st.header("📖 Instructions")
        
        with st.expander("🎯 How to Use", expanded=True):
            st.markdown("""
            1. **Enter Website URL**: The full URL of the page containing locations
            2. **JavaScript Selector**: The DOM selector to find the location container
            3. **Choose Search Strategy**: 
               - **Comprehensive**: Performs multiple searches to load all data
               - **Single**: Extracts only currently visible data
            4. **Click Start Scraping**: Begin the extraction process
            5. **Download Results**: Get your data in CSV, JSON, or Excel format
            """)
        
        with st.expander("💡 Tips"):
            st.markdown("""
            - Use browser developer tools to find the correct DOM selector
            - For dynamic content, use "Comprehensive" search strategy
            - The scraper will try multiple search terms to populate all locations
            - Check the sample results to verify data quality
            """)
        
        with st.expander("🔧 JavaScript Selector Examples"):
            st.code('document.querySelector("#locations-list")')
            st.code('document.querySelector(".store-locator-results")')
            st.code('document.querySelectorAll(".location-item")')
            st.code('document.querySelector("#hbp-location-search > div.hbp-location-list")')
        
        # System requirements
        st.header("⚙️ Requirements")
        st.markdown("""
        **Required Python packages:**
        ```bash
        pip install streamlit selenium beautifulsoup4 pandas openpyxl
