import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
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

    # This sets the global default for RemoteConnection timeouts for all Selenium commands.
    # It's good to keep this, although the Service start_timeout is more critical for initial driver launch.
    RemoteConnection.set_timeout(300)

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

    driver = webdriver.Firefox(service=service, options=options)
    print("WebDriver initialized. Navigating to URL...") # Added print statement for clarity

    data = []
    try:
        driver.get(url)
        print(f"Navigated to: {url}")

        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CLASS_NAME, "v-data-table__wrapper"))
        )
        print("Table wrapper found. Proceeding to parse.")

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
                print("No <table> element found inside 'v-data-table__wrapper' div.")
        else:
            print("Div with class 'v-data-table__wrapper' not found.")

    except Exception as e:
        print(f"An unexpected error occurred during scraping: {e}")
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # output_dir
