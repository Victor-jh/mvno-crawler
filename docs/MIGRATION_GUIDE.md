# 🔄 시스템 마이그레이션 가이드

## 📋 개요

기존 "구글 안티그래비티" 프로그램이 구축한 크롤링 시스템을 **MVNO 통합 크롤링 시스템 v2.0**으로 마이그레이션하는 가이드입니다.

---

## 🏗️ 기존 시스템 vs 신규 시스템

### 기존 시스템 (E:\알뜰폰\크롤링\mvno_system)

```
mvno_system/
├── config/
│   ├── platforms.yaml          # 23개 플랫폼 정보
│   ├── schedule.yaml           # 스케줄 설정
│   └── selectors/              # 23개 셀렉터 YAML
│       ├── hellomobile.yaml
│       ├── phoneb.yaml
│       └── ...
├── crawlers/
│   ├── base_crawler.py
│   ├── phoneb_crawler.py       # 23개 개별 크롤러 (하드코딩)
│   └── ...
├── storage/
│   ├── database.py             # SQLAlchemy ORM
│   └── mvno.db
└── main.py
```

**주요 특징:**
- ✅ 23개 플랫폼 크롤러 구현
- ✅ DB 통합 (SQLite)
- ✅ 스케줄러 연동
- ❌ **하드코딩 많음** (JS 내부 셀렉터)
- ❌ **사업자 구분 없음** (플랫폼만 관리)
- ❌ **데이터 스키마 불일치**
- ❌ **제휴 관리 기능 없음**

---

### 신규 시스템 (E:\알뜰폰\mvno_integrated_system)

```
mvno_integrated_system/
├── config/
│   ├── schema/
│   │   ├── standard.yaml       # ✨ 표준 스키마 (25개 필드)
│   │   └── parsers.yaml        # ✨ 공통 파싱 규칙
│   ├── carriers/               # ✨ 사업자 제휴 관리 (18개)
│   │   ├── hellomobile.yaml
│   │   └── ...
│   ├── platforms.yaml          # 24개 플랫폼
│   └── selectors/
│       ├── official/           # ✨ 자사사이트 (18개)
│       └── platforms/          # 플랫폼 (6개)
├── core/
│   ├── schema_engine.py        # ✨ 스키마 검증/변환
│   ├── parser_engine.py        # ✨ 파싱 엔진
│   └── selector_manager.py     # ✨ 동적 셀렉터
├── crawlers/
│   ├── base_crawler.py         # ✨ 표준 스키마 통합
│   ├── universal_crawler.py    # ✨ YAML 전용 (하드코딩 제거)
│   ├── official/               # ✨ 자사사이트 (18개)
│   └── platforms/              # 플랫폼 (6개)
├── carrier_modules/            # ✨ 사업자 통합 모듈 (18개)
│   └── hellomobile_module.py
└── scheduler/
    └── master_scheduler.py     # ✨ 전체 자동화
```

**주요 개선:**
- ✅ **하드코딩 제거** (YAML 기반 동적 셀렉터)
- ✅ **표준 스키마 통합** (25개 필드 통일)
- ✅ **사업자 중심 관리** (18개 사업자별 모듈)
- ✅ **제휴 현황 관리** (사업자별 플랫폼 연동)
- ✅ **중복 제거 로직** (다중 출처 통합)
- ✅ **Simple Mode** (YAML만으로 크롤러 생성)

---

## 🔄 마이그레이션 전략

### 옵션 1: 점진적 마이그레이션 (추천) ✅

**전략:** 기존 시스템 유지하면서 신규 시스템을 병행 구축

```
Phase 1: 신규 시스템 구축 (Week 1-3)
    └── 기존 시스템은 계속 운영
         ↓
Phase 2: MVP 검증 (Week 4)
    └── 헬로모바일 1개 사업자로 비교 테스트
         ↓
Phase 3: 단계적 전환 (Week 5-6)
    └── 사업자별로 하나씩 신규 시스템으로 이전
         ↓
Phase 4: 완전 전환
    └── 기존 시스템 폐기
```

