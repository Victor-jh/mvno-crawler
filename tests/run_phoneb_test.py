
import asyncio
import os
from mvno_system.crawlers.phoneb_crawler import PhonebCrawler

async def main():
    print("=== Starting PhoneB Isolated Test (Session: Verify Detail & Screenshot) ===")
    
    crawler = PhonebCrawler()
    print("Crawler loaded. Starting crawl...")
    
    # Run with limit=3 and test_mode=True
    await crawler.crawl(headless=True, limit=3, test_mode=True)
    
    print("Crawl finished.")
    
    # Check results
    if crawler.results:
        print(f"Success! Found {len(crawler.results)} items.")
        print(f"First item: {crawler.results[0]}")
        
        # Check screenshot path
        if 'screenshot_path' in crawler.results[0]:
            print(f"Screenshot saved to: {crawler.results[0]['screenshot_path']}")
            
        # Export Excel
        saved_file = crawler.export_excel()
        if saved_file:
            print(f"Excel saved to: {saved_file}")
            
    else:
        print("No items found.")
        
if __name__ == "__main__":
    asyncio.run(main())
