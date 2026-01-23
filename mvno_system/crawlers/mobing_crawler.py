from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio

class MobingCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('mobing')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("모빙 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                base_url = self.selectors.get('url', "https://www.mobing.co.kr/product/plan/telecom")
                await page.goto(base_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # Close Popups
                try:
                    close_btns = await page.locator('.all-close__btn, .btn-close, button:has-text("닫기")').all()
                    for btn in close_btns:
                        if await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(500)
                except:
                    pass
                
                # Carriers to crawl
                carriers = ['SKT', 'KT', 'LG U+']
                
                total_items = 0
                
                for carrier in carriers:
                    self.logger.info(f"[{carrier}] 요금제 수집 시작")
                    
                    # Click filter tab
                    try:
                        # Find tab by text
                        # Selector: li.filter__li.network containing text
                        filter_tab = page.locator(f"li.filter__li.network").filter(has_text=carrier).first
                        
                        if await filter_tab.is_visible():
                            await filter_tab.click()
                            await page.wait_for_timeout(3000) # Wait for reload
                        else:
                            self.logger.warning(f"필터 탭 찾을 수 없음: {carrier}")
                            
                    except Exception as e:
                        self.logger.error(f"필터 클릭 중 에러 ({carrier}): {e}")
                        continue
                        
                    # Load all plans via "More" button
                    while True:
                        if kwargs.get('test_mode'):
                            break
                            
                        try:
                            more_btn = page.locator('.page-more__btn, .i-btn-more').first
                            if await more_btn.is_visible():
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
                        const items = document.querySelectorAll('.callplan-list__listbox');
                        
                        items.forEach(item => {{
                            const result = {{}};
                            
                            // Carrier
                            const chip = item.querySelector('.chip-area div');
                            let chipClass = chip ? chip.className : '';
                            let carrierName = network;
                            if (chipClass.includes('chip-skt')) carrierName = 'SKT';
                            else if (chipClass.includes('chip-kt')) carrierName = 'KT';
                            else if (chipClass.includes('chip-lgt')) carrierName = 'LGU+';
                            
                            result.carrier = 'Mobing (' + carrierName + ')';
                            
                            // Plan Name
                            const nameEl = item.querySelector('.name');
                            result.plan_name = nameEl ? nameEl.innerText.trim() : '';
                            
                            // Data
                            const dataEl = item.querySelector('.data');
                            result.data = dataEl ? dataEl.innerText.trim() : '';
                            
                            // Voice
                            const voiceEl = item.querySelector('.voice');
                            result.voice = voiceEl ? voiceEl.innerText.trim() : '';
                            
                            // Price
                            // Promo price often in .price .sum strong
                            // Original in .price .costprice
                            const promoEl = item.querySelector('.price .sum strong');
                            const originalEl = item.querySelector('.price .costprice');
                            
                            let priceText = '0';
                            if (promoEl) priceText = promoEl.innerText;
                            else if (originalEl) priceText = originalEl.innerText;
                            
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