**장점:**
- 리스크 최소화 (기존 시스템이 백업 역할)
- 데이터 비교 검증 가능
- 문제 발생 시 롤백 가능

**단점:**
- 전환 기간 중 이중 관리

---

### 옵션 2: 병렬 운영 (안전) ✅✅

**전략:** 두 시스템을 영구히 병렬 운영

```
[기존 시스템]              [신규 시스템]
mvno_system/              mvno_integrated_system/
    ↓                          ↓
플랫폼 중심 수집     →    사업자 중심 통합 수집
    ↓                          ↓
[데이터 비교 및 검증]
    ↓
[최종 통합 DB]
```

**장점:**
- 최대 안정성 (이중화)
- 데이터 품질 검증 용이
- 기존 시스템 자산 100% 활용

**단점:**
- 리소스 2배 사용
- 관리 복잡도 증가

---

### 옵션 3: 전면 재구축 (비추천) ❌

**전략:** 기존 시스템 폐기 후 신규 시스템만 사용

**장점:**
- 깔끔한 시작

**단점:**
- 높은 리스크
- 검증 기간 없음
- 문제 발생 시 대응 어려움

---

## 📦 마이그레이션 체크리스트

### Phase 1: 신규 시스템 구축 준비

#### Week 1: 환경 설정
- [ ] 신규 디렉토리 생성 (`E:\알뜰폰\mvno_integrated_system`)
- [ ] 표준 스키마 작성 (`config/schema/standard.yaml`)
- [ ] 파싱 규칙 정의 (`config/schema/parsers.yaml`)
- [ ] 핵심 엔진 구현 (SchemaEngine, ParserEngine)

#### Week 2: 크롤러 마이그레이션 시작
- [ ] **기존 크롤러 분석**
  ```bash
  # 기존 크롤러 중 가장 안정적인 것 선택
  # 예: hellomobile, phoneb
  ```

- [ ] **신규 형식으로 변환**
  ```yaml
  # 기존: config/selectors/hellomobile.yaml
  selectors:
    list:
      item_card: 'li.list-item'
      plan_name: '.plan-rate-name'

  # 신규: config/selectors/official/hellomobile.yaml
  metadata:
    crawl_mode: "simple"

  selectors:
    list:
      item_card: 'li.list-item'

  schema_mapping:        # ← 추가
    carrier:
      type: "fixed"
      value: "헬로모바일"
    plan_name:
      type: "selector"
      selector: ".plan-rate-name"
  ```

#### Week 3: MVP 검증
- [ ] 헬로모바일 자사사이트 크롤러 작동 확인
- [ ] 폰비 크롤러 작동 확인
- [ ] HelloMobileModule (통합 모듈) 작동 확인
- [ ] **데이터 비교 검증**
  ```python
  # 기존 시스템 결과
  old_data = crawl_with_old_system()

  # 신규 시스템 결과
  new_data = crawl_with_new_system()

  # 비교
  compare_data_quality(old_data, new_data)
  ```

---

### Phase 2: 기존 자산 활용 방안

#### 1. 셀렉터 YAML 재사용

**기존 파일 위치:**
```
E:\알뜰폰\크롤링\mvno_system\config\selectors\
├── hellomobile.yaml
├── phoneb.yaml
├── moyo.yaml
└── ... (23개)
```

