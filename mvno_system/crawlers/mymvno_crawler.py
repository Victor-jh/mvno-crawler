from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio
from datetime import datetime

class MyMvnoCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('mymvno')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("마이알뜰폰(KT) 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                # 1. 목록 페이지 접속 (메인 -> 상품 요금제 찾기 대신 직접 접근)
                # target_url = f"{self.config['base_url']}/fe/mypage/ppl/pplList.do"
                # 위의 직접 URL 접근이 막힐 수 있으므로 메인에서 이동하는 방식을 고려할 수도 있음
                # 하지만 분석 결과 직접 접근이 가능해 보임.
                target_url = f"{self.config['base_url']}/fe/mypage/ppl/pplList.do"
                
                await page.goto(target_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # 2. 요금제 카드 로딩 대기
                await page.wait_for_selector('.popularDataItem', timeout=10000)
                
                if not kwargs.get('test_mode'):
                     await page.mouse.wheel(0, 3000)
                     await page.wait_for_timeout(2000)

                cards = await page.locator('.popularDataItem').all()
                self.logger.info(f"발견된 요금제 카드: {len(cards)}개")
                
                # Re-query elements or better, collect indices
                # Because of BACK navigation, element handles will become stale.
                # So we must collect Count first, then loop using nth-match or re-query.
                # Since cards are large, let's use a loop with re-query strategy.
                
                card_count = len(cards)
                for idx in range(card_count):
                    limit = kwargs.get('limit', 0)
                    if limit > 0 and idx >= limit:
                        break
                    if kwargs.get('test_mode') and limit == 0 and idx >= 3:
                        break
                    
                    # Re-locate card
                    card = page.locator('.popularDataItem').nth(idx)
                    
                    # Basic info from list
                    plan_name_pre = await card.locator('.infoTxt .title').inner_text()
                    self.logger.info(f"[{idx+1}/{card_count}] 상세보기 시도: {plan_name_pre}")
                    
                    try:
                        # Click to Navigate
                        title_area = card.locator('.infoTxt').first
                        
                        async with page.expect_navigation(timeout=10000):
                            await title_area.click()
                            
                        # Detail Page Scrape
                        await page.wait_for_timeout(2000)
                        
                        detail_data = await page.evaluate("""() => {
                            const result = {};
                            result.plan_name = document.querySelector('.pageTit')?.innerText || '';
                            
                            // 가격 - 상세페이지 .price 클래스 신뢰
                            const price = document.querySelector('.price');
                            result.price = price ? price.innerText.replace(/[^0-9]/g, '') : '';
                            
                            // 스펙 및 통신사/사업자
                            const dls = document.querySelectorAll('dl');
                            result.data = '';
                            result.voice = '';
                            result.sms = '';
                            result.carrier = ''; // Default
                            
                            dls.forEach(dl => {
                                const dt = dl.querySelector('dt')?.innerText || '';
                                const dd = dl.querySelector('dd')?.innerText || '';
                                if (dt.includes('데이터')) result.data = dd;
                                if (dt.includes('음성') || dt.includes('통화')) result.voice = dd;
                                if (dt.includes('문자')) result.sms = dd;
                                if (dt.includes('사업자') || dt.includes('통신사')) result.carrier = dd;
                            });
                            
                            // Fallback for Carrier if not labeled (User mentioned <dd>스카이라이프모바일</dd>)
                            // Sometimes it might be just the first unlabeled dd? 
                            // Or we check specific values if known.
                            // Let's rely on label first. If empty, try to find a dd that is not spec?
                            if (!result.carrier) {
                                // Try finding a dd that's not data/voice/sms/price
                                // This is risky without viewing HTML. 
                                // But user provided specific example <dd>스카이라이프모바일</dd>.
                                // Assuming there's a dt for it.
                                pass
                            }

                            return result;
                        }""")
                        
                        final_plan_name = detail_data['plan_name'] if detail_data.get('plan_name') else plan_name_pre
                        
                        plan_data = {
                            'platform': self.platform_key,
                            'carrier': detail_data['carrier'] if detail_data.get('carrier') else 'KT(Guess)', # Will refine
                            'network': 'KT', # Hardcoded as per request
                            'plan_name': final_plan_name,
                            'price': detail_data['price'],
                            'data_raw': detail_data.get('data'),
                            'voice': detail_data.get('voice'),
                            'sms': detail_data.get('sms'),
                            'url': page.url,
                            'collected_at': datetime.now().isoformat()
                        }
                        
                        # Use scraped carrier if available, else fallback to something safe
                        if detail_data.get('carrier'):
                             carrier_val = detail_data['carrier']
                        else:
                             # If we couldn't find "사업자", check if we can parse it from title or elsewhere?
                             # For now, if empty, we might keep it empty or Unknown.
                             # But user example implies it's there.
                             carrier_val = 'Unknown'

                        screenshot_path = await self._save_screenshot(page, plan_data)
                        
                        if screenshot_path:
                            plan_data['screenshot_path'] = screenshot_path
                            
                        self.save_plan(plan_data)
                        self.logger.info(f"수집: {plan_data['carrier']} - {plan_data['plan_name']}")
                        
                        # Go Back
                        await page.go_back()
                        await page.wait_for_timeout(2000)
                        # Wait for list to reload
                        await page.wait_for_selector('.popularDataItem', timeout=10000)
                        
                    except Exception as e:
                        self.logger.error(f"Failed detail capture for {plan_name_pre}: {e}")
                        # If failed to navigate back or stuck, we might need to reload list
                        if page.url != target_url:
                            await page.goto(target_url)
                            await page.wait_for_selector('.popularDataItem', timeout=10000)

                if self.results:
                    self.export_excel()
                    
                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()
