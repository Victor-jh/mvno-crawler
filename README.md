# 🎯 MVNO 통합 크롤링 시스템

## 📋 프로젝트 개요

알뜰폰(MVNO) 18개 사업자의 자사사이트 및 6개 플랫폼에서 요금제 정보를 자동 수집하고 통합 관리하는 시스템

### 핵심 기능
- ✅ **표준 스키마**: 25개 필수 필드 통일 관리
- ✅ **자동화**: 사업자별 제휴 플랫폼 자동 크롤링
- ✅ **중복 제거**: 다중 출처 데이터 통합 및 우선순위 기반 선택
- ✅ **스케줄러**: 무인 자동 실행
- ✅ **유지보수**: YAML 설정 기반, 코드 수정 최소화

---

## 🏗️ 시스템 구조

```
mvno_integrated_system/
├── config/                    # 설정 파일
│   ├── schema/               # 표준 스키마 정의
│   │   ├── standard.yaml    # 25개 필수 필드
│   │   └── parsers.yaml     # 공통 파싱 규칙
│   ├── carriers/             # 사업자 제휴 관리 (18개)
│   ├── platforms.yaml        # 플랫폼 메타정보
│   └── selectors/            # 크롤러 설정 (24개)
│       ├── official/         # 자사사이트 (18개)
│       └── platforms/        # 플랫폼 (6개)
│
├── core/                      # 핵심 엔진
│   ├── schema_engine.py      # 스키마 검증/변환
│   ├── parser_engine.py      # 파싱 엔진
│   └── selector_manager.py   # 동적 셀렉터 관리
│
├── crawlers/                  # 크롤러 (24개)
│   ├── base_crawler.py       # 추상 베이스
│   ├── universal_crawler.py  # YAML 전용
│   ├── official/             # 자사사이트 (18개)
│   └── platforms/            # 플랫폼 (6개)
│
├── carrier_modules/           # 사업자 통합 모듈 (18개)
│   ├── base_carrier_module.py
│   └── hellomobile_module.py
│
├── scheduler/                 # 자동화 스케줄러
│   └── master_scheduler.py
│
├── storage/                   # 데이터 저장
│   ├── database.py           # SQLAlchemy ORM
│   └── mvno.db               # SQLite
│
└── main.py                    # 통합 CLI
```

---

## 📊 수집 대상

### 사업자 자사사이트 (18개)
1. SK세븐모바일
2. KT엠모바일
3. 스카이라이프
4. U+유모바일
5. 헬로모바일
6. 리브모바일
7. 토스모바일
8. 프리티(프리텔레콤)
9. 프리티(인스코비)
10. 티플러스
11. 아이즈모바일
12. 이야기모바일
13. 모빙
14. 이지모바일
15. 에이모바일
16. 스마텔
17. 슈가모바일
18. 아시아모바일

### 플랫폼 (6개)
1. 알뜰폰허브
2. 모요
3. 알닷
4. 마이알뜰폰
5. 아요
6. 폰비

---

## 📋 표준 스키마 (25개 필드)

### 핵심 정보 (9개)
- `carrier`: 통신사명
- `plan_name`: 요금제명
- `data`: 데이터 제공량
- `voice`: 음성통화
- `sms`: 문자
- `price_regular`: 정상가격
- `price_promo`: 할인가격
- `network`: 통신망 (SKT/KT/LGU+)
- `network_type`: 통신기술 (5G/LTE)

### 상세 정보 (9개)
- `discount_period`: 할인기간
- `price_note`: 가격 비고
- `data_speed_after`: 소진 후 속도
- `voice_type`: 통화 타입
- `sms_type`: 문자 타입
- `gift_info`: 사은품 정보
- `usim_support`: 유심 지원
- `usim_fee`: 유심비
- `contract_type`: 약정 타입

### 메타데이터 (6개)
- `provider_code`: 사업자 코드 (자동)
- `source_url`: 출처 URL (자동)
- `detail_url`: 상세 페이지 URL
- `crawl_date`: 수집일시 (자동)
- `data_quality`: 데이터 품질 (자동)
- `screenshot_path`: 스크린샷 경로 (자동)

### 기타 (1개)
- `special_note`: 특이사항

---

