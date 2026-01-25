from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio

class TossMobileCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('tossmobile')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("토스모바일 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                base_url = self.selectors.get('url', f"{self.config['base_url']}/pricing")
                networks = self.selectors.get('networks', ["SKT", "KT", "LGU"])
                
                total_items = 0
                
                for network in networks:
                    target_url = f"{base_url}?carrier={network}"
                    self.logger.info(f"접속: {target_url} ({network})")
                    
                    await page.goto(target_url, wait_until='domcontentloaded')
                    await page.wait_for_timeout(3000)
                    
                    # Scroll to load all
                    last_height = await page.evaluate("document.body.scrollHeight")
                    while True:
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(1000)
                        new_height = await page.evaluate("document.body.scrollHeight")
                        if new_height == last_height:
                            break
                        last_height = new_height
                    
                    await page.wait_for_timeout(1000)
                    
                    # Extract items
                    # Pass network to JS
                    # Extract plan URLs from list
                    plan_urls = await page.evaluate(f"""(network) => {{
                        const list = [];
                        const items = document.querySelectorAll('.plan_item');
                        
                        items.forEach(item => {{
                            const href = item.getAttribute('href');
                            if (!href) return;
                            
                            const fullUrl = 'https://tossmobile.co.kr' + href + (href.includes('?') ? '&' : '?') + 'carrier=' + network;
                            
                            const result = {{
                                'carrier': '토스모바일',  // Standardized Korean name
                                'url': fullUrl,
                                'plan_name': item.innerText.split('\\n')[0] // Temporary name for validation
                            }};
                            
                            list.push(result);
                        }});
                        
                        return list;
                    }}""", network)
                    
                    self.logger.info(f"[{network}] 발견된 상세 URL: {len(plan_urls)}개")
                    total_items += len(plan_urls)
                    
                    # 4. Visit Detail Pages
                    for idx, plan in enumerate(plan_urls):
                        if kwargs.get('test_mode') and idx >= 2:
                            break
                            
                        try:
                            # Visit Detail Page
                            await page.goto(plan['url'], wait_until='domcontentloaded')
                            await page.wait_for_timeout(2000)
                            
                            # Scrape Detail
                            detail_data = await page.evaluate("""() => {
                                const result = {};
                                
                                // Proper extraction on detail page
                                // Toss Detail Structure: usually a big title, price, and specs list
                                
                                const titleEl = document.querySelector('h1, h2, h3'); // Catch main heading
                                result.plan_name = titleEl ? titleEl.innerText : document.title;
                                
                                // Price
                                // Find specific price element if possible, or search small elements
                                // Look for '월 ...원' pattern
                                const priceCandidates = Array.from(document.querySelectorAll('span, div, p'));
                                // Filter for elements with '원' and length < 20 to avoid containers
                                const validEl = priceCandidates.find(el => el.innerText.includes('원') && el.innerText.length < 20 && /\d/.test(el.innerText));
                                
                                let finalPrice = '0';
                                if (validEl) {
                                    // Extract digits
                                    finalPrice = validEl.innerText.replace(/[^0-9]/g, '');
                                }
                                
                                // Cap at reasonable value (e.g. 1 million)
                                if (finalPrice.length > 7) finalPrice = finalPrice.slice(0, 7);
                                
                                result.price = finalPrice;
                                
                                // Specs (Data/Voice)
                                
                                // Specs (Data/Voice)
                                const bodyText = document.body.innerText;
                                result.data_full = 'See screenshot'; 
                                result.voice_full = 'See screenshot';
                                
                                // Attempt to find spec blocks
                                const labels = Array.from(document.querySelectorAll('div')).filter(d => d.innerText === '데이터' || d.innerText === '통화' || d.innerText === '문자');
                                labels.forEach(label => {
                                    const value = label.nextElementSibling;
                                    if (value) {
                                        if (label.innerText === '데이터') result.data_full = value.innerText;
                                        if (label.innerText === '통화') result.voice_full = value.innerText;
                                        if (label.innerText === '문자') result.sms_full = value.innerText;
                                    }
                                });
                                
                                return result;
                            }""")
                            
                            # Screenshot
                            # Carrier in plan['carrier'] is "TossMobile (KT)". 
                            # Extract raw network if possible, or just pass as is.
                            # plan['carrier'] e.g. "TossMobile (KT)"
                            # Construct Final Data
                            final_data = {
                                'platform': self.platform_key,
                                'carrier': '토스모바일',  # Standardized Korean name
                                'plan_name': detail_data.get('plan_name', plan['plan_name']),
                                'price': detail_data.get('price'),
                                'data_raw': detail_data.get('data_full', '').replace('\n', ' '),
                                'url': plan['url'],
                                'details': detail_data,
                                'network': plan['carrier'].split('(')[-1].replace(')', '') # Extract Network
                            }

                            # Screenshot
                            # Carrier in plan['carrier'] is "TossMobile (KT)". 
                            # Extract raw network if possible, or just pass as is.
                            # plan['carrier'] e.g. "TossMobile (KT)"
                            screenshot_path = await self._save_screenshot(page, final_data)
                            
                            self.save_plan(final_data)
                            self.logger.info(f"수집 완료: {final_data['plan_name']}")
                            
                        except Exception as e:
                            self.logger.error(f"상세 수집 실패 ({plan['url']}): {e}")
                            continue
                
                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()
