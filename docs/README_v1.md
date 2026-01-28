# MVNO Monitoring Crawler System

국내 주요 알뜰폰(MVNO) 사업자와 중개 플랫폼의 요금제 정보를 실시간으로 수집하고 모니터링하는 시스템입니다.

## 📌 지원 플랫폼 (13개)
*   **중개/통합:** 모요, 알뜰폰허브, 폰비, 마이알뜰폰
*   **통신사 (자회사):** KT M Mobile, 보남모바일(SkyLife), SK 7Mobile, U+ 유모바일, 헬로모바일, 리브모바일, 프리티
*   **기타 파트너:** 알닷, 토스모바일

## 📁 디렉토리 구조
```
mvno_system/
├── config/             # 플랫폼별 설정 (YAML) 및 CSS 셀렉터
├── core/               # 크롤러 로더 및 공통 로직
├── crawlers/           # 개별 크롤러 구현체 (Platform Specific Code)
├── storage/            # 데이터베이스 모델 및 세션 관리
├── utils/              # 로깅 및 헬퍼 함수
└── main.py             # 메인 실행 진입점

tests/                  # 개별 크롤러 테스트 스크립트 (run_*_test.py)
debug/                  # 개발 디버깅 스크립트 및 덤프 파일
```

## 🚀 설치 및 실행

### 1. 환경 설정
Python 3.9+ 환경이 필요합니다.
```bash
# 가상환경 생성 (권장)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 실행 방법
```bash
# 메인 시스템 실행 (대화형 메뉴)
python mvno_system/main.py

# 스케줄러 모드 실행 (데몬)
python mvno_system/main.py --scheduler
```

### 3. 테스트 실행
특정 플랫폼만 빠르게 검증하고 싶을 때 사용합니다.
```bash
# 예: 리브모바일 테스트
python tests/run_liivm_test.py
```

## ⚠️ 주의사항
*   **LiivM / UMobile:** 모바일 뷰포트 에뮬레이션 및 팝업 제어가 포함되어 있습니다.
*   **동기화:** `storage/screenshots` 폴더는 용량이 크므로 Git 등 VCS 업로드 시 제외하는 것을 권장합니다.

## License
Private Project