**마이그레이션 스크립트:**
```python
# migrate_selectors.py
import yaml
from pathlib import Path

def migrate_selector_yaml(old_path, new_path):
    """기존 YAML을 신규 형식으로 변환"""

    with open(old_path, 'r', encoding='utf-8') as f:
        old_config = yaml.safe_load(f)

    # 신규 형식으로 변환
    new_config = {
        'metadata': {
            'provider': old_config.get('metadata', {}).get('provider', ''),
            'base_url': old_config.get('url', ''),
            'crawl_mode': 'simple'  # 기본값
        },
        'selectors': old_config.get('selectors', {}),
        'schema_mapping': {
            # 자동 생성 (기본 매핑)
            'carrier': {'type': 'fixed', 'value': ''},
            'plan_name': {'type': 'selector', 'selector': ''},
            # ... (나머지 필드)
        }
    }

    with open(new_path, 'w', encoding='utf-8') as f:
        yaml.dump(new_config, f, allow_unicode=True)

# 실행
for yaml_file in Path('old_system/config/selectors').glob('*.yaml'):
    migrate_selector_yaml(
        yaml_file,
        f'new_system/config/selectors/platforms/{yaml_file.name}'
    )
```

#### 2. 데이터베이스 마이그레이션

**기존 DB:**
```python
# mvno_system/storage/database.py
class Plan(Base):
    carrier = Column(String(100))
    plan_name = Column(String(200))
    price = Column(String(50))
    data_raw = Column(String(100))
    details = Column(JSON)  # 비정형 데이터
```

**신규 DB:**
```python
# mvno_integrated_system/storage/database.py
class Plan(Base):
    # 표준 필드 (25개)
    carrier = Column(String(100))
    plan_name = Column(String(200))
    data = Column(String(50))
    voice = Column(String(50))
    sms = Column(String(50))
    price_regular = Column(Integer)
    price_promo = Column(Integer)
    # ... (나머지 필드)

    # 메타데이터
    provider_code = Column(String(50))
    source_url = Column(Text)
    crawl_date = Column(DateTime)
    data_quality = Column(String(20))
```

**마이그레이션 스크립트:**
```python
# migrate_database.py
from old_system.storage.database import Plan as OldPlan
from new_system.storage.database import Plan as NewPlan
from new_system.core.schema_engine import SchemaEngine

def migrate_database():
    """기존 DB 데이터를 신규 스키마로 변환"""

    engine = SchemaEngine('default')
    old_session = OldSessionLocal()
    new_session = NewSessionLocal()

    old_plans = old_session.query(OldPlan).all()

    for old_plan in old_plans:
        # 표준 스키마로 변환
        new_data = engine.transform({
            'carrier': old_plan.carrier,
            'plan_name': old_plan.plan_name,
            'data': extract_data(old_plan.data_raw),
            'price_regular': extract_price(old_plan.price),
            # ... (나머지 필드)
        })

        # 신규 DB에 저장
        new_plan = NewPlan(**new_data)
        new_session.add(new_plan)

    new_session.commit()
```

#### 3. 스케줄러 설정 마이그레이션

**기존:**
```yaml
# mvno_system/config/schedule.yaml
schedules:
  phoneb:
    enabled: true
    cron: "0 */12 * * *"

  moyo:
    enabled: true
    cron: "0 */6 * * *"
```

**신규:**
```yaml
# mvno_integrated_system/config/schedule.yaml
carriers:
  hellomobile:
    enabled: true
    cron:
      hour: "2"
      minute: "0"
      day_of_week: "*"

  kgmobile:
    enabled: true
    cron:
      hour: "3"
      minute: "0"
```

---

## 🔧 기존 크롤러 개선 방안

### 문제 1: 하드코딩된 셀렉터

**기존 코드 (phoneb_crawler.py):**
```python
# ❌ JS 내부에 하드코딩
plan_data = await page.evaluate('''() => {
    const planNameSpan = document.querySelector('._1sdiozaf');  // 하드코딩
    const dataSpan = document.querySelector('._1sdiozag');      // 하드코딩
    return {planName: planNameSpan.textContent, ...};
}''')
```

**개선 방법:**
```python
# ✅ YAML에서 셀렉터 주입
selectors = self.load_selectors()
selectors_json = json.dumps(selectors['detail'])

plan_data = await page.evaluate(f'''(selectors) => {{
    const planNameSpan = document.querySelector(selectors.plan_name);
    const dataSpan = document.querySelector(selectors.data_info);
    return {{planName: planNameSpan.textContent, ...}};
}}''', selectors_json)
```

