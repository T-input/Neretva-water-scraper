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

def scrape_vodostaji_voda_hr(url):
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
        print(f"Navigated to: {url}")
        try:
            btn_list_element = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "btn_list"))
            )
            btn_list_element.click()
            print("Clicked 'btn_list' to proceed.")
            time.sleep(2)
        except Exception as e:
            print(f"Failed to find or click 'btn_list' element: {e}")
            return []

        try:
            dropdown_trigger = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "bp"))
            )
            dropdown_trigger.click()
            print("Clicked the dropdown trigger (ID 'bp').")
            time.sleep(2)
        except Exception as e:
            print(f"Failed to find or click dropdown trigger (ID 'bp'): {e}")
            return []

        option_text = "32 Mali slivovi Neretva - Korčula i Dubrovačko primorje i otoci"
        try:
            option_element = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, f"//a[normalize-space()='{option_text}']"))
            )
            option_element.click()
            print(f"Selected '{option_text}' from dropdown.")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            print("Table element found on page after selection.")
            time.sleep(2)
        except Exception as e:
            print(f"Failed to find or click dropdown option '{option_text}' or table did not load: {e}")
            return []

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        actual_table = soup.find('table', width="96%", border="0", cellspacing="0", cellpadding="5")
        if actual_table:
            print("Found the data table.")
            headers = [th.get_text(strip=True) for th in actual_table.find_all('th')]
            if headers:
                data.append(headers)
                print("Headers:", headers)
            rows = actual_table.find('tbody').find_all('tr') if actual_table.find('tbody') else actual_table.find_all('tr')
            start_row = 1 if headers and len(rows) > 0 and rows[0].find('th') else 0
            for row in rows[start_row:]:
                cols = row.find_all('td')
                cols = [col.get_text(strip=True) for col in cols]
                if cols and any(col for col in cols):
                    data.append(cols)
                print(f"Scraped {len(data) - (1 if headers else 0)} data rows.")
            else:
                print("No <table> element found with the specified attributes. Check the selector again.")
        except Exception as e:
            print(f"An unexpected error occurred during scraping: {e}")
        finally:
            driver.quit()
        return data

    if __name__ == "__main__":
        url = "https://vodostaji.voda.hr/"
        print("\n--- Scraping from vodostaji.voda.hr ---")
        scraped_data = scrape_vodostaji_voda_hr(url)
        if scraped_data:
            output_dir = "scraped_data_vodostaji_voda_hr"
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(output_dir, f"water_levels_voda_hr_{timestamp}.json")
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(scraped_data, f, ensure_ascii=False, indent=4)
            print(f"Data from vodostaji.voda.hr saved to: {filename}")
        else:
            print("No data scraped from vodostaji.voda.hr.")