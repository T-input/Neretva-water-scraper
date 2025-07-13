import os
import json
import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def setup_driver(headless=True):
    options = FirefoxOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Firefox(options=options)


def wait_and_click(driver, by, value, timeout=20):
    """Wait for an element to be clickable and click it."""
    element = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, value))
    )
    element.click()
    return element


def scrape_water_levels(url):
    driver = None
    data = []

    try:
        driver = setup_driver()
        driver.get(url)
        print(f"Opened: {url}")

        # Step 1: Click Accept/List button
        wait_and_click(driver, By.ID, "btn_list")
        print("Clicked 'btn_list'")

        # Step 2: Open dropdown
        wait_and_click(driver, By.ID, "bp")
        print("Opened dropdown 'bp'")

        # Step 3: Choose option
        option_text = "32 Mali slivovi Neretva - Korčula i Dubrovačko primorje i otoci"
        wait_and_click(driver, By.XPATH, f"//a[normalize-space()='{option_text}']")
        print(f"Selected dropdown option: {option_text}")

        # Step 4: Wait for table to load
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        print("Table loaded")

        # Step 5: Parse table
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        table = soup.find('table', width="96%", border="0", cellspacing="0", cellpadding="5")

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


def save_data(data, output_dir="HRvode_scraped_data"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"HRvode_water_levels_{timestamp}.json")

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"Saved scraped data to: {filename}")


if __name__ == "__main__":
    url = "https://vodostaji.voda.hr/"
    print(f"Starting scrape from: {url}")
    scraped_data = scrape_water_levels(url)

    if scraped_data:
        save_data(scraped_data)
    else:
        print("No data scraped.")
