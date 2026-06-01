# D3D Audit Report - audit_report_78.md

## 0. 감사 요약

- 감사 기준: `AI_AUDIT_DOC_STANDARD.md`
- 감사 방식: 재감사, 구현 중심 3-Pass 감사
- 감사 대상 경로: `/mnt/Projects_SSD/python/JissouParkEmpire`
- 직전 감사 문서: `audit_report_77.md`
- 새 보고서 번호: `audit_report_78.md`
- 감사일: 2026-06-01
- 최종 판정: **HOLD**

이번 재감사는 77번 감사의 HOLD 사유가 실제 구현과 문서에서 얼마나 해소되었는지 확인하는 방식으로 수행했다. 실행 게이트 자체는 양호하다. `pytest`, `-W error`, `py_compile`, `git diff --check`, DB 설정 smoke, SQLite PRAGMA smoke, 개발 서버 바인딩 보안 smoke, XSS mutation smoke는 모두 통과했다. 특히 77번에서 해소 확인된 `run.py` 사용자-facing 배너 버전은 현재도 `v1.8.9`로 유지된다.

그러나 PASS로 전환할 수는 없다. 감사 산출물 및 작업트리 추적성, README 다국어 품질, 문서/주석의 hard-boundary 표현, 문서 파일명 authority 불일치, 실제 RDBMS/브라우저 DOM E2E 미검증 리스크가 남아 있다. 따라서 현재 판정은 구현 실행 실패가 아닌 **품질 게이트와 문서 authority 정합성 미완료로 인한 HOLD**다.

## 1. Audit Scope

### 1.1 포함 범위

- 감사 표준: `AI_AUDIT_DOC_STANDARD.md`
- 직전 감사: `audit_report_77.md`
- 프로젝트 governance 문서: `AGENTS.md` 지침, `spec.md`, `README.md`, `CHANGELOG.md`, `BUILD_GUIDE.md`, `DESIGN_DECISIONS.md`, `audit_roadmap.md`, `designs.md`, `implementation_summary.md`, `lessons_learned.md`
- 구현 파일: `run.py`, `app/config.py`, `app/game_engine.py`, `app/npc_engine.py`, `app/static/js/game.js`, `app/routes/game_routes.py`
- 테스트 파일: `tests/conftest.py`, `tests/test_regression.py`
- 의존성: `requirements.txt`
- 로컬 상태: `git status --short`, `git diff --stat`, `git diff --check`, `git diff --cached --check`

### 1.2 감사 기준 적용

`AI_AUDIT_DOC_STANDARD.md`는 감사 입력물, 결과물, 3-Pass 실행 모델, finding status/severity, 보안 경계, 재감사 조건을 요구한다. 특히 다음 기준을 적용했다.

- 문서와 구현의 정합성 판정
- 빌드/실행/테스트 재현성 판정
- 보안 경계와 공격 표면 판정
- 문서-소스 양방향 동기화 판정
- 재감사와 Phase gate 판정
- finding별 evidence, expected, actual, impact, suggested fix, re-audit method 기록

## 2. Excluded Scope

- 소스 코드 수정: 사용자 지시에 따라 수행하지 않음
- 기존 문서 수정: 사용자 지시에 따라 수행하지 않음
- 실제 PostgreSQL/MySQL 인스턴스 기반 row-lock/deadlock E2E: 로컬 인프라 미제공으로 제외
- 실제 브라우저 또는 jsdom 기반 DOM XSS E2E: 로컬 테스트 스위트에 없음
- Gunicorn 다중 워커 부하 테스트: 로컬 수동 smoke 범위 밖
- 모바일/APK Phase 9 구현 검증: 현재 Phase 밖
- `.antigravitycli/`, `stitch_shitsiseki_empire_ui_refactor/`: 현재 감사 대상 변경 범위가 아니므로 내용 감사 제외

## 3. 이전 감사 요청사항 재확인

직전 `audit_report_77.md`의 최종 판정은 HOLD였다. 77번 감사의 잔여 사유는 다음이었다.

1. 최신 감사 보고서 73-77이 추적성 정리 전 상태
2. 문서/코드/테스트 modified 상태가 남아 clean base와 의도 변경 구분 필요
3. 한국어 README와 일부 소스 주석에 검증 범위를 초과하는 `보장`, `원천`, `근본`, `완치`, `0 보장` 계열 표현 잔존
4. README 일본어/번체/간체 섹션의 언어 혼입과 번역 품질 회귀
5. 실제 PostgreSQL/MySQL E2E 및 브라우저 DOM E2E는 Accepted Risk 또는 Known Residual Risk로 유지

### 3.1 재감사 결과 매트릭스

