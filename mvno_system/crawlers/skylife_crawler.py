from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio
import re

class SkylifeCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('skylife')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("스카이라이프 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                # 1. 목록 페이지 접속
                target_url = self.selectors.get('url', f"{self.config['base_url']}/product/mobile/goods")
                await page.goto(target_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # 팝업 닫기 Logic
                try:
                    close_btns = await page.locator('button:has-text("닫기")').all()
                    for btn in close_btns:
                        if await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(500)
                except:
                    pass

                # 2. 더보기 버튼 클릭 Loop
                while True:
                    if kwargs.get('test_mode'): 
                        # 테스트모드면 더보기 클릭 없이 현재 데이터만 수집
                        break

                    try:
                        more_btn = page.locator('button:has-text("더보기")').first
                        if await more_btn.is_visible():
                            await more_btn.click()
                            await page.wait_for_timeout(1000)
                        else:
                            break
                    except:
                        break
                
                # 3. 요금제 카드 로딩 대기
                # 스크롤 조금 해서 로딩 유도
                await page.mouse.wheel(0, 500)
                await page.wait_for_timeout(1000)
                
                try:
                    await page.wait_for_selector('a[href^="/product/mobile/goods/"]', timeout=60000)
                except Exception as e:
                    await page.screenshot(path=f"{self.screenshot_dir}/error_loading_items.png")
                    raise e
                
                # 카드 컨테이너 찾기
                # a 태그의 상위 div (rounded-xl bg-white)
                
                # JS로 전체 데이터 추출이 효율적
                cards = await page.locator('div.rounded-xl.bg-white').all() 
                
                if len(cards) == 0:
                     # Fallback check
                     self.logger.warning("div.rounded-xl.bg-white 카드 미발견. a 태그 기준으로 탐색 시도.")
                     pass
                
                # 3. Extract URLs
                self.logger.info("상세 URL 추출 시작")
                
                plan_urls = await page.evaluate("""() => {
                    const list = [];
                    const links = document.querySelectorAll('a[href^="/product/mobile/goods/"]');
                    
                    links.forEach(link => {
                        const href = link.getAttribute('href');
                        // Deduplicate logic if needed, but set will handle it
                        list.push(href);
                    });
                    
                    return [...new Set(list)]; // Unique URLs
                }""")
                
                self.logger.info(f"발견된 상세 URL: {len(plan_urls)}개")
                
                valid_count = 0
                for href in plan_urls:
                     limit = kwargs.get('limit', 0)
                     if limit > 0 and valid_count >= limit:
                         break
                     if kwargs.get('test_mode') and valid_count >= 3:
                         break
                        
                     full_url = f"https://shop.skylife.co.kr{href}"
                     
                     try:
                         # Visit Detail
                         await page.goto(full_url, wait_until='domcontentloaded')
                         await page.wait_for_timeout(3000)
                         
                         # Check for error
                         if "페이지 주소를 다시 한번" in await page.content():
                             self.logger.warning(f"잘못된 상세 페이지 (404-like): {full_url}")
                             continue
                         
                         # Scrape
                         detail_data = await page.evaluate("""() => {
                             const result = {};
                             
                             // Scrape Title
                             const titleEl = document.querySelector('.text-2xl.font-bold, h1, h2');
                             result.plan_name = titleEl ? titleEl.innerText : document.title;
                             result.carrier = 'Skylife';
                             
                             // Price
                             const priceEl = document.querySelector('.text-3xl.font-bold, .price'); 
                             result.price = priceEl ? priceEl.innerText.replace(/[^0-9]/g, '') : '0';
                             
                             // Specs
                             const bodyText = document.body.innerText;
                             result.data_full = bodyText.includes('데이터') ? 'See screenshot' : '';
                             
                             return result;
                         }""")
                         
                         # Save
                         plan_data = {
                            'platform': self.platform_key,
                            'carrier': detail_data.get('carrier'),
                            'plan_name': detail_data.get('plan_name'),
                            'price': detail_data.get('price'),
                            'data_raw': detail_data.get('data_full'),
                            'url': full_url, 
                            'details': detail_data,
                            'network': 'KT' # SkyLife uses KT
                         }

                         # Screenshot (Standardized: Network_Carrier_Platform_PlanName)
                         screenshot_path = await self._save_screenshot(page, plan_data)
                         
                         # Save
                         plan_data = {
                            'platform': self.platform_key,
                            'carrier': detail_data.get('carrier'),
                            'plan_name': detail_data.get('plan_name'),
                            'price': detail_data.get('price'),
                            'data_raw': detail_data.get('data_full', '').replace('\n', ' '),
                            'url': full_url, 
                            'details': detail_data,
                            'screenshot_path': screenshot_path
                         }
                         
                         self.save_plan(plan_data)
                         valid_count += 1
                         self.logger.info(f"수집 완료: {plan_data['plan_name']}")
                         
                     except Exception as e:
                         self.logger.error(f"상세 수집 실패 ({full_url}): {e}")
                         continue
                
                self.finish_crawl_log(status='success')
                
                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                try:
                    await page.screenshot(path=f"{self.screenshot_dir}/error_final.png")
                except:
                    pass
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()
