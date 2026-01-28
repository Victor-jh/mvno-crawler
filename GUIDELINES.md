# 📘 MVNO 통합 크롤링 시스템 - 구축 가이드라인

## 목차
1. [시스템 아키텍처](#시스템-아키텍처)
2. [표준 스키마 정의](#표준-스키마-정의)
3. [구축 로드맵](#구축-로드맵)
4. [핵심 컴포넌트 구현](#핵심-컴포넌트-구현)
5. [크롤러 개발 가이드](#크롤러-개발-가이드)
6. [사업자 통합 모듈](#사업자-통합-모듈)
7. [자동화 스케줄러](#자동화-스케줄러)
8. [테스트 및 검증](#테스트-및-검증)

---

## 시스템 아키텍처

### 전체 구조
```
[Phase 1] 개별 크롤러 구축
    ├── 자사사이트 크롤러 (18개)
    └── 플랫폼 크롤러 (6개)
         ↓
[Phase 2] 사업자별 통합 모듈
    └── 사업자별로 자사 + 제휴 플랫폼 통합 (18개)
         ↓
[Phase 3] 전체 자동화 스케줄러
    └── 18개 사업자 모듈을 시간별 자동 실행
```

### 디렉토리 구조
```
mvno_integrated_system/
├── config/                    # 모든 설정 파일 (YAML)
│   ├── schema/
│   │   ├── standard.yaml     # 표준 스키마 25개 필드
│   │   └── parsers.yaml      # 공통 파싱 규칙 (regex, keyword 등)
│   ├── carriers/              # 사업자 제휴 현황 (18개 YAML)
│   │   ├── hellomobile.yaml
│   │   ├── kgmobile.yaml
│   │   └── ... (18개)
│   ├── platforms.yaml         # 플랫폼 메타정보 (24개)
│   └── selectors/             # 크롤러별 셀렉터 설정
│       ├── official/          # 자사사이트 (18개)
│       └── platforms/         # 플랫폼 (6개)
│
├── core/                      # 핵심 엔진 (재사용 가능)
│   ├── schema_engine.py      # 스키마 검증/변환 엔진
│   ├── parser_engine.py      # 파싱 엔진 (parsers.yaml 기반)
│   ├── selector_manager.py   # 동적 셀렉터 관리
│   ├── platform_loader.py    # 동적 크롤러 로더 (Factory Pattern)
│   └── health_checker.py     # 사이트 변경 감지
│
├── crawlers/                  # 크롤러 구현체
│   ├── base_crawler.py       # 추상 베이스 클래스
│   ├── universal_crawler.py  # YAML 전용 범용 크롤러 (Simple Mode)
│   ├── official/             # 자사사이트 크롤러 (18개)
│   │   ├── hellomobile_crawler.py
│   │   ├── kgmobile_crawler.py
│   │   └── ...
│   └── platforms/            # 플랫폼 크롤러 (6개)
│       ├── phoneb_crawler.py
│       ├── moyo_crawler.py
│       ├── alttelecomhub_crawler.py
│       ├── aldoot_crawler.py
│       ├── mymvno_crawler.py
│       └── ayo_crawler.py
│
├── carrier_modules/          # 사업자 통합 모듈 (18개)
│   ├── base_carrier_module.py
│   ├── hellomobile_module.py
│   ├── kgmobile_module.py
│   └── ...
│
├── storage/                  # 데이터 저장
│   ├── database.py          # SQLAlchemy ORM
│   ├── mvno.db              # SQLite 데이터베이스
│   ├── sessions/            # 세션별 데이터
│   └── screenshots/         # 스크린샷 저장소
│
├── scheduler/               # 자동화 스케줄러
│   ├── master_scheduler.py # 전체 스케줄러
│   └── carrier_job.py      # 사업자별 작업 래퍼
│
├── utils/                   # 유틸리티
│   ├── alert.py            # Slack/Email 알림
│   ├── validators.py       # 데이터 검증
│   └── auto_repair.py      # 자동 복구 (선택)
│
├── tests/                   # 테스트 코드
│   ├── test_schema.py
│   ├── test_crawlers.py
│   └── test_carriers.py
│
├── main.py                  # 통합 CLI 진입점
├── requirements.txt
└── README.md
```

---

## 표준 스키마 정의

### 필수 필드 (25개)

#### 핵심 정보 (9개)
| 필드명 | 타입 | 필수 | 설명 | 예시 |
|--------|------|------|------|------|
| carrier | string | ✅ | 통신사명 | "헬로모바일" |
| plan_name | string | ✅ | 요금제명 | "데이터 무제한" |
| data | string | ✅ | 데이터 제공량 | "100GB" |
| voice | string | ✅ | 음성통화 | "무제한" |
| sms | string | ✅ | 문자 | "기본제공" |
| price_regular | integer | ✅ | 정상가격 | 35000 |
| price_promo | integer | ❌ | 할인가격 | 28000 |
| network | enum | ✅ | 통신망 | "SKT", "KT", "LGU+" |
| network_type | enum | ✅ | 통신기술 | "5G", "LTE" |

#### 상세 정보 (9개)
| 필드명 | 타입 | 필수 | 설명 | 예시 |
|--------|------|------|------|------|
| discount_period | string | ❌ | 할인기간 | "7개월" |
| price_note | string | ❌ | 가격 비고 | "7개월 이후 정상가" |
| data_speed_after | string | ❌ | 소진 후 속도 | "3Mbps" |
| voice_type | string | ❌ | 통화 타입 | "기본제공" |
| sms_type | string | ❌ | 문자 타입 | "기본제공" |
| gift_info | string | ❌ | 사은품 정보 | "첫 달 5,000원 할인" |
| usim_support | string | ❌ | 유심 지원 | "eSIM 지원" |
| usim_fee | integer | ❌ | 유심비 | 0 |
| contract_type | enum | ❌ | 약정 타입 | "선불", "후불" |

#### 메타데이터 (6개)
| 필드명 | 타입 | 필수 | 자동생성 | 설명 |
|--------|------|------|----------|------|
| provider_code | string | ✅ | ✅ | 사업자 코드 |
| source_url | string | ✅ | ✅ | 출처 URL |
| detail_url | string | ❌ | ❌ | 상세 페이지 URL |
| crawl_date | datetime | ✅ | ✅ | 수집일시 |
| data_quality | enum | ✅ | ✅ | "완전", "부분", "오류" |
| screenshot_path | string | ❌ | ✅ | 스크린샷 경로 |

#### 기타 (1개)
| 필드명 | 타입 | 필수 | 설명 |
|--------|------|------|------|
| special_note | string | ❌ | 특이사항 |

---

## 구축 로드맵

### Week 1: 기반 구축 🏗️

#### Day 1-2: 프로젝트 초기화
**목표:** 디렉토리 구조 생성 및 표준 스키마 정의

**작업:**
```bash
# 1. 디렉토리 구조 생성
mkdir -p config/schema config/carriers config/selectors/{official,platforms}
mkdir -p core crawlers/{official,platforms} carrier_modules
mkdir -p storage/sessions storage/screenshots scheduler utils tests

# 2. 표준 스키마 작성
# config/schema/standard.yaml
# config/schema/parsers.yaml

# 3. requirements.txt 작성
```

**산출물:**
- [ ] 폴더 구조 완성
- [ ] `config/schema/standard.yaml` (25개 필드)
- [ ] `config/schema/parsers.yaml` (5개 파서)
- [ ] `requirements.txt`

#### Day 3-4: 핵심 엔진 구현
**목표:** 재사용 가능한 핵심 엔진 완성

**구현 순서:**
1. `core/schema_engine.py` - 스키마 로드/검증/변환
2. `core/parser_engine.py` - 파싱 규칙 적용
3. `core/selector_manager.py` - 셀렉터 동적 관리

**산출물:**
- [ ] SchemaEngine 클래스
- [ ] ParserEngine 클래스
- [ ] SelectorManager 클래스
- [ ] 유닛 테스트 (`tests/test_schema.py`)

#### Day 5-7: BaseCrawler 구현
**목표:** 모든 크롤러의 부모 클래스 완성

**핵심 기능:**
- 표준 스키마 통합
- 데이터 품질 자동 판정
- 스크린샷 자동 저장
- DB 저장 로직

**산출물:**
- [ ] `crawlers/base_crawler.py` (추상 클래스)
- [ ] `crawlers/universal_crawler.py` (YAML 전용)
- [ ] 데이터 품질 자동 판정 로직

---

### Week 2: MVP 구현 🚀

#### Day 8-10: 헬로모바일 자사사이트 크롤러
**목표:** 첫 번째 크롤러 완성 (Simple Mode)

**작업:**
```yaml
# 1. config/selectors/official/hellomobile.yaml 작성
metadata:
  provider: "헬로모바일"
  crawl_mode: "simple"

selectors:
  list:
    item_card: "li.list-item"
    # ...

schema_mapping:
  carrier:
    type: "fixed"
    value: "헬로모바일"
  # ... (25개 필드 매핑)
```

```python
# 2. crawlers/official/hellomobile_crawler.py
class HelloMobileCrawler(UniversalCrawler):
    # YAML 설정만으로 작동
    pass
```

**산출물:**
- [ ] `hellomobile.yaml` 완성
- [ ] HelloMobileCrawler 작동
- [ ] 10개 요금제 수집 테스트
- [ ] 데이터 품질 검증

#### Day 11-13: 폰비 플랫폼 크롤러
**목표:** 두 번째 크롤러 완성 (Advanced Mode)

**작업:**
```yaml
# 1. config/selectors/platforms/phoneb.yaml
metadata:
  provider: "폰비"
  crawl_mode: "advanced"  # 복잡한 필터링 로직

selectors:
  # ... (기존 폰비 크롤러 참고)

schema_mapping:
  # ... (표준 스키마 매핑)
```

```python
# 2. crawlers/platforms/phoneb_crawler.py (기존 코드 개선)
class PhonebCrawler(BaseCrawler):
    async def crawl(self, carrier_filter=None):
        # 사업자 필터링 기능 추가
        # 표준 스키마 변환 적용
```

**산출물:**
- [ ] `phoneb.yaml` 완성
- [ ] PhonebCrawler 개선
- [ ] 사업자 필터링 기능
- [ ] 표준 스키마 변환 적용

#### Day 14: 통합 테스트
**체크리스트:**
- [ ] 헬로모바일 자사: 데이터 품질 "완전" 달성
- [ ] 폰비: 헬로모바일 필터링 정상 작동
- [ ] 두 크롤러 모두 25개 필드 수집
- [ ] Excel 출력 정상

---

### Week 3: 사업자 통합 모듈 🔗

#### Day 15-17: HelloMobileModule 구현
**목표:** 첫 번째 사업자 통합 모듈 완성

**작업:**
```yaml
# 1. config/carriers/hellomobile.yaml
carrier:
  code: "hellomobile"
  name: "헬로모바일"
  network: "LGU+"

platforms:
  official:
    platform_code: "hellomobile"
    enabled: true
    priority: 1

  phoneb:
    platform_code: "phoneb"
    enabled: true
    priority: 2
```

```python
# 2. carrier_modules/base_carrier_module.py
class BaseCarrierModule(ABC):
    @abstractmethod
    async def crawl_all(self):
        pass

# 3. carrier_modules/hellomobile_module.py
class HelloMobileModule(BaseCarrierModule):
    async def crawl_all(self):
        # 1. 활성화된 플랫폼 목록 로드
        # 2. 순차/병렬 크롤링
        # 3. 중복 제거
        # 4. 통합 Excel 생성
```

**산출물:**
- [ ] BaseCarrierModule (추상 클래스)
- [ ] HelloMobileModule 완성
- [ ] 중복 제거 알고리즘
- [ ] 통합 Excel 생성

#### Day 18-19: 데이터 통합 검증
**체크리스트:**
- [ ] 자사사이트 45개 + 폰비 43개 수집
- [ ] 중복 제거 → 최종 47개 (예상)
- [ ] 우선순위 높은 데이터 자동 선택
- [ ] `hellomobile_통합_20260128.xlsx` 생성

#### Day 20-21: MVP 완성
**최종 검증:**
- [ ] `python main.py` → 헬로모바일 선택 → 정상 작동
- [ ] 통합 Excel 25개 필드 모두 채워짐
- [ ] 데이터 품질 95% 이상
- [ ] 실행 시간 5분 이내

---

### Week 4: 확장 1단계 📈

#### Day 22-26: 플랫폼 크롤러 4개 추가
**목표:** moyo, alttelecomhub, aldoot, mymvno

**우선순위:**
1. **aldoot** (Simple Mode) - 가장 간단
2. **mymvno** (Simple Mode) - 간단
3. **alttelecomhub** (Simple/Advanced 선택)
4. **moyo** (Advanced Mode) - 복잡한 동적 클래스

**산출물:**
- [ ] 각 플랫폼별 YAML + 크롤러
- [ ] HelloMobileModule 확장 (4개 플랫폼 연동)
- [ ] 통합 테스트

#### Day 27-28: 사업자 2개 추가
**목표:** KG모바일, 프리티

**산출물:**
- [ ] kgmobile_crawler.py (자사)
- [ ] freet_crawler.py (자사)
- [ ] KGMobileModule
- [ ] FreetModule

---

### Week 5: 확장 2단계 📈

#### Day 29-35: 나머지 확장
**목표:** 18개 사업자 + 6개 플랫폼 완성

**전략:**
- Simple Mode 우선 (빠른 구축)
- 매일 3개씩 추가
- 복잡한 사이트만 Advanced Mode

**산출물:**
- [ ] 18개 자사사이트 크롤러 완성
- [ ] 6개 플랫폼 크롤러 완성
- [ ] 18개 사업자 통합 모듈 완성

---

### Week 6: 자동화 & 안정화 🎯

#### Day 36-38: 스케줄러 구현
```python
# scheduler/master_scheduler.py
class MasterScheduler:
    def setup_jobs(self):
        # 18개 사업자 스케줄 등록
        # 시간 분산 (새벽 2시~6시)
```

```yaml
# config/schedule.yaml
carriers:
  hellomobile:
    enabled: true
    cron:
      hour: "2"
      minute: "0"
```

**산출물:**
- [ ] MasterScheduler 클래스
- [ ] 18개 사업자 스케줄 등록
- [ ] 시간 분산 설정

#### Day 39-40: 모니터링 & 알림
**산출물:**
- [ ] Slack Webhook 연동 (`utils/alert.py`)
- [ ] 실패 시 자동 알림
- [ ] Health Check 자동화

#### Day 41-42: 최종 테스트
**체크리스트:**
- [ ] 18개 사업자 × 평균 6개 플랫폼 = 108개 작업
- [ ] 스케줄러 24시간 무인 운영
- [ ] 에러율 5% 이하
- [ ] 평균 수집 시간: 사업자당 10분 이내

---

## 핵심 컴포넌트 구현

### 1. SchemaEngine (core/schema_engine.py)

**역할:** 표준 스키마 로드/검증/변환

**주요 메서드:**
```python
class SchemaEngine:
    def __init__(self, platform_key):
        self.standard = self._load_standard()
        self.mapping = self._load_mapping(platform_key)

    def validate(self, data: dict) -> bool:
        """필수 필드 검증"""

    def transform(self, raw_data: dict) -> dict:
        """원시 데이터 → 표준 스키마 변환"""

    def judge_quality(self, data: dict) -> str:
        """데이터 품질 자동 판정 (완전/부분/오류)"""
```

### 2. ParserEngine (core/parser_engine.py)

**역할:** parsers.yaml 기반 파싱

**주요 메서드:**
```python
class ParserEngine:
    def __init__(self):
        self.parsers = self._load_parsers()

    def parse(self, parser_name: str, text: str) -> str:
        """파싱 규칙 적용"""
        # data_parser: "월 100GB" → "100GB"
        # price_parser: "35,000원" → 35000
```

### 3. UniversalCrawler (crawlers/universal_crawler.py)

**역할:** YAML 설정만으로 작동하는 범용 크롤러

**핵심 로직:**
```python
class UniversalCrawler(BaseCrawler):
    async def _extract_schema(self, page, item):
        """schema_mapping에 따라 자동 필드 추출"""

        for field_name, config in self.mapping.items():
            if config['type'] == 'selector':
                # CSS 셀렉터로 추출
                text = await item.locator(config['selector']).inner_text()

                # 파서 적용
                if config.get('parser'):
                    text = self.parser_engine.parse(config['parser'], text)

                result[field_name] = text
```

---

## 크롤러 개발 가이드

### Simple Mode vs Advanced Mode

#### Simple Mode (추천)
- **적용 대상:** 단순한 구조의 사이트
- **특징:** YAML 설정만으로 작동, 코드 작성 불필요
- **크롤러:** UniversalCrawler 사용

**예시:**
```yaml
# config/selectors/official/hellomobile.yaml
metadata:
  crawl_mode: "simple"

selectors:
  list:
    item_card: "li.list-item"

schema_mapping:
  carrier:
    type: "fixed"
    value: "헬로모바일"

  plan_name:
    type: "selector"
    selector: ".plan-rate-name"
```

#### Advanced Mode
- **적용 대상:** 복잡한 필터링, 동적 로딩, 다단계 네비게이션
- **특징:** Python 코드 작성 필요
- **크롤러:** BaseCrawler 상속

**예시:**
```python
# crawlers/platforms/phoneb_crawler.py
class PhonebCrawler(BaseCrawler):
    async def crawl(self, carrier_filter=None):
        # 복잡한 필터링 로직
        # 페이지네이션 처리
        # 표준 스키마 변환
```

---

## 사업자 통합 모듈

### 구조
```python
# carrier_modules/hellomobile_module.py
class HelloMobileModule(BaseCarrierModule):
    def __init__(self):
        self.carrier_code = "hellomobile"
        self.config = self._load_config()  # carriers/hellomobile.yaml

    async def crawl_all(self, mode='sequential'):
        # 1. 활성화된 플랫폼 필터링
        active = self._get_active_platforms()

        # 2. 순차/병렬 크롤링
        for platform in active:
            crawler = PlatformLoader.load(platform['code'])
            await crawler.crawl(carrier_filter='헬로모바일')

        # 3. 중복 제거
        self._merge_results()

        # 4. 통합 Excel
        self._export_merged_excel()
```

### 중복 제거 알고리즘
```python
def _merge_results(self):
    unique_plans = {}

    for plan in all_plans:
        # plan_name + data 기준
        key = f"{plan['plan_name']}_{plan['data']}"

        if key not in unique_plans:
            unique_plans[key] = plan
        else:
            # 우선순위 높은 플랫폼 선택
            if self._get_priority(plan['_source_platform']) < \
               self._get_priority(unique_plans[key]['_source_platform']):
                unique_plans[key] = plan
```

---

## 자동화 스케줄러

### 설정
```yaml
# config/schedule.yaml
carriers:
  hellomobile:
    enabled: true
    cron:
      hour: "2"        # 새벽 2시
      minute: "0"
      day_of_week: "*" # 매일

  kgmobile:
    enabled: true
    cron:
      hour: "3"        # 부하 분산
      minute: "0"
```

### 구현
```python
# scheduler/master_scheduler.py
class MasterScheduler:
    def setup_jobs(self):
        for carrier_code, setting in config['carriers'].items():
            self.scheduler.add_job(
                self._run_carrier_job,
                trigger='cron',
                hour=setting['cron']['hour'],
                args=[carrier_code],
                id=f"carrier_{carrier_code}"
            )
```

---

## 테스트 및 검증

### MVP 검증 기준
- [x] 헬로모바일 통합 크롤링 100% 작동
- [x] 표준 스키마 25개 필드 수집
- [x] 중복 제거 정확도 100%
- [x] 데이터 품질 "완전" 90% 이상

### 유닛 테스트
```python
# tests/test_schema.py
def test_schema_validation():
    engine = SchemaEngine('hellomobile')
    data = {'carrier': '헬로모바일', ...}
    assert engine.validate(data) == True

def test_parser():
    parser = ParserEngine()
    assert parser.parse('data_parser', '월 100GB') == '100GB'
    assert parser.parse('price_parser', '35,000원') == 35000
```

---

## 참고 자료

- [Playwright 문서](https://playwright.dev/python/)
- [SQLAlchemy 문서](https://docs.sqlalchemy.org/)
- [APScheduler 문서](https://apscheduler.readthedocs.io/)

---

**작성일:** 2026-01-28
**버전:** 1.0.0
