import requests
import json
import time
from bs4 import BeautifulSoup

def fetch_order_books(url: str) -> tuple[list[dict], list[dict]]:
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    }

    response = requests.get(url, headers=headers)
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

def calculate_weighted_price(orders: list[dict], target_amount: float, order_type: str) -> float | None:
    accumulated = 0.0
    total_rub = 0.0
    print(f"\n=== {'Buying' if order_type == 'ask' else 'Selling'} {target_amount} USDT ===")

    for order in orders:
        price = float(order['price'])
        volume = float(order['volume'])  # USDT
        amount = float(order['amount'])  # RUB

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
        print("❗ Not enough volume in the order book.")
        return None

    average_price = total_rub / target_amount
    print(f"Weighted average rate: {average_price:.4f} RUB/USDT")
    return average_price

if __name__ == "__main__":
    URL = 'https://grinex.io/trading/usdtrub'
    TARGET_AMOUNT = 30000.0

    while True:
        try:
            ask_orders, bid_orders = fetch_order_books(URL)
            calculate_weighted_price(ask_orders, TARGET_AMOUNT, order_type="ask")
            calculate_weighted_price(bid_orders, TARGET_AMOUNT, order_type="bid")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(60)  # Wait for 60 seconds before the next iteration
