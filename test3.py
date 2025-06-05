import os
import time
import json
import csv
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime


# ========== Setup Logging ==========
os.makedirs("log", exist_ok=True)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("log/ovationtix_scraper.log", mode="a", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))

logger.addHandler(file_handler)
logger.addHandler(console_handler)


# ========== Setup Driver ==========
def setup_driver(headless=False):
    options = uc.ChromeOptions()
    options.headless = headless  # Change to True for headless
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )

    driver = uc.Chrome(options=options)
    if not headless:
        driver.maximize_window()
    return driver


# ========== Load Page ==========
def load_page(driver, url):
    try:
        driver.get(url)
        logger.info(f"Navigated to {url}")
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        logger.info("Page fully loaded")
        return True
    except Exception as e:
        logger.error(f"Error loading page: {e}")
        return False


# ========== Click Calendar Button ==========
def click_calendar_button(driver):
    try:
        calendar_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="calendar_button"]'))
        )
        calendar_btn.click()
        logger.info("Clicked the 'Calendar' button")

        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ot_prodListContainer"))
        )
        logger.info("Calendar content loaded and visible")
        return True
    except Exception as e:
        logger.error(f"Failed to click calendar button: {e}")
        return False


# ========== Extract Event Links ==========
def extract_event_links(driver):
    try:
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ot_prodListContainer"))
        )

        event_links = []
        events = driver.find_elements(By.CSS_SELECTOR, ".ot_prodListItem.ot_callout")
        logger.info(f"Found {len(events)} events")

        for idx in range(len(events)):
            # Refetch elements to avoid stale reference
            events = driver.find_elements(By.CSS_SELECTOR, ".ot_prodListItem.ot_callout")
            if idx >= len(events):
                logger.warning(f"Event #{idx + 1} disappeared, skipping")
                continue

            try:
                # Find the button inside the current event
                button = events[idx].find_element(By.CSS_SELECTOR, "button.ot_prodInfoButton")

                # Scroll button into view for better interaction
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", button)

                # Wait for THIS specific button element to be clickable (not a global selector)
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(button))

                button.click()
                logger.info(f"Clicked 'See this event' button on event #{idx + 1}")

                # Instead of waiting just for URL change, wait for key detail page element to appear
                WebDriverWait(driver, 15).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, ".ot_productionTitle h1"))
                )

                event_url = driver.current_url
                event_links.append(event_url)
                logger.info(f"Captured event URL: {event_url}")

                driver.back()

                # Wait for calendar page and event list container to reload
                WebDriverWait(driver, 15).until(
                    EC.visibility_of_element_located((By.CLASS_NAME, "ot_prodListContainer"))
                )

                # Small pause to stabilize page after going back
                time.sleep(1.5)

            except Exception as e:
                logger.error(f"Error processing event #{idx + 1}: {e}")

        return event_links

    except Exception as e:
        logger.error(f"Failed to extract event links: {e}")
        return []


# ========== Extract Event Details ==========
def extract_event_details(driver):
    import re

    details = {
        "title": "N/A",
        "date": "N/A",
        "time": "N/A",
        "link": driver.current_url,
        "image_url": "N/A",
        "production_type": "N/A",
        "status": "N/A",
        "origin": "N/A",
        "market_presence": "N/A",
        "age_of_production": "N/A",
    }

    try:
        title_elem = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ot_productionTitle h1"))
        )
        details["title"] = title_elem.text.strip()
    except Exception as e:
        logger.warning(f"Title not found: {e}")

    try:
        # Date and time - get first performance date/time if possible
        perf_elems = driver.find_elements(By.CSS_SELECTOR, ".ot_dateGroup .ot_perfInfo")
        if perf_elems:
            first_text = perf_elems[0].text.strip()
            date_match = re.search(r"\w{3},\s[\w\s]+\d{4}", first_text)
            time_match = re.search(r"\d{1,2}:\d{2}\s[APMapm]{2}", first_text)
            if date_match:
                details["date"] = date_match.group(0)
            if time_match:
                details["time"] = time_match.group(0)
    except Exception as e:
        logger.warning(f"Date/time not found: {e}")

    try:
        img_elem = driver.find_element(By.CSS_SELECTOR, ".ot_productionPoster img")
        details["image_url"] = img_elem.get_attribute("src")
    except Exception as e:
        logger.warning(f"Image URL not found: {e}")

    # Helper function to get text from dd following a dt label
    def get_dd_text(label_text):
        try:
            dd = driver.find_element(By.XPATH, f"//dt[contains(text(), '{label_text}')]/following-sibling::dd[1]")
            return dd.text.strip()
        except:
            return "N/A"

    details["production_type"] = get_dd_text("Production Type")
    details["status"] = get_dd_text("Status")
    details["origin"] = get_dd_text("Origin")
    details["market_presence"] = get_dd_text("Market")

    try:
        opening_text = get_dd_text("Opening Date")
        year_match = re.search(r"\d{4}", opening_text)
        if year_match:
            opening_year = int(year_match.group(0))
            current_year = datetime.now().year
            details["age_of_production"] = f"{current_year - opening_year} years"
    except:
        pass

    return details


# ========== Main ==========
def main():
    start_url = "https://ci.ovationtix.com/35583/production/1152995"  # Starting page URL

    driver = setup_driver(headless=False)  # headless=True to run without UI

    all_event_details = []

    try:
        if not load_page(driver, start_url):
            logger.error("Failed to load start page, exiting.")
            return

        if not click_calendar_button(driver):
            logger.error("Failed to open calendar, exiting.")
            return

        event_links = extract_event_links(driver)
        logger.info(f"Total event links extracted: {len(event_links)}")

        if not event_links:
            logger.warning("No event links found.")
            return

        for idx, link in enumerate(event_links, 1):
            try:
                driver.get(link)
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ot_productionTitle h1"))
                )
                time.sleep(1)  # slight delay to ensure content loads

                details = extract_event_details(driver)
                all_event_details.append(details)
                logger.info(f"[{idx}/{len(event_links)}] Extracted event details: {details['title']}")
            except Exception as e:
                logger.error(f"Error extracting details from event {link}: {e}")

    finally:
        driver.quit()

    if all_event_details:
        os.makedirs("data", exist_ok=True)
        csv_file = "data/ovationtix_events.csv"
        json_file = "data/ovationtix_events.json"

        keys = all_event_details[0].keys()
        with open(csv_file, "w", newline="", encoding="utf-8") as f_csv:
            dict_writer = csv.DictWriter(f_csv, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_event_details)
        logger.info(f"Saved data to CSV: {csv_file}")

        with open(json_file, "w", encoding="utf-8") as f_json:
            json.dump(all_event_details, f_json, indent=4)
        logger.info(f"Saved data to JSON: {json_file}")
    else:
        logger.warning("No event details extracted; no files saved.")


if __name__ == "__main__":
    main()