| 77번 요구사항 | 78번 상태 | 판정 |
| --- | --- | --- |
| 감사 보고서 및 작업트리 추적성 정리 | `audit_report_73.md`-`audit_report_77.md`가 여전히 untracked, 12개 파일 modified | **Needs Fix / HOLD** |
| `run.py` 배너 버전 정렬 | `run.py` 헤더와 배너가 `v1.8.9`로 정렬, 서버 smoke에서도 `Jissou Park Empire v1.8.9` 출력 | **Verified** |
| README/소스 hard-boundary 표현 완화 | `game.js`, `game_engine.py` 등 일부는 `완화/낮춘다`로 개선됐으나 `audit_roadmap.md`, `CHANGELOG.md`, 일부 주석에는 강한 보증 표현 잔존 | **Partially Fixed / Needs Fix** |
| README 다국어 혼입 해소 | 일본어/번체/간체 섹션에 언어 혼입이 계속 존재 | **Needs Fix / HOLD** |
| 실제 RDBMS/브라우저 DOM E2E | 여전히 미수행. 문서상 Accepted Risk 또는 Known Residual Risk로만 관리 | **Accepted Risk / Residual Risk** |

## 4. Pass 1: Implementation Compliance Findings

## [IMP-F001] 감사 산출물과 작업트리 추적성이 아직 정리되지 않았다

- Pass: Implementation Compliance
- Pattern: Audit Traceability / Source of Truth
- Area: Git status, audit reports, release trace
- Severity: Major
- Status: Needs Fix / Hold
- Summary: 현재 구현은 테스트를 통과하지만, 최신 감사 보고서들과 변경 파일들이 추적성 정리 전 상태라 PASS 기준의 immutable audit trail이 성립하지 않는다.
- Evidence:
  - `git status --short` 결과:
    - `M CHANGELOG.md`
    - `M DESIGN_DECISIONS.md`
    - `M README.md`
    - `M app/config.py`
    - `M app/game_engine.py`
    - `M app/npc_engine.py`
    - `M app/static/js/game.js`
    - `M designs.md`
    - `M lessons_learned.md`
    - `M run.py`
    - `M tests/conftest.py`
    - `M tests/test_regression.py`
    - `?? audit_report_73.md`
    - `?? audit_report_74.md`
    - `?? audit_report_75.md`
    - `?? audit_report_76.md`
    - `?? audit_report_77.md`
    - `?? .antigravitycli/`
    - `?? stitch_shitsiseki_empire_ui_refactor/`
  - `git diff --stat` 결과: 12개 파일, 117 insertions, 117 deletions
- Expected: PASS 판정 전에는 감사 대상 변경과 감사 산출물이 추적 가능한 상태여야 한다.
- Actual: 변경 의도와 감사 산출물의 소유권이 아직 clean base와 분리되지 않았다.
- Impact: 이후 감사자가 어떤 변경이 구현 수정이고 어떤 변경이 감사 대응인지 재현하기 어렵다. PASS 판정의 근거가 약해진다.
- Suggested Fix: 감사 보고서 73-78의 보존 정책을 정하고, 현재 modified 파일들의 변경 목적을 정리한 뒤 커밋 또는 명시적 보류 목록으로 분리한다.
- Re-audit Method:
  - `git status --short`
  - `git diff --stat`
  - 최신 `audit_report_*.md` 연속성 확인

## [IMP-F002] `run.py` 사용자-facing 버전 drift는 해소된 상태다

- Pass: Implementation Compliance
- Pattern: Version Consistency
- Area: Runtime banner, release docs
- Severity: Info
- Status: Verified
- Summary: 76번에서 지적됐던 런타임 배너 버전 불일치는 77번에서 해소되었고, 78번에서도 유지된다.
- Evidence:
  - `run.py:4`: `[v1.8.9] 개발 서버 실행. Gunicorn에서도 app 객체 직접 사용 가능.`
  - `run.py:52`: `print("  Jissou Park Empire v1.8.9")`
  - 서버 smoke:
    - 명령: `timeout 3 env SECRET_KEY=smoke-secret PYTHONDONTWRITEBYTECODE=1 venv/bin/python run.py`
    - 결과: `Jissou Park Empire v1.8.9`, `Running on http://127.0.0.1:5000`, exit code `124` by timeout
- Expected: 문서 릴리스 버전과 런타임 배너가 일치해야 한다.
- Actual: `v1.8.9`로 일치한다.
- Impact: 사용자-facing 실행 로그의 버전 혼란은 해소됐다.
- Suggested Fix: 없음.
- Re-audit Method: 서버 smoke를 재실행하고 배너 버전을 확인한다.

## [IMP-F003] README 다국어 섹션의 언어 혼입이 계속 남아 있다

