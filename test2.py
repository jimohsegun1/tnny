import os
import time
import json
import hashlib
import logging
import schedule
import smtplib
import random
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import requests


# --- Setup logging ---
if not os.path.exists('log'):
    os.makedirs('log')
log_file = os.path.join('log', 'scrape.log')

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_and_print(message):
    print(message)
    logging.info(message)


def scrape_shows():
    start_time = datetime.now()
    log_and_print("🚀 Starting ovationtix.com/35583 Scraper...")

    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument('--disable-images')
    options.add_argument('--disable-javascript')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36')

    driver = uc.Chrome(options=options)
    driver.get('https://ci.ovationtix.com/35583')
    time.sleep(random.uniform(2, 4))

    soup = BeautifulSoup(driver.page_source, 'lxml')
    cards = soup.find_all('li', class_='ot_prodListItem ot_callout')

    links = []

    for idx, item in enumerate(cards):
        try:
            # Extract title
            title_tag = item.find('h1')
            title = title_tag.text.strip() if title_tag else "N/A"

            # Extract background image from style
            image_div = item.find('div', class_='ot_prodImg')
            style = image_div.get('style', '') if image_div else ''
            match = re.search(r'url\(&quot;(.+?)&quot;\)', style)
            image_url = match.group(1) if match else "N/A"

            # Click button to get event link
            button = driver.find_elements(By.CSS_SELECTOR, 'button.ot_prodInfoButton')[idx]
            driver.execute_script("arguments[0].scrollIntoView(true);", button)
            time.sleep(1)
            button.click()
            time.sleep(random.uniform(2, 4))

            link = driver.current_url

            links.append({
                'title': title,
                'image': image_url,
                'Link': link
            })

            log_and_print(f"✅ Fetched: {title} | {Link}")

            driver.back()
            time.sleep(random.uniform(2, 4))
            soup = BeautifulSoup(driver.page_source, 'lxml')
            cards = soup.find_all('li', class_='ot_prodListItem ot_callout')

        except Exception as e:
            log_and_print(f"❌ Error processing card #{idx}: {e}")



        






scrape_shows()

# --- Scheduling ---
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true', help='Run scraper once and exit')
    args = parser.parse_args()

    if args.once:
        scrape_shows()
    else:
        schedule.every(6).hours.do(scrape_shows)
        log_and_print("🕒 Scheduler started. Scraper will run every 6 hours.")
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    main()