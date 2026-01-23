from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio
import re

class AsiaMobileCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('asiamobile')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("아시아모바일 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                base_url = self.selectors.get('url', "https://asiamobile.kr/view/price/pricePlan.aspx")
                await page.goto(base_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # Tabs to crawl: Postpaid mainly, maybe Prepaid too if valid
                tabs = [
                    {'name': 'Postpaid', 'selector': '#btnPostpay'},
                    # {'name': 'Prepaid', 'selector': '#btnPrepay'} # Optional, can enable if needed
                ]
                
                total_items = 0
                
                for tab in tabs:
                    self.logger.info(f"[{tab['name']}] 탭 진입")
                    
                    # Click Tab
                    try:
                        tab_el = page.locator(tab['selector'])
                        if await tab_el.is_visible():
                            await tab_el.click()
                            await page.wait_for_timeout(2000)
                    except Exception as e:
                        self.logger.error(f"탭 클릭 실패 ({tab['name']}): {e}")
                        continue
                        
                    # Click 'All' filter to see all carriers
                    try:
                        all_btn = page.locator('#btnAll')
                        if await all_btn.is_visible():
                            await all_btn.click()
                            await page.wait_for_timeout(2000)
                    except Exception as e:
                        self.logger.warning(f"전체 필터 클릭 실패: {e}")
                    
                    # Scroll down multiple times to load all
                    for i in range(5):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(1000)
                        
                    # Extract items
                    items = await page.evaluate(f"""(tabName) => {{
                        const list = [];
                        const items = document.querySelectorAll('div.plan');
                        
                        items.forEach(item => {{
                            const result = {{}};
                            
                            // Carrier
                            const carrierEl = item.querySelector('div > p:first-child');
                            result.carrier = carrierEl ? 'Asia Mobile (' + carrierEl.innerText.trim() + ')' : 'Asia Mobile';
                            
                            // Plan Name
                            const nameEl = item.querySelector('ul > li:first-child > p');
                            result.plan_name = nameEl ? nameEl.innerText.trim() : '';
                            
                            // Details
                            const dataEl = item.querySelector('ul > li:first-child > ul > li:nth-child(1) > p');
                            const voiceEl = item.querySelector('ul > li:first-child > ul > li:nth-child(2) > p');
                            
                            result.data = dataEl ? dataEl.innerText.trim() : '';
                            result.voice = voiceEl ? voiceEl.innerText.trim() : '';
                            
                            // Price Parsing
                            // The price container is the 2nd li
                            const priceLi = item.querySelector('ul > li:nth-child(2)');
                            let priceText = '0';
                            
                            if (priceLi) {{
                                const pTags = priceLi.querySelectorAll('p');
                                // Usually:
                                // p[0]: Original Price (정가 ...)
                                // p[1]: Promo Price (월 ...원) if exists
                                // p[2]: Note
                                
                                // Strategy: Look for numbers in p tags.
                                // If multiple numbers, usually the smallest is promo, or look for specific styles?
                                // Let's try to identify promo lines vs original.
                                
                                // Simple logic:
                                // If p[1] exists and has '월' and numbers, use it.
                                // Else use p[0].
                                
                                if (pTags.length >= 2) {{
                                    const p1_text = pTags[1].innerText.trim();
                                    if (p1_text.includes('월')) {{
                                        priceText = p1_text;
                                    }} else {{
                                        priceText = pTags[0].innerText.trim();
                                    }}
                                }} else if (pTags.length == 1) {{
                                    priceText = pTags[0].innerText.trim();
                                }}
                            }}
                            
                            result.price = priceText;
                            list.push(result);
                        }});
                        
                        return list;
                    }}""", tab['name'])
                    
                    self.logger.info(f"[{tab['name']}] 수집된 요금제: {len(items)}개")
                    
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