- Pass: Implementation Compliance
- Pattern: User-Facing Documentation / i18n Quality
- Area: `README.md`
- Severity: Major
- Status: Needs Fix / Hold
- Summary: README는 AGENTS.md 및 프로젝트 규칙상 한국어, 영어, 일본어, 번체, 간체 순서의 다국어 사용자 문서여야 한다. 현재 일본어/번체/간체 섹션에 서로 다른 문자권과 어휘가 섞여 있어 사용자-facing 품질 게이트를 통과하기 어렵다.
- Evidence:
  - `README.md:307`: 일본어 문장에 번체/중국어 `持續` 혼입
  - `README.md:316`: 일본어 문장에 한국어 `적` 혼입 (`悲観적ロック`)
  - `README.md:342`: 번체 섹션에 간체 표현 다수 혼입 (`我们`, `交易拒绝`, `防护条件`, `仅筛选`, `发送方`, `交易提议`)
  - `README.md:346`: 번체 섹션에 간체 표현 다수 혼입 (`战斗内部`, `替换`, `保护`, `执行`, `悲观锁`)
  - `README.md:356`: 간체 섹션에 `事務事务` 중복 혼입
  - `README.md:360`: 간체 섹션에 번체 `持續` 혼입
  - `README.md:362`: 간체 섹션에 번체 `與`, `風險` 혼입
  - `README.md:368`, `README.md:376`: 간체 섹션에 번체 `鎖` 혼입
  - `README.md:374`: 간체 섹션에 번체 `已緩解` 혼입
- Expected: 각 언어 섹션은 해당 언어와 문자 체계로 일관되어야 한다.
- Actual: 여러 release note 문장에 언어 혼입이 존재한다.
- Impact: README의 다국어 품질이 낮아지고, 프로젝트가 주장하는 5개 언어 지원 신뢰도가 떨어진다.
- Suggested Fix: README 다국어 release note 구간을 언어별로 재검수한다. 번체와 간체는 문자 체계를 분리하고, 일본어 섹션은 한국어/중국어 문자 혼입을 제거한다.
- Re-audit Method:
  - `rg -n "悲観적|持續|事務事务|與 TOCTOU|相互鎖|已緩解|我们|仅筛选|发送方|战斗内部|替换|保护嵌套|执行显式|悲观锁" README.md`
  - 다국어 섹션 수동 읽기

## [IMP-F004] 문서 파일명 authority가 대소문자 기준에서 충돌한다

- Pass: Implementation Compliance
- Pattern: Required Inputs / Governance Drift
- Area: Required documentation files
- Severity: Minor
- Status: Needs Spec Clarification
- Summary: AGENTS.md의 Required Files에는 `IMPLEMENTATION_SUMMARY.md`, `LESSONS_LEARNED.md`가 명시되어 있으나 실제 저장소에는 소문자 `implementation_summary.md`, `lessons_learned.md`만 있다. 반면 `AI_AUDIT_DOC_STANDARD.md`는 `implementation_summary.md`를 입력물로 언급하고 `LESSONS_LEARNED.md`도 요구한다.
- Evidence:
  - `ls -1 spec.md README.md CHANGELOG.md BUILD_GUIDE.md IMPLEMENTATION_SUMMARY.md implementation_summary.md LESSONS_LEARNED.md lessons_learned.md DESIGN_DECISIONS.md audit_roadmap.md designs.md AI_AUDIT_DOC_STANDARD.md`
  - 결과:
    - `IMPLEMENTATION_SUMMARY.md`: No such file
    - `LESSONS_LEARNED.md`: No such file
    - `implementation_summary.md`: 존재
    - `lessons_learned.md`: 존재
- Expected: required document set은 대소문자까지 포함해 단일 authority가 있어야 한다.
- Actual: Linux 파일시스템에서는 대소문자 파일명이 다르므로 일부 규칙상 required file이 누락으로 보인다.
- Impact: 자동 감사나 cross-platform 환경에서 누락 문서로 오판될 수 있다.
- Suggested Fix: 표준 파일명을 하나로 결정한다. 소문자명을 유지할 경우 AGENTS.md/표준 문서를 동기화하고, 대문자명을 요구할 경우 파일명 변경 또는 alias 문서를 만든다.
- Re-audit Method: required docs inventory를 다시 실행하고 표준 문서와 대조한다.

## [IMP-F005] hard-boundary 표현 완화는 부분 완료 상태다

