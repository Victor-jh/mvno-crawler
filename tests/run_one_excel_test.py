import asyncio
import logging
import sys
import os
import pandas as pd
from datetime import datetime

# Project root setup
try:
    # Point to ../mvno_system
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mvno_system')))
except:
    pass

from core.platform_loader import PlatformLoader

# Configure logging
logging.basicConfig(level=logging.ERROR) # Helper logging
logger = logging.getLogger('one_excel_test')

async def process_platform(sem, loader, key, data, session_id):
    async with sem:
        platform_name = data.get('name', key)
        # print(f"[{platform_name}] Queueing...")
        try:
            crawler = loader.get_crawler(key)
            if not crawler:
                print(f"!!! [{platform_name}] Failed to load crawler")
                return (platform_name, [])
            
            crawler.set_session(session_id)
            # Use headless=True for parallel execution stability
            await crawler.crawl(headless=True, test_mode=True, limit=1)
            
            if crawler.results:
                print(f"V [{platform_name}] Success: {len(crawler.results)} items")
                return (platform_name, crawler.results)
            else:
                print(f"X [{platform_name}] process finished but no items")
                return (platform_name, [])
                
        except Exception as e:
            print(f"!!! [{platform_name}] Error: {e}")
            return (platform_name, [])

async def main():
    loader = PlatformLoader()
    platforms = loader.get_enabled_platforms()
    
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print(f"=== Starting Concurrent One-Excel Test (Session: {session_id}) ===")
    print(f"Target: {len(platforms)} platforms. Max concurrency: 4")
    
    sem = asyncio.Semaphore(4) 
    tasks = []
    
    for key, data in platforms:
        tasks.append(process_platform(sem, loader, key, data, session_id))
        
    results_list = await asyncio.gather(*tasks)
    
    # Filter empty results
    all_data = {name: res for name, res in results_list if res}
    
    print("\n=== All Crawling Completed. Saving Combined Excel... ===")
    
    if all_data:
        session_root = os.path.join("storage", "sessions", session_id)
        os.makedirs(session_root, exist_ok=True)
        
        output_path = os.path.join(session_root, f"combined_results_{session_id}.xlsx")
        
        try:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                for p_name, results in all_data.items():
                    df = pd.DataFrame(results)
                    if 'details' in df.columns:
                        df = df.drop(columns=['details'])
                    
                    # Sanitize sheet name
                    safe_name = "".join(c for c in p_name if c not in r":\/?*[]")
                    safe_name = safe_name[:31]
                    
                    df.to_excel(writer, sheet_name=safe_name, index=False)
            
            print(f"SUCCESS: Combined Excel saved at:\n{output_path}")
            print(f"Total Sheets: {len(all_data)}")
            
        except Exception as e:
            print(f"!!! Failed to save combined Excel: {e}")
    else:
        print("!!! No data collected from any platform.")

if __name__ == "__main__":
    asyncio.run(main())
