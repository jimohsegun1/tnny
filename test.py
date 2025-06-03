import os
import logging
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ========== Setup Logging ==========
os.makedirs("log", exist_ok=True)

# Create logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler('log/ovationtix_scraper.log', mode='a', encoding='utf-8')
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Console handler
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter('%(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Attach handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ========== Setup Driver ==========
def setup_driver():
    options = uc.ChromeOptions()
    options.headless = False
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )

    driver = uc.Chrome(options=options)
    return driver

# ========== Load Page and Wait ==========
def load_page(driver, url):
    try:
        driver.get(url)
        logging.info(f"Navigated to {url}")

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        logging.info("Page fully loaded")
        return True
    except Exception as e:
        logging.error(f"Error loading page: {e}")
        return False

def click_calendar_button(driver):
    try:
        # Wait for the calendar button to be clickable
        calendar_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="calendar_button"]'))
        )
        calendar_btn.click()
        logging.info("Clicked the 'Calendar' button successfully.")

        # Wait for the new calendar page to load (wait for .ot_prodListContainer)
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ot_prodListContainer"))
        )
        logging.info("Calendar content (.ot_prodListContainer) is visible.")
        
        return True
    except Exception as e:
        logging.error(f"Failed to click the 'Calendar' button: {e}")
        return False

def extract_events(driver):
    try:
        # Find all event elements
        events = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.ot_prodListItem.ot_callout'))
        )
        logging.info(f"Found {len(events)} events.")

        for idx, event in enumerate(events, start=1):
            logging.info(f"Event #{idx} HTML snippet:\n{event.get_attribute('outerHTML')[:200]}...")

        # TODO: Extract details like date, time, etc. from each event
        return events
    except Exception as e:
        logging.error(f"Failed to extract events: {e}")
        return []





# ========== Main Script ==========
def main():
    url = "https://ci.ovationtix.com/35583/production/1152995"
    driver = setup_driver()

    try:
        if load_page(driver, url):
            logging.info("Ready to begin scraping content...")
            # TODO: Add scraping logic here

             # Click calendar button
            if click_calendar_button(driver):
                logging.info("Calendar panel should now be visible.")

                events = extract_events(driver)

                if events:
                    logging.info("Successfully extracted events.")
    finally:
        driver.quit()
        del driver  # Helps suppress Windows cleanup warnings

if __name__ == "__main__":
    main()
