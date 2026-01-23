
import asyncio
import sys
import os
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mvno_system.crawlers.freet_crawler import FreeTCrawler

# Set up logging to console
logging.basicConfig(level=logging.INFO)

async def main():
    print("=== Starting FreeT Isolated Test ===")
    crawler = FreeTCrawler()
    
    # Run in test mode (limit 3 items)
    await crawler.crawl(test_mode=True, limit=3, headless=True)
    
    # Export
    crawler.export_excel()
    print("Test finished.")

if __name__ == "__main__":
    asyncio.run(main())
