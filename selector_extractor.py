"""
=============================================================================
인터랙티브 셀렉터 추출 도구 v3.0 (Full Browser Mode)
=============================================================================
모든 조작을 브라우저 내에서 수행 (터미널 의존 최소화)
- 브라우저 내 필드명 입력/선택
- 페이지 이동 시 자동 패널 재주입
- 실시간 셀렉터 미리보기
=============================================================================
"""

import asyncio
import sys
import os
import yaml
from datetime import datetime
from playwright.async_api import async_playwright

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# 자주 사용하는 필드명 프리셋 (필드명: 한글설명)
FIELD_PRESETS = {
    # === 목록 페이지 ===
    "list.item_card": "📋 [목록] 요금제 카드",
    "list.plan_name": "📋 [목록] 요금제명", 
    "list.price_base": "📋 [목록] 기본료",
    "list.price_contract": "📋 [목록] 약관금액",
    "list.price_discounted": "📋 [목록] 할인 후 금액",
    "list.discount_months": "📋 [목록] 할인 개월",
    "list.data": "📋 [목록] 데이터",
    "list.voice": "📋 [목록] 음성통화",
    "list.sms": "📋 [목록] 문자",
    "list.carrier_badge": "📋 [목록] 통신사 배지",
    "list.network_badge": "📋 [목록] 통신망 배지",
    "list.more_btn": "📋 [목록] 더보기 버튼",
    # === 상세 페이지 ===
    "detail.plan_name": "📄 [상세] 요금제명",
    "detail.price_base": "📄 [상세] 기본료",
    "detail.price_contract": "📄 [상세] 약관금액",
    "detail.price_discounted": "📄 [상세] 할인 후 금액",
    "detail.discount_months": "📄 [상세] 할인 개월",
    "detail.discount_info": "📄 [상세] 할인 정보",
    "detail.data": "📄 [상세] 데이터",
    "detail.voice": "📄 [상세] 음성통화", 
    "detail.sms": "📄 [상세] 문자",
    "detail.carrier": "📄 [상세] 통신사",
    "detail.network": "📄 [상세] 통신망",
    "detail.gift": "📄 [상세] 사은품/경품",
    "detail.event": "📄 [상세] 이벤트",
    "detail.usim_fee": "📄 [상세] 유심비용",
    # === 기타 ===
    "url": "🔗 상세페이지 URL",
}