- Pass: Implementation Compliance
- Pattern: Documentation-Implementation Claim Alignment
- Area: README, CHANGELOG, audit_roadmap, source comments
- Severity: Major
- Status: Partially Fixed / Needs Fix
- Summary: 77번에서 지적된 `완치`, `원천`, `근본`, `보장` 계열 표현 중 일부는 `완화`, `낮춘다`로 개선됐다. 그러나 문서와 일부 주석에는 아직 구현/테스트 범위를 초과할 수 있는 강한 보증 표현이 남아 있다.
- Evidence:
  - 개선 확인:
    - `app/static/js/game.js:4`: `DOM XSS 취약점 완화`
    - `app/game_engine.py:195`: `락 순서 역전 교착 상태 완화`
    - `README.md:57`: 실제 PostgreSQL/MySQL 검증을 Accepted Risk로 명시
  - 잔존 표현:
    - `app/routes/game_routes.py:761`: `근본 차단`
    - `app/routes/game_routes.py:777`: `안전하게 차단`
    - `app/routes/game_routes.py:1042`: `Canonical Ordering: 항상 park_a_id < park_b_id 보장`
    - `app/routes/game_routes.py:1193`: `Canonical Ordering: 항상 park_a_id < park_b_id 보장`
    - `audit_roadmap.md:122`: `완전 해결`
    - `audit_roadmap.md:126`: `완치 검증 완료`
    - `audit_roadmap.md:127`: `원천 차단 검증 완료`
    - `audit_roadmap.md:129`: `데드락 완치`
    - `CHANGELOG.md:23`: `원천 소멸`, `안전하게 동시 획득하도록 보장`
    - `CHANGELOG.md:27`: `취약점을 치료`, `무결성을 달성`
    - `CHANGELOG.md:29`: `무결성을 달성`
- Expected: 실제 검증이 SQLite/정적 테스트/로컬 smoke 중심인 항목은 hard guarantee가 아니라 설계적 완화, 특정 조건 하 검증, Accepted Risk로 표현해야 한다.
- Actual: 일부 문서와 주석은 여전히 완전 해결 또는 절대 보증처럼 읽힐 수 있다.
- Impact: 실제 RDBMS/브라우저 DOM/Gunicorn E2E 미수행 상태와 충돌한다. 감사 기준상 hard boundary가 불명확하면 HOLD 또는 Needs Spec Clarification 대상이다.
- Suggested Fix: 문서와 소스 주석에서 hard-boundary 표현을 검증 범위와 일치하도록 정리한다. 불변식 보장처럼 코드상 수학적으로 성립하는 표현은 유지 가능하지만, 외부 런타임/동시성/보안 완전성을 암시하는 표현은 완화한다.
- Re-audit Method:
  - `rg -n "완치|완전 해결|원천|근본|보장|무결성을 달성|치료|0건|완벽" README.md CHANGELOG.md audit_roadmap.md app tests`
  - 실제 E2E 범위와 표현을 수동 대조한다.

## 5. Pass 2: Debug / Engineering Quality Findings

## [DBG-F001] Python 회귀 테스트와 warning-as-error 게이트는 통과한다

- Pass: Debug / Engineering Quality
- Pattern: Deterministic Test Gate
- Area: `tests/test_regression.py`, pytest
- Severity: Info
- Status: Verified
- Summary: 현재 테스트 스위트는 기본 실행과 warning-as-error 실행 모두 통과한다.
- Evidence:
  - 명령: `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q`
  - 결과: `7 passed in 0.32s`
  - 명령: `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q -W error`
  - 결과: `7 passed in 0.32s`
- Expected: 회귀 테스트가 실패 없이 통과해야 한다.
- Actual: 통과.
- Impact: 최근 회귀 테스트가 현재 구현과 맞물려 실행 가능함을 확인했다.
- Suggested Fix: 없음.
- Re-audit Method: 동일 명령 재실행.

## [DBG-F002] 문법/공백 품질 게이트는 통과한다

- Pass: Debug / Engineering Quality
- Pattern: Static Quality Gate
- Area: Python syntax, diff whitespace
- Severity: Info
- Status: Verified
- Summary: Python 문법 검사와 Git whitespace 검사가 통과한다.
- Evidence:
  - 명령: `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m py_compile app/__init__.py app/battle_engine.py app/config.py app/game_engine.py app/models.py app/npc_engine.py app/routes/auth_routes.py app/routes/game_routes.py run.py tests/conftest.py tests/test_regression.py`
  - 결과: exit code `0`
  - 명령: `git diff --check`
  - 결과: exit code `0`
  - 명령: `git diff --cached --check`
  - 결과: exit code `0`
- Expected: syntax error와 whitespace error가 없어야 한다.
- Actual: 통과.
- Impact: 로컬 정적 품질 측면에서 즉시 차단되는 문제는 없다.
- Suggested Fix: 없음.
- Re-audit Method: 동일 명령 재실행.

## [DBG-F003] DB 설정 우선순위와 SQLite PRAGMA smoke는 통과한다

