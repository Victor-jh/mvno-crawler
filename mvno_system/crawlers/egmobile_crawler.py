from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio

class EgMobileCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('egmobile')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("이지모바일 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                base_url = self.selectors.get('url', "https://www.egmobile.co.kr/charge/list")
                
                # Carriers to crawl (KT, LG U+) - Query param te=kt / te=lg
                carriers = [
                    {'name': 'KT', 'param': 'kt'},
                    {'name': 'LGU+', 'param': 'lg'}
                ]
                
                total_items = 0
                
                for carrier in carriers:
                    self.logger.info(f"[{carrier['name']}] 요금제 수집 시작")
                    
                    target_url = f"{base_url}?te={carrier['param']}"
                    await page.goto(target_url, wait_until='domcontentloaded')
                    await page.wait_for_timeout(2000)
                    
                    # No pagination found in analysis, assuming all on one page or infinite scroll (but analysis said "No infinite scroll")
                    # Let's scroll down a bit just in case
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)
                    
                    # Extract items
                    items = await page.evaluate(f"""(network) => {{
                        const list = [];
                        // Select rows in the table
                        // Updated to 'div.rate_table table tbody tr'
                        const rows = document.querySelectorAll('div.rate_table table tbody tr');
                        
                        rows.forEach(tr => {{
                            const result = {{}};
                            result.carrier = 'EG Mobile (' + network + ')';
                            
                            // Plan Name - 1st col
                            const nameTd = tr.querySelector('td:nth-child(1)');
                            result.plan_name = nameTd ? nameTd.innerText.trim() : '';
                            
                            // Data - 2nd col
                            const dataTd = tr.querySelector('td:nth-child(2)');
                            result.data = dataTd ? dataTd.innerText.trim() : '';
                            
                            // Voice - 3rd col
                            const voiceTd = tr.querySelector('td:nth-child(3)');
                            result.voice = voiceTd ? voiceTd.innerText.trim() : '';
                            
                            // Price - 5th col
                            // Promo is usually strong, Original is span:first-child
                            const priceTd = tr.querySelector('td:nth-child(5)');
                            
                            let priceText = '0';
                            if (priceTd) {{
                                const promoEl = priceTd.querySelector('strong');
                                const originalEl = priceTd.querySelector('span:first-child');
                                
                                // Logic: if promo exists, use it? Or capture both?
                                // Our standard is just one price field, usually promo if available.
                                if (promoEl) priceText = promoEl.innerText;
                                else if (originalEl) priceText = originalEl.innerText;
                                else priceText = priceTd.innerText; // Fallback
                            }}
                            
                            result.price = priceText.trim();
                            
                            list.push(result);
                        }});
                        
                        return list;
                    }}""", carrier['name'])
                    
                    self.logger.info(f"[{carrier['name']}] 수집된 요금제: {len(items)}개")
                    
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
                            'url': target_url, 
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
