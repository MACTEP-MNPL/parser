import cloudscraper
import re
import random
import time
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

# Случайные user-agents для маскировки
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/112.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
]

# Валютные пары: (url, label, min, max, invert)
CURRENCY_PAIRS = [
    ("https://www.investing.com/currencies/eur-usd", "1 EUR = USD", 0.5, 2.0, False),
    ("https://www.investing.com/currencies/eur-usd", "1 USD = EUR", 0.5, 2.0, True),
    ("https://www.investing.com/currencies/usd-gbp", "1 USD = GBP", 0.5, 2.0, False),
    ("https://www.investing.com/currencies/usd-cny", "1 USD = CNY", 4, 10, False),
    ("https://www.investing.com/currencies/usd-krw", "1 USD = KRW", 500, 2000, False)
]

# Сохраняем последнее удачное значение
last_successful = {}

def get_random_headers():
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

def extract_price(html: str, min_val: float, max_val: float) -> float | None:
    match = re.search(r'"last"\s*:\s*([\d.]+)', html)
    if match:
        value = float(match.group(1))
        if min_val < value < max_val:
            return value
    soup = BeautifulSoup(html, "html.parser")
    spans = soup.find_all("span", string=re.compile(r"^\d{1,5}\.\d{1,6}$"))
    for span in spans:
        try:
            val = float(span.get_text(strip=True).replace(",", "."))
            if min_val < val < max_val:
                return val
        except:
            continue
    return None

def fetch_and_print(pair):
    url, label, min_val, max_val, invert = pair
    delay = random.randint(8, 12)

    for attempt in range(1, 4):  # до 3 попыток
        headers = get_random_headers()
        try:
            scraper = cloudscraper.create_scraper(delay=delay, browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'mobile': False
            })
            res = scraper.get(url, headers=headers)
            res.raise_for_status()

            price = extract_price(res.text, min_val, max_val)
            if price:
                result = 1 / price if invert else price
                rounded = round(result, 6)
                last_successful[label] = rounded
                print(f"{label}: {rounded}")
                return
            else:
                print(f"{label}: ❌ курс не найден. Попытка {attempt}/3")
        except Exception as e:
            print(f"{label}: ❌ ошибка — {e}. Попытка {attempt}/3")

        time.sleep(random.randint(3, 5))

    # Все попытки провалены — используем прошлое значение
    if label in last_successful:
        print(f"{label}: ⚠️ не удалось получить, используем предыдущее значение: {last_successful[label]}")
    else:
        print(f"{label}: ❌ окончательная ошибка после 3 попыток. Нет прошлых данных.")

def run_loop():
    while True:
        now = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n--- Investing.com Rates at {now} (MSK) ---\n")
        for pair in CURRENCY_PAIRS:
            fetch_and_print(pair)
        time.sleep(60)

if __name__ == "__main__":
    run_loop()
