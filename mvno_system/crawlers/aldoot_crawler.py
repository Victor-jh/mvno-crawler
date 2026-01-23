from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio

class AldootCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('aldoot')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("알닷(LGU+) 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                # 1. 목록 페이지 접속
                target_url = f"{self.config['base_url']}/plan/plan-list"
                await page.goto(target_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # 팝업 닫기 (있을 경우)
                try:
                    close_btn = page.locator('button:has-text("닫기")').first
                    if await close_btn.is_visible():
                        await close_btn.click()
                        await page.wait_for_timeout(1000)
                except:
                    pass

                # 2. 요금제 카드 로딩 대기
                await page.wait_for_selector('.plan_item.ticket', timeout=10000)
                
                # 테스트 아니면 스크롤
                if not kwargs.get('test_mode'):
                     await page.mouse.wheel(0, 3000)
                     await page.wait_for_timeout(2000)

                cards = await page.locator('.plan_item.ticket').all()
                self.logger.info(f"발견된 요금제 카드: {len(cards)}개")
                
                cards = await page.locator('.plan_item.ticket').all()
                self.logger.info(f"발견된 요금제 카드: {len(cards)}개")
                
                valid_count = 0
                for i in range(len(cards)):
                    # Re-query
                    cards = await page.locator('.plan_item.ticket').all()
                    if i >= len(cards): break
                    card = cards[i]
                    
                    if kwargs.get('test_mode') and valid_count >= 3:
                        break
                        
                    try:
                        # 1. Basic Info
                        data = await card.evaluate("""(card) => {
                            const result = {};
                            const img = card.querySelector('.partner img');
                            result.carrier = img ? img.alt.split('_')[0] : 'Unknown';
                            const tit = card.querySelector('.plan_tit');
                            result.plan_name = tit ? tit.innerText : '';
                            return result;
                        }""")
                        
                        self.logger.info(f"상세 수집 시도: {data['plan_name']}")
                        
                        # 2. Click and Navigate (SPA support)
                        # New Tab failed, so we use main page navigation
                        curr_url = page.url
                        await card.click()
                        
                        # Wait for URL change or meaningful element
                        try:
                            await page.wait_for_condition(lambda: page.url != curr_url, timeout=5000)
                            await page.wait_for_load_state('domcontentloaded')
                            await page.wait_for_timeout(2000)
                        except:
                            self.logger.warning(f"이동 실패 또는 URL 변경 없음: {data['plan_name']}")
                            # Try to see if it's a modal? No, debug showed navigation.
                            # Just continue to scrape if content changed?
                            pass

                        # 3. Scrape Detail
                        # Screenshot - AlDot is LGU+ network
                        # Screenshot - AlDot is LGU+ network
                        screenshot_data = {
                            'carrier': data['carrier'],
                            'network': 'LGU+',
                            'plan_name': data['plan_name']
                        }
                        screenshot_path = await self._save_screenshot(page, screenshot_data)
                        
                        detail_data = await page.evaluate("""() => {
                            const result = {};
                            const getVal = (label) => {
                                const dl = Array.from(document.querySelectorAll('dl')).find(d => d.innerText.includes(label));
                                return dl ? dl.innerText.replace(label, '').trim() : '';
                            };
                            
                            result.data_full = getVal('데이터');
                            result.voice_full = getVal('음성');
                            result.sms_full = getVal('문자');
                            
                            const priceEl = document.querySelector('.price');
                            result.price = priceEl ? priceEl.innerText : '0';
                            
                            return result;
                        }""")
                        
                        # 5. Save
                        plan_data = {
                            'platform': self.platform_key,
                            'carrier': data.get('carrier'),
                            'plan_name': data.get('plan_name'),
                            'price': detail_data.get('price'),
                            'data_raw': detail_data.get('data_full', '').replace('\n', ' '),
                            'url': page.url,
                            'details': detail_data,
                            'screenshot_path': screenshot_path
                        }
                        
                        self.save_plan(plan_data)
                        valid_count += 1
                        self.logger.info(f"수집 완료: {plan_data['plan_name']}")
                        
                        # 6. Go Back
                        await page.go_back()
                        await page.wait_for_load_state('domcontentloaded')
                        await page.wait_for_timeout(2000) # Wait for list to render
                        
                    except Exception as e:
                        self.logger.error(f"카드 처리 중 에러: {e}")
                        # Ensure we are back on list
                        if page.url != target_url and 'plan-list' not in page.url:
                             try:
                                 await page.go_back()
                                 await page.wait_for_timeout(2000)
                             except:
                                 pass
                        continue
                        
                    except Exception as e:
                        self.logger.error(f"카드 처리 중 에러: {e}")
                        continue
                
                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()
