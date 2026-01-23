import asyncio
import logging
import sys
import os
import pandas as pd
from datetime import datetime

# Project root setup
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mvno_system')))
except:
    pass

from core.platform_loader import PlatformLoader

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger('moyo_test')

async def main():
    loader = PlatformLoader()
    
    # Manually select Moyo
    platforms = [('moyo', {'name': '모요', 'base_url': 'https://www.moyoplan.com', 'enabled': True})]
    
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    print(f"=== Starting Moyo Isolated Test (Session: {session_id}) ===")
    
    crawler = loader.get_crawler('moyo')
    if crawler:
        crawler.set_session(session_id)
        print("Crawler loaded. Starting crawl...")
        try:
           # Using headless=True to match run_one_excel_test.py
           await crawler.crawl(headless=True, test_mode=True, limit=1)
           print("Crawl finished.")
           if crawler.results:
               print(f"Success! Found {len(crawler.results)} items.")
               print(crawler.results[0])
           else:
               print("Failed. No items found.")
        except Exception as e:
            print(f"Exception during crawl: {e}")
    else:
        print("Failed to load Moyo crawler.")

if __name__ == "__main__":
    asyncio.run(main())
