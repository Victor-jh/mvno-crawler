import asyncio
from abc import ABC, abstractmethod
import yaml
import pandas as pd
from pathlib import Path
from playwright.async_api import async_playwright
import logging
from datetime import datetime
import os
import sys

# 프로젝트 루트 경로 추가 (storage 모듈 import 위해)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage.database import SessionLocal, CrawlLog, Plan as PlanModel

# 로거 설정 (임시, 추후 utils/logger.py로 분리)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crawler.log', encoding='utf-8')
    ]
)

class BaseCrawler(ABC):
    """
    모든 크롤러가 상속받아야 할 기본 추상 클래스
    공통 기능: 설정 로드, 브라우저 관리, 스크린샷 저장
    """
    
    def __init__(self, platform_key):
        self.platform_key = platform_key
        self.logger = logging.getLogger(platform_key)
        self.config = self._load_platform_config()
        self.selectors = self._load_selectors()
        self.results = []
        self.db = SessionLocal()
        self.crawl_log = None
        
        self.session_id = None
        self.session_dir = None
        
        # Default usage (legacy)
        self.screenshot_dir = Path(f"storage/screenshots/{platform_key}")
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def set_session(self, session_id):
        """세션 ID 설정 및 디렉토리 준비"""
        self.session_id = session_id
        # Structure: storage/sessions/{session_id}/{platform}/
        self.session_dir = Path(f"storage/sessions/{session_id}/{self.platform_key}")
        
        # Sub-directories
        self.screenshot_dir = self.session_dir / "screenshots"
        self.data_dir = self.session_dir
        
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"세션 디렉토리 설정: {self.session_dir}")
        
    def __del__(self):
        """소멸자: DB 세션 닫기"""
        if hasattr(self, 'db'):
            self.db.close()
        
    def _load_platform_config(self):
        """platforms.yaml에서 해당 플랫폼 설정을 로드"""
        try:
            # 현재 파일(base_crawler.py) 기준 프로젝트 루트(mvno_system) 찾기
            # base_crawler.py path: .../mvno_system/crawlers/base_crawler.py
            root_dir = Path(__file__).parent.parent
            config_path = root_dir / 'config' / 'platforms.yaml'
            
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data['platforms'].get(self.platform_key)
        except Exception as e:
            self.logger.error(f"설정 로드 실패 ({config_path if 'config_path' in locals() else 'unknown'}): {e}")
            return {}
            
    def _load_selectors(self):
        """지정된 셀렉터 파일을 로드"""
        if not self.config or 'selectors_file' not in self.config:
            self.logger.error("Config가 로드되지 않았거나 selectors_file 설정이 없습니다.")
            return {}
            
        try:
            root_dir = Path(__file__).parent.parent
            # selectors_file은 "config/selectors/phoneb.yaml" 형태로 저장되어 있음
            # 따라서 root_dir / selectors_file 로 접근하면 된다.
            # 하지만 yaml에 저장된 경로가 이미 config/ 부터 시작하므로 주의
            
            # Yaml에 "config/selectors/phoneb.yaml"로 되어 있다면: root_dir / "config/selectors/phoneb.yaml" (X)
            # 만약 mvno_system이 root라면: root_dir / val (O)
            
            # 여기서 root_dir은 .../mvno_system
            if os.path.isabs(self.config['selectors_file']):
                 selector_path = Path(self.config['selectors_file'])
            else:
                 selector_path = root_dir / self.config['selectors_file']

            with open(selector_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data.get('selectors', {})
        except Exception as e:
            self.logger.error(f"셀렉터 파일 로드 실패: {e}")
            return {}

    @abstractmethod
    async def crawl(self, **kwargs):
        """
        메인 크롤링 진입점. 
        자식 클래스에서 반드시 구현해야 함.
        """
        pass

    async def _save_screenshot(self, page, name_parts_or_data):
        """
        공통 스크린샷 저장 메서드
        
        Args:
            page: Playwright page object
            name_parts_or_data: 
                - List: [Network, Carrier, Platform, PlanName] (Legacy)
                - Dict: plan_data object containing 'carrier', 'network', 'plan_name'
        
        Format: Carrier(MVNO)_Network(SK/KT/LG)_Platform(Specific/Official)_PlanName_Time.png
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # --- Mappings ---
        AGGREGATORS = {
            'moyo': '모요',
            'alttelecomhub': '알뜰폰허브',
            'aldot': '알닷',
            'ajo': '아요',
            'phoneb': '폰비',
            'mymvno': '마이알뜰폰',
            'toss': '토스'
        }
        
        # Simplified Network Names
        NETWORK_MAP = {
            'SKT': 'SK', 'SK': 'SK', 
            'KT': 'KT', 
            'LGU+': 'LG', 'LG U+': 'LG', 'LG': 'LG'
        }

        # Carrier Name Normalization (English -> Korean preferred)
        # This list can be expanded.
        CARRIER_MAP = {
            'LiivM': '리브모바일',
            'U+Umobile': '유모바일',
            'SK7Mobile': 'SK7모바일',
            'KTMobile': 'KT엠모바일',
            'HelloMobile': '헬로모바일',
            'FreeT': '프리티',
            'SkyLife': '스카이라이프',
            'A-Mobile': '에이모바일',
            'Smile': '스마일게이트',
            'Tplus': '티플러스',
            'Story': '이야기모바일',
            'Snowman': '스노우맨',
            'Sugar': '슈가모바일',
            'Mobing': '모빙',
            'Eyes': '아이즈모바일'
        }

        # --- Extract Components ---
        carrier = "Unknown"
        network = "Unknown"
        plan_name = "Unknown"
        
        # 1. Platform Name Resolution
        if self.platform_key in AGGREGATORS:
            platform_name = AGGREGATORS[self.platform_key]
        else:
            platform_name = "자사홈페이지"

        # 2. Component Extraction
        if isinstance(name_parts_or_data, dict):
            # plan_data dict passed
            raw_carrier = name_parts_or_data.get('carrier', '')
            raw_network = name_parts_or_data.get('network', '')
            plan_name = name_parts_or_data.get('plan_name', '')
            
            carrier = CARRIER_MAP.get(raw_carrier, raw_carrier)
            network = NETWORK_MAP.get(raw_network, raw_network)
            
        elif isinstance(name_parts_or_data, list):
            # Legacy list: [Network, Carrier, (Platform), PlanName]
            # Try to identify slots
            parts = [str(p) for p in name_parts_or_data if str(p) != self.platform_key]
            
            if len(parts) >= 3:
                raw_network = parts[0] # Typically first
                raw_carrier = parts[1] # Typically second
                plan_name = parts[-1]  # Typically last
                
                carrier = CARRIER_MAP.get(raw_carrier, raw_carrier)
                network = NETWORK_MAP.get(raw_network, raw_network)
            else:
                # Fallback join
                carrier = parts[0] if parts else "Unknown"
                plan_name = parts[-1] if len(parts) > 1 else "Unknown"
        
        # --- Construct Filename ---
        # Format: Carrier_Network_Platform_PlanName_Time
        
        # Filename Sanitization
        def sanitize(s):
            return str(s).replace('/', '_').replace('\\', '_').replace(':', '').replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '').strip()

        final_parts = [
            sanitize(carrier),
            sanitize(network),
            sanitize(platform_name),
            sanitize(plan_name),
            timestamp
        ]
        
        safe_name = "_".join(final_parts)
        # Remove spaces in filename for consistency? User didn't specify, but usually good practice.
        # User example: "통신사_통신망_플랫폼명_요금제명_시간.png" (Korean has no spaces usually in these keys, but checks are good)
        safe_name = safe_name.replace(' ', '')
        
        target_dir = self.screenshot_dir
        filename = target_dir / f"{safe_name}.png"
        
        try:
            await page.screenshot(path=str(filename), full_page=True, timeout=10000)
            self.logger.info(f"스크린샷 저장: {filename}")
            return str(filename)
        except Exception as e:
            self.logger.error(f"스크린샷 저장 에러: {e}")
            return None



    def start_crawl_log(self):
        """크롤링 시작 로그 기록"""
        try:
            self.crawl_log = CrawlLog(
                platform=self.platform_key,
                status='running',
                start_time=datetime.now()
            )
            self.db.add(self.crawl_log)
            self.db.commit()
            self.logger.info(f"크롤링 로그 시작 (ID: {self.crawl_log.id})")
        except Exception as e:
            self.logger.error(f"DB 로그 시작 실패: {e}")

    def save_plan(self, plan_data):
        """요금제 정보 DB 저장"""
        if not self.crawl_log:
            self.logger.warning("Crawl Log가 시작되지 않아 데이터가 저장되지 않습니다.")
            return

        try:
            # 가격 문자열에서 숫자 추출 (예: "15,000" -> 15000)
            price_str = str(plan_data.get('price', '0'))
            price_int = int(''.join(filter(str.isdigit, price_str))) if any(char.isdigit() for char in price_str) else 0

            plan = PlanModel(
                crawl_log_id=self.crawl_log.id,
                platform=self.platform_key,
                carrier=plan_data.get('carrier'),
                plan_name=plan_data.get('plan_name'),
                price=price_str,
                price_int=price_int,
                data_raw=plan_data.get('data_raw'),
                url=plan_data.get('url'),
                screenshot_path=plan_data.get('screenshot_path'),
                details=plan_data, # 전체 원본 데이터도 JSON으로 저장
                collected_at=datetime.now()
            )
            self.db.add(plan)
            # 성능을 위해 매번 커밋하지 않고 flush 만 하거나, 주기적으로 커밋할 수 있음
            # 여기서는 안전을 위해 바로 커밋
            self.db.commit() 
            self.results.append(plan_data) # 메모리에도 유지 (선택사항)
            
        except Exception as e:
            self.logger.error(f"요금제 저장 실패: {e}")
            self.db.rollback()

    def finish_crawl_log(self, status='success', error=None):
        """크롤링 종료 로그 기록"""
        if not self.crawl_log:
            return

        try:
            self.crawl_log.end_time = datetime.now()
            self.crawl_log.status = status
            self.crawl_log.items_count = len(self.results)
            self.crawl_log.error_message = str(error) if error else None
            
            self.db.commit()
            self.logger.info(f"크롤링 로그 종료 (Status: {status}, Count: {len(self.results)})")
        except Exception as e:
            self.logger.error(f"DB 로그 종료 실패: {e}")

    def export_json(self):
        """결과를 JSON으로 저장 (임시)"""
        import json
        output_file = Path(f"storage/data/{self.platform_key}_{datetime.now().strftime('%Y%m%d')}.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        self.logger.info(f"데이터 저장 완료: {output_file}")
    def export_excel(self):
        """결과를 Excel로 저장"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if self.session_dir:
                 # Session Mode: storage/sessions/{session_id}/{platform}/{platform}.xlsx
                 # Or just data.xlsx? Let's keep platform name for clarity if copied out.
                 output_file = self.data_dir / f"{self.platform_key}.xlsx"
            else:
                 # Legacy Mode
                 output_file = Path(f"storage/data/{self.platform_key}_{timestamp}.xlsx")
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            df = pd.DataFrame(self.results)
            # Remove detailed JSON object for clean excel
            if 'details' in df.columns:
                df = df.drop(columns=['details'])
                
            df.to_excel(output_file, index=False)
            self.logger.info(f"엑셀 저장 완료: {output_file}")
            return str(output_file)
        except Exception as e:
            self.logger.error(f"엑셀 저장 실패: {e}")
            return None
