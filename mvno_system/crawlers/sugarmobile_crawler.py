from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio

class SugarMobileCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('sugarmobile')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("슈가모바일 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                base_url = self.selectors.get('url', "https://www.sugarmobile.co.kr/rate_plan.do")
                
                # Categories to crawl
                # T014: Sugar Deal / T006: LTE / T005: 5G
                # Skipping Prepaid (T004) for now as typical requirement is postpaid/unlimited focus
                categories = [
                    {'name': 'Sugar Deal', 'type': 'T014'},
                    {'name': 'LTE', 'type': 'T006'},
                    {'name': '5G', 'type': 'T005'}
                ]
                
                total_items = 0
                
                for cat in categories:
                    self.logger.info(f"[{cat['name']}] 요금제 수집 시작")
                    
                    target_url = f"{base_url}?type={cat['type']}"
                    await page.goto(target_url, wait_until='domcontentloaded')
                    await page.wait_for_timeout(2000)
                    
                    # Scroll down to ensure all items load
                    for i in range(3):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(1000)
                    
                    # Extract items
                    try:
                        await page.wait_for_selector('li.card_list_item', timeout=10000)
                    except:
                        self.logger.warning(f"[{cat['name']}] 요금제 리스트 로딩 실패 혹은 없음")
                        continue

                    items = await page.evaluate(f"""(category) => {{
                        const list = [];
                        const items = document.querySelectorAll('li.card_list_item');
                        
                        items.forEach(item => {{
                            const result = {{}};
                            
                            // Carrier is fixed LGU+
                            result.carrier = 'Sugar Mobile (LGU+)';
                            
                            // Plan Name
                            // .tit_card includes a span for badge sometimes, we want text
                            const nameEl = item.querySelector('.tit_card');
                            if (nameEl) {{
                                // Clone node to remove children if needed, or just iterate nodes
                                // Detailed selector analysis: "The main text node within this element"
                                // Let's just take innerText and cleanup
                                result.plan_name = nameEl.innerText.trim();
                            }} else {{
                                result.plan_name = '';
                            }}
                            
                            // Data
                            const dataEl = item.querySelector('.list_rate_info li:nth-child(1)');
                            result.data = dataEl ? dataEl.innerText.trim() : '';
                            
                            // Voice
                            const voiceEl = item.querySelector('.list_rate_info li:nth-child(2)');
                            result.voice = voiceEl ? voiceEl.innerText.trim() : '';
                            
                            // Price
                            const promoEl = item.querySelector('.price_after');
                            const originalEl = item.querySelector('.price_before');
                            
                            let priceText = '0';
                            if (promoEl) priceText = promoEl.innerText;
                            else if (originalEl) priceText = originalEl.innerText;
                            
                            result.price = priceText.trim();
                            
                            list.push(result);
                        }});
                        
                        return list;
                    }}""", cat['name'])
                    
                    self.logger.info(f"[{cat['name']}] 수집된 요금제: {len(items)}개")
                    
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
