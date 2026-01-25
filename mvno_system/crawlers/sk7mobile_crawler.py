from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio
from datetime import datetime

class SK7MobileCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('sk7mobile')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("SK세븐모바일 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                # 1. 목록 페이지 접속
                target_url = self.selectors.get('url', f"{self.config['base_url']}/prod/data/callingPlanList.do?refCode=USIM")
                await page.goto(target_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # 팝업 닫기
                try:
                    close_btn = page.locator('.btn-close-popup, .layer-popup .btn-close')
                    if await close_btn.count() > 0:
                         await close_btn.first.click()
                         await page.wait_for_timeout(500)
                except:
                    pass

                # 2. 모든 카테고리 펼치기 (닫혀있는 경우)
                toggles = await page.locator('button.btn-toggle').all()
                for toggle in toggles:
                    try:
                        await toggle.click()
                        await page.wait_for_timeout(500)
                    except:
                        pass
                
                await page.wait_for_timeout(1000)

                # 3. 요금제 카드 로딩 대기 및 수집
                try:
                    await page.wait_for_load_state('networkidle', timeout=10000)
                except:
                    pass
                
                try:
                    await page.wait_for_selector('a.planItem', timeout=30000)
                except Exception as e:
                    self.logger.error(f"요금제 목록 로딩 실패: {e}")
                    # Dump page content for debug if needed
                    # with open('sk7_error.html', 'w', encoding='utf-8') as f:
                    #     f.write(await page.content())
                    raise e
                
                if not kwargs.get('test_mode'):
                     await page.mouse.wheel(0, 5000)
                     await page.wait_for_timeout(2000)

                items = await page.evaluate("""() => {
                    const list = [];
                    const items = document.querySelectorAll('a.planItem');
                    
                    items.forEach(item => {
                        const result = {};
                        
                        // Extract ID from onclick="fnSearchView('PD00000296');"
                        const onclick = item.getAttribute('onclick');
                        const match = onclick ? onclick.match(/'([^']+)'/) : null;
                        const pkgCd = match ? match[1] : null;
                        
                        if (pkgCd) {
                            // Construct Detail URL
                            result.url = 'https://www.sk7mobile.com/prod/data/callingPlanView.do?pkgCd=' + pkgCd + '&refCode=USIM';
                            result.pkgCd = pkgCd;
                        } else {
                            result.url = null;
                        }
                        
                        // Basic Meta for fallback
                        const nameEl = item.querySelector('strong.name-area span.name');
                        result.plan_name = nameEl ? nameEl.innerText : '';
                        
                        list.push(result);
                    });
                    
                    return list;
                }""")
                
                self.logger.info(f"발견된 요금제 ID: {len(items)}개")
                
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
        """상세 페이지 수집"""
        self.logger.info(f"상세 이동: {url}")
        try:
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            
            # 상세 데이터 추출
            detail_data = await page.evaluate("""() => {
                const result = {};
                
                // 가격
                const priceEl = document.querySelector('.view-price strong');
                result.price = priceEl ? priceEl.innerText.replace(/[^0-9]/g, '') : '0';
                
                // Plan Name
                const nameEl = document.querySelector('.subject');
                result.plan_name = nameEl ? nameEl.innerText.trim() : '';
                
                // Specs (Data, Voice, SMS)
                const specs = document.querySelectorAll('.data-info-list li');
                specs.forEach(li => {
                    const txt = li.innerText;
                    if (txt.includes('데이터')) result.data = li.querySelector('.val')?.innerText;
                    if (txt.includes('음성')) result.voice = li.querySelector('.val')?.innerText;
                    if (txt.includes('문자')) result.sms = li.querySelector('.val')?.innerText;
                });
                
                return result;
            }""")
            
            final_plan_name = detail_data.get('plan_name') or meta.get('plan_name')
            
            plan_data = {
                'platform': self.platform_key,
                'carrier': 'SK세븐모바일',  # Standardized Korean name
                'network': 'SKT', 
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
