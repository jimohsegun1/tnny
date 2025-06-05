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
file_handler = logging.FileHandler(
    "log/ovationtix_scraper.log", mode="a", encoding="utf-8"
)
file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)

# Console handler
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter("%(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)

# Attach handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)


# ========== Setup Driver ==========
def setup_driver():
    options = uc.ChromeOptions()
    options.headless = True  # Set to False if debugging
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # options.add_argument("--start-maximized")  # ✅ Launch in maximizrd window

    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )

    driver = uc.Chrome(options=options)
    if not options.headless:
        driver.maximize_window()
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
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'button[data-test="calendar_button"]')
            )
        )
        calendar_btn.click()
        logging.info("Clicked the 'Calendar' button successfully.")

        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ot_prodListContainer"))
        )
        logging.info("Calendar content (.ot_prodListContainer) is visible.")

        return True
    except Exception as e:
        logging.error(f"Failed to click the 'Calendar' button: {e}")
        return False


# ========== Extract Event Links ==========
def extract_events(driver):
    try:
        # Wait for the event list container to appear
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ot_prodListContainer"))
        )
        logging.info("Event list container is visible.")

        # Get the initial list of event containers once
        original_events = driver.find_elements(
            By.CSS_SELECTOR, ".ot_prodListItem.ot_callout"
        )
        logging.info(f"Found {len(original_events)} event items.")

        event_links = []  # Store final URLs here

        # Loop to click each "See this event" button and capture the URL
        for idx in range(len(original_events)):
            try:
                # Refetch all current events each time to avoid stale element references
                events = driver.find_elements(
                    By.CSS_SELECTOR, ".ot_prodListItem.ot_callout"
                )

                # Skip if the number of events has changed (e.g., due to loading issues)
                if idx >= len(events):
                    logging.warning(
                        f"Event #{idx + 1} no longer exists on reloaded page."
                    )
                    continue

                button = events[idx].find_element(
                    By.CSS_SELECTOR, "button.ot_prodInfoButton"
                )  # Get the correct button inside this event

                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});",
                    button,
                )  # Scroll to the button (helps avoid hidden elements)

                button.click()  # Click the event button
                logging.info(f"Clicked 'See this event' on event #{idx + 1}")

                # Wait for the new URL to load (event detail page)
                WebDriverWait(driver, 10).until(EC.url_contains("production"))
                current_url = driver.current_url
                event_links.append(current_url)
                logging.info(f"Captured event URL: {current_url}")

                # Go back to the calendar page
                driver.back()
                logging.info("Returned to calendar page.")

                # Wait for calendar to reload
                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.CLASS_NAME, "ot_prodListContainer")
                    )
                )

            except Exception as e:
                logging.error(f"Error processing event #{idx + 1}: {e}")

        return event_links

    except Exception as e:
        logging.error(f"Failed to extract events: {e}")
        return []


# ========== Main Script ==========
def main():
    url = "https://ci.ovationtix.com/35583/production/1152995"  # URL of the production page to scrape

    driver = setup_driver()  # Set up the undetected Chrome driver in headless mode

    try:
        # Step 1: Load the main page
        if load_page(driver, url):
            logging.info("Ready to begin scraping content...")

            # Step 2: Click the "Calendar" button to open the event listings
            if click_calendar_button(driver):
                logging.info("Calendar panel should now be visible.")

                # Step 3: Extract event links by clicking each "See this event" button
                event_links = extract_events(driver)

                # Step 4: Check and log the extracted event URLs
                if event_links:
                    logging.info(
                        f"Successfully extracted {len(event_links)} event URLs."
                    )
                    for link in event_links:
                        logging.info(f"→ {link}")  # Print each event link to the log
                else:
                    logging.warning("No event URLs were extracted.")
            else:
                logging.error("Failed to open calendar panel.")
        else:
            logging.error("Page did not load properly.")
    finally:
        # Step 5: Close the browser and cleanup
        driver.quit()
        del driver  # Helps suppress warning messages in Windows


if __name__ == "__main__":
    main()
