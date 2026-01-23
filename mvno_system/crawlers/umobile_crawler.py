from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio
import re
from datetime import datetime

class UMobileCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('umobile')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("U+유모바일 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            # Grant permission for multiple pages/popups
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                # 1. 목록 페이지 접속
                target_url = self.selectors.get('url', f"{self.config['base_url']}/product/pric/usim/pricList")
                await page.goto(target_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # Close Popups
                try:
                    close_btns = await page.locator('button.btn-close, button.close').all()
                    for btn in close_btns:
                        if await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(500)
                except:
                    pass

                # 2. 모든 요금제 로딩 (무한 스크롤 / 더보기)
                prev_count = 0
                max_scrolls = 20
                scroll_count = 0
                
                while scroll_count < max_scrolls:
                    if kwargs.get('test_mode'):
                        break
                        
                    # 맨 아래로 스크롤
                    await page.keyboard.press('End')
                    await page.wait_for_timeout(1000)
                    
                    # 더보기 버튼
                    try:
                        more_btn = page.locator('button.btn-more, .more-btn').first
                        if await more_btn.is_visible():
                             await more_btn.click()
                             await page.wait_for_timeout(1000)
                    except:
                        pass
                    
                    cards = await page.locator('div.price-card-list > ul > li').all()
                    current_count = len(cards)
                    
                    if current_count == prev_count:
                         # Retry scroll
                         no_change = 0
                         for _ in range(3):
                             await page.keyboard.press('End')
                             await page.wait_for_timeout(1000)
                             cards_check = await page.locator('div.price-card-list > ul > li').all()
                             if len(cards_check) > current_count:
                                 no_change = 0
                                 break
                             no_change += 1
                         
                         if no_change >= 3:
                             break
                    
                    prev_count = current_count
                    scroll_count += 1
                    self.logger.info(f"스크롤 {scroll_count}회 완료. 현재 아이템 수: {current_count}")

                # 3. 데이터 수집
                # Inject target="_blank" to searchFrm to open details in new tab
                await page.evaluate("""() => {
                    const form = document.querySelector('#searchFrm');
                    if(form) form.setAttribute('target', '_blank');
                }""")
                
                # Get all items first
                # Using a generic selector as confirmed by debug
                await page.wait_for_selector('a.gtm-tracking, .price-card-list a', timeout=10000)
                items = await page.locator('a.gtm-tracking').all()
                items_count = len(items)
                self.logger.info(f"발견된 요금제: {items_count}개")
                
                for i in range(items_count):
                    limit = kwargs.get('limit', 0)
                    if limit > 0 and i >= limit:
                        break
                    if kwargs.get('test_mode') and limit == 0 and i >= 3:
                        break

                    try:
                        # Re-query is safer
                        items = await page.locator('a.gtm-tracking').all()
                        if i >= len(items): break
                        item = items[i]
                        
                        # Basic Info (Inside the 'a' tag)
                        plan_name_el = item.locator('strong.pln-tit, strong.tit')
                        plan_name = await plan_name_el.inner_text() if await plan_name_el.count() > 0 else ''
                        if not plan_name: continue

                        # Click to open in new tab
                        # Use expect_page to catch the new tab
                        async with context.expect_page() as new_page_info:
                            # Use JS click to bypass potential overlays/interceptors
                            await item.evaluate("el => el.click()")
                        
                        new_page = await new_page_info.value
                        await new_page.wait_for_load_state('domcontentloaded')
                        await new_page.wait_for_timeout(2000)
                        
                        # Scrape Detail
                        detail_data = await new_page.evaluate("""() => {
                            const result = {};
                            
                            // Price
                            const priceEl = document.querySelector('.price strong, .tit-price .price');
                            result.price = priceEl ? priceEl.innerText.replace(/[^0-9]/g, '') : '0';
                            
                            // Specs
                            const specItems = document.querySelectorAll('.plan-info-list li, .info-list li');
                            specItems.forEach(li => {
                                const txt = li.innerText;
                                if (txt.includes('데이터')) result.data = li.querySelector('strong')?.innerText || li.innerText;
                                if (txt.includes('음성')) result.voice = li.querySelector('strong')?.innerText || li.innerText;
                                if (txt.includes('문자')) result.sms = li.querySelector('strong')?.innerText || li.innerText;
                            });

                            return result;
                        }""")
                        
                        # Network detection
                        network_badge = "LGU+" 
                        
                        plan_data = {
                            'platform': self.platform_key,
                            'carrier': 'U+Umobile',
                            'network': network_badge,
                            'plan_name': plan_name,
                            'price': detail_data.get('price'),
                            'data_raw': detail_data.get('data'),
                            'voice': detail_data.get('voice'),
                            'sms': detail_data.get('sms'),
                            'url': new_page.url, 
                            'collected_at': datetime.now().isoformat()
                        }
                        
                        # Save
                        self.save_plan(plan_data)
                        
                        # Screenshot
                        await self._save_screenshot(new_page, plan_data)
                        
                        self.logger.info(f"수집: {plan_data['carrier']} - {plan_data['plan_name']}")
                        
                        await new_page.close()
                        
                    except Exception as e:
                        self.logger.error(f"상세 수집 실패 (Item {i}): {e}")
                        continue
                        
                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()
