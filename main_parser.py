import requests
import json
import time
import random
import os
from bs4 import BeautifulSoup
from datetime import datetime
from database import Database
from typing import Tuple, List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CombinedParser:
    def __init__(self):
        self.db = Database()
        self.grinex_url = os.getenv('GRINEX_URL', 'https://grinex.io/trading/usdtrub')
        self.target_amount = float(os.getenv('TARGET_AMOUNT', '30000.0'))
        self.min_delay = float(os.getenv('MIN_DELAY', '45'))
        self.max_delay = float(os.getenv('MAX_DELAY', '60'))
        
    def fetch_xe_rates(self) -> Dict[str, float]:
        headers = {
            'authorization': 'Basic bG9kZXN0YXI6cHVnc25heA==',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        }

        try:
            response = requests.get('https://www.xe.com/api/protected/midmarket-converter/', headers=headers)
            response.raise_for_status()
            data = response.json()
            rates = data["rates"]

            result = {
                "1 EUR = USD": 1 / rates["EUR"],
                "1 USD = EUR": rates["EUR"],
                "1 USD = GBP": rates["GBP"],
                "1 USD = CNY": rates["CNY"],
                "1 USD = KRW": rates["KRW"]
            }
            
            print(f"\n--- XE Rates at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
            for key, value in result.items():
                print(f"{key}: {value:.6f}")
                
            return result

        except Exception as e:
            print(f"XE Error: {str(e)}")
            return {}

    def fetch_grinex_books(self) -> Tuple[List[Dict], List[Dict]]:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        }

        try:
            response = requests.get(self.grinex_url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            for script in soup.find_all('script'):
                if 'window.gon' in script.text:
                    raw_json = script.text.replace('window.gon = ', '').strip()
                    if raw_json.endswith(';'):
                        raw_json = raw_json[:-1]
                    gon_data = json.loads(raw_json)
                    usdtrub = gon_data.get('exchangers', {}).get('usdtrub', {})
                    return usdtrub.get('ask', []), usdtrub.get('bid', [])

            raise ValueError("Unable to find order book data.")
        except Exception as e:
            print(f"Grinex Error: {str(e)}")
            return [], []

    def calculate_weighted_price(self, orders: List[Dict], target_amount: float, order_type: str) -> Optional[float]:
        if not orders:
            return None
            
        accumulated = 0.0
        total_rub = 0.0

        for order in orders:
            price = float(order['price'])
            volume = float(order['volume'])
            amount = float(order['amount'])

            if accumulated + volume <= target_amount:
                total_rub += amount
                accumulated += volume
            else:
                remaining = target_amount - accumulated
                partial_rub = remaining * price
                total_rub += partial_rub
                accumulated += remaining
                break

        if accumulated < target_amount:
            print(f"❗ Not enough volume in the {order_type} order book.")
            return None

        average_price = total_rub / target_amount
        print(f"{order_type.upper()} weighted average rate: {average_price:.4f} RUB/USDT")
        return average_price

    def run(self):
        print("Starting combined parser...")
        print(f"Target amount: {self.target_amount} USDT")
        print(f"Delay range: {self.min_delay}-{self.max_delay} seconds")
        
        while True:
            try:
                # Random delay between min_delay and max_delay seconds
                delay = random.uniform(self.min_delay, self.max_delay)
                
                # Fetch and save XE rates
                xe_rates = self.fetch_xe_rates()
                if xe_rates:
                    self.db.save_xe_rates(xe_rates)

                # Fetch and save Grinex rates
                ask_orders, bid_orders = self.fetch_grinex_books()
                ask_price = self.calculate_weighted_price(ask_orders, self.target_amount, "ask")
                bid_price = self.calculate_weighted_price(bid_orders, self.target_amount, "bid")
                
                if ask_price is not None and bid_price is not None:
                    self.db.save_grinex_rates(ask_price, bid_price, self.target_amount)
                
                # Create database backup every 24 hours (86400 seconds)
                if int(time.time()) % 86400 < 60:  # Check if we're in the first minute of the day
                    self.db.backup_database()
                
                print(f"\nNext update in {delay:.2f} seconds...")
                time.sleep(delay)
                
            except Exception as e:
                print(f"Error in main loop: {str(e)}")
                time.sleep(60)  # Wait a minute on error before retrying

if __name__ == "__main__":
    parser = CombinedParser()
    parser.run() 