from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio
import re

class SmarterCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('smarter')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("스마텔 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                base_url = self.selectors.get('url', "https://smartel.kr/phoneplan")
                await page.goto(base_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # Close Popups
                try:
                    close_btns = await page.locator('.modal-close, .close-btn, button:has-text("닫기"), img[alt="닫기"]').all()
                    for btn in close_btns:
                        if await btn.is_visible():
                            await btn.click()
                            await page.wait_for_timeout(500)
                except:
                    pass
                
                # Carriers to crawl
                # Tabs: SKT망, KT망, LGU+망 (Using labels)
                carriers = [
                    {'name': 'SKT', 'selector': 'label[for="skt"]'},
                    {'name': 'KT', 'selector': 'label[for="kt"]'},
                    {'name': 'LGU+', 'selector': 'label[for="lg"]'}
                ]
                
                total_items = 0
                
                for carrier in carriers:
                    self.logger.info(f"[{carrier['name']}] 요금제 수집 시작")
                    
                    # Click filter tab
                    try:
                        # Find tab by selector
                        tab = page.locator(carrier['selector']).first
                        
                        if await tab.is_visible():
                            await tab.click()
                            await page.wait_for_timeout(2000)
                        else:
                            self.logger.warning(f"필터 탭 찾을 수 없음: {carrier['name']}")
                    except Exception as e:
                        self.logger.error(f"필터 클릭 중 에러 ({carrier['name']}): {e}")
                        continue
                        
                    # Scroll down to load all
                    # Agent said "no pagination ... long vertical list"
                    # Scroll multiple times
                    for i in range(5):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(1000)
                    
                    await page.wait_for_timeout(2000)
                    
                    # Extract items
                    items = await page.evaluate(f"""(network) => {{
                        const list = [];
                        // Use href selector to catch both Mobile and PC versions
                        const items = document.querySelectorAll('a[href^="/phoneplan/"]');
                        
                        // Filter out hidden items to avoid duplicates if both exist
                        const visibleItems = Array.from(items).filter(item => {{
                            return item.offsetWidth > 0 && item.offsetHeight > 0;
                        }});
                        
                        visibleItems.forEach(item => {{
                            const result = {{}};
                            
                            // Carrier
                            // Often inside span > span as per analysis e.g. "SKT"
                            const spans = item.querySelectorAll('span span');
                            let carrierBadge = '';
                            spans.forEach(s => {{
                                const txt = s.innerText.trim();
                                if (txt === 'SKT' || txt === 'KT' || txt === 'LG U+') carrierBadge = txt;
                            }});
                            
                            result.carrier = 'Smarter (' + (carrierBadge || network) + ')';
                            
                            // Plan Name
                            const nameEl = item.querySelector('h1');
                            result.plan_name = nameEl ? nameEl.innerText.trim() : '';
                            
                            // Text parsing for Data/Voice/SMS/Price
                            const fullText = item.innerText;
                            
                            // Data
                            // Regex: 총\s*(.+) or similar. Simply look for GB/MB lines
                            const dataMatch = fullText.match(/총\\s*(.+)/);
                            if (dataMatch) result.data = dataMatch[1].trim();
                            else {{
                                // Fallback: find line with GB
                                const lines = fullText.split('\\n');
                                for (const line of lines) {{
                                    if (line.includes('GB') || line.includes('MB')) {{
                                        result.data = line.trim();
                                        break;
                                    }}
                                }}
                            }}
                            
                            // Voice
                            const voiceMatch = fullText.match(/(\\d+분)/);
                            if (voiceMatch) result.voice = voiceMatch[1];
                            else if (fullText.includes('기본 제공')) result.voice = '기본 제공';
                            
                            // SMS
                            const smsMatch = fullText.match(/(\\d+건)/);
                            if (smsMatch) {{ 
                                // Assign to voice field if needed or handle separately? 
                                // BaseCrawler expects 'voice' often to include sms or separate?
                                // Let's append to voice if no separate field in BaseCrawler standard, 
                                // but we do have 'details'.
                            }}
                            
                            // Price
                            // Regex: match number before '원' that is NOT '개월' context
                            // Simple approach: Find distinct price-like line, usually the largest number or last number
                            // Analysis said "Large numeric text"
                            // Let's try to match lines that end with '원' and have digits
                            const priceMatch = fullText.match(/월\\s*([\\d,]+)\\s*원/);
                            if (priceMatch) result.price = priceMatch[1];
                            else {{
                                // Try finding any number + 원
                                const matches = fullText.match(/([\\d,]+)원/g);
                                if (matches && matches.length > 0) {{
                                     // Provide the first one as it's often the main price
                                     result.price = matches[0].replace('원', '');
                                }} else {{
                                     result.price = '0';
                                }}
                            }}
                            
                            list.push(result);
                        }});
                        
                        return list;
                    }}""", carrier['name'])
                    
                    self.logger.info(f"[{carrier['name']}] 수집된 요금제: {len(items)}개")
                    
                    valid_count = 0
                    for item in items:
                        limit = kwargs.get('limit', 0)
                        if limit > 0 and valid_count >= limit:
                            break
                        if kwargs.get('test_mode') and limit == 0 and valid_count >= 3:
                            break
                        
                        if not item['plan_name']:
                            continue

                        valid_count += 1
                        total_items += 1
                        
                        plan_data = {
                            'platform': self.platform_key,
                            'carrier': item.get('carrier'),
                            'plan_name': item.get('plan_name'),
                            'price': item.get('price'),
                            'data_raw': item.get('data'),
                            'url': base_url, 
                            'details': item
                        }
                        
                        plan_data['screenshot_path'] = 'captured_in_list'
                        
                        self.save_plan(plan_data)
                        self.logger.info(f"수집: {plan_data['carrier']} - {plan_data['plan_name']}")
                
                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()