- Pass: Debug / Engineering Quality
- Pattern: Runtime Config / DB Portability
- Area: `app/config.py`, SQLAlchemy engine setup
- Severity: Info
- Status: Verified
- Summary: `SQLALCHEMY_DATABASE_URI`, `DATABASE_URL`, PostgreSQL driver import, SQLite WAL/busy_timeout 설정이 로컬 smoke에서 확인됐다.
- Evidence:
  - `DATABASE_URL=postgresql://u:p@localhost:5432/jissou_audit` smoke 결과: `postgresql://u:p@localhost:5432/jissou_audit`
  - `SQLALCHEMY_DATABASE_URI=postgresql://u:p@localhost:5432/jissou_uri` smoke 결과: `postgresql://u:p@localhost:5432/jissou_uri`
  - `import psycopg2` 결과: `2.9.12 (dt dec pq3 ext lo64)`
  - SQLite PRAGMA smoke 결과:
    - `journal_mode`: `wal`
    - `busy_timeout`: `5000`
  - `requirements.txt:9`: `psycopg2-binary>=2.9.0`
- Expected: 문서화된 DB 설정 fallback과 SQLite 완화 설정이 실제 런타임에서 작동해야 한다.
- Actual: smoke 범위에서는 작동한다.
- Impact: 설정 wiring은 구현되어 있다.
- Suggested Fix: 실제 PostgreSQL/MySQL E2E는 별도 Accepted Risk로 유지한다.
- Re-audit Method:
  - 환경변수별 config smoke 재실행
  - 실제 RDBMS 인스턴스에서 row-lock/deadlock E2E 추가 수행

## [DBG-F004] CI/workflow 파일은 검색되지 않아 수동 게이트 의존 상태다

- Pass: Debug / Engineering Quality
- Pattern: Reproducibility / CI
- Area: CI/CD
- Severity: Minor
- Status: Accepted Risk / Known Operational Risk
- Summary: 로컬 수동 게이트는 통과했지만 `.github` 또는 workflow/ci 파일은 검색되지 않았다.
- Evidence:
  - 명령: `rg --files -g '.github/**' -g '*workflow*' -g '*ci*'`
  - 결과: exit code `1`, 출력 없음
- Expected: 반복 가능한 품질 게이트는 CI 또는 명시적 수동 gate evidence로 유지되어야 한다.
- Actual: 현재는 수동 실행 증거에 의존한다.
- Impact: 로컬 환경 차이로 회귀가 늦게 발견될 수 있다.
- Suggested Fix: 최소 CI를 추가하거나, 수동 gate 실행 증적을 릴리스 체크리스트에 강제한다.
- Re-audit Method: workflow 파일 존재 여부와 CI 실행 결과를 확인한다.

## [DBG-F005] BUILD_GUIDE의 Gunicorn 안내 일부가 현재 구현과 어긋난다

- Pass: Debug / Engineering Quality
- Pattern: Build/Run Documentation Drift
- Area: `BUILD_GUIDE.md`, `run.py`
- Severity: Minor
- Status: Needs Fix
- Summary: `run.py`는 이미 module import 시 `app = create_app()`를 제공한다. 하지만 `BUILD_GUIDE.md`에는 여전히 Gunicorn을 위해 `run.py` 끝에 `app = create_app()` 추가가 필요하다는 안내가 남아 있다.
- Evidence:
  - `run.py:46`-`run.py:48`: `from app import create_app`, `app = create_app()`
  - `BUILD_GUIDE.md:126`-`BUILD_GUIDE.md:130`: `Gunicorn에 맞게 run.py 수정 필요`, `app = create_app()`
- Expected: 빌드 가이드는 현재 구현 상태를 그대로 반영해야 한다.
- Actual: 이미 반영된 작업을 추가 작업처럼 안내한다.
- Impact: 운영자가 불필요하게 `run.py`를 중복 수정할 수 있다.
- Suggested Fix: 해당 섹션을 "현재 run.py는 이미 Gunicorn app 객체를 제공한다"로 갱신한다.
- Re-audit Method: `BUILD_GUIDE.md`와 `run.py`의 Gunicorn 진입점을 다시 대조한다.

## 6. Pass 3: Security Findings

## [SEC-F001] 개발 서버 외부 바인딩 fail-closed는 동작한다