class SelectorExtractor:
    """브라우저 기반 셀렉터 추출기"""
    
    def __init__(self):
        self.extracted_selectors = {}
        self.current_platform = None
        
    async def run(self, platform_key: str, url: str = None):
        self.current_platform = platform_key
        
        # 기존 셀렉터 로드
        selector_path = f"mvno_system/config/selectors/{platform_key}.yaml"
        if os.path.exists(selector_path):
            with open(selector_path, 'r', encoding='utf-8') as f:
                self.extracted_selectors = yaml.safe_load(f) or {}
        
        # URL 결정
        if not url:
            platforms_path = "mvno_system/config/platforms.yaml"
            with open(platforms_path, 'r', encoding='utf-8') as f:
                platforms = yaml.safe_load(f)
            platform_data = platforms['platforms'].get(platform_key, {})
            url = platform_data.get('base_url', '')
            platform_name = platform_data.get('name', platform_key)
        else:
            platform_name = platform_key
        
        self._print_header(platform_key, platform_name, url)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(viewport={'width': 1400, 'height': 900})
            page = await context.new_page()
            
            # 페이지 이동 시 자동으로 패널 재주입
            page.on("load", lambda: asyncio.create_task(self._inject_panel_safe(page, platform_name)))
            
            # 초기 패널 주입
            await self._inject_visual_ui(page, platform_name)
            
            if url:
                await page.goto(url, wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)
            
            # 메인 루프 - 브라우저에서 추출 완료 신호 대기
            print("\n💡 브라우저 패널에서 필드를 선택하고 요소를 클릭하세요.")
            print("   터미널 명령: s=저장, v=보기, q=종료\n")
            
            while True:
                try:
                    # 터미널 입력 (비동기)
                    user_input = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, 
                            lambda: input("🔷 명령 (s/v/q): ").strip()
                        ),
                        timeout=0.5
                    )
                    
                    if user_input.lower() == 'q':
                        break
                    elif user_input.lower() == 's':
                        # 브라우저에서 추출된 데이터 가져오기
                        await self._sync_from_browser(page)
                        self._save_selectors()
                    elif user_input.lower() == 'v':
                        await self._sync_from_browser(page)
                        self._show_selectors()
                        
                except asyncio.TimeoutError:
                    # 타임아웃은 정상 - 브라우저 상호작용 계속
                    pass
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\n\n저장하시겠습니까? (y/n): ", end="")
                    try:
                        if input().strip().lower() == 'y':
                            await self._sync_from_browser(page)
                            self._save_selectors()
                    except:
                        pass
                    break
            
            await browser.close()
            print("\n종료되었습니다.")
    
    async def _inject_panel_safe(self, page, platform_name):
        """안전하게 패널 주입 (에러 무시)"""
        try:
            await asyncio.sleep(1)
            await self._inject_visual_ui(page, platform_name)
        except:
            pass
    
    async def _inject_visual_ui(self, page, platform_name):
        """브라우저에 완전한 UI 패널 주입"""
        # 한글 라벨 포함 옵션 생성
        field_options = "\n".join([f'<option value="{k}">{v} ({k})</option>' for k, v in FIELD_PRESETS.items()])
        
        await page.evaluate(f"""() => {{
            // 기존 패널 제거
            const existing = document.getElementById('selector-panel');
            if (existing) existing.remove();
            
            // 스타일 추가
            if (!document.getElementById('selector-styles')) {{
                const style = document.createElement('style');
                style.id = 'selector-styles';
                style.textContent = `
                    #selector-panel * {{
                        box-sizing: border-box;
                    }}
                    #selector-panel input, #selector-panel select, #selector-panel button {{
                        font-family: 'Malgun Gothic', sans-serif;
                    }}
                    #selector-panel button:hover {{
                        opacity: 0.8;
                        transform: scale(1.02);
                    }}
                    #selector-panel .selector-item {{
                        animation: fadeIn 0.3s;
                    }}
                    @keyframes fadeIn {{
                        from {{ opacity: 0; transform: translateX(20px); }}
                        to {{ opacity: 1; transform: translateX(0); }}
                    }}
                `;
                document.head.appendChild(style);
            }}
            
            // 메인 패널 생성
            const panel = document.createElement('div');
            panel.id = 'selector-panel';
            panel.innerHTML = `
                <div style="
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    width: 340px;
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    border: 2px solid #00d4ff;
                    border-radius: 12px;
                    padding: 15px;
                    z-index: 999999;
                    font-family: 'Malgun Gothic', sans-serif;
                    color: #fff;
                    box-shadow: 0 8px 32px rgba(0, 212, 255, 0.3);
                    max-height: 90vh;
                    overflow-y: auto;
                ">
                    <!-- 헤더 -->
                    <div style="
                        font-size: 15px;
                        font-weight: bold;
                        margin-bottom: 12px;
                        padding-bottom: 10px;
                        border-bottom: 1px solid #00d4ff44;
                        display: flex;
                        align-items: center;
                        gap: 8px;
                    ">
                        <span style="font-size: 18px;">🔍</span>
                        셀렉터 추출기 - {platform_name}
                    </div>
                    
                    <!-- 필드 선택 영역 -->
                    <div style="margin-bottom: 12px;">
                        <label style="font-size: 11px; color: #aaa; display: block; margin-bottom: 4px;">
                            📌 필드명 선택 또는 입력:
                        </label>
                        <select id="field-select" style="
                            width: 100%;
                            padding: 8px;
                            border: 1px solid #00d4ff;
                            border-radius: 6px;
                            background: #0f3460;
                            color: #fff;
                            font-size: 13px;
                            margin-bottom: 6px;
                            cursor: pointer;
                        ">
                            <option value="">-- 프리셋에서 선택 --</option>
                            {field_options}
                        </select>
                        <input type="text" id="field-input" placeholder="직접 입력 (예: list.custom_field)" style="
                            width: 100%;
                            padding: 8px;
                            border: 1px solid #00d4ff55;
                            border-radius: 6px;
                            background: #0a1628;
                            color: #fff;
                            font-size: 12px;
                        "/>
                    </div>
                    
                    <!-- 상태 표시 -->
                    <div id="status-box" style="
                        background: #0f3460;
                        padding: 10px;
                        border-radius: 8px;
                        margin-bottom: 12px;
                        text-align: center;
                        font-size: 13px;
                        border-left: 3px solid #3498db;
                    ">
                        ⬆️ 필드를 선택한 후 요소를 클릭하세요
                    </div>
                    
                    <!-- 버튼 영역 -->
                    <div style="display: flex; gap: 6px; margin-bottom: 8px;">
                        <button id="btn-save" style="
                            flex: 2;
                            padding: 10px;
                            background: linear-gradient(135deg, #27ae60, #2ecc71);
                            color: #fff;
                            border: none;
                            border-radius: 6px;
                            cursor: pointer;
                            font-size: 13px;
                            font-weight: bold;
                        ">💾 저장하기</button>
                    </div>
                    <div style="display: flex; gap: 6px; margin-bottom: 12px;">
                        <button id="btn-undo" style="
                            flex: 1;
                            padding: 8px;
                            background: #f39c12;
                            color: #fff;
                            border: none;
                            border-radius: 6px;
                            cursor: pointer;
                            font-size: 12px;
                        ">↩️ 되돌리기</button>
                        <button id="btn-clear" style="
                            flex: 1;
                            padding: 8px;
                            background: #e74c3c;
                            color: #fff;
                            border: none;
                            border-radius: 6px;
                            cursor: pointer;
                            font-size: 12px;
                        ">🗑️ 초기화</button>
                    </div>
                    
                    <!-- 추출 목록 -->
                    <div style="font-size: 11px; color: #aaa; margin-bottom: 6px;">
                        📋 추출된 셀렉터 (터미널에서 's' 입력하여 저장):
                    </div>
                    <div id="selector-list" style="
                        background: #0a0a1a;
                        border-radius: 8px;
                        padding: 8px;
                        max-height: 250px;
                        overflow-y: auto;
                        font-family: 'Consolas', monospace;
                        font-size: 11px;
                    ">
                        <div class="empty-msg" style="color: #666; font-style: italic; text-align: center; padding: 10px;">
                            아직 추출된 셀렉터가 없습니다
                        </div>
                    </div>
                    
                    <!-- 힌트 -->
                    <div style="
                        margin-top: 10px;
                        font-size: 10px;
                        color: #666;
                        text-align: center;
                    ">
                        💡 Tip: 마우스를 올리면 요소가 하이라이트됩니다
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            // =========================================================
            // 전역 상태 및 데이터
            // =========================================================
            window.__selectorExtractor = {{
                lastSelector: null,
                isWaiting: false,
                lastHighlighted: null,
                extractedData: {{}},  // field -> selector 매핑
                history: []           // 되돌리기용
            }};
            
            // =========================================================
            // 셀렉터 생성 함수
            // =========================================================
            window.__generateSelector = (element) => {{
                if (!element) return null;
                if (element.id === 'selector-panel' || element.closest('#selector-panel')) return null;
                
                if (element.id && !element.id.match(/^[0-9]/)) {{
                    return '#' + element.id;
                }}
                
                if (element.className && typeof element.className === 'string') {{
                    const classes = element.className.trim().split(/\\s+/)
                        .filter(c => c && !c.match(/^[0-9]/) && c.length < 40 && !c.includes('hover') && !c.includes('active'));
                    if (classes.length > 0) {{
                        const selector = element.tagName.toLowerCase() + '.' + classes.slice(0, 3).join('.');
                        const count = document.querySelectorAll(selector).length;
                        if (count >= 1 && count <= 50) {{
                            return selector;
                        }}
                    }}
                }}
                
                const dataAttrs = Array.from(element.attributes)
                    .filter(a => a.name.startsWith('data-') && a.value.length < 50 && a.value.length > 0);
                for (const attr of dataAttrs) {{
                    const selector = element.tagName.toLowerCase() + `[${{attr.name}}="${{attr.value}}"]`;
                    if (document.querySelectorAll(selector).length <= 10) {{
                        return selector;
                    }}
                }}
                
                let path = [];
                let el = element;
                while (el && el.tagName && el.tagName !== 'HTML' && el.tagName !== 'BODY') {{
                    let selector = el.tagName.toLowerCase();
                    if (el.className && typeof el.className === 'string') {{
                        const classes = el.className.trim().split(/\\s+/)
                            .filter(c => c && !c.match(/^[0-9]/) && c.length < 30);
                        if (classes.length > 0) {{
                            selector += '.' + classes.slice(0, 2).join('.');
                        }}
                    }}
                    path.unshift(selector);
                    const fullPath = path.join(' > ');
                    try {{
                        if (document.querySelectorAll(fullPath).length === 1) {{
                            return fullPath;
                        }}
                    }} catch(e) {{}}
                    if (path.length >= 4) break;
                    el = el.parentElement;
                }}
                return path.join(' > ') || element.tagName.toLowerCase();
            }};
            
            // =========================================================
            // 현재 선택된 필드명 가져오기
            // =========================================================
            const getFieldName = () => {{
                const input = document.getElementById('field-input');
                const select = document.getElementById('field-select');
                return (input && input.value.trim()) || (select && select.value) || '';
            }};
            
            // =========================================================
            // 상태 업데이트
            // =========================================================
            const updateStatus = (msg, type) => {{
                const box = document.getElementById('status-box');
                if (!box) return;
                const colors = {{
                    info: '#3498db',
                    waiting: '#f39c12',
                    success: '#27ae60',
                    error: '#e74c3c'
                }};
                box.style.borderLeftColor = colors[type] || colors.info;
                box.style.background = (colors[type] || colors.info) + '22';
                box.innerHTML = msg;
            }};
            
            // =========================================================
            // 목록에 항목 추가
            // =========================================================
            const addToList = (field, selector) => {{
                const list = document.getElementById('selector-list');
                if (!list) return;
                
                const empty = list.querySelector('.empty-msg');
                if (empty) empty.remove();
                
                // 중복 제거
                const existingItems = list.querySelectorAll('.selector-item');
                existingItems.forEach(item => {{
                    if (item.dataset.field === field) item.remove();
                }});
                
                const item = document.createElement('div');
                item.className = 'selector-item';
                item.dataset.field = field;
                item.style.cssText = 'padding: 6px; margin-bottom: 4px; background: #1a1a3a; border-radius: 4px; border-left: 3px solid #00ff88;';
                item.innerHTML = `
                    <div style="color: #00d4ff; font-weight: bold; margin-bottom: 2px; font-size: 11px;">${{field}}</div>
                    <div style="color: #aaa; word-break: break-all; font-size: 10px;">${{selector}}</div>
                `;
                list.insertBefore(item, list.firstChild);
            }};
            
            // =========================================================
            // 프리셋 선택 시 입력창에 복사
            // =========================================================
            document.getElementById('field-select').addEventListener('change', (e) => {{
                const input = document.getElementById('field-input');
                if (e.target.value) {{
                    input.value = e.target.value;
                    updateStatus('✋ 요소를 클릭하세요: ' + e.target.value, 'waiting');
                }}
            }});
            
            document.getElementById('field-input').addEventListener('input', (e) => {{
                if (e.target.value.trim()) {{
                    updateStatus('✋ 요소를 클릭하세요: ' + e.target.value.trim(), 'waiting');
                }}
            }});
            
            // =========================================================
            // 저장 버튼 (파일 다운로드)
            // =========================================================
            document.getElementById('btn-save').addEventListener('click', () => {{
                const data = window.__selectorExtractor.extractedData;
                if (Object.keys(data).length === 0) {{
                    updateStatus('⚠️ 저장할 데이터가 없습니다', 'error');
                    return;
                }}
                
                // YAML 형식으로 변환
                let yaml = 'selectors:\\n';
                const grouped = {{}};
                
                for (const [key, value] of Object.entries(data)) {{
                    const parts = key.split('.');
                    if (parts.length === 2) {{
                        if (!grouped[parts[0]]) grouped[parts[0]] = {{}};
                        grouped[parts[0]][parts[1]] = value;
                    }} else {{
                        grouped[key] = value;
                    }}
                }}
                
                for (const [group, items] of Object.entries(grouped)) {{
                    if (typeof items === 'object') {{
                        yaml += `  ${{group}}:\\n`;
                        for (const [k, v] of Object.entries(items)) {{
                            yaml += `    ${{k}}: '${{v}}'\\n`;
                        }}
                    }} else {{
                        yaml += `  ${{group}}: '${{items}}'\\n`;
                    }}
                }}
                
                // 파일 다운로드
                const blob = new Blob([yaml], {{ type: 'text/yaml' }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = '{self.current_platform}_selectors.yaml';
                a.click();
                URL.revokeObjectURL(url);
                
                updateStatus('💾 파일 다운로드 완료! 다운로드 폴더 확인', 'success');
            }});
            
            // =========================================================
            // 초기화 버튼
            // =========================================================
            document.getElementById('btn-clear').addEventListener('click', () => {{
                if (confirm('모든 추출 데이터를 초기화하시겠습니까?')) {{
                    window.__selectorExtractor.extractedData = {{}};
                    window.__selectorExtractor.history = [];
                    const list = document.getElementById('selector-list');
                    list.innerHTML = '<div class="empty-msg" style="color: #666; font-style: italic; text-align: center; padding: 10px;">초기화되었습니다</div>';
                    updateStatus('🗑️ 초기화 완료', 'info');
                }}
            }});
            
            // =========================================================
            // 되돌리기 버튼
            // =========================================================
            document.getElementById('btn-undo').addEventListener('click', () => {{
                const history = window.__selectorExtractor.history;
                if (history.length > 0) {{
                    const last = history.pop();
                    delete window.__selectorExtractor.extractedData[last.field];
                    
                    const list = document.getElementById('selector-list');
                    const item = list.querySelector(`[data-field="${{last.field}}"]`);
                    if (item) item.remove();
                    
                    if (Object.keys(window.__selectorExtractor.extractedData).length === 0) {{
                        list.innerHTML = '<div class="empty-msg" style="color: #666; font-style: italic; text-align: center; padding: 10px;">아직 추출된 셀렉터가 없습니다</div>';
                    }}
                    
                    updateStatus('↩️ 되돌리기: ' + last.field, 'info');
                }} else {{
                    updateStatus('되돌릴 항목이 없습니다', 'error');
                }}
            }});
            
            // =========================================================
            // 마우스오버 하이라이트
            // =========================================================
            document.addEventListener('mouseover', (e) => {{
                if (e.target.id === 'selector-panel' || e.target.closest('#selector-panel')) return;
                
                if (window.__selectorExtractor.lastHighlighted && 
                    window.__selectorExtractor.lastHighlighted !== e.target) {{
                    window.__selectorExtractor.lastHighlighted.style.outline = '';
                    window.__selectorExtractor.lastHighlighted.style.outlineOffset = '';
                }}
                
                e.target.style.outline = '2px dashed #00d4ff';
                e.target.style.outlineOffset = '2px';
                window.__selectorExtractor.lastHighlighted = e.target;
            }}, true);
            
            document.addEventListener('mouseout', (e) => {{
                if (e.target.id !== 'selector-panel' && !e.target.closest('#selector-panel')) {{
                    if (!e.target.dataset.selected) {{
                        e.target.style.outline = '';
                        e.target.style.outlineOffset = '';
                    }}
                }}
            }}, true);
            
            // =========================================================
            // 클릭 핸들러 (핵심!)
            // =========================================================
            document.addEventListener('click', (e) => {{
                // 패널 내부 클릭은 무시
                if (e.target.id === 'selector-panel' || e.target.closest('#selector-panel')) return;
                
                const fieldName = getFieldName();
                if (!fieldName) {{
                    updateStatus('⚠️ 먼저 필드명을 선택/입력하세요', 'error');
                    return;
                }}
                
                e.preventDefault();
                e.stopPropagation();
                
                const selector = window.__generateSelector(e.target);
                if (!selector) {{
                    updateStatus('❌ 셀렉터 추출 실패', 'error');
                    return;
                }}
                
                // 데이터 저장
                window.__selectorExtractor.extractedData[fieldName] = selector;
                window.__selectorExtractor.history.push({{ field: fieldName, selector: selector }});
                
                // UI 업데이트
                addToList(fieldName, selector);
                updateStatus('✅ 추출 완료: ' + fieldName, 'success');
                
                // 선택된 요소 하이라이트 유지
                e.target.style.outline = '3px solid #00ff88';
                e.target.style.outlineOffset = '2px';
                e.target.dataset.selected = 'true';
                
                // 입력 초기화
                document.getElementById('field-input').value = '';
                document.getElementById('field-select').value = '';
                
            }}, true);
        }}""")
    
    async def _sync_from_browser(self, page):
        """브라우저에서 추출된 데이터 동기화"""
        try:
            data = await page.evaluate("window.__selectorExtractor?.extractedData || {}")
            if data:
                for field, selector in data.items():
                    parts = field.split('.')
                    self._set_nested_value(self.extracted_selectors, parts, selector)
                print(f"   📥 {len(data)}개 항목 동기화됨")
        except Exception as e:
            print(f"   ⚠️ 동기화 실패: {e}")
    
    def _set_nested_value(self, d, keys, value):
        if 'selectors' not in d:
            d['selectors'] = {}
        current = d['selectors']
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def _save_selectors(self):
        selector_path = f"mvno_system/config/selectors/{self.current_platform}.yaml"
        
        if os.path.exists(selector_path):
            backup_path = f"{selector_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(selector_path, backup_path)
            print(f"   📦 백업: {os.path.basename(backup_path)}")
        
        with open(selector_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.extracted_selectors, f, allow_unicode=True, default_flow_style=False)
        
        print(f"   💾 저장 완료: {selector_path}")
    
    def _show_selectors(self):
        print("\n" + "━"*50)
        print("  📋 현재 추출된 셀렉터")
        print("━"*50)
        print(yaml.dump(self.extracted_selectors, allow_unicode=True, default_flow_style=False))
        print("━"*50)
    
    def _print_header(self, platform_key, platform_name, url):
        print()
        print("╔" + "═"*58 + "╗")
        print("║" + "  🔍 셀렉터 추출기 v3.0 - Full Browser Mode".center(56) + "║")
        print("╠" + "═"*58 + "╣")
        print(f"║  플랫폼: {platform_name} ({platform_key})".ljust(57) + "║")
        short_url = url[:42] + "..." if len(url) > 45 else url
        print(f"║  URL: {short_url}".ljust(57) + "║")
        print("╚" + "═"*58 + "╝")


async def main():
    if len(sys.argv) < 2:
        print("\n" + "═"*50)
        print("  🔍 셀렉터 추출기 v3.0 - Full Browser Mode")
        print("═"*50)
        print("\n사용법: python selector_extractor.py <플랫폼> [URL]")
        print("\n예시:")
        print("  python selector_extractor.py liivm")
        print("  python selector_extractor.py phoneb https://www.phoneb.co.kr")
        print("\n" + "─"*50)
        print("사용 가능한 플랫폼:")
        print("─"*50)
        
        platforms_path = "mvno_system/config/platforms.yaml"
        if os.path.exists(platforms_path):
            with open(platforms_path, 'r', encoding='utf-8') as f:
                platforms = yaml.safe_load(f)
            for key, data in platforms.get('platforms', {}).items():
                print(f"  • {key}: {data.get('name', '')}")
        print()
        return
    
    platform_key = sys.argv[1]
    url = sys.argv[2] if len(sys.argv) > 2 else None
    
    extractor = SelectorExtractor()
    await extractor.run(platform_key, url)


if __name__ == "__main__":
    asyncio.run(main())
