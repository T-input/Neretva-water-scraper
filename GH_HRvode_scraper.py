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
import logging

logging.basicConfig(level = logging.DEBUG)

def scrape_vodostaji_voda_hr(url):
    logging.info("Starting scrape")
    options = FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # IMPORTANT: Use GeckoDriverManager to automatically manage geckodriver
    service = webdriver.firefox.service.Service(GeckoDriverManager().install()) # UNCOMMENT THIS LINE
    driver = webdriver.Firefox(service=service, options=options) # MODIFY THIS LINE to use service=service

    logging.info("Initialized driver")
    data = []
    try:
        driver.get(url)
    except Exception as e:
        logging.warning(f"Failed to load page: {e}")
    try:
        btn_list_element = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.ID, "btn_list"))
        )
        btn_list_element.click()
        logging.info("Clicked 'btn_list' to proceed.")
        time.sleep(5)
    except Exception as e:
        logging.warning(f"Failed to find or click 'btn_list' element: {e}")
        return []

    try:
        dropdown_trigger = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.ID, "bp"))
        )
        dropdown_trigger.click()
        logging.info("Clicked the dropdown trigger (ID 'bp').")
        time.sleep(5)
    except Exception as e:
        logging.warning(f"Failed to find or click dropdown trigger (ID 'bp'): {e}")
        return []

    option_text = "32 Mali slivovi Neretva - Korčula i Dubrovačko primorje i otoci"
    try:
        option_element = WebDriverWait(driver, 60).until(
            EC.element_to_be_clickable((By.XPATH, f"//a[normalize-space()='{option_text}']"))
        )
        option_element.click()
        logging.info(f"Selected '{option_text}' from dropdown.")
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        logging.info("Table element found on page after selection.")
        time.sleep(5)
    except Exception as e:
        logging.warning(f"Failed to find or click dropdown option '{option_text}' or table did not load: {e}")
        return []
        
    try:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        actual_table = soup.find('table', width="96%", border="0", cellspacing="0", cellpadding="5")
        if actual_table:
            logging.info("Found the data table.")
            headers = [th.get_text(strip=True) for th in actual_table.find_all('th')]
            if headers:
                data.append(headers)
                logging.info("Headers:", headers)
            rows = actual_table.find('tbody').find_all('tr') if actual_table.find('tbody') else actual_table.find_all('tr')
            start_row = 1 if headers and len(rows) > 0 and rows[0].find('th') else 0
            for row in rows[start_row:]:
                cols = row.find_all('td')
                cols = [col.get_text(strip=True) for col in cols]
                if cols and any(col for col in cols):
                    data.append(cols)
                logging.info(f"Scraped {len(data) - (1 if headers else 0)} data rows.")
            else:
                logging.warning("No <table> element found with the specified attributes. Check the selector again.")
    except Exception as e:
        logging.exception(f"An unexpected error occurred during scraping: {e}")
    finally:
        driver.quit()
    return data

if __name__ == "__main__":
    url = "https://vodostaji.voda.hr/"
    logging.info("\n--- Scraping from vodostaji.voda.hr ---")
    for attempt in range(3):
        try:
            scraped_data = scrape_vodostaji_voda_hr(url)
            break
        except Exception as e:
            logging.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(10)
    else:
        logging.warning("All retries failed.")
    logging.info(f"Scraped data {len(scraped_data)}")
    if scraped_data:
        output_dir = "scraped_data_vodostaji_voda_hr"
        logging.info(f"Saving scraped data to {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"water_levels_voda_hr_{timestamp}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(scraped_data, f, ensure_ascii=False, indent=4)
        print(f"Data from vodostaji.voda.hr saved to: {filename}")
    else:
        print("No data scraped from vodostaji.voda.hr.")