**또는 Simple Mode 전환:**
```yaml
# config/selectors/platforms/phoneb.yaml
schema_mapping:
  plan_name:
    type: "selector"
    selector: "._1sdiozaf"
  data:
    type: "selector"
    selector: "._1sdiozag"
    parser: "data_parser"
```

### 문제 2: 데이터 스키마 불일치

**기존:**
```python
# hellomobile_crawler.py
plan_data = {
    'carrier': '헬로모바일',
    'plan_name': '...',
    'data': '...',
    'voice': '...'
}

# phoneb_crawler.py
plan_data = {
    'carrier': '...',
    'plan_name': '...',
    'network': '...',    # ← hellomobile에는 없음
    'price': '...'
}
```

**개선:**
```python
# 모든 크롤러가 동일한 스키마 사용
from core.schema_engine import SchemaEngine

class BaseCrawler:
    def to_standard_schema(self, raw_data):
        return SchemaEngine.transform(raw_data)
        # → 25개 필드로 통일
```

### 문제 3: 사업자 구분 없음

**기존:**
```python
# 플랫폼별로만 실행 가능
python main.py --platform phoneb  # 모든 사업자 수집
```

**개선:**
```python
# 사업자 중심으로 실행
python main.py --carrier hellomobile
# → 자사사이트 + 제휴 플랫폼 자동 통합
```

---

## 📊 데이터 비교 검증

### 검증 스크립트

```python
# compare_systems.py
import pandas as pd

def compare_crawl_results():
    """기존 vs 신규 시스템 결과 비교"""

    # 1. 기존 시스템 실행
    old_data = run_old_crawler('hellomobile')

    # 2. 신규 시스템 실행
    new_data = run_new_crawler('hellomobile')

    # 3. 비교
    df_old = pd.DataFrame(old_data)
    df_new = pd.DataFrame(new_data)

    print(f"기존 시스템: {len(df_old)}개")
    print(f"신규 시스템: {len(df_new)}개")

    # 4. 필드별 비교
    common_fields = ['carrier', 'plan_name', 'data', 'price_regular']

    for field in common_fields:
        if field in df_old.columns and field in df_new.columns:
            old_missing = df_old[field].isna().sum()
            new_missing = df_new[field].isna().sum()

            print(f"{field}:")
            print(f"  기존 누락: {old_missing}개")
            print(f"  신규 누락: {new_missing}개")

            if new_missing < old_missing:
                print(f"  ✅ 개선됨 ({old_missing - new_missing}개)")
            elif new_missing > old_missing:
                print(f"  ⚠️ 악화됨 ({new_missing - old_missing}개)")

    # 5. 데이터 품질 비교
    print("\n데이터 품질:")
    print(f"  기존: {calculate_quality(df_old):.1f}%")
    print(f"  신규: {calculate_quality(df_new):.1f}%")

def calculate_quality(df):
    """데이터 품질 계산 (필수 필드 완성도)"""
    required = ['carrier', 'plan_name', 'data', 'voice', 'sms', 'price_regular']
    total = len(df) * len(required)
    filled = sum(df[field].notna().sum() for field in required if field in df.columns)
    return (filled / total) * 100
```

---

## 🚦 마이그레이션 의사결정 가이드

### 언제 기존 시스템을 유지할까?

**유지 권장:**
- ✅ 현재 시스템이 안정적으로 작동 중
- ✅ 데이터 품질 검증 기간 필요
- ✅ 리스크 회피 우선

**방법:**
```bash
# 병렬 운영
/알뜰폰/
├── 크롤링/mvno_system/              # 기존 (유지)
└── mvno_integrated_system/          # 신규 (병행 구축)
```

### 언제 신규 시스템으로 전환할까?

