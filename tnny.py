import datetime
from datetime import timedelta # Add timedelta for robust comparison
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_driver():
    """Sets up the Selenium WebDriver."""
    try:
        # For Chrome, you might need to download chromedriver and specify its path, or ensure it's in your PATH
        driver = webdriver.Chrome()
        driver.maximize_window()    # Add this line to maximize the window
        logging.info("WebDriver initialized successfully.")
        return driver
    except Exception as e:
        logging.error(f"Error initializing WebDriver: {e}")
        return None

def navigate_to_calendar(driver, url):
    """Navigates to the website and clicks the Calendar link."""
    logging.info(f"Navigating to {url}")
    driver.get(url)
    try:
        # Corrected: Targeting the button using its data-test attribute
        calendar_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-test='calendar_button']"))
        )
        calendar_button.click()
        logging.info("Clicked 'Calendar' button.")
        time.sleep(2)  # Give some time for the page to load
        return True
    except Exception as e:
        logging.error(f"Error navigating to calendar or clicking button: {e}")
        return False

def get_event_buttons(driver): # Renamed function
    """Extracts the web elements for individual event 'See this event' buttons."""
    event_buttons = [] # Renamed list to reflect buttons
    try:
        # This selector `By.CLASS_NAME, "ot_prodListItem ot_callout"` is assumed to correctly identify the parent container for each event.
        event_elements = driver.find_elements(By.CLASS_NAME, "ot_prodListItem ot_callout") # Use dot notation for multiple classes
        logging.info(f"Found {len(event_elements)} event elements (containers).")

        for event_element in event_elements:
            try:
                # Find the 'See this event' button within each event_element
                # The button has a span with data-i18n-key="productionCalendar.seeEvent" or text "See this event"
                see_event_button = WebDriverWait(event_element, 5).until( # Use WebDriverWait on the event_element itself
                    EC.element_to_be_clickable((By.XPATH, ".//button[./span[text()='See this event']]"))
                    # OR, if data-i18n-key is more stable:
                    # EC.element_to_be_clickable((By.XPATH, ".//button[./span[@data-i18n-key='productionCalendar.seeEvent']]"))
                )
                event_buttons.append(see_event_button) # Append the WebElement button itself
                logging.info(f"Found 'See this event' button for an event.")
            except Exception as e:
                logging.warning(f"Could not find 'See this event' button within an event container: {e}")
        logging.info(f"Extracted {len(event_buttons)} 'See this event' button elements.")
    except Exception as e:
        logging.error(f"Error getting event container elements: {e}")
    return event_buttons

