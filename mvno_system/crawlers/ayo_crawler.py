from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio

class AyoCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('ayo')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("아요(Weayo) 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                # 1. 목록 페이지 접속 (요금제 찾기)
                # 메인 -> 메뉴 클릭 대신 직접 URL 접근 시도
                # 메뉴 클릭 시 URL이 변경되는지 확인 필요하나 보통 /network/plan_list.php 등의 형태임
                # 하지만 분석 결과에서 URL 변화를 명확히 못 봤으므로 메인에서 이동 로직 구현
                
                await page.goto(self.config['base_url'], wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)
                
                # 요금제 찾기 메뉴 클릭 (텍스트로 찾기)
                await page.click('text="요금제 찾기"')
                await page.wait_for_timeout(3000)
                
                # 2. 요금제 카드 로딩 대기
                # .x13 클래스가 있는 span이 로드될 때까지 대기
                await page.wait_for_selector('span.x13', timeout=10000)
                
                if not kwargs.get('test_mode'):
                     await page.mouse.wheel(0, 3000)
                     await page.wait_for_timeout(2000)

                # Playwright의 :has() 유사 기능 사용 또는 필터링
                # 요소가 많으므로 JS로 처리하는게 빠름
                cards = await page.locator('.col-md-12').all()
                self.logger.info(f"발견된 잠재적 카드: {len(cards)}개")
                
                valid_count = 0
                for card in cards:
                     limit = kwargs.get('limit', 0)
                     if limit > 0 and valid_count >= limit:
                         break
                     if kwargs.get('test_mode') and limit == 0 and valid_count >= 3:
                         break
                        
                     # 데이터 추출
                     try:
                         # Plan Name 확인으로 유효 카드 필터링
                         if await card.locator('span.x13').count() == 0:
                             continue
                             
                         data = await card.evaluate("""(card) => {
                            const result = {};
                            
                            // 통신사 (이미지 alt)
                            const img = card.querySelector('img');
                            result.carrier = img ? img.alt : 'Unknown';
                            
                            // 요금제명
                            const nameEl = card.querySelector('span.x13');
                            result.plan_name = nameEl ? nameEl.innerText : '';
                            
                            // 데이터
                            const dataEl = card.querySelector('.textcolor3');
                            result.data = dataEl ? dataEl.innerText : '';
                            
                            // 가격
                            // .textcolor1 내부 span 찾기
                            const priceWrapper = card.querySelector('.textcolor1');
                            const priceEl = priceWrapper ? priceWrapper.querySelector('span') : null;
                            result.price = priceEl ? priceEl.innerText : '0';
                            
                            return result;
                         }""")
                         
                         if not data['plan_name']:
                             continue

                         valid_count += 1
                         
                         plan_data = {
                            'platform': self.platform_key,
                            'carrier': data.get('carrier'),
                            'plan_name': data.get('plan_name'),
                            'price': data.get('price'),
                            'data_raw': data.get('data'),
                            'url': page.url, 
                            'details': data
                         }
                         
                         await self._save_screenshot(page, plan_data)
                         plan_data['screenshot_path'] = 'captured_in_list'
                         
                         self.save_plan(plan_data)
                         self.logger.info(f"수집: {plan_data['carrier']} - {plan_data['plan_name']}")
                         
                     except Exception as e:
                         # 개별 카드 에러 무시
                         continue
                
                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()
