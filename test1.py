import csv
import os
import time
# import datetime
from datetime import datetime
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


def extract_event_details(driver):
    details = {}

    try:
        # Always include the event URL
        details["event_url"] = driver.current_url
    except Exception:
        details["event_url"] = "N/A"

    try:
        title_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "h1.calendarTitle.prodTitle")
            )
        )
        details["title"] = title_element.text.strip()
        logging.info(f"Extracted title: {details['title']}")
    except Exception as e:
        logging.warning(f"Failed to extract title: {e}")
        details["title"] = "N/A"

    # ✅ Extract and format all date-time strings
    formatted_date_times = []

    try:
        event_list_items = driver.find_elements(By.CSS_SELECTOR, "li.events")

        for item in event_list_items:
            try:
                # Get the date
                date_div = item.find_element(
                    By.CSS_SELECTOR, "h5.ot_eventDateTitle .date"
                )
                date_text = date_div.text.strip()

                # Get all time slots for this date
                time_buttons = item.find_elements(
                    By.CSS_SELECTOR, "button.ot_timeSlotBtn p"
                )
                time_texts = [
                    btn.text.strip() for btn in time_buttons if btn.text.strip()
                ]

                for time in time_texts:
                    formatted_date_times.append(f"{date_text} - {time}")

            except Exception as inner_e:
                logging.warning(
                    f"Failed to extract date/time from an event item: {inner_e}"
                )

        # Join into a single string for CSV output
        details["date_times"] = formatted_date_times

    except Exception as outer_e:
        logging.error(f"Error while extracting all dates and times: {outer_e}")
        details["date_and_times"] = "N/A"

    try:
        image_element = driver.find_element(By.CSS_SELECTOR, "img.ot_prodImg")
        details["image_url"] = image_element.get_attribute("src")
        logging.info(f"Extracted image URL: {details['image_url']}")
    except Exception as e:
        logging.warning(f"Image not found or selector issue: {e}")
        details["image_url"] = "N/A"

    # You can add more fields as needed here

    return details


def extract_events(driver):
    try:
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "ot_prodListContainer"))
        )
        logging.info("Event list container is visible.")

        original_events = driver.find_elements(
            By.CSS_SELECTOR, ".ot_prodListItem.ot_callout"
        )
        logging.info(f"Found {len(original_events)} event items.")

        event_data_list = []

        for idx in range(len(original_events)):
            try:
                events = driver.find_elements(
                    By.CSS_SELECTOR, ".ot_prodListItem.ot_callout"
                )

                if idx >= len(events):
                    logging.warning(
                        f"Event #{idx + 1} no longer exists on reloaded page."
                    )
                    continue

                button = events[idx].find_element(
                    By.CSS_SELECTOR, "button.ot_prodInfoButton"
                )

                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});",
                    button,
                )

                button.click()
                logging.info(f"Clicked 'See this event' on event #{idx + 1}")

                WebDriverWait(driver, 10).until(EC.url_contains("production"))

                # ✅ Get event details + link
                details = extract_event_details(driver)
                event_data_list.append(details)
                logging.info(f"Extracted event #{idx + 1} details: {details}")

                driver.back()
                logging.info("Returned to calendar page.")

                WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located(
                        (By.CLASS_NAME, "ot_prodListContainer")
                    )
                )

            except Exception as e:
                logging.error(f"Error processing event #{idx + 1}: {e}")

        return event_data_list

    except Exception as e:
        logging.error(f"Failed to extract events: {e}")
        return []


# ========== Main Script ==========
def main():
    url = "https://ci.ovationtix.com/35583/production/1152995"  # URL of the production page to scrape
    driver = setup_driver()  # Set up the undetected Chrome driver in headless mode

    all_events = []  # This will hold all event data to be written to CSV

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
                        logging.info(f"→ {link['event_url']}")  # Log each event URL

                    # Step 5: Visit each event link to extract detailed data
                    for idx, link in enumerate(event_links, start=1):
                        try:
                            driver.get(link["event_url"])
                            time.sleep(2)

                            event_data = extract_event_details(driver)

                            merged_data = link.copy()
                            for key in set(list(link.keys()) + list(event_data.keys())):
                                val1 = event_data.get(key, "N/A")
                                val2 = link.get(key, "N/A")
                                merged_data[key] = val1 if val1 not in [None, "", "N/A"] else val2

                            for date_time in merged_data.get("date_times", []):
                                # 🔍 Check for missing title
                                if not merged_data.get("title") or merged_data.get("title") == "N/A":
                                    logging.warning(f"Missing title for event: {merged_data.get('event_url')}")

                            # ➕ Determine status based on date_time
                                try:
                                    event_datetime = datetime.strptime(date_time, "%d %B %Y - %I:%M %p")
                                    now = datetime.now()

                                    if abs((event_datetime - now).total_seconds()) <= 300:
                                        status = "active"
                                    elif event_datetime > now:
                                        status = "upcoming"
                                    else:
                                        status = "closed"
                                except Exception as e:
                                    logging.warning(f"Could not parse date_time '{date_time}' for status: {e}")
                                    status = "N/A"

                                all_events.append(
                                    {
                                        "title": merged_data.get("title", "N/A"),
                                        "event_url": merged_data.get("event_url", "N/A"),
                                        "image_url": merged_data.get("image_url", "N/A"),
                                        "status": status,
                                        "production_type": merged_data.get("production_type", "N/A"),
                                        "date_time": date_time,
                                    }
                                )


                        except Exception as e:
                            logging.error(
                                f"Error scraping event page {link['event_url']}: {e}"
                            )

                else:
                    logging.warning("No event URLs were extracted.")
            else:
                logging.error("Failed to open calendar panel.")
        else:
            logging.error("Page did not load properly.")

        # Step 8: Save results to CSV if data was collected
        if all_events:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/ovationtix_events_{timestamp}.csv"
            os.makedirs("data", exist_ok=True)
            with open(filename, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "title",
                        "event_url",
                        "image_url",
                        "status",
                        "production_type",
                        "date_time",
                    ],
                )
                writer.writeheader()
                writer.writerows(all_events)
            logging.info(f"Successfully saved {len(all_events)} records to {filename}")
        else:
            logging.warning("No event data collected. CSV not created.")

    finally:
        # Step 9: Close the browser and cleanup
        driver.quit()
        del driver  # Helps suppress warning messages in Windows


if __name__ == "__main__":
    main()
