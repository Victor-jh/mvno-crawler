import asyncio
import logging
import sys
import os
from datetime import datetime

# Project root setup
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mvno_system')))
except:
    pass

from core.platform_loader import PlatformLoader

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger('toss_test')

async def main():
    loader = PlatformLoader()
    
    # Manually select Toss
    crawler = loader.get_crawler('tossmobile')
    if crawler:
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        print(f"=== Starting Toss Isolated Test (Session: {session_id}) ===")
        crawler.set_session(session_id)
        
        print("Crawler loaded. Starting crawl...")
        try:
           # Test with small limit
           await crawler.crawl(headless=True, test_mode=True)
           print("Crawl finished.")
           if crawler.results:
               print(f"Success! Found {len(crawler.results)} items.")
               print(f"First item: {crawler.results[0]}")
               print(f"Screenshot path: {crawler.results[0].get('screenshot_path')}")
               
               # Save Excel
               excel_path = crawler.export_excel()
               print(f"Excel saved to: {excel_path}")
           else:
               print("Failed. No items found.")
        except Exception as e:
            print(f"Exception during crawl: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Failed to load Toss crawler.")

if __name__ == "__main__":
    asyncio.run(main())
