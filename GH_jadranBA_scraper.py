import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager # UNCOMMENT THIS LINE

import json
import os
import datetime
import time

def scrape_avpjm_jadran_ba(url):
    options = FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # IMPORTANT: Use GeckoDriverManager to automatically manage geckodriver
    service = webdriver.firefox.service.Service(GeckoDriverManager().install()) # UNCOMMENT THIS LINE
    driver = webdriver.Firefox(service=service, options=options) # MODIFY THIS LINE to use service=service

    data = []
    try:
        driver.get(url)
    except Exception as e:
        print(f"Failed to load page: {e}")
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
    finally:
        driver.quit()
    return data

if __name__ == "__main__":
    url = "https://avpjm.jadran.ba/vodomjerne_stanice"
    print("\n--- Scraping from avpjm.jadran.ba ---")
    scraped_data = None
    for attempt in range(3):
        try:
            scraped_data = scrape_avpjm_jadran_ba(url)
            if scraped_data:
                break
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(10)
    else:
        print("All retries failed.")
        exit(1)
    if scraped_data:
        output_dir = "scraped_data_avpjm_jadran_ba"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"water_levels_jadran_ba_{timestamp}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(scraped_data, f, ensure_ascii=False, indent=4)
        print(f"Data from avpjm.jadran.ba saved to: {filename}")
    else:
        print("No data scraped from avpjm.jadran.ba.")
