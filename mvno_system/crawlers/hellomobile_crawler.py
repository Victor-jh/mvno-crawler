from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio
import re
from datetime import datetime

class HelloMobileCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('hellomobile')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("헬로모바일 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                # 1. 목록 페이지 접속
                target_url = self.selectors.get('url', f"{self.config['base_url']}/rate/rateViewUsim.do")
                await page.goto(target_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # 팝업 닫기
                try:
                    close_btns = await page.locator('.btn_close, .btn-close, button:has-text("닫기")').all()
                    for btn in close_btns:
                         if await btn.is_visible():
                             await btn.click()
                             await page.wait_for_timeout(500)
                except:
                    pass
                
                # 2. 더보기 버튼 클릭 Loop
                while True:
                    if kwargs.get('test_mode'): 
                        break

                    try:
                        # #moreBtn
                        more_btn = page.locator('#moreBtn')
                        if await more_btn.is_visible():
                            await more_btn.click()
                            await page.wait_for_timeout(1500) # Wait for ajax load
                        else:
                            break
                    except:
                        break
                
                # 3. 데이터 수집 (리스트 순회하며 팝업 오픈)
                await page.wait_for_selector('li.list-item', timeout=10000)
                
                # Get all items first
                items_count = await page.locator('li.list-item').count()
                self.logger.info(f"발견된 요금제: {items_count}개")
                
                for i in range(items_count):
                    limit = kwargs.get('limit', 0)
                    if limit > 0 and i >= limit:
                        break
                    if kwargs.get('test_mode') and limit == 0 and i >= 3:
                        break

                    try:
                        # Re-locate item to avoid stale element reference
                        item = page.locator('li.list-item').nth(i)
                        
                        # Basic Info from List (PlanName)
                        plan_name_el = item.locator('.plan-rate-name')
                        plan_name = await plan_name_el.inner_text() if await plan_name_el.count() > 0 else ''
                        
                        if not plan_name:
                            continue
                            
                        # Click for Detail (Popup)
                        trigger = item.locator('.info-wrap')
                        await trigger.click()
                        
                        # Wait for Modal
                        modal = page.locator('.plans-modal')
                        try:
                            await modal.wait_for(state="visible", timeout=5000)
                        except:
                            self.logger.warning(f"모달 로딩 실패: {plan_name}")
                            continue

                        await page.wait_for_timeout(500)
                        
                        # Scrape Detail from Modal
                        detail_data = await page.evaluate("""() => {
                            const result = {};
                            const modal = document.querySelector('.plans-modal');
                            if(!modal) return result;
                            
                            // Price
                            const priceEl = modal.querySelector('.price strong, .price-area strong');
                            result.price = priceEl ? priceEl.innerText.replace(/[^0-9]/g, '') : '0';
                            
                            // Specs (Data, Voice, SMS)
                            const specItems = modal.querySelectorAll('.spec-list li, .product-spec li, .pop-spec li');
                            specItems.forEach(li => {
                                const txt = li.innerText;
                                if (txt.includes('데이터')) result.data = li.querySelector('.val, strong')?.innerText || li.innerText;
                                if (txt.includes('음성')) result.voice = li.querySelector('.val, strong')?.innerText || li.innerText;
                                if (txt.includes('문자')) result.sms = li.querySelector('.val, strong')?.innerText || li.innerText;
                            });
                            
                            return result;
                        }""")
                        
                        # Network detection fallback (from list badge or modal)
                        network_badge = ''
                        badges = item.locator('.badge-network, .network-type, .badge.lg, .badge.kt, .badge.sk')
                        if await badges.count() > 0:
                            network_badge = await badges.first.inner_text()

                        plan_data = {
                            'platform': self.platform_key,
                            'carrier': 'HelloMobile',
                            'network': network_badge.strip() if network_badge else 'Unknown',
                            'plan_name': plan_name,
                            'price': detail_data.get('price'),
                            'data_raw': detail_data.get('data'),
                            'voice': detail_data.get('voice'),
                            'sms': detail_data.get('sms'),
                            'url': target_url, 
                            'collected_at': datetime.now().isoformat()
                        }
                        
                        # Save
                        self.save_plan(plan_data)
                        
                        # Screenshot of Modal
                        await self._save_screenshot(page, plan_data)
                        
                        self.logger.info(f"수집: {plan_data['carrier']} - {plan_data['plan_name']}")
                        
                        # Close Modal
                        try:
                            # 1. Try JS Hide/Close first (Fastest)
                            await page.evaluate("""() => {
                                const modal = document.querySelector('.plans-modal');
                                const dim = document.querySelector('.dim');
                                if(modal) modal.style.display = 'none';
                                if(dim) dim.style.display = 'none';
                                
                                // Also try standard close function
                                if(typeof closeModal === 'function') closeModal('plans-modal');
                            }""")
                            
                            # 2. Click button if still visible
                            if await modal.is_visible():
                                close_btn = modal.locator('.modal_close_btn, .btn-close, .btn_close, button:has-text("닫기")').first
                                if await close_btn.is_visible():
                                    await close_btn.click(force=True)
                            
                            # 3. Wait for hidden
                            await modal.wait_for(state="hidden", timeout=3000)
                            
                        except Exception as e:
                            self.logger.warning(f"모달 닫기 실패: {e}")
                            # Final Force Hide
                            await page.evaluate("document.querySelectorAll('.plans-modal, .dim').forEach(el => el.style.display='none')")
                            
                    except Exception as e:
                        self.logger.error(f"상세 수집 실패 (Item {i}): {e}")
                        continue

                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()