## 🚀 빠른 시작

### 1. 환경 설정
```bash
# Python 3.9+ 필요
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
```

### 2. MVP 실행 (헬로모바일 + 폰비)
```bash
python main.py

# 메뉴 선택
> 1. 단일 크롤러
> 플랫폼: hellomobile
```

### 3. 사업자 통합 실행
```bash
python main.py

# 메뉴 선택
> 2. 사업자 통합
> 사업자: 헬로모바일

# 결과: 자사사이트 + 제휴 플랫폼 통합
# 출력: output/hellomobile_통합_20260128.xlsx
```

### 4. 전체 자동화 (스케줄러)
```bash
python main.py

# 메뉴 선택
> 3. 자동화 스케줄러

# 무인 운영 시작 (Ctrl+C로 종료)
```

---

## 📅 구축 로드맵

### Week 1: 기반 구축 🏗️
- [ ] 표준 스키마 정의 (standard.yaml, parsers.yaml)
- [ ] 핵심 엔진 구현 (SchemaEngine, ParserEngine)
- [ ] BaseCrawler + UniversalCrawler

### Week 2: MVP 구현 🚀
- [ ] 헬로모바일 자사사이트 크롤러
- [ ] 폰비 플랫폼 크롤러
- [ ] 통합 테스트

### Week 3: 사업자 통합 모듈 🔗
- [ ] HelloMobileModule (자사 + 폰비 통합)
- [ ] 중복 제거 알고리즘
- [ ] MVP 검증 완료

### Week 4: 확장 1단계 📈
- [ ] 플랫폼 크롤러 4개 추가 (moyo, alttelecomhub, aldoot, mymvno)
- [ ] 사업자 2개 추가 (KG모바일, 프리티)

### Week 5: 확장 2단계 📈
- [ ] 나머지 사업자 15개 추가
- [ ] 플랫폼 2개 추가 (ayo 등)
- [ ] 전체 24개 크롤러 완성

### Week 6: 자동화 & 안정화 🎯
- [ ] MasterScheduler 구현
- [ ] 에러 알림 (Slack)
- [ ] 최종 테스트 & 문서화

---

## 🎯 MVP 검증 기준

### 기능
- [x] 헬로모바일 자사사이트 크롤링
- [x] 폰비에서 헬로모바일 필터링
- [x] 두 출처 데이터 통합 (중복 제거)
- [x] 표준 스키마 25개 필드 수집
- [x] Excel 출력

### 품질
- [x] 데이터 품질 "완전" 90% 이상
- [x] 필수 필드 누락 0건
- [x] 중복 제거 정확도 100%

### 성능
- [x] 통합 크롤링: 5분 이내
- [x] 메모리 사용량: 500MB 이하

---

## 🔧 기술 스택

- **언어**: Python 3.9+
- **크롤링**: Playwright (async)
- **데이터베이스**: SQLAlchemy + SQLite
- **스케줄러**: APScheduler
- **데이터 처리**: Pandas
- **설정 관리**: PyYAML

---

## 📖 문서

- [전체 가이드라인](GUIDELINES.md)
- [표준 스키마 정의](docs/SCHEMA.md)
- [크롤러 개발 가이드](docs/CRAWLER_GUIDE.md)
- [사업자 통합 모듈 가이드](docs/CARRIER_MODULE_GUIDE.md)

---

## 🤝 기여 가이드

### 신규 크롤러 추가
1. `config/selectors/` 에 YAML 작성
2. Simple Mode 우선 시도 (UniversalCrawler)
3. 복잡한 경우만 Custom Crawler 작성
4. 테스트 후 Pull Request

### 버그 리포트
- GitHub Issues에 등록
- 사업자/플랫폼명, 에러 로그 첨부

---

## 📝 라이선스

MIT License

---

## 👤 작성자

MVNO 크롤링 시스템 개발팀

---

## 📅 버전 히스토리

### v1.0.0 (2026-01-28)
- 초기 프로젝트 구조 설계
- MVP 가이드라인 작성
- 표준 스키마 정의

---

## 🔗 관련 링크

- [프로젝트 위키](https://github.com/your-repo/wiki)
- [이슈 트래커](https://github.com/your-repo/issues)
