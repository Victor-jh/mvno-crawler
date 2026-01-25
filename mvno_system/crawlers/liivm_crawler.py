from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio
import re
from datetime import datetime

class LiivMCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('liivm')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("리브모바일 크롤링 시작 (Mobile URL Strategy)")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            # Use Mobile Viewport & User Agent to ensure m.liivm.com renders correctly
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={'width': 375, 'height': 812}, 
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
            )
            page = await context.new_page()
            
            try:
                # 1. 목록 페이지 접속 (Mobile URL)
                target_url = "https://m.liivm.com/rateplan/plans/products"
                self.logger.info(f"이동: {target_url}")
                await page.goto(target_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(5000)
                
                # 팝업 닫기
                try:
                    close_btns = await page.locator('.btn_close, .util_close, button:has-text("닫기")').all()
                    for btn in close_btns:
                        if await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(500)
                except:
                    pass

                # 2. 데이터 로딩 (무한 스크롤)
                # Scroll down to load more items
                self.logger.info("아이템 로딩 중...")
                last_height = await page.evaluate("document.body.scrollHeight")
                max_scrolls = 20
                scroll_count = 0
                
                while scroll_count < max_scrolls:
                    if kwargs.get('test_mode') and scroll_count > 2:
                        break
                        
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1500)
                    new_height = await page.evaluate("document.body.scrollHeight")
                    if new_height == last_height:
                        # Try button click if exists
                        try:
                            more_btn = page.locator('button:has-text("더보기")').first
                            if await more_btn.is_visible():
                                await more_btn.click()
                                await page.wait_for_timeout(1500)
                            else:
                                break
                        except:
                            break
                    last_height = new_height
                    scroll_count += 1
                    
                # 3. 데이터 수집
                # Find items with prodDetailPage onclick
                await page.wait_for_selector('[onclick*="prodDetailPage"]', timeout=10000)
                
                # Extract IDs for URL construction
                items_data = await page.evaluate("""() => {
                    const list = [];
                    // Look for elements calling prodDetailPage
                    const elements = document.querySelectorAll('[onclick*="prodDetailPage"]');
                    
                    elements.forEach(el => {
                        const soId = el.getAttribute('data-soId');
                        const prodGrpCd = el.getAttribute('data-prodGrpCd');
                        const prodCd = el.getAttribute('data-prodCd');
                        
                        // Try to find name/price in parent/sibling context if needed
                        // But usually we just need IDs to visit detail
                        // Let's grab name for logging
                        let container = el.closest('li') || el.closest('div.card_item') || el.closest('div');
                        let name = '';
                        if(container) {
                            const nameEl = container.querySelector('.tit, strong, .name');
                            if(nameEl) name = nameEl.innerText.trim();
                        }
                        
                        if(soId && prodGrpCd && prodCd) {
                            list.push({
                                soId: soId,
                                prodGrpCd: prodGrpCd,
                                prodCd: prodCd,
                                temp_name: name
                            });
                        }
                    });
                    return list;
                }""")
                
                self.logger.info(f"발견된 요금제(ID 추출): {len(items_data)}개")
                
                valid_count = 0
                for item in items_data:
                    limit = kwargs.get('limit', 0)
                    if limit > 0 and valid_count >= limit:
                        break
                    if kwargs.get('test_mode') and limit == 0 and valid_count >= 3:
                        break
                        
                    try:
                        # Construct Detail URL
                        # /rateplan/plans/product-detailed?soId=01&prodGrpCd=K01&prodCd=P000000001
                        detail_url = f"https://m.liivm.com/rateplan/plans/product-detailed?soId={item['soId']}&prodGrpCd={item['prodGrpCd']}&prodCd={item['prodCd']}"
                        
                        self.logger.info(f"상세 이동: {detail_url}")
                        await page.goto(detail_url, wait_until='domcontentloaded')
                        await page.wait_for_timeout(2000)
                        
                        # Scrape Detail Data
                        detail_data = await page.evaluate("""() => {
                            const result = {};
                            
                            // Plan Name
                            const titleEl = document.querySelector('.h2_tit, .tit_area h2');
                            result.plan_name = titleEl ? titleEl.innerText.trim() : '';
                            
                            // Price
                            const priceEl = document.querySelector('.price .num, .tit_area .price strong');
                            result.price = priceEl ? priceEl.innerText.replace(/[^0-9]/g, '') : '0';
                            
                            // Specs (Data, Voice, SMS)
                            // Look for spec list
                            const specs = document.querySelectorAll('dl.list_info dt, dl.list_info dd, .spec_list li');
                            // Generic text search in body or specific containers
                            result.data = 'Unknown';
                            result.voice = 'Unknown';
                            result.sms = 'Unknown';
                            
                            // Specific to LiivM Mobile structure
                            // Often .data_info .val or similar
                            // Let's try to parse the main spec area
                            const specArea = document.querySelector('.spec_area, .prod_spec');
                            if(specArea) {
                                const txt = specArea.innerText;
                                // Basic parsing if structured elements missing
                            }
                            
                            // Try generic list parsing
                            const listItems = document.querySelectorAll('li, dl');
                            listItems.forEach(li => {
                                const text = li.innerText;
                                if(text.includes('데이터') && !result.data.includes('GB')) {
                                     result.data = text.replace('데이터', '').trim();
                                }
                                if(text.includes('음성') || text.includes('통화')) {
                                     result.voice = text.replace('음성', '').replace('통화', '').trim();
                                }
                                if(text.includes('문자')) {
                                     result.sms = text.replace('문자', '').trim();
                                }
                            });
                            
                            return result;
                        }""")
                        
                        if not detail_data['plan_name']:
                            self.logger.warning("상세 페이지 로딩 실패 또는 이름 없음")
                            continue
                            
                        # Default carrier
                        carrier_name = "리브모바일"  # Standardized Korean name
                        # Network detection (LGU+ or KT or SKT)
                        # LiivM supports LGU+ and KT mostly
                        # Detect from page text
                        page_text = await page.content()
                        network_badge = "Unknown"
                        if "LGU+" in page_text or "LG U+" in page_text:
                            network_badge = "LGU+"
                        elif "KT" in page_text:
                            network_badge = "KT"
                        elif "SKT" in page_text or "SK" in page_text:
                            network_badge = "SKT"

                        plan_data = {
                            'platform': self.platform_key,
                            'carrier': carrier_name,
                            'network': network_badge,
                            'plan_name': detail_data['plan_name'],
                            'price': detail_data.get('price'),
                            'data_raw': detail_data.get('data'),
                            'voice': detail_data.get('voice'),
                            'sms': detail_data.get('sms'),
                            'url': detail_url, 
                            'collected_at': datetime.now().isoformat()
                        }
                        
                        # Save
                        self.save_plan(plan_data)
                        
                        # Screenshot
                        # Pass plan_data object for standardized naming
                        await self._save_screenshot(page, plan_data)
                        
                        self.logger.info(f"수집: {plan_data['carrier']} - {plan_data['plan_name']}")
                        valid_count += 1
                        
                    except Exception as e:
                        self.logger.error(f"상세 수집 실패 ({item.get('temp_name')}): {e}")
                        continue

                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()