**전환 권장:**
- ✅ MVP 검증 완료 (Week 3)
- ✅ 데이터 품질 기존 대비 95% 이상
- ✅ 3개 이상 사업자 정상 작동 확인

**전환 절차:**
```bash
# 1. 신규 시스템 검증 (1주일)
python new_system/main.py --carrier hellomobile
# → 결과 확인

# 2. 데이터 비교
python compare_systems.py
# → 품질 확인

# 3. 점진적 전환 (사업자별)
# Week 1: hellomobile
# Week 2: kgmobile, freet
# Week 3: 나머지 사업자

# 4. 완전 전환 (Week 6)
# 기존 시스템 스케줄러 중지
# 신규 시스템만 운영
```

---

## 📝 롤백 계획

### 문제 발생 시 롤백

**상황:**
- 신규 시스템에서 치명적 버그 발견
- 데이터 품질 저하
- 성능 문제

**롤백 절차:**
```bash
# 1. 신규 시스템 스케줄러 중지
cd mvno_integrated_system
python main.py --stop-scheduler

# 2. 기존 시스템 재활성화
cd ../크롤링/mvno_system
python main.py --start-scheduler

# 3. 신규 시스템 버그 수정
# (기존 시스템이 백업 역할)

# 4. 수정 후 재검증
```

**롤백 체크리스트:**
- [ ] 신규 시스템 중지 확인
- [ ] 기존 시스템 정상 작동 확인
- [ ] 데이터 수집 중단 없음 확인
- [ ] 버그 원인 분석 및 기록

---

## 🎯 권장 마이그레이션 방안

### **"점진적 병렬 운영" (Best Practice)**

```
Week 1-3: 신규 시스템 MVP 구축
    ↓
Week 4: 헬로모바일 1개 사업자 병렬 운영
    ├── 기존 시스템: 계속 수집
    └── 신규 시스템: 병행 수집 → 데이터 비교
    ↓
Week 5: 3개 사업자 병렬 운영
    ├── hellomobile, kgmobile, freet
    └── 데이터 품질 95% 이상 확인
    ↓
Week 6: 전체 사업자 전환
    ├── 신규 시스템: 18개 사업자 모두 전환
    └── 기존 시스템: 백업 모드 (1개월)
    ↓
Week 10: 기존 시스템 폐기
    └── 신규 시스템만 운영
```

**장점:**
- ✅ 리스크 최소화
- ✅ 데이터 검증 기간 충분
- ✅ 롤백 가능
- ✅ 점진적 학습 가능

---

## 📞 지원 및 문의

### 마이그레이션 중 문제 발생 시

1. **데이터 품질 저하**
   - `compare_systems.py` 실행
   - 어느 필드에서 문제인지 확인
   - 해당 크롤러 YAML 점검

2. **크롤러 오류**
   - 로그 확인 (`storage/crawler.log`)
   - Health Check 실행
   - 사이트 구조 변경 여부 확인

3. **성능 문제**
   - 병렬 크롤링 수 조정
   - headless 모드 확인
   - 메모리 사용량 모니터링

---

## ✅ 마이그레이션 완료 체크리스트

### MVP 완료 (Week 3)
- [ ] 헬로모바일 자사사이트 크롤러 작동
- [ ] 폰비 크롤러 작동
- [ ] HelloMobileModule 작동
- [ ] 데이터 품질 기존 대비 95% 이상

### Phase 1 완료 (Week 5)
- [ ] 18개 자사사이트 크롤러 완성
- [ ] 6개 플랫폼 크롤러 완성
- [ ] 18개 사업자 통합 모듈 완성

### 최종 완료 (Week 6)
- [ ] 스케줄러 정상 작동
- [ ] 24시간 무인 운영 테스트 통과
- [ ] 기존 시스템 대비 데이터 품질 동등 이상
- [ ] 문서화 완료

---

**작성일:** 2026-01-28
**버전:** 1.0.0
**대상:** 구글 안티그래비티 프로그램 개발팀