def extract_event_details(driver, event_url):
    """Extracts details from a single event page."""
    logging.info(f"Visiting event page: {event_url}")
    driver.get(event_url)
    time.sleep(2)  # Give some time for the page to load

    details = {
        "Title": "N/A",
        "Production type": "N/A",
        "Status": "N/A",
        "Origin": "N/A",
        "Market presence": "N/A",
        "Age of production": "N/A"
    }

    try:
        # Title
        title_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//h1[@class='calendarTitle prodTitle']"))
        )
        details["Title"] = title_element.text.strip()
        logging.info(f"Extracted Title: {details['Title']}")
    except Exception as e:
        logging.warning(f"Could not extract Title: {e}")

    # Production type (This often needs to be inferred from keywords or specific sections)
    try:
        # Example: check for keywords in description or specific tags
        description = driver.find_element(By.CSS_SELECTOR, "prodDescriptionCollapsed").text.lower()
        if "musical" in description:
            details["Production type"] = "musical"
        elif "play" in description:
            details["Production type"] = "play"
        # Add more logic for 'immersive', 'concert', 'stream'
        else:
            details["Production type"] = "play" # Default assumption if no clear indicator
        logging.info(f"Extracted Production type: {details['Production type']}")
    except Exception as e:
        logging.warning(f"Could not infer Production type: {e}")


    try:
        # Find all individual date list items (each <li> with class "events" represents a day)
        date_list_items = driver.find_elements(By.CSS_SELECTOR, "li.events") # Selects all <li> with class "events"
        logging.info(f"Found {len(date_list_items)} date list items.")

        if not date_list_items:
            details["Status"] = "N/A - No dates found"
            logging.warning("No date list items found for status determination.")
            return details # Return early or continue based on your preference

        has_future_performances = False
        has_past_performances = False
        has_active_performances = False # For performances scheduled for today

        current_datetime = datetime.datetime.now() # Get current date and time

        for list_item in date_list_items:
            try:
                # Extract the date string (e.g., "4 June 2025") from the <div class="date">
                date_div = list_item.find_element(By.CSS_SELECTOR, "h5.ot_eventDateTitle div.date")
                date_str = date_div.text.strip()
                logging.debug(f"Processing date: {date_str}")

                # Parse the date string. Format: "DD Month YYYY" (e.g., "4 June 2025")
                parsed_date = datetime.datetime.strptime(date_str, "%d %B %Y").date()

                # Find all time slots for this specific date
                time_slot_buttons = list_item.find_elements(By.CSS_SELECTOR, "div.ot_calendarTimeSlots button p")
                logging.debug(f"Found {len(time_slot_buttons)} time slots for {date_str}.")

                for time_p_tag in time_slot_buttons:
                    time_str = time_p_tag.text.strip()
                    logging.debug(f"Processing time: {time_str}")

                    try:
                        # Parse the time string (e.g., "7:00 pm"). Adjust format as needed.
                        # Using %I for 12-hour clock, %M for minute, %p for AM/PM
                        parsed_time = datetime.datetime.strptime(time_str, "%I:%M %p").time()

                        # Combine date and time for a full datetime object
                        performance_datetime = datetime.datetime.combine(parsed_date, parsed_time)

                        # Compare with current time
                        # Give a small buffer (e.g., 5 minutes) for "active" status around the current time
                        time_buffer = timedelta(minutes=5)

                        if performance_datetime > current_datetime + time_buffer:
                            has_future_performances = True
                        elif performance_datetime < current_datetime - time_buffer:
                            has_past_performances = True
                        else: # Within the buffer of current time
                            has_active_performances = True

                    except ValueError as ve:
                        logging.warning(f"Could not parse time string '{time_str}' for date '{date_str}': {ve}")
                        continue # Skip to the next time slot

            except Exception as e:
                logging.warning(f"Could not process date item or its times: {e}")
                continue # Skip to the next list item if there's an issue with a date

        # Determine overall status based on combined flags
        if has_active_performances:
            details["Status"] = "active"
        elif has_future_performances and not has_past_performances:
            details["Status"] = "upcoming"
        elif has_past_performances and not has_future_performances and not has_active_performances:
            details["Status"] = "closed"
        elif has_future_performances and has_past_performances:
            # If there are both past and future performances (but none currently active),
            # it implies it's an ongoing run, so "active" is still appropriate.
            details["Status"] = "active"
        else:
            details["Status"] = "N/A - Indeterminate" # Fallback if logic doesn't fit

        logging.info(f"Extracted Status: {details['Status']} (Active: {has_active_performances}, Future: {has_future_performances}, Past: {has_past_performances})")

    except Exception as e:
        logging.error(f"Error determining Status for production: {e}")
        details["Status"] = "N/A - Error"


    # Origin (original, revival, adaptation, co-production)
    try:
        # This is highly speculative and often needs manual review or very specific text on the page.
        # Look for keywords in the description or dedicated "about" sections.
        description_text = driver.find_element(By.CSS_SELECTOR, "prodDescriptionCollapsed").text.lower()
        if "adaptation" in description_text:
            details["Origin"] = "adaptation"
        elif "revival" in description_text:
            details["Origin"] = "revival"
        elif "co-production" in description_text:
            details["Origin"] = "co-production"
        else:
            details["Origin"] = "original" # Default
        logging.info(f"Extracted Origin: {details['Origin']}")
    except Exception as e:
        logging.warning(f"Could not infer Origin: {e}")

    # Market presence (US, UK)
    # This usually depends on the website's location or explicit text.
    # Given "Soho Playhouse", it's likely UK based, but could also host US productions.
    try:
        # If the website is primarily for UK, assume UK unless specified.
        # Look for explicit location information on the page.
        if "soho playhouse" in driver.current_url.lower(): # Basic check
             details["Market presence"] = "UK" # Assuming Soho Playhouse is in the UK
        logging.info(f"Extracted Market presence: {details['Market presence']}")
    except Exception as e:
        logging.warning(f"Could not determine Market presence: {e}")


    # Age of production (Years since the show first opened)
    # This is often not explicitly stated and might require external lookups or careful parsing of historical notes.
    try:
        # Look for phrases like "premiered in YEAR" or "first opened in YEAR"
        # This is a very challenging field to scrape accurately without consistent data.
        # As a placeholder, we'll set it to N/A unless a specific pattern is found.
        details["Age of production"] = "N/A" # Default
        # Example: If you found "Opened in 2010"
        # current_year = datetime.now().year
        # opened_year = 2010 # Extracted from text
        # details["Age of production"] = current_year - opened_year
        logging.info(f"Extracted Age of production: {details['Age of production']}")
    except Exception as e:
        logging.warning(f"Could not extract Age of production: {e}")

    return details


