import threading
import time
import random
import os
from dotenv import load_dotenv
from datetime import datetime
from database import Database

# Import parsers
from main_parser import CombinedParser
from investing_parser import InvestingParser

# Load environment variables
load_dotenv()

class ParserManager:
    def __init__(self):
        self.db = Database()
        self.min_delay = float(os.getenv('MIN_DELAY', '45'))
        self.max_delay = float(os.getenv('MAX_DELAY', '60'))
        
    def start_parsers(self):
        """Start all parsers in separate threads"""
        print(f"Starting all parsers at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Create and start thread for main parser (XE and Grinex)
        main_thread = threading.Thread(target=self._run_main_parser, daemon=True)
        main_thread.start()
        
        # Create and start thread for investing parser
        investing_thread = threading.Thread(target=self._run_investing_parser, daemon=True)
        investing_thread.start()
        
        # Check for database backup in main thread
        self._manage_backup()
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nShutting down parsers...")
    
    def _run_main_parser(self):
        """Run the main parser (XE and Grinex)"""
        parser = CombinedParser()
        parser.run()
    
    def _run_investing_parser(self):
        """Run the investing.com parser"""
        # Add a small delay to stagger the parsers
        time.sleep(random.uniform(5, 15))
        parser = InvestingParser()
        parser.run()
    
    def _manage_backup(self):
        """Manage database backups in main thread"""
        while True:
            # Check if we're in the first minute of a day
            if int(time.time()) % 86400 < 60:
                self.db.backup_database()
            
            # Check again in 10 minutes
            time.sleep(600)

if __name__ == "__main__":
    manager = ParserManager()
    manager.start_parsers() 