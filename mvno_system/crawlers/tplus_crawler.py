from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio

class TplusCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('tplusmobile')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("티플러스 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                target_url = self.selectors.get('url', f"{self.config['base_url']}/main/rate/join")
                await page.goto(target_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # Close Popups
                try:
                    # Common popup close buttons
                    close_btns = await page.locator('.layerPopup .btn_close, .btn_pop_close, button:has-text("닫기"), button:has-text("오늘 하루 열지 않기")').all()
                    for btn in close_btns:
                        if await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(500)
                except:
                    pass
                
                # Load all plans via "More" button
                while True:
                    if kwargs.get('test_mode'):
                        break
                        
                    try:
                        # board_paging contains the more button or is the container
                        # The analysis said #board_paging is the button or clicks trigger it
                        # Let's check if #board_paging text contains "더보기" and click it
                        more_btn = page.locator('#board_paging')
                        if await more_btn.is_visible() and "더보기" in await more_btn.inner_text():
                            await more_btn.click()
                            await page.wait_for_timeout(1000) # Wait for ajax
                        else:
                            break
                    except:
                        break
                        
                # Extract items
                items = await page.evaluate("""() => {
                    const list = [];
                    const items = document.querySelectorAll('.listArea .cardArea');
                    
                    items.forEach(item => {
                        const result = {};
                        
                        // Carrier
                        const badge = item.querySelector('.cardHead .tag i.badge');
                        let network = 'Unknown';
                        if (badge) {
                            const text = badge.innerText.trim();
                            if (text.includes('SKT')) network = 'SKT';
                            else if (text.includes('KT')) network = 'KT';
                            else if (text.includes('LGU') || text.includes('LG')) network = 'LGU+';
                            else network = text;
                        }
                        result.carrier = 'tplus (' + network + ')';
                        
                        // Plan Name
                        const nameEl = item.querySelector('.cardBody .title');
                        result.plan_name = nameEl ? nameEl.innerText.trim() : '';
                        
                        // Data
                        const dataEl = item.querySelector('.cardBody .info .data p span');
                        result.data = dataEl ? dataEl.innerText.trim() : '';
                        
                        // Voice
                        const voiceEl = item.querySelector('.cardBody .info .call span');
                        result.voice = voiceEl ? voiceEl.innerText.trim() : '';
                        
                        // Price
                        // .cardBody .priceInfo .mainPrice span:nth-child(2)
                        const priceEl = item.querySelector('.cardBody .priceInfo .mainPrice span:nth-child(2)');
                        result.price = priceEl ? priceEl.innerText.trim() : '0';
                        
                        list.push(result);
                    });
                    
                    return list;
                }""")
                
                self.logger.info(f"수집된 요금제: {len(items)}개")
                
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
