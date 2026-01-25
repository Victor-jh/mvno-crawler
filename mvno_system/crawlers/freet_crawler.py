from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio
from datetime import datetime

class FreeTCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('freet')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("프리티 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                target_url = self.selectors.get('url', f"{self.config['base_url']}/plan/ratePlan")
                await page.goto(target_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # Close Popups if any
                try:
                    # Common popup close buttons
                    close_btns = await page.locator('.modal-close, .btn-close, button:has-text("닫기")').all()
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
                        more_btn = page.locator('a.btn-type3:has-text("더보기")')
                        if await more_btn.is_visible():
                            await more_btn.click()
                            await page.wait_for_timeout(1000)
                        else:
                            break
                    except:
                        break
                        

                # Extract items (URL Harvesting)
                items = await page.evaluate("""() => {
                    const list = [];
                    const items = document.querySelectorAll('li.plan-item');
                    
                    items.forEach(item => {
                        const result = {};
                        
                        // Link for Detail
                        const link = item.querySelector('a');
                        const href = link ? link.getAttribute('href') : '';
                        
                        if (href && href.includes('/plan/ratePlan/detail')) {
                             result.url = 'https://www.freet.co.kr' + href;
                        } else {
                             result.url = '';
                        }
                        
                        // Carrier
                        const label = item.querySelector('span.label');
                        let network = 'Unknown';
                        if (label) {
                            if (label.classList.contains('skt')) network = 'SKT';
                            else if (label.classList.contains('kt')) network = 'KT';
                            else if (label.classList.contains('lg')) network = 'LGU+';
                            else network = label.innerText.trim();
                        }
                        result.carrier = '프리티';  // Standardized Korean name
                        result.network = network;
                        
                        // Plan Name
                        const nameEl = item.querySelector('.plan-top p');
                        result.plan_name = nameEl ? nameEl.innerText.trim() : '';
                        
                        list.push(result);
                    });
                    
                    return list;
                }""")
                
                self.logger.info(f"수집된 요금제 URL: {len(items)}개")
                
                valid_count = 0
                for item in items:
                     limit = kwargs.get('limit', 0)
                     if limit > 0 and valid_count >= limit:
                         break
                     if kwargs.get('test_mode') and limit == 0 and valid_count >= 3:
                         break
                     
                     if not item['url']:
                         continue
 
                     valid_count += 1
                     await self._crawl_plan_detail(item['url'], item, page)
                
                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()

    async def _crawl_plan_detail(self, url, meta, page):
        self.logger.info(f"상세 이동: {url}")
        try:
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)

            try:
                # Close potential popups in detail page
                await page.evaluate("""() => {
                    const btn = document.querySelector('.btn-close, .modal-close, .xo-popup-close');
                    if(btn) btn.click();
                }""")
                await page.wait_for_timeout(500)
            except:
                pass

            # Scrape Detail
            detail_data = await page.evaluate("""() => {
                const result = {};
                
                // Plan Name
                const nameEl = document.querySelector('.plan-tit h2') || document.querySelector('.plan-top p');
                result.plan_name = nameEl ? nameEl.innerText.trim() : '';
                
                // Price - Try multiple selectors
                const priceEl = document.querySelector('.plan-price strong') || 
                                document.querySelector('.price strong') || 
                                document.querySelector('.price-info strong');
                result.price = priceEl ? priceEl.innerText.replace(/[^0-9]/g, '') : '0';
                
                // Specs
                const specs = document.querySelectorAll('.plan-info-list li, .info ul li');
                specs.forEach(li => {
                    const txt = li.innerText;
                    if (txt.includes('데이터')) result.data = li.querySelector('strong')?.innerText || li.innerText;
                    if (txt.includes('음성')) result.voice = li.querySelector('strong')?.innerText || li.innerText;
                    if (txt.includes('문자')) result.sms = li.querySelector('strong')?.innerText || li.innerText;
                });
                
                return result;
            }""")
            
            final_plan_name = detail_data.get('plan_name') or meta.get('plan_name')
            
            plan_data = {
                'platform': self.platform_key,
                'carrier': meta.get('carrier'), # FreeT (SKT)
                'network': meta.get('network'), # SKT
                'plan_name': final_plan_name,
                'price': detail_data.get('price'),
                'data_raw': detail_data.get('data'),
                'voice': detail_data.get('voice'),
                'sms': detail_data.get('sms'),
                'url': url,
                'collected_at': datetime.now().isoformat()
            }
            
            self.save_plan(plan_data)
            
            await self._save_screenshot(page, plan_data)
            
        except Exception as e:
            self.logger.error(f"상세 수집 실패 ({url}): {e}")
