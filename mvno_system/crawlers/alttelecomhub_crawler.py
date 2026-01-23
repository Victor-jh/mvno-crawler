from .base_crawler import BaseCrawler
from playwright.async_api import async_playwright
import asyncio
from datetime import datetime
import re

class HubCrawler(BaseCrawler):
    def __init__(self):
        super().__init__('alttelecomhub')
        
    async def crawl(self, headless=False, **kwargs):
        self.logger.info("알뜰폰허브 크롤링 시작")
        self.start_crawl_log()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
            page = await context.new_page()
            
            try:
                # 1. 목록 페이지 접속
                target_url = f"{self.config['base_url']}/product/products.do"
                await page.goto(target_url, wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # 팝업 닫기
                try:
                    await page.click('.layer_popup .btn_close', timeout=1000)
                except:
                    pass

                # 2. 메타데이터 및 URL 수집 (Hybrid Approach)
                # 리스트에서만 얻을 수 있는 정보(통신사, 망 등 relative selector로 쉬운 것)를 먼저 수집
                
                # selectors.yaml: a.click-guard[href*="/product/products/"]
                selector = 'a.click-guard[href*="/product/products/"]' 
                # Fallback
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                except:
                    selector = 'a[href*="/product/products/"]'
                    await page.wait_for_selector(selector, timeout=5000)
                
                cards = await page.locator(selector).all()
                self.logger.info(f"발견된 요금제 카드: {len(cards)}개")
                
                metadata_list = []
                for idx, card in enumerate(cards):
                    limit = kwargs.get('limit', 0)
                    if limit > 0 and idx >= limit:
                        break
                    if kwargs.get('test_mode') and limit == 0 and idx >= 3:
                        break
                        
                    # 리스트 정보 추출
                    meta = await card.evaluate("""(card) => {
                        const result = {};
                        
                        // 제목
                        const tit = card.querySelector('p.tit');
                        result.plan_name = tit ? tit.innerText.trim() : '';

                        // 통신사/망 정보 (이미지 기반)
                        result.network = 'Unknown';
                        result.carrier = 'Unknown';
                        
                        // 1. 이미지 Alt에서 찾기
                        const imgs = card.querySelectorAll('img');
                        imgs.forEach(img => {
                             const alt = img.alt || '';
                             // 망
                             if (alt.includes('KT') || alt.includes('kt')) result.network = 'KT';
                             if (alt.includes('SKT') || alt.includes('skt') || alt.includes('SK')) result.network = 'SKT';
                             if (alt.includes('LGU+') || alt.includes('LG') || alt.includes('lgu')) result.network = 'LGU+';
                             
                             // 사업자 (이미지 alt가 보통 사업자명임, 예: 리브엠, 아이즈모바일)
                             // 망 이름이 아닌 경우 사업자명으로 간주 (단, '요금제', '혜택' 등 제외)
                             if (alt.length > 1 && !alt.includes('요금제') && !alt.includes('혜택') && !alt.includes('이벤트')) {
                                  // 망 키워드가 없는 경우에만 carrier로 설정하거나, 
                                  // 망 키워드가 있더라도 분리할 수 없으면 전체를 carrier로
                                  if (!['KT', 'SKT', 'LGU+', 'LG'].some(k => alt.includes(k))) {
                                       result.carrier = alt;
                                  }
                             }
                        });
                        
                        // 2. Plan Name에서 망 추론 ([K], [S], [L])
                        if (result.network === 'Unknown' && result.plan_name) {
                             if (result.plan_name.includes('[K]') || result.plan_name.includes('(K)')) result.network = 'KT';
                             if (result.plan_name.includes('[S]') || result.plan_name.includes('(S)')) result.network = 'SKT';
                             if (result.plan_name.includes('[L]') || result.plan_name.includes('(L)')) result.network = 'LGU+';
                        }
                        
                        // 3. Fallback: Carrier가 여전히 Unknown이면, Network와 동일하게라도 설정
                        if (result.carrier === 'Unknown' && result.network !== 'Unknown') {
                            result.carrier = result.network + ' MVNO'; 
                        }
                        
                        // href
                        result.href = card.getAttribute('href');
                        
                        return result;
                    }""")
                    
                    if meta.get('href'):
                        meta['full_url'] = f"{self.config['base_url']}{meta['href']}"
                        metadata_list.append(meta)

                self.logger.info(f"수집된 요금제 메타데이터: {len(metadata_list)}개")
                
                # 3. 상세 페이지 순회 및 수집
                for idx, meta in enumerate(metadata_list):
                    url = meta['full_url']
                    
                    # Skip if meta has no plan_name or generic
                    if not meta.get('plan_name'):
                        continue
                        
                    limit = kwargs.get('limit', 0)
                    # Check limit based on collected count so far (not just loop index if we skip)
                    # For simplicity, just use loop index
                    
                    self.logger.info(f"[{idx+1}/{len(metadata_list)}] 상세 이동: {url}")
                    
                    try:
                        await page.goto(url, wait_until='domcontentloaded')
                        await page.wait_for_timeout(2000) # Wait for render
                        
                        # 상세 데이터 추출
                        # List에서 가져온 plan_name이 더 정확할 수 있음 (상세페이지 타이틀이 이벤트명인 경우 등)
                        # 따라서 상세에서는 Price, Data, Voice, SMS 위주로 보강하거나, 
                        # List 정보를 우선시하되 상세에서 없으면 채워넣는 방식 사용.
                        
                        detail_data = await page.evaluate("""() => {
                            const result = {};
                            
                            // 가격
                            const price = document.querySelector('.price');
                            result.price = price ? price.innerText.replace(/[^0-9]/g, '') : '';
                            
                            // 스펙
                            const dls = document.querySelectorAll('dl');
                            result.data = '';
                            result.voice = '';
                            result.sms = '';
                            
                            dls.forEach(dl => {
                                const dt = dl.querySelector('dt')?.innerText || '';
                                const dd = dl.querySelector('dd')?.innerText || '';
                                if (dt.includes('데이터')) result.data = dd;
                                if (dt.includes('음성') || dt.includes('통화')) result.voice = dd;
                                if (dt.includes('문자')) result.sms = dd;
                            });
                            
                            // 통신망 및 사업자 (User supplied: <li>KT</li>, <li>스마텔</li>)
                            // Look for li tags containing specific network names
                            result.network = '';
                            result.carrier = '';
                            
                            const lis = document.querySelectorAll('li');
                            lis.forEach(li => {
                                const txt = li.innerText.trim();
                                // Network Check
                                if (txt === 'KT' || txt === 'SKT' || txt === 'LGU+') {
                                    result.network = txt;
                                }
                                
                                // Carrier Check
                                // Assumption: Carrier is also in an li, and is NOT a network name.
                                // We might need a list of known MVNOs or just take 'li' that looks like a carrier?
                                // Or maybe they are siblings?
                                // User example: <li>KT</li>, <li>스마텔</li>.
                                // If they are in the same list (ul), maybe we can infer?
                                // For now, if we find a list item that is NOT network, NOT specs, maybe it's carrier?
                                // Or we specifically look for known text or length.
                                // Let's try to capture '스마텔', '프리티', etc.
                            });
                            
                            // Parsing refined: try to find the ul holding the network
                            if (result.network) {
                                // Find parent ul of the network li
                                Array.from(document.querySelectorAll('li')).forEach(li => {
                                    if (li.innerText.trim() === result.network) {
                                        const parent = li.parentElement;
                                        if (parent) {
                                            const siblings = parent.querySelectorAll('li');
                                            // Siblings: [Network, Carrier] or [Carrier, Network]?
                                            // usually text is like "KT", "스마텔", "LTE"
                                            siblings.forEach(sib => {
                                                const t = sib.innerText.trim();
                                                const ignored = ['LTE', '5G', '3G', result.network];
                                                
                                                if (!ignored.includes(t) && t.length > 0 && !t.includes('원') && !t.includes('데이터')) {
                                                    result.carrier = t;
                                                }
                                            });
                                        }
                                    }
                                });
                            }

                            return result;
                        }""")
                        
                        # Merge Data
                        # Prefer Detail page info if found, else List info (meta)
                        final_network = detail_data.get('network') if detail_data.get('network') else meta.get('network', 'Unknown')
                        final_carrier = detail_data.get('carrier') if detail_data.get('carrier') else meta.get('carrier', 'Unknown')
                        
                        plan_data = {
                            'platform': self.platform_key,
                            'carrier': final_carrier,
                            'network': final_network,
                            'plan_name': meta.get('plan_name', 'Unknown'), # List Name preferred
                            'price': detail_data.get('price') or '0',
                            'data_raw': detail_data.get('data', ''),
                            'voice': detail_data.get('voice', ''),
                            'sms': detail_data.get('sms', ''),
                            'url': url,
                            'collected_at': datetime.now().isoformat()
                        }
                        
                        # 스크린샷
                        screenshot_path = await self._save_screenshot(page, plan_data)
                        
                        if screenshot_path:
                            plan_data['screenshot_path'] = screenshot_path
                            
                        self.save_plan(plan_data)
                        
                    except Exception as e:
                        self.logger.error(f"상세 수집 실패 ({url}): {e}")
                
                if self.results:
                    self.export_excel()
                    
                self.finish_crawl_log(status='success')
                
            except Exception as e:
                self.logger.error(f"크롤링 에러: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                self.finish_crawl_log(status='failed', error=e)
            finally:
                await browser.close()
                