def main():
    # >>> IMPORTANT: Replace this with the actual base URL of the website's homepage or calendar page <<<
    base_url = "https://ci.ovationtix.com/35583/production/1152995" # THIS IS LIKELY WRONG, NEEDS TO BE THE CALENDAR PAGE BASE URL
    logging.warning(f"Ensure base_url '{base_url}' is the correct entry point to the calendar.")

    driver = setup_driver()
    if not driver:
        return

    all_events_data = []

    try:
        if navigate_to_calendar(driver, base_url):
            # Store the URL of the calendar page after successful navigation
            calendar_page_url = driver.current_url
            logging.info(f"Calendar page URL captured: {calendar_page_url}")

            # Get the initial count of event buttons. We'll re-find them inside the loop.
            # Using a temporary driver instance or quickly navigating to get count, then closing.
            # For robustness, we'll navigate back for each click.
            temp_driver_for_count = setup_driver()
            if not temp_driver_for_count:
                logging.error("Failed to setup temp driver for initial count. Exiting.")
                return
            try:
                temp_driver_for_count.get(calendar_page_url)
                WebDriverWait(temp_driver_for_count, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ot_prodListItem.ot_callout"))
                )
                temp_event_buttons = get_event_buttons(temp_driver_for_count)
                total_events_to_process = len(temp_event_buttons)
                logging.info(f"Detected {total_events_to_process} events to process from calendar.")
            except Exception as e:
                logging.error(f"Error getting initial event count: {e}")
                total_events_to_process = 0
            finally:
                temp_driver_for_count.quit()


            for i in range(total_events_to_process):
                logging.info(f"Processing event {i+1} of {total_events_to_process}...")
                driver.get(calendar_page_url) # Navigate back to the calendar page for each event
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ot_prodListItem.ot_callout")) # Wait for event containers to reappear
                )
                time.sleep(1) # Small pause for page rendering

                # Re-find ALL the buttons on the current (refreshed) calendar page
                current_event_buttons = get_event_buttons(driver)

                if i >= len(current_event_buttons):
                    logging.warning(f"Could not find button for event {i+1} after re-navigation. Skipping.")
                    continue # Skip to the next iteration if the element is unexpectedly gone

                event_button_to_click = current_event_buttons[i] # Get the specific button for this iteration

                try:
                    # Scroll the button into view to ensure it's clickable
                    driver.execute_script("arguments[0].scrollIntoView(true);", event_button_to_click)
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable(event_button_to_click))
                    event_button_to_click.click()
                    logging.info(f"Clicked 'See this event' button for event {i+1}.")
                    time.sleep(3) # Wait for the new event details page to load

                    event_url = driver.current_url # Get the URL of the newly loaded page
                    event_data = extract_event_details(driver, event_url)
                    all_events_data.append(event_data)
                    print(f"Collected data for: {event_data['Title']}")
                    logging.info(f"Successfully collected data for: {event_data['Title']}")

                except Exception as e:
                    logging.error(f"Error processing event {i+1} (button click or data extraction): {e}")
                    continue # Continue to the next event even if this one failed

    except Exception as e:
        logging.critical(f"An overarching error occurred during the main scraping process: {e}")
    finally:
        logging.info("Scraping process finished. Quitting driver.")
        driver.quit()

    # Save to CSV
    try:
        df = pd.DataFrame(all_events_data)
        df.to_csv("production_details.csv", index=False)
        logging.info("Data saved to production_details.csv")
        print("\nData saved to production_details.csv")
    except Exception as e:
        logging.error(f"Error saving to CSV: {e}")

    # Save to JSON
    try:
        with open("production_details.json", "w", encoding="utf-8") as f:
            json.dump(all_events_data, f, indent=4)
        logging.info("Data saved to production_details.json")
        print("Data saved to production_details.json")
    except Exception as e:
        logging.error(f"Error saving to JSON: {e}")

if __name__ == "__main__":
    main()