- Pass: Security
- Pattern: Network Exposure / Debug Server Lockdown
- Area: `run.py`
- Severity: Info
- Status: Verified
- Summary: 기본 개발 서버는 loopback으로 기동하고, 외부 바인딩은 명시 opt-in 없이는 차단된다. opt-in 시에도 debug는 off로 강제된다.
- Evidence:
  - 기본 실행:
    - 명령: `timeout 3 env SECRET_KEY=smoke-secret PYTHONDONTWRITEBYTECODE=1 venv/bin/python run.py`
    - 결과: `Debug mode: on`, `Running on http://127.0.0.1:5000`, timeout exit `124`
  - 외부 바인딩 차단:
    - 명령: `timeout 3 env FLASK_RUN_HOST=0.0.0.0 SECRET_KEY=smoke-secret PYTHONDONTWRITEBYTECODE=1 venv/bin/python run.py`
    - 결과: `ValueError: CRITICAL SECURITY ERROR: 외부 바인딩...`
  - 외부 바인딩 opt-in:
    - 명령: `timeout 3 env FLASK_RUN_HOST=0.0.0.0 ALLOW_UNSAFE_DEV_SERVER=1 SECRET_KEY=custom-key PYTHONDONTWRITEBYTECODE=1 venv/bin/python run.py`
    - 결과: `Debug mode: off`, `Running on all addresses (0.0.0.0)`, timeout exit `124`
- Expected: 개발 서버 debug가 LAN에 무심코 노출되지 않아야 한다.
- Actual: 기본 차단 및 opt-in 분기가 동작한다.
- Impact: 개발 서버 노출 위험이 크게 완화됐다.
- Suggested Fix: 없음.
- Re-audit Method: 세 서버 smoke를 다시 실행한다.

## [SEC-F002] production DEBUG 강제 off와 SECRET_KEY 경계는 smoke 범위에서 확인됐다

- Pass: Security
- Pattern: Secret / Production Config
- Area: `app/config.py`
- Severity: Info
- Status: Verified
- Summary: `FLASK_ENV=production`에서 `DEBUG=true`를 주입해도 `Config.DEBUG`는 `False`로 강제된다.
- Evidence:
  - 명령: `env FLASK_ENV=production DEBUG=true SECRET_KEY=prod-secret PYTHONDONTWRITEBYTECODE=1 venv/bin/python -c "from app.config import Config; print(Config.DEBUG); print(len(Config.SECRET_KEY))"`
  - 결과:
    - `False`
    - `11`
  - `app/config.py:41`-`app/config.py:44`: explicit production 감지 시 `DEBUG = False`
  - `app/config.py:49`-`app/config.py:54`: secret 누락 시 production 또는 non-debug에서 `ValueError`
- Expected: production에서 debug 활성화와 secret 누락이 방치되지 않아야 한다.
- Actual: smoke 범위에서는 차단된다.
- Impact: production misconfig 위험이 완화됐다.
- Suggested Fix: secret 누락 실패 smoke도 release gate에 추가하면 더 명확하다.
- Re-audit Method: production DEBUG/SECRET_KEY 조합 smoke 재실행.

## [SEC-F003] XSS escape guard와 mutation-sensitive 테스트는 현재 확인된 sink를 잡는다

- Pass: Security
- Pattern: XSS / Mutation-Sensitive Regression
- Area: `app/static/js/game.js`, `tests/test_regression.py`
- Severity: Info
- Status: Verified with Known Residual Risk
- Summary: 현재 정적/Node 기반 테스트는 `game.js`의 주요 innerHTML sink에서 `escapeHtml` 누락을 검출한다. mutation smoke에서도 주요 guard 제거가 모두 실패로 감지됐다.
- Evidence:
  - `app/static/js/game.js:10`-`app/static/js/game.js:19`: `escapeHtml(str)` 구현
  - `app/static/js/game.js:105`: `escapeHtml(parkName)`
  - `app/static/js/game.js:133`: `escapeHtml(data.error || I18N.scoutFail)`
  - `app/static/js/game.js:136`: `escapeHtml(err.message)`
  - `tests/test_regression.py:237`-`tests/test_regression.py:263`: 실제 `game.js`의 `escapeHtml`를 Node.js로 실행해 교차 검증
  - mutation smoke 결과:
    - `current PASS`
    - `parkName FAILS_AS_EXPECTED`
    - `targetName FAILS_AS_EXPECTED`
    - `data.error FAILS_AS_EXPECTED`
    - `err.message FAILS_AS_EXPECTED`
- Expected: 알려진 동적 HTML sink에서 사용자/서버 입력이 escape 없이 삽입되지 않아야 한다.
- Actual: 현재 검사 대상 sink는 guard 누락 시 테스트가 실패한다.
- Impact: 정적 회귀 테스트의 변별력은 확인됐다.
- Suggested Fix: 실제 브라우저 또는 jsdom DOM E2E를 추가하면 residual risk를 줄일 수 있다.
- Re-audit Method:
  - `pytest` 재실행
  - mutation smoke 재실행
  - 브라우저/jsdom 기반 XSS E2E 추가 확인

## [SEC-F004] 실제 RDBMS row-lock/deadlock E2E는 아직 Accepted Risk다

- Pass: Security
- Pattern: Concurrency Boundary / External DB Validation
- Area: PostgreSQL/MySQL production target
- Severity: Major
- Status: Accepted Risk
- Summary: PostgreSQL/MySQL URI 설정과 driver import는 확인됐지만, 실제 DB 인스턴스 기반 다중 worker row-lock/deadlock E2E는 수행되지 않았다.
- Evidence:
  - `README.md:57`: PostgreSQL/MySQL row-lock/deadlock 미검증을 Accepted Risk로 문서화
  - PostgreSQL URI smoke는 설정 문자열 확인에 한정됨
  - 실제 PostgreSQL/MySQL 서버 연결, migration, 다중 worker 동시성 테스트는 수행하지 않음
- Expected: Target Production 표현을 PASS로 판정하려면 실제 대상 DB에서 동시성 E2E가 필요하다. 그렇지 않으면 Accepted Risk가 명시되어야 한다.
- Actual: 문서상 Accepted Risk로 명시되어 있으나 실제 E2E는 없다.
- Impact: 설계상 안전성은 추정 가능하지만 운영 DB에서 lock timeout/deadlock이 발생할 가능성은 배제할 수 없다.
- Suggested Fix: PostgreSQL 또는 MySQL 테스트 인스턴스에서 다중 worker 동시성 시나리오를 수행한다.
- Re-audit Method:
  - 실제 DB 컨테이너 또는 외부 인스턴스 준비
  - Gunicorn 다중 worker 부하 실행
  - deadlock/lock timeout 로그 수집

## 7. Cross-Pass Conflicts

## [XPF-F001] 실행 게이트는 통과하지만 문서 authority는 아직 PASS 수준이 아니다

- Pass: Cross-Pass
- Severity: Major
- Status: Hold
- Summary: 테스트와 smoke는 통과하지만, README 다국어 품질과 hard-boundary 표현이 프로젝트 문서 표준과 충돌한다.
- Evidence:
  - `pytest`: 7 passed
  - 서버 및 보안 smoke: 통과
  - README 언어 혼입: `README.md:307`, `README.md:316`, `README.md:342`, `README.md:346`, `README.md:356`, `README.md:360`, `README.md:362`, `README.md:368`, `README.md:374`, `README.md:376`
  - hard-boundary 잔존: `audit_roadmap.md:122`-`audit_roadmap.md:129`, `CHANGELOG.md:23`-`CHANGELOG.md:29`
- Impact: 구현 품질만으로는 사용자-facing 문서와 감사 표준을 만족하지 못한다.

## [XPF-F002] Accepted Risk와 완전 해결 표현이 같은 릴리스 문서 집합에 공존한다

- Pass: Cross-Pass
- Severity: Major
- Status: Needs Fix
- Summary: README는 RDBMS E2E 미검증을 Accepted Risk로 낮췄지만, `audit_roadmap.md`와 `CHANGELOG.md`에는 여전히 완치/원천/보장 계열 표현이 남아 있다.
- Impact: 후속 감사자가 어느 문서를 authoritative boundary로 봐야 하는지 불명확하다.

## 8. Required Fixes Before PASS

1. `audit_report_73.md`-`audit_report_78.md`와 현재 modified 파일들의 추적성 정책을 정리한다.
2. README 일본어/번체/간체 섹션의 언어 혼입을 제거한다.
3. `README.md`, `CHANGELOG.md`, `audit_roadmap.md`, 소스 주석의 hard-boundary 표현을 실제 검증 범위에 맞게 정렬한다.
4. `IMPLEMENTATION_SUMMARY.md`/`implementation_summary.md`, `LESSONS_LEARNED.md`/`lessons_learned.md` 파일명 authority를 정한다.
5. `BUILD_GUIDE.md`의 Gunicorn 안내를 현재 `run.py` 상태와 맞춘다.
6. 실제 PostgreSQL/MySQL row-lock/deadlock E2E 또는 명시적 Accepted Risk 유지 조건을 릴리스 체크리스트에 고정한다.
7. 브라우저/jsdom DOM XSS E2E를 추가하거나 Known Residual Risk로 계속 유지할지 명시한다.

## 9. Accepted Risks

| Risk | Status | Owner | Revisit Trigger |
| --- | --- | --- | --- |
| SQLite multi-worker `Database Locked` 가능성 | Accepted Risk | Project Lead Architect / Eunho Lim | DAU 100명 초과, 초당 DB 쓰기 10회 초과, locked error 주 3회 이상 |
| 실제 PostgreSQL/MySQL row-lock/deadlock E2E 미수행 | Accepted Risk | Project Lead Architect / Eunho Lim | 실제 RDBMS 이주, lock timeout/deadlock 주 1회 이상 |
| 실제 브라우저/jsdom DOM XSS E2E 미수행 | Known Residual Risk | Coder / Auditor | 브라우저/jsdom 테스트 추가 전까지 |
| CI/workflow 부재 | Known Operational Risk | Maintainer | CI 도입 또는 수동 gate evidence 아카이브 |

