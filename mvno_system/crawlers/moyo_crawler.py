from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio

class MoyoCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('moyo')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("모요 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                # 1. 목록 페이지 접속
                target_url = f"{self.config['base_url']}/plans"
                await page.goto(target_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # 2. 요금제 카드 로딩 대기
                selector = self.selectors['list']['item_card']
                await page.wait_for_selector(selector, timeout=30000)
                
                if not kwargs.get('test_mode'):
                     await page.mouse.wheel(0, 3000)
                     await page.wait_for_timeout(2000)

                # 3. 목록에서 기본 정보 수집
                cards = await page.locator(selector).all()
                self.logger.info(f"목록에서 발견된 요금제: {len(cards)}개")
                
                plan_urls = []
                for idx, card in enumerate(cards):
                    if kwargs.get('test_mode') and idx >= 5:
                        break
                        
                    # Extract basic info from list
                    href = await card.get_attribute('href')
                    full_url = f"{self.config['base_url']}{href}"
                    
                    data = await card.evaluate("""(card) => {
                        const result = {};
                        const img = card.querySelector('img');
                        result.carrier = img ? img.alt : 'Unknown';
                        const titleEl = card.querySelector('div:nth-child(2) > div:nth-child(1) > span');
                        result.plan_name = titleEl ? titleEl.innerText : '';
                        const priceEl = Array.from(card.querySelectorAll('span')).find(s => s.innerText.includes('원') && s.innerText.includes('월'));
                        result.price = priceEl ? priceEl.innerText : '0';
                        return result;
                    }""")
                    
                    plan_urls.append({
                        'url': full_url,
                        'carrier': data.get('carrier'),
                        'plan_name': data.get('plan_name'),
                        'price': data.get('price')
                    })
                
                # 4. 상세 페이지 순회
                self.logger.info(f"상세 크롤링 시작: {len(plan_urls)}개")
                
                for plan in plan_urls:
                    try:
                        self.logger.info(f"이동: {plan['url']}")
                        await page.goto(plan['url'], wait_until='domcontentloaded')
                        await page.wait_for_timeout(2000) # Wait for render
                        
                        # Full page screenshot
                        # Moyo Network is mixed/various. Usually displayed in carrier or list.
                        # For now, put 'MoyoNet' or extract if possible.
                        # In Moyo, 'carrier' is e.g. "SK 7Mobile". Network is SKT implicit.
                        # Let's extract inferred network
                        net = 'Unknown'
                        c_lower = plan['carrier'].lower()
                        if 'sk' in c_lower or 'tplus' in c_lower: net = 'SKT' # Rough heuristic
                        if 'kt' in c_lower or 'cj' in c_lower: net = 'KT'
                        if 'lg' in c_lower or 'u+' in c_lower: net = 'LGU+'
                        
                        plan['network'] = net
                        screenshot_path = await self._save_screenshot(page, plan)
                        plan['screenshot_path'] = screenshot_path or 'failed'
                        
                        # Extract Details
                        # Use text-based finding as per debug
                        details = await page.evaluate("""() => {
                            const result = {};
                            
                            // Helper to get parent text
                            const getParentText = (text) => {
                                const el = Array.from(document.querySelectorAll('span, div, p')).find(e => e.innerText === text);
                                return el ? el.parentElement.innerText : '';
                            };
                            
                            result.data_full = getParentText('데이터');
                            result.voice_full = getParentText('통화');
                            result.sms_full = getParentText('문자');
                            
                            return result;
                        }""")
                        
                        plan['details'] = details
                        # Map detail data to main field (simple heuristic)
                        if details['data_full']:
                            plan['data_raw'] = details['data_full'].replace('\n', ' ').replace('데이터', '').strip()
                        else:
                            plan['data_raw'] = 'Unknown'
                            
                        self.save_plan(plan)
                        self.logger.info(f"수집 완료: {plan['carrier']} - {plan['plan_name']}")
                        
                    except Exception as e:
                        self.logger.error(f"상세 수집 실패 ({plan['url']}): {e}")
                
                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()
