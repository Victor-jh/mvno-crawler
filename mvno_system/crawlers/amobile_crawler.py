from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio

class AmobileCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('amobile')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("에이모바일 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                base_url = self.selectors.get('url', "https://www.amobile.co.kr/plannew")
                await page.goto(base_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # Close Popups
                try:
                    close_btns = await page.locator('.main-popup .close-btn, .btn-close, button:has-text("닫기"), .layer-popup .btn-close').all()
                    for btn in close_btns:
                        if await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(500)
                except:
                    pass
                
                # Carriers to crawl
                # Select values: S, K, L
                carriers = [
                    {'name': 'SKT', 'value': 'S'},
                    {'name': 'KT', 'value': 'K'},
                    {'name': 'LGU+', 'value': 'L'}
                ]
                
                total_items = 0
                
                for carrier in carriers:
                    self.logger.info(f"[{carrier['name']}] 요금제 수집 시작")
                    
                    # Select Carrier
                    try:
                        select = page.locator('#telecom')
                        if await select.is_visible():
                            await select.select_option(value=carrier['value'])
                            await page.wait_for_timeout(3000) # Wait for reload
                    except Exception as e:
                        self.logger.error(f"통신사 선택 실패 ({carrier['name']}): {e}")
                        continue
                        
                    # Scroll to ensure all items load
                    # Agent said no pagination, just one page. Let's scroll a bit.
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)
                    
                    # Extract items
                    items = await page.evaluate(f"""(network) => {{
                        const list = [];
                        const items = document.querySelectorAll('.plan-area');
                        
                        items.forEach(item => {{
                            const result = {{}};
                            
                            // Carrier
                            result.carrier = 'A Mobile (' + network + ')';
                            
                            // Plan Name
                            const nameEl = item.querySelector('.plan-name');
                            result.plan_name = nameEl ? nameEl.innerText.trim() : '';
                            
                            // Data
                            const dataEl = item.querySelector('.basic-data');
                            result.data = dataEl ? dataEl.innerText.trim() : '';
                            
                            // Voice
                            const voiceEl = item.querySelector('.add-call-text');
                            result.voice = voiceEl ? voiceEl.innerText.trim() : '';
                            
                            // Price
                            const promoEl = item.querySelector('.real-price');
                            const originalEl = item.querySelector('.strikethrough');
                            
                            let priceText = '0';
                            if (promoEl) priceText = promoEl.innerText;
                            else if (originalEl) priceText = originalEl.innerText;
                            
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
