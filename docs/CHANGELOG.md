# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- [ ] Week 1: 기반 구축 (표준 스키마, 핵심 엔진)
- [ ] Week 2: MVP 구현 (헬로모바일 + 폰비)
- [ ] Week 3: 사업자 통합 모듈
- [ ] Week 4-5: 전체 사업자 확장
- [ ] Week 6: 자동화 스케줄러

---

## [1.0.0] - 2026-01-28

### Added
- 프로젝트 초기 구조 설계
- README.md 작성
- GUIDELINES.md 작성 (상세 구축 가이드)
- 표준 스키마 정의 (25개 필수 필드)
- 구축 로드맵 (6주 계획)
- requirements.txt (의존성 패키지)
- .gitignore (Git 제외 파일)

### Architecture
- 3단계 아키텍처 설계
  - Phase 1: 개별 크롤러 (24개)
  - Phase 2: 사업자 통합 모듈 (18개)
  - Phase 3: 자동화 스케줄러

### Components
- 핵심 엔진 설계
  - SchemaEngine (스키마 검증/변환)
  - ParserEngine (파싱 규칙)
  - SelectorManager (동적 셀렉터)
  - PlatformLoader (Factory Pattern)

- 크롤러 설계
  - BaseCrawler (추상 베이스)
  - UniversalCrawler (YAML 전용)
  - Simple Mode vs Advanced Mode

- 사업자 통합 모듈 설계
  - BaseCarrierModule (추상 베이스)
  - 중복 제거 알고리즘
  - 우선순위 기반 데이터 선택

### Documentation
- MVP 검증 기준 정의
- 크롤러 개발 가이드
- 사업자 통합 모듈 가이드
- 스케줄러 구현 가이드

---

## Version History

### v1.0.0 - 초기 설계 (2026-01-28)
- 프로젝트 구조 설계 완료
- 문서화 완료
- Git 저장소 초기화

---

## Upcoming Milestones

### MVP (Week 3)
- 헬로모바일 자사사이트 크롤러
- 폰비 플랫폼 크롤러
- HelloMobileModule (통합 모듈)
- 데이터 품질 95% 이상 달성

### Phase 1 (Week 5)
- 18개 자사사이트 크롤러 완성
- 6개 플랫폼 크롤러 완성
- 18개 사업자 통합 모듈 완성

### Phase 2 (Week 6)
- MasterScheduler 구현
- 24시간 무인 운영
- 에러 알림 시스템 (Slack)
- 최종 안정화

---

**참고:**
- 각 마일스톤 완료 시 태그 생성 예정
- 주요 변경사항은 GitHub Releases에 기록
