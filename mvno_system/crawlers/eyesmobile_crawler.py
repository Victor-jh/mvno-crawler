from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio

class EyesMobileCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('eyesmobile')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("아이즈모바일 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                target_url = self.selectors.get('url', "https://www.eyes.co.kr/payplan/info2")
                await page.goto(target_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # Close Popups
                try:
                    close_btns = await page.locator('.layer-popup .btn-close, .popup-close, button:has-text("닫기")').all()
                    for btn in close_btns:
                        if await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(500)
                except:
                    pass
                
                # Click "View All" (전체보기)
                # It's usually in a nav list
                try:
                    all_btn = page.locator('.cal-nav li.all a, a:has-text("전체보기")')
                    if await all_btn.count() > 0:
                        await all_btn.first.click()
                        await page.wait_for_timeout(2000)
                except Exception as e:
                    self.logger.warning(f"전체보기 클릭 실패 (이미 전체보기 상태일 수 있음): {e}")

                # Carriers to crawl
                # The select box values are SKT, KT, LGT
                carriers = [
                    {'name': 'SKT', 'value': 'SKT'},
                    {'name': 'KT', 'value': 'KT'},
                    {'name': 'LGU+', 'value': 'LGT'}
                ]
                
                total_items = 0
                
                for carrier in carriers:
                    self.logger.info(f"[{carrier['name']}] 요금제 수집 시작")
                    
                    # Select Carrier
                    try:
                        # Find select box
                        select = page.locator('select.select-style1').first
                        if await select.is_visible():
                            await select.select_option(value=carrier['value'])
                            await page.wait_for_timeout(2000) # Wait for ajax reload
                    except Exception as e:
                        self.logger.error(f"통신사 선택 실패 ({carrier['name']}): {e}")
                        continue

                    # Load all plans via "More" button
                    while True:
                        if kwargs.get('test_mode'):
                            break
                            
                        try:
                            more_btn = page.locator('button.btn-type3')
                            # Check if visible and has text "더보기"
                            if await more_btn.is_visible() and "더보기" in await more_btn.inner_text():
                                await more_btn.click()
                                await page.wait_for_timeout(1000)
                            else:
                                break
                        except:
                            break
                    
                    await page.wait_for_timeout(1000)
                    
                    # Extract items
                    items = await page.evaluate(f"""(network) => {{
                        const list = [];
                        const items = document.querySelectorAll('.payplan-info-list li');
                        
                        items.forEach(item => {{
                            const result = {{}};
                            result.carrier = 'EyesMobile (' + network + ')';
                            
                            // Plan Name
                            const nameEl = item.querySelector('.tit');
                            result.plan_name = nameEl ? nameEl.innerText.trim() : '';
                            
                            // Data
                            const dataEl = item.querySelector('.data');
                            result.data = dataEl ? dataEl.innerText.trim() : '';
                            
                            // Voice
                            const voiceEl = item.querySelector('.provide .call span');
                            result.voice = voiceEl ? voiceEl.innerText.trim() : '';
                            
                            // Price
                            const priceEl = item.querySelector('.price');
                            result.price = priceEl ? priceEl.innerText.trim() : '0';
                            
                            list.push(result);
                        }});
                        
                        return list;
                    }}""", carrier['name'])
                    
                    self.logger.info(f"[{carrier['name']}] 수집된 요금제: {len(items)}개")
                    total_items += len(items)
                    
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
