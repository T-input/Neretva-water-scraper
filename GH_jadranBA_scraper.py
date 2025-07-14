import os
import json
import datetime
import argparse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException


def setup_driver(firefox_binary_path=None, headless=True):
    options = FirefoxOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    if firefox_binary_path:
        options.binary_location = firefox_binary_path

    return webdriver.Firefox(options=options)



def wait_and_click(driver, by, value, timeout=20, post_delay=1):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.5)  # Allow scroll animation
        element.click()
        time.sleep(post_delay)  # Let the page react/render
        return element
    except (TimeoutException, ElementClickInterceptedException) as e:
        print(f"[!] Failed to click element ({by}, {value}): {e}")
        raise
def scrape_water_levels(url, firefox_binary_path=None):
    driver = None
    data = []

    try:
        driver = setup_driver(firefox_binary_path=firefox_binary_path)
        driver.get(url)
        print(f"Opened: {url}")

        # Step 1: Wait for table to load
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "v-data-table__wrapper")))
        
        print("Table loaded")

        # Step 2: Parse table
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table = soup.find('div', class_='v-data-table__wrapper')

        if not table:
            print("Table not found")
            return []

        headers = [th.get_text(strip=True) for th in table.find_all('th')]
        if headers:
            data.append(headers)
            print(f"Headers: {headers}")

        rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')
        start_index = 1 if headers and rows and rows[0].find('th') else 0

        for row in rows[start_index:]:
            cols = [td.get_text(strip=True) for td in row.find_all('td')]
            if any(cols):  # Skip empty rows
                data.append(cols)

        print(f"Scraped {len(data) - (1 if headers else 0)} rows")

    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        if driver:
            driver.quit()

    return data


def save_data(data, output_dir="jadranBA_scraped_data"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"jadran.BA_water_levels_{timestamp}.json")

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Saved scraped data to: {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--firefox-path", type=str, help="Path to Firefox binary")
    args = parser.parse_args()

    url = "https://avpjm.jadran.ba/vodomjerne_stanice"
    print(f"Starting scrape from: {url}")

    scraped_data = scrape_water_levels(url, firefox_binary_path=args.firefox_path)

    if scraped_data:
        save_data(scraped_data)
    else:
        print("No data scraped.")