## 10. Needs Spec Clarification

1. 감사 보고서가 untracked 상태로 누적될 때 PASS 판정 전에 반드시 커밋되어야 하는지, 또는 별도 immutable archive만으로 충분한지 기준이 필요하다.
2. README release note의 다국어 품질을 Major gate로 유지할지, Known Documentation Risk로 낮출지 결정해야 한다.
3. historical changelog와 audit roadmap의 `완치`, `원천`, `보장` 표현을 현재 검증 범위 기준으로 다시 써야 하는지, 당시 의도 보존으로 허용할지 기준이 필요하다.
4. `IMPLEMENTATION_SUMMARY.md`/`implementation_summary.md` 및 `LESSONS_LEARNED.md`/`lessons_learned.md` 중 어느 파일명이 표준인지 결정해야 한다.
5. Node.js 정적/결합 XSS 검증을 충분한 gate로 볼지, 브라우저/jsdom DOM E2E를 필수로 요구할지 결정해야 한다.
6. 실제 PostgreSQL/MySQL E2E 전에도 `Target Production` 표현을 유지할 수 있는지, `Target Production Design / Accepted Risk`로만 제한할지 결정해야 한다.

## 11. Re-audit Checklist

- [x] `AI_AUDIT_DOC_STANDARD.md` 확인
- [x] 최신 감사 보고서 번호 확인: `audit_report_77.md` 이후 `audit_report_78.md`
- [x] 직전 감사 `audit_report_77.md` HOLD 사유 확인
- [x] `test -f audit_report_78.md`: 기존 파일 없음 확인
- [x] `git status --short`
- [x] `git diff --stat`
- [x] `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q`: `7 passed in 0.32s`
- [x] `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q -W error`: `7 passed in 0.32s`
- [x] `git diff --check`: pass
- [x] `git diff --cached --check`: pass
- [x] `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m py_compile ...`: pass
- [x] `DATABASE_URL` PostgreSQL URI smoke: pass
- [x] `SQLALCHEMY_DATABASE_URI` PostgreSQL URI smoke: pass
- [x] `psycopg2` import smoke: `2.9.12`
- [x] SQLite `journal_mode`: `wal`
- [x] SQLite `busy_timeout`: `5000`
- [x] production `DEBUG=true` 강제 off smoke: `False`
- [x] loopback 개발 서버 smoke: `127.0.0.1`, `v1.8.9`
- [x] 외부 바인딩 fail-closed smoke: `ValueError`
- [x] 외부 바인딩 opt-in debug off smoke: `0.0.0.0`, `Debug mode: off`
- [x] XSS mutation smoke: 주요 guard 제거 4건 모두 `FAILS_AS_EXPECTED`
- [x] README 다국어 혼입 검색
- [x] hard-boundary 표현 잔존 검색
- [x] CI/workflow 파일 검색: 없음
- [x] required docs 파일명 inventory 확인

## 12. Final Decision

**HOLD**

현재 구현은 로컬 실행 및 회귀 테스트 관점에서 상당 부분 안정화되어 있다. 특히 다음 항목은 Verified로 본다.

- `run.py` 배너와 버전 `v1.8.9` 정렬
- loopback 기본 개발 서버 및 외부 바인딩 fail-closed
- 외부 바인딩 opt-in 시 debug off
- production DEBUG 강제 off
- DB URI fallback 및 PostgreSQL driver import
- SQLite WAL/busy_timeout
- XSS escape guard와 mutation-sensitive 정적 테스트
- `pytest`, `-W error`, `py_compile`, whitespace gate

하지만 `AI_AUDIT_DOC_STANDARD.md` 기준 PASS는 실행 성공만으로 결정되지 않는다. 현재 PASS 차단 사유는 다음이다.

1. 감사 보고서와 modified 파일 추적성이 아직 정리되지 않았다.
2. README 다국어 섹션에 사용자-facing 품질 회귀가 남아 있다.
3. Accepted Risk와 hard-boundary 표현이 문서 집합 내에서 충돌한다.
4. required documentation 파일명의 대소문자 authority가 불명확하다.
5. 실제 RDBMS row-lock/deadlock E2E와 브라우저 DOM XSS E2E는 여전히 residual risk다.

따라서 78번 재감사의 최종 판정은 **HOLD**다. 소스 코드와 기존 문서는 수정하지 않았고, 감사 결과 문서 `audit_report_78.md`만 생성했다.
