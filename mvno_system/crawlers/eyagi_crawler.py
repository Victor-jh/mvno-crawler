from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio

class EyagiCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('eyagi')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("이야기모바일 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                # Use a URL that shows plans initially
                base_url = self.selectors.get('url', "https://www.eyagi.co.kr/shop/plan/list.php?tag=pick")
                
                # Carriers to crawl
                carriers = ['SKT', 'KT', 'LGU+']
                
                total_items = 0
                
                for carrier in carriers:
                    # Construct URL with network filter provided by analysis (check if query param works, else click)
                    # Analysis showed hash filters like #SKT. Usually this means JS filter.
                    # Let's go to base URL first.
                    if carrier == 'SKT': 
                        await page.goto(base_url, wait_until='domcontentloaded')
                    
                    # Click filter
                    try:
                        # Find filter link by text or href
                        filter_selector = f"a:has-text('{carrier}')" # broad selector, refine?
                        # Or specifically the tab links
                        # Analysis: a containing #SKT
                        # Let's try to find the specific filter button
                        
                        # Wait for page load
                        await page.wait_for_timeout(2000)
                        
                        # Click filter
                        # Browser agent found filters use onclick="location.href='list.php?tag=skt'"
                        # We can try to click them by text or specific attribute
                        
                        # Try finding by text first as it is most reliable for tabs
                        filter_btn = page.locator(f"a").filter(has_text=carrier).first
                        
                        if await filter_btn.is_visible():
                            await filter_btn.click()
                            self.logger.info(f"필터 클릭: {carrier}")
                            await page.wait_for_timeout(3000) # Wait for reload
                        else:
                             # Try partial match for "SKT", "KT", "LGU+" in href/onclick if text fails
                             # Mapping carrier names to tag values if needed
                             tag_val = ''
                             if carrier == 'SKT': tag_val = 'skt'
                             elif carrier == 'KT': tag_val = 'kt'
                             elif carrier == 'LGU+': tag_val = 'lgt'
                             
                             if tag_val:
                                 filter_btn = page.locator(f"a[onclick*='tag={tag_val}']").first
                                 if await filter_btn.is_visible():
                                     await filter_btn.click()
                                     self.logger.info(f"필터 클릭(tag): {carrier}")
                                     await page.wait_for_timeout(3000)
                                 else:
                                     self.logger.warning(f"필터 버튼 찾을 수 없음: {carrier}")

                    except Exception as e:
                        self.logger.error(f"필터 클릭 중 에러 ({carrier}): {e}")
                        continue

                    # Scroll to load all
                    # Infinite scroll
                    last_height = await page.evaluate("document.body.scrollHeight")
                    while True:
                        if kwargs.get('test_mode'): 
                             # In test mode, maybe scroll just once or twice
                             await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                             await page.wait_for_timeout(2000)
                             break
                        
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(2000)
                        new_height = await page.evaluate("document.body.scrollHeight")
                        if new_height == last_height:
                            break
                        last_height = new_height
                        
                        # Safety break for huge lists
                        if total_items > 500: # just safety
                            break

                    await page.wait_for_timeout(1000)
                    
                    # Extract items
                    items = await page.evaluate(f"""(network) => {{
                        const list = [];
                        const items = document.querySelectorAll('a.plan-item');
                        
                        items.forEach(item => {{
                            // Check visibility (some might be hidden by filter)
                            if (item.offsetParent === null) return;
                        
                            const result = {{}};
                            
                            // Carrier Badge - sometimes inside item
                            const badge = item.querySelector('span.badge.mno');
                            let carrierName = badge ? badge.innerText.trim() : network;
                            result.carrier = 'Eyagi (' + carrierName + ')';
                            
                            // Plan Name
                            // Corrected: .name (p class="name") or .item-title .name
                            let nameEl = item.querySelector('.name');
                            if (!nameEl) nameEl = item.querySelector('.item-title p');
                            result.plan_name = nameEl ? nameEl.innerText.trim() : '';
                            
                            // Data
                            const dataEl = item.querySelector('.spec-box .data p.free');
                            result.data = dataEl ? dataEl.innerText.trim() : '';
                            
                            // Voice
                            const voiceEl = item.querySelector('.spec-box .call p.free');
                            result.voice = voiceEl ? voiceEl.innerText.trim() : '';
                            
                            // Price
                            // Try promo first
                            const promoEl = item.querySelector('.price-box .current-price');
                            const basicEl = item.querySelector('.price-box .basic-price');
                            
                            // Getting text, removing '월', ','
                            let priceText = '0';
                            if (promoEl) priceText = promoEl.innerText;
                            else if (basicEl) priceText = basicEl.innerText;
                            
                            result.price = priceText.trim();
                            
                            list.push(result);
                        }});
                        
                        return list;
                    }}""", carrier)
                    
                    self.logger.info(f"[{carrier}] 수집된 요금제: {len(items)}개")
                    
                    valid_count = 0
                    for item in items:
                        limit = kwargs.get('limit', 0)
                        if limit > 0 and valid_count >= limit:
                            break
                        if kwargs.get('test_mode') and limit == 0 and valid_count >= 3:
                            break
                        
                        if not item['plan_name']:
                            continue

                        valid_count += 1
                        total_items += 1
                        
                        plan_data = {
                            'platform': self.platform_key,
                            'carrier': item.get('carrier'),
                            'plan_name': item.get('plan_name'),
                            'price': item.get('price'),
                            'data_raw': item.get('data'),
                            'url': base_url, 
                            'details': item
                        }
                        
                        plan_data['screenshot_path'] = 'captured_in_list'
                        
                        self.save_plan(plan_data)
                        self.logger.info(f"수집: {plan_data['carrier']} - {plan_data['plan_name']}")
                
                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()
