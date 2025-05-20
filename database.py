import os
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class Database:
    def __init__(self):
        # Get database configuration from environment variables
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '3306')),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME', 'coinswap')
        }
        
        # Create backup directory if it doesn't exist
        self.backup_path = Path(os.getenv('DB_BACKUP_PATH', './backups'))
        self.backup_path.mkdir(parents=True, exist_ok=True)
        
        self.init_database()

    def get_connection(self):
        try:
            connection = mysql.connector.connect(**self.db_config)
            return connection
        except Error as e:
            print(f"Error connecting to MySQL Database: {e}")
            return None

    def init_database(self):
        connection = self.get_connection()
        if connection is None:
            return
        
        try:
            cursor = connection.cursor()
            
            # Create table for XE rates
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS xe_rates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME,
                    usd_eur DECIMAL(10, 6),
                    eur_usd DECIMAL(10, 6),
                    usd_gbp DECIMAL(10, 6),
                    usd_cny DECIMAL(10, 6),
                    usd_krw DECIMAL(10, 6)
                )
            ''')
            
            # Create table for Grinex order books
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS grinex_rates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME,
                    ask_weighted_price DECIMAL(10, 6),
                    bid_weighted_price DECIMAL(10, 6),
                    target_amount DECIMAL(10, 2)
                )
            ''')
            
            # Create table for Investing.com currency rates
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS investing_rates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    timestamp DATETIME,
                    usd_rub DECIMAL(10, 6),
                    eur_rub DECIMAL(10, 6),
                    status VARCHAR(50)
                )
            ''')
            
            connection.commit()
            
        except Error as e:
            print(f"Error creating tables: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def backup_database(self):
        """Create a timestamped backup of the database using mysqldump"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_path / f'coinswap_backup_{timestamp}.sql'
        
        # Construct mysqldump command
        command = f"mysqldump -h {self.db_config['host']} -P {self.db_config['port']} " \
                 f"-u {self.db_config['user']} -p{self.db_config['password']} " \
                 f"{self.db_config['database']} > {backup_file}"
        
        try:
            os.system(command)
            print(f"Database backup created: {backup_file}")
        except Exception as e:
            print(f"Error creating database backup: {e}")

    def save_xe_rates(self, rates: Dict[str, float]):
        connection = self.get_connection()
        if connection is None:
            return
        
        try:
            cursor = connection.cursor()
            cursor.execute('''
                INSERT INTO xe_rates (
                    timestamp, usd_eur, eur_usd, usd_gbp, usd_cny, usd_krw
                ) VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                datetime.now(),
                rates.get("1 USD = EUR"),
                rates.get("1 EUR = USD"),
                rates.get("1 USD = GBP"),
                rates.get("1 USD = CNY"),
                rates.get("1 USD = KRW")
            ))
            connection.commit()
            
        except Error as e:
            print(f"Error saving XE rates: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

    def save_grinex_rates(self, ask_price: float, bid_price: float, target_amount: float):
        connection = self.get_connection()
        if connection is None:
            return
        
        try:
            cursor = connection.cursor()
            cursor.execute('''
                INSERT INTO grinex_rates (
                    timestamp, ask_weighted_price, bid_weighted_price, target_amount
                ) VALUES (%s, %s, %s, %s)
            ''', (
                datetime.now(),
                ask_price,
                bid_price,
                target_amount
            ))
            connection.commit()
            
        except Error as e:
            print(f"Error saving Grinex rates: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                
    def save_investing_rates(self, rates: Dict[str, float], status: str = "OK"):
        connection = self.get_connection()
        if connection is None:
            return
        
        try:
            cursor = connection.cursor()
            cursor.execute('''
                INSERT INTO investing_rates (
                    timestamp, usd_rub, eur_rub, status
                ) VALUES (%s, %s, %s, %s)
            ''', (
                datetime.now(),
                rates.get("USD/RUB"),
                rates.get("EUR/RUB"),
                status
            ))
            connection.commit()
            
        except Error as e:
            print(f"Error saving Investing rates: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close() 