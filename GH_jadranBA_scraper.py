import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
# Import RemoteConnection to configure its timeout
from selenium.webdriver.remote.remote_connection import RemoteConnection 

import json
import os
import datetime
import time

def scrape_avpjm_jadran_ba(url):
    options = FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

    # --- RE-INTRODUCED CLIENT CONNECTION CONFIGURATION ---
    # Create an instance of RemoteConnection and set the timeout directly in its constructor.
    # The 'remote_server_addr' ("http://localhost:4444/wd/hub") is a placeholder,
    # as Selenium will internally connect to geckodriver's dynamic port.
    # We set timeout to 300 seconds (5 minutes) to avoid "Read timed out" errors.
    selenium_connection = RemoteConnection("http://localhost:4444/wd/hub", keep_alive=True, timeout=300)
    # --- END RE-INTRODUCED SECTION ---

    # Define output directory early to use for geckodriver logs
    output_dir = "scraped_data_avpjm_jadran_ba"
    os.makedirs(output_dir, exist_ok=True) # Ensure directory exists before creating log file
    geckodriver_log_path = os.path.join(output_dir, "geckodriver.log")

    # Initialize the GeckoDriver service with an increased startup timeout
    # and a log path for debugging. This is crucial for the "Read timed out" error during startup.
    service = webdriver.firefox.service.Service(
        executable_path=GeckoDriverManager().install(),
        log_path=geckodriver_log_path, # This will save geckodriver's internal logs
        start_timeout=180 # Increased to 3 minutes, as default 30s is often too short for CI
    )

    driver = None # Initialize driver to None in case creation fails
    data = [] # Initialize data list
    try:
        # Pass the configured selenium_connection instance to the driver constructor
        driver = webdriver.Firefox(service=service, options=options, client=selenium_connection)
        print("WebDriver initialized. Navigating to URL...")

        driver.get(url)
        print(f"Navigated to: {url}")

        # Wait for the table wrapper div to be present, giving JavaScript time to render it
        WebDriverWait(driver, 60).until( # Wait up to 60 seconds for the element
            EC.presence_of_element_located((By.CLASS_NAME, "v-data-table__wrapper"))
        )
        print("Table wrapper found. Proceeding to parse.")

        # Once the element is present, get the page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table_wrapper_div = soup.find('div', class_='v-data-table__wrapper')

        if table_wrapper_div:
            actual_table = table_wrapper_div.find('table')
            if actual_table:
                print("Found the data table.")
                headers = [th.get_text(strip=True) for th in actual_table.find('thead').find_all('th')]
                if headers:
                    data.append(headers)
                    print("Headers:", headers)

                rows = actual_table.find('tbody').find_all('tr')
                for row in rows:
                    cols_raw = row.find_all('td')
                    row_data = []
                    for i, col in enumerate(cols_raw):
                        if headers[i] == 'Trend':
                            trend_icon = col.find('i', class_=lambda x: x and 'mdi-trending' in x)
                            trend_value_text = col.get_text(strip=True).replace('\n', ' ').strip()
                            trend_direction = "N/A"
                            if trend_icon:
                                if 'mdi-trending-up' in trend_icon.get('class', []):
                                    trend_direction = "Up"
                                elif 'mdi-trending-down' in trend_icon.get('class', []):
                                    trend_direction = "Down"
                                elif 'mdi-trending-neutral' in trend_icon.get('class', []):
                                    trend_direction = "Neutral"
                            row_data.append(f"{trend_direction} {trend_value_text}")
                        elif headers[i] == 'Vrijednost':
                            value_span = col.find('span')
                            if value_span:
                                row_data.append(value_span.get_text(strip=True))
                            else:
                                row_data.append(col.get_text(strip=True))
                        else:
                            row_data.append(col.get_text(strip=True))
                    if row_data:
                        data.append(row_data)
                print(f"Scraped {len(data) - (1 if headers else 0)} data rows.")
            else:
                print("No <table> element found inside 'v-data-table__wrapper' div after waiting.")
        else:
            print("Div with class 'v-data-table__wrapper' not found even after waiting.")

    except Exception as e:
        print(f"An unexpected error occurred during scraping: {e}")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Save screenshot and page source for debugging if an error occurs
        if driver: # Only attempt to save if driver was successfully initialized
            driver.save_screenshot(os.path.join(output_dir, f"error_screenshot_{timestamp}.png"))
            with open(os.path.join(output_dir, f"error_page_source_{timestamp}.html"), "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        else:
            print("Driver not initialized, cannot save screenshot or page source.")
    finally:
        if driver: # Ensure driver exists before trying to quit or save artifacts
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Always save final screenshot and page source for general debugging
            with open(os.path.join(output_dir, f"page_source_{timestamp}.html"), 'w', encoding='utf-8') as f_html:
                f_html.write(driver.page_source)
            driver.save_screenshot(os.path.join(output_dir, f"screenshot_{timestamp}.png"))
            driver.quit() # Ensure the browser is closed
        else:
            print("Driver was not initialized, no browser to quit.")
    return data # Return collected data (may be empty if errors occurred)

if __name__ == "__main__":
    url = "https://avpjm.jadran.ba/vodomjerne_stanice"
    print("\n--- Scraping from avpjm.jadran.ba ---")
    scraped_data = [] # Initialize scraped_data to an empty list
    for attempt in range(3): # Retry mechanism for transient failures
        print(f"Attempt {attempt+1} to scrape avpjm.jadran.ba...")
        try:
            scraped_data = scrape_avpjm_jadran_ba(url)
            if scraped_data: # Check if data was actually returned
                print(f"Attempt {attempt+1} successful. Data scraped.")
                break # Exit loop if data is successfully scraped
            else:
                print(f"Attempt {attempt+1} completed but returned no data. Retrying in 10 seconds...")
                time.sleep(10)
        except Exception as e: # Catch any exceptions from the scrape function call
            print(f"Attempt {attempt+1} failed with an error: {e}. Retrying in 10 seconds...")
            time.sleep(10)
    else: # This block executes if the loop completes without a 'break' (all retries failed)
        print("All retries failed for avpjm.jadran.ba. No data could be scraped.")
        exit(1) # Indicate failure to GitHub Actions

    if scraped_data: # Only proceed to save if data was collected
        output_dir = "scraped_data_avpjm_jadran_ba"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"water_levels_jadran_ba_{timestamp}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(scraped_data, f, ensure_ascii=False, indent=4)
        print(f"Data from avpjm.jadran.ba saved to: {filename}")
    else:
        print("No data was collected from avpjm.jadran.ba to save.")
