import cloudscraper
import re
import random
import time
import os
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from database import Database
from typing import Dict, Optional

# Load environment variables
load_dotenv()

# Random user agents for disguise
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/112.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
]

# Currency pairs: (url, label, min, max, invert)
CURRENCY_PAIRS = [
    ("https://www.investing.com/currencies/usd-rub", "USD/RUB", 50, 200, False),
    ("https://www.investing.com/currencies/eur-rub", "EUR/RUB", 50, 220, False)
]

class InvestingParser:
    def __init__(self):
        self.db = Database()
        self.min_delay = float(os.getenv('MIN_DELAY', '45'))
        self.max_delay = float(os.getenv('MAX_DELAY', '60'))
        self.last_successful = {}
        
    def get_random_headers(self):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.investing.com/",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "keep-alive",
        }

    def extract_price(self, html: str, min_val: float, max_val: float) -> Optional[float]:
        # For *USD/RUB and EUR/RUB, we expect values between 50-220
        
        # Try to extract from JSON structure
        match = re.search(r'"last"\s*:\s*([\d.]+)', html)
        if match:
            value = float(match.group(1))
            if min_val < value < max_val:
                return value
                
        # Try to extract from HTML
        soup = BeautifulSoup(html, "html.parser")
        spans = soup.find_all("span", string=re.compile(r"^\d{2,3}\.\d{1,6}$"))
        for span in spans:
            try:
                val = float(span.get_text(strip=True).replace(",", "."))
                if min_val < val < max_val:
                    return val
            except:
                continue
        return None

    def fetch_rate(self, pair):
        url, label, min_val, max_val, invert = pair
        delay = random.randint(8, 12)

        for attempt in range(1, 4):  # Up to 3 attempts
            headers = self.get_random_headers()
            try:
                scraper = cloudscraper.create_scraper(delay=delay, browser={
                    'browser': 'chrome',
                    'platform': 'darwin',
                    'mobile': False
                })
                res = scraper.get(url, headers=headers)
                res.raise_for_status()

                price = self.extract_price(res.text, min_val, max_val)
                if price:
                    result = 1 / price if invert else price
                    rounded = round(result, 6)
                    self.last_successful[label] = rounded
                    print(f"{label}: {rounded}")
                    return rounded
                else:
                    print(f"{label}: ❌ Rate not found. Attempt {attempt}/3")
            except Exception as e:
                print(f"{label}: ❌ Error — {e}. Attempt {attempt}/3")

            time.sleep(random.randint(3, 5))

        # All attempts failed - use previous value
        if label in self.last_successful:
            print(f"{label}: ⚠️ Failed to retrieve, using previous value: {self.last_successful[label]}")
            return self.last_successful[label]
        else:
            print(f"{label}: ❌ Final error after 3 attempts. No previous data.")
            return None

    def get_rates(self) -> Dict[str, float]:
        now = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n--- Investing.com Currency Rates at {now} (MSK) ---\n")
        
        rates = {}
        status = "OK"
        missing_count = 0
        
        for pair in CURRENCY_PAIRS:
            _, label, _, _, _ = pair
            rate = self.fetch_rate(pair)
            rates[label] = rate
            
            if rate is None:
                missing_count += 1
                
        # Set status based on results
        if missing_count == len(CURRENCY_PAIRS):
            status = "FAILED"
        elif missing_count > 0:
            status = "PARTIAL"
            
        return rates, status

    def run(self):
        print("Starting Investing.com currency parser...")
        print(f"Delay range: {self.min_delay}-{self.max_delay} seconds")
        
        while True:
            try:
                # Get rates and save to database
                rates, status = self.get_rates()
                
                # Only save if we have data
                if status != "FAILED":
                    self.db.save_investing_rates(rates, status)
                
                # Random delay between min_delay and max_delay seconds
                delay = random.uniform(self.min_delay, self.max_delay)
                print(f"\nNext update in {delay:.2f} seconds...")
                time.sleep(delay)
                
            except Exception as e:
                print(f"Error in main loop: {str(e)}")
                time.sleep(60)  # Wait a minute on error before retrying

if __name__ == "__main__":
    parser = InvestingParser()
    parser.run() 