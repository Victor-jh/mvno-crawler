from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio

class KTMobileCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('ktmmobile')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("KT엠모바일 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                # 1. 목록 페이지 접속
                target_url = self.selectors.get('url', f"{self.config['base_url']}/rate/rateList.do")
                await page.goto(target_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # 팝업 닫기 Logic (여러 팝업 대응)
                try:
                    popups = await page.locator('.pop-wrap, .main-popup').all()
                    for popup in popups:
                        if await popup.is_visible():
                            try:
                                close_btn = popup.locator('button.close, .btn-close')
                                if await close_btn.count() > 0:
                                    await close_btn.first.click()
                                    await page.wait_for_timeout(500)
                            except:
                                pass
                except:
                    pass

                # 2. 아코디언 펼치기
                try:
                    # 아코디언 버튼 대기
                    await page.wait_for_selector('button.c-accordion__button', timeout=10000)
                    buttons = await page.locator('button.c-accordion__button').all()
                    self.logger.info(f"아코디언 버튼 {len(buttons)}개 발견 - 펼치기 시도")
                    
                    for btn in buttons:
                        if await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(500)
                except Exception as e:
                    self.logger.warning(f"아코디언 펼치기 중 오류 (또는 없음): {e}")

                # 3. 요금제 카드 로딩 대기
                try:
                    await page.wait_for_selector('a.rate-info__wrap', timeout=30000)
                except Exception as e:
                    await page.screenshot(path=f"{self.screenshot_dir}/error_loading_list.png")
                    raise e
                
                # '요금제 더보기' 버튼이 있는지 확인하고 클릭하는 로직이 필요할 수 있음
                # 하지만 분석 내용에 따르면 아코디언 방식이라고 함.
                # 리스트가 많을 경우 paging인지 더보기인지 확인 필요. 우선 스크롤.
                
                if not kwargs.get('test_mode'):
                     await page.mouse.wheel(0, 5000)
                     await page.wait_for_timeout(2000)

                cards = await page.locator('a.rate-info__wrap').all()
                self.logger.info(f"발견된 요금제 카드: {len(cards)}개")
                
                valid_count = 0
                for i in range(len(cards)):
                     # Re-locate cards in case DOM changed
                     cards = await page.locator('a.rate-info__wrap').all()
                     if i >= len(cards): break
                     card = cards[i]

                     limit = kwargs.get('limit', 0)
                     if limit > 0 and valid_count >= limit:
                         break
                     if kwargs.get('test_mode') and limit == 0 and valid_count >= 3:
                         break
                        
                     try:
                         # 1. Get Basic Info from List (Carrier, Name)
                         basic_data = await card.evaluate("""(card) => {
                            const result = {};
                            result.carrier = 'KT엠모바일';  // Standardized Korean name
                            const nameEl = card.querySelector('strong');
                            result.plan_name = nameEl ? nameEl.innerText : 'Unknown Plan';
                            return result;
                         }""")
                         
                         self.logger.info(f"상세 수집 시도: {basic_data['plan_name']}")
                         
                         # 2. Click to Open Modal
                         await card.click()
                         
                         # 3. Wait for Modal
                         try:
                             modal = page.locator('.c-modal__body').first
                             await modal.wait_for(state='visible', timeout=5000)
                             await page.wait_for_timeout(1000) # Render wait
                         except:
                             self.logger.warning(f"모달 로딩 실패: {basic_data['plan_name']}")
                             continue

                         # 4. Scrape Detail Data from Modal
                         detail_data = await modal.evaluate("""(modal) => {
                             const result = {};
                             
                             // Helper to extract text from product-summary items
                             const items = Array.from(modal.querySelectorAll('li.product-summary__item'));
                             
                             items.forEach(item => {
                                 const img = item.querySelector('img');
                                 if (!img) return;
                                 const src = img.src;
                                 const textEl = item.querySelector('.product-summary__text');
                                 const text = textEl ? textEl.innerText : '';
                                 
                                 if (src.includes('data')) result.data_full = text;
                                 else if (src.includes('call')) result.voice_full = text;
                                 else if (src.includes('sms')) result.sms_full = text;
                             });
                             
                             // Price
                             const priceEl = modal.querySelector('.product-detail__price b');
                             result.price = priceEl ? priceEl.innerText : '0';
                             
                             return result;
                         }""")
                         
                         # Screenshot (with Modal open)
                         # KTMobile uses KT network
                         screenshot_data = {
                             'carrier': basic_data['carrier'],
                             'network': 'KT',
                             'plan_name': basic_data['plan_name']
                         }
                         screenshot_path = await self._save_screenshot(page, screenshot_data)
                         
                         # 6. Close Modal (Robust)
                         # Try button click first
                         try:
                             close_btn = page.locator('button.c-popup-close, button.close, .c-modal__close').first
                             if await close_btn.is_visible():
                                 await close_btn.click()
                             else:
                                 await page.keyboard.press('Escape')
                         except:
                             await page.keyboard.press('Escape')
                             
                         # Wait for modal to disappear
                         try:
                             await page.locator('.c-modal__body').first.wait_for(state='hidden', timeout=3000)
                         except:
                             # Force reload if sticky
                             self.logger.warning("모달 닫기 실패. 페이지 리로드")
                             await page.reload()
                             await page.wait_for_timeout(2000)
                             # Re-open accordions if needed, but simple reload might be safer to reset state
                         
                         await page.wait_for_timeout(500)
                         
                         # 7. Save
                         final_data = {
                            'platform': self.platform_key,
                            'carrier': basic_data['carrier'],
                            'plan_name': basic_data['plan_name'],
                            'price': detail_data.get('price'),
                            'data_raw': detail_data.get('data_full', '').replace('\n', ' '),
                            'url': target_url, # Same URL since it's a modal
                            'details': detail_data,
                            'screenshot_path': screenshot_path
                         }
                         
                         self.save_plan(final_data)
                         valid_count += 1
                         self.logger.info(f"수집 완료: {final_data['plan_name']}")
                         
                     except Exception as e:
                         self.logger.error(f"카드 처리 중 에러: {e}")
                         # Try to recover by closing modal if open
                         await page.keyboard.press('Escape')
                         await page.wait_for_timeout(1000)
                         continue
                
                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()
