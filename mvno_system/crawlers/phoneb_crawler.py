from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio
import re
from datetime import datetime

class PhonebCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('phoneb')
        
    async def crawl(self, headless=False, selection_mode='auto', **kwargs):
        """
        폰비 크롤링 메인 로직
        """
        self.logger.info("폰비 크롤링 시작")
        
        # DB 로그 시작
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            error_occured = None
            try:
                # 1. 접속
                await page.goto(f"{self.config['base_url']}/plans", wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)
                
                # 2. 필터 및 정렬 설정 (간소화: 전체 수집 기준)
                await self._set_sorting(page)
                
                # 3. URL 수집
                plan_urls = await self._get_plan_urls(page)
                self.logger.info(f"수집된 요금제 URL: {len(plan_urls)}개")
                
                # 4. 상세 수집
                for idx, url in enumerate(plan_urls, 1):
                    self.logger.info(f"[{idx}/{len(plan_urls)}] 상세 수집: {url}")
                    plan_data = await self._crawl_plan_detail(page, url)
                    if plan_data:
                        # DB 저장 (BaseCrawler 메서드)
                        self.save_plan(plan_data)
                        
                    # 테스트 모드라면 앞 3개만 수집하고 종료 (속도 위해)
                    # 수집 제한 및 테스트 모드 체크
                    limit = kwargs.get('limit', 0)
                    if limit > 0 and idx >= limit:
                        self.logger.info(f"수집 제한({limit}개) 도달로 종료")
                        break
                        
                    if kwargs.get('test_mode') and limit == 0 and idx >= 3:
                        self.logger.info("테스트 모드: 3개 수집 후 종료")
                        break
                        
                # 5. 결과 저장
                if self.results:
                    self.export_excel() # 엑셀 출력 추가
                    # self.export_json()
                
                # 정상 종료 로그
                self.finish_crawl_log(status='success')
                
            except Exception as e:
                error_occured = e
                self.logger.error(f"크롤링 중 에러: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                
                # 실패 로그
                self.finish_crawl_log(status='failed', error=e)
                
            finally:
                await browser.close()

    async def _set_sorting(self, page):
        """데이터 많은 순 정렬 (Selectors.yaml 활용)"""
        try:
            await page.click(self.selectors['list']['sort_btn'])
            await page.wait_for_timeout(500)
            await page.locator('li:has-text("데이터 많은 순")').click()
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2000)
        except Exception as e:
            self.logger.warning(f"정렬 설정 실패: {e}")

    async def _get_plan_urls(self, page):
        """URL 수집 로직 (기존 코드 단순화 이식)"""
        all_urls = []
        visited_urls = set()
        
        # 첫 페이지 수집
        links = await page.locator(self.selectors['list']['item_card']).all()
        for link in links:
            href = await link.get_attribute('href')
            if href:
                full_url = f"{self.config['base_url']}{href}"
                if full_url not in visited_urls:
                    visited_urls.add(full_url)
                    all_urls.append(full_url)
                    
        return all_urls

    async def _crawl_plan_detail(self, page, url):
        """상세 페이지 파싱"""
        try:
            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            
            # Selectors 활용하여 데이터 추출
            # (복잡한 로직은 JS evaluation 사용이 유리하므로 유지)
            data = await page.evaluate('''() => {
                const result = {};
                // 통신사
                const carrierImg = document.querySelector('article img[alt*="모바일"]');
                result.carrier = carrierImg?.alt?.replace('폰비, ', '').replace(' 로고', '') || '';
                
                // 요금제명 (CSS Selector 변수화 필요하나 일단 하드코딩된 JS 유지 후 추후 매핑)
                const planNameSpan = document.querySelector('._1sdiozaf');
                result.planName = planNameSpan?.textContent || '';
                
                // 가격
                const prices = Array.from(document.querySelectorAll('._1sdiozam'));
                result.price = prices[0]?.textContent?.replace(/,/g, '') || '';
                
                // 데이터
                const dataSpan = document.querySelector('._1sdiozag');
                result.dataInfo = dataSpan?.textContent || '';
                
                return result;
            }''')
            
            # 파이썬 레벨 가공
            # PhoneB carrier string usually looks like "KT 이지모바일" or just "이지모바일"
            carrier_str = data.get('carrier', '')
            
            # Network Detection Strategy:
            # 1. Check carrier string
            # 2. Check body text for 'KT망', 'SKT망', 'LGU망'
            network_name = 'Unknown'
            
            if 'KT' in carrier_str.upper():
                network_name = 'KT'
            elif 'SKT' in carrier_str.upper() or 'SK' in carrier_str.upper():
                network_name = 'SKT'
            elif 'LG' in carrier_str.upper():
                network_name = 'LGU+'
            else:
                # Fallback to body text search
                try:
                    body_text = await page.inner_text('body')
                    if 'KT망' in body_text or 'KT 망' in body_text:
                        network_name = 'KT'
                    elif 'SKT망' in body_text or 'SKT 망' in body_text or 'SK망' in body_text:
                        network_name = 'SKT'
                    elif 'LGU망' in body_text or 'LGU+망' in body_text or 'LG망' in body_text:
                        network_name = 'LGU+'
                except:
                    pass
            
            final_data = {
                'platform': self.platform_key,
                'carrier': carrier_str,
                'network': network_name, # Added network
                'plan_name': data.get('planName'),
                'price': data.get('price'),
                'data_raw': data.get('dataInfo'),
                'url': url,
                'collected_at': datetime.now().isoformat()
            }
            
            # 스크린샷 캡처
            # Standardized: Network_Carrier_Platform_PlanName_Timestamp
            
            screenshot_path = await self._save_screenshot(page, final_data)
            
            if screenshot_path:
                 final_data['screenshot_path'] = screenshot_path
            
            return final_data
            
        except Exception as e:
            self.logger.error(f"상세 페이지 에러 ({url}): {e}")
            return None
