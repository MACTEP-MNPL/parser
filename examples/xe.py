import requests
import time

def get_xe_currency_rates():
    headers = {
        'authorization': 'Basic bG9kZXN0YXI6cHVnc25heA==',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    }

    try:
        response = requests.get('https://www.xe.com/api/protected/midmarket-converter/', headers=headers)
        response.raise_for_status()
        data = response.json()

        rates = data["rates"]

        return {
            "1 EUR = USD": 1 / rates["EUR"],
            "1 USD = EUR": rates["EUR"],
            "1 USD = GBP": rates["GBP"],
            "1 USD = CNY": rates["CNY"],
            "1 USD = KRW": rates["KRW"]
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except KeyError:
        return {"error": "Unexpected data format"}
    except Exception as e:
        return {"error": f"{str(e)}"}

if __name__ == "__main__":
    while True:
        rates = get_xe_currency_rates()
        print(f"\n--- Rates at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        if "error" not in rates:
            for key, value in rates.items():
                print(f"{key}: {value:.6f}")
        else:
            print(rates["error"])
        time.sleep(60)  # wait 60 seconds before the next request
