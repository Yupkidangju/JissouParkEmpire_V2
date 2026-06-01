# D3D Audit Report - audit_report_79.md

## 0. 감사 요약

- 감사 기준: `AI_AUDIT_DOC_STANDARD.md`
- 감사 방식: 재감사, 구현 중심 3-Pass 감사
- 감사 대상 경로: `/mnt/Projects_SSD/python/JissouParkEmpire`
- 직전 감사 문서: `audit_report_78.md`
- 새 보고서 번호: `audit_report_79.md`
- 감사일: 2026-06-01
- 최종 판정: **HOLD**

78번 이후 작업트리에 추가 변경이 있었다. 변경 범위는 15개 tracked 파일이며, 주로 README 다국어 문구 정리, hard-boundary 표현 완화, `BUILD_GUIDE.md` Gunicorn 안내 조정, 소스 주석 정리다. 실행 게이트는 다시 통과했다. `pytest`, `-W error`, `py_compile`, `git diff --check`, DB 설정 smoke, SQLite PRAGMA smoke, 개발 서버 바인딩 smoke, XSS mutation smoke 모두 정상이다.

그러나 이번 재감사에서 새 PASS 차단 이슈가 확인됐다. `BUILD_GUIDE.md`의 systemd Gunicorn 예시가 `--bind 127.0.0.1:8000`에서 `--bind 0.0.0.0:8000`으로 변경되어, 같은 문서의 Nginx reverse proxy 구성과 충돌하고 애플리케이션 포트를 LAN에 직접 노출할 수 있다. 또한 감사 산출물과 modified 파일 추적성은 아직 정리되지 않았다. 따라서 최종 판정은 **HOLD**다.

## 1. Audit Scope

### 1.1 포함 범위

- 감사 표준: `AI_AUDIT_DOC_STANDARD.md`
- 직전 감사: `audit_report_78.md`
- 프로젝트 문서: `spec.md`, `README.md`, `CHANGELOG.md`, `BUILD_GUIDE.md`, `DESIGN_DECISIONS.md`, `audit_roadmap.md`, `designs.md`, `implementation_summary.md`, `lessons_learned.md`
- 구현 파일: `run.py`, `app/config.py`, `app/game_engine.py`, `app/npc_engine.py`, `app/routes/game_routes.py`, `app/static/js/game.js`
- 테스트 파일: `tests/conftest.py`, `tests/test_regression.py`
- 의존성: `requirements.txt`
- 로컬 상태: `git status --short`, `git diff --stat`, `git diff --name-only`, `git diff --check`, `git diff --cached --check`

### 1.2 감사 모델

`AI_AUDIT_DOC_STANDARD.md`의 3-Pass 모델을 적용했다.

- Pass 1: 문서-구현 정합성 및 이전 HOLD 항목 재확인
- Pass 2: 테스트, 빌드, 실행, 설정, 재현성 확인
- Pass 3: 보안 경계, 네트워크 노출, XSS, secret/config 경계 확인

## 2. Excluded Scope

- 소스 코드 수정: 사용자 지시에 따라 수행하지 않음
- 기존 문서 수정: 사용자 지시에 따라 수행하지 않음
- 실제 PostgreSQL/MySQL 인스턴스 기반 row-lock/deadlock E2E: 로컬 인프라 미제공으로 제외
- 실제 브라우저 또는 jsdom 기반 DOM XSS E2E: 현재 테스트 스위트 밖
- Gunicorn 실제 기동 및 포트 노출 실측: 문서/설정 정합성 감사로 대체
- `.antigravitycli/`, `stitch_shitsiseki_empire_ui_refactor/`: 현재 감사 대상 변경 범위 밖

## 3. 직전 감사 요청사항 재확인

78번 보고서의 PASS 전 요구사항은 다음이었다.

1. `audit_report_73.md`-`audit_report_78.md`와 현재 modified 파일들의 추적성 정책 정리
2. README 일본어/번체/간체 섹션 언어 혼입 제거
3. `README.md`, `CHANGELOG.md`, `audit_roadmap.md`, 소스 주석의 hard-boundary 표현 정렬
4. required documentation 파일명 authority 정리
5. `BUILD_GUIDE.md` Gunicorn 안내와 현재 `run.py` 상태 정렬
6. 실제 PostgreSQL/MySQL row-lock/deadlock E2E 또는 Accepted Risk 유지 조건 고정
7. 브라우저/jsdom DOM XSS E2E 추가 또는 Known Residual Risk 유지

### 3.1 79번 재감사 판정 매트릭스

| 78번 요구사항 | 79번 상태 | 판정 |
| --- | --- | --- |
| 감사 산출물/작업트리 추적성 | `audit_report_73.md`-`audit_report_78.md` untracked, 15개 tracked 파일 modified | **Needs Fix / HOLD** |
| README 다국어 혼입 제거 | 이전에 확인된 일본어 `持續`, `悲観적`, 번체 섹션의 간체 혼입, 간체 섹션의 번체 혼입은 대부분 제거됨 | **Mostly Verified** |
| hard-boundary 표현 완화 | 주요 `완치`, `원천`, `무결성 달성`, `보장` 표현 상당수 완화됨. 일부 잔존 표현은 historical/changelog 또는 테스트 기준 문맥 | **Partially Verified / Minor cleanup** |
| 문서 파일명 authority | `IMPLEMENTATION_SUMMARY.md`, `LESSONS_LEARNED.md`는 여전히 없음 | **Needs Spec Clarification** |
| `BUILD_GUIDE.md` Gunicorn 안내 | `app = create_app()` 중복 안내는 수정됨. 그러나 `--bind 0.0.0.0:8000` 회귀 발생 | **Needs Fix / HOLD** |
| 실제 RDBMS E2E | 미수행, Accepted Risk 유지 | **Accepted Risk** |
| 브라우저/jsdom DOM XSS E2E | 미수행, mutation-sensitive 정적/Node 검증만 유지 | **Known Residual Risk** |

## 4. Pass 1: Implementation Compliance Findings

## [IMP-F001] 감사 산출물과 작업트리 추적성이 여전히 PASS 기준에 미달한다

- Pass: Implementation Compliance
- Pattern: Audit Traceability / Source Control Hygiene
- Area: Git status, audit reports
- Severity: Major
- Status: Needs Fix / Hold
- Summary: 구현 게이트는 통과하지만 현재 변경 세트와 감사 산출물이 아직 추적 가능한 상태로 정리되지 않았다.
- Evidence:
  - `git status --short`:
    - `M BUILD_GUIDE.md`
    - `M CHANGELOG.md`
    - `M DESIGN_DECISIONS.md`
    - `M README.md`
    - `M app/config.py`
    - `M app/game_engine.py`
    - `M app/npc_engine.py`
    - `M app/routes/game_routes.py`
    - `M app/static/js/game.js`
    - `M audit_roadmap.md`
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
    - `?? audit_report_78.md`
  - `git diff --stat`: 15 files changed, 203 insertions, 207 deletions
- Expected: PASS 전에는 감사 대상 변경과 감사 보고서의 보존/추적 정책이 명확해야 한다.
- Actual: 변경 파일과 감사 보고서가 여전히 untracked/modified 상태다.
- Impact: 이후 재감사에서 어떤 변경이 실제 구현 수정이고 어떤 변경이 감사 대응인지 구분하기 어렵다.
- Suggested Fix: 감사 보고서 73-79 및 현재 변경 파일을 커밋, 별도 브랜치, 또는 명시적 immutable archive 정책으로 정리한다.
- Re-audit Method: `git status --short`, `git diff --stat`, 최신 `audit_report_*.md` 연속성 확인.

## [IMP-F002] README 다국어 혼입은 78번 대비 상당 부분 해소됐다

- Pass: Implementation Compliance
- Pattern: User-Facing Documentation / i18n Quality
- Area: `README.md`
- Severity: Info
- Status: Mostly Verified
- Summary: 78번에서 Major로 분류했던 일본어/번체/간체 섹션의 명백한 문자권 혼입은 대부분 제거됐다.
- Evidence:
  - 현재 일본어 섹션:
    - `README.md:307`: `相手の公園が削除されたとき...`로 정리되어 이전 `持續` 혼입 제거
    - `README.md:316`: `再度悲観的ロック` 계열로 정리되어 이전 `悲観적ロック` 혼입 제거
  - 현재 번체 섹션:
    - `README.md:321`-`README.md:347`에서 이전 `我们`, `交易拒绝`, `战斗内部`, `替换`, `保护嵌套`, `执行显式`, `悲观锁` 계열 간체 혼입이 사라짐
  - 현재 간체 섹션:
    - `README.md:349`-`README.md:375`에서 이전 `事務事务`, `持續`, `與`, `風險`, `鎖`, `已緩解` 혼입이 제거됨
- Expected: README의 5개 언어 섹션은 각 언어/문자 체계가 일관되어야 한다.
- Actual: 이전에 식별된 명백한 혼입은 재현되지 않는다.
- Impact: 사용자-facing 다국어 문서 품질이 개선됐다.
- Suggested Fix: 남은 번역 품질은 원어민 리뷰로 확인한다. 예를 들어 간체 `隔离交易`는 DB transaction 의미라면 `隔离事务`가 더 정확할 수 있다.
- Re-audit Method: 다국어 섹션 수동 검토 및 문자권 혼입 검색.

## [IMP-F003] hard-boundary 표현은 완화됐지만 일부 cleanup은 남아 있다

- Pass: Implementation Compliance
- Pattern: Claim Strength / Evidence Alignment
- Area: `CHANGELOG.md`, `audit_roadmap.md`, source comments
- Severity: Minor
- Status: Partially Verified
- Summary: 78번에서 지적한 `완치`, `원천`, `무결성을 달성`, `보장` 계열 표현은 상당히 줄었다. 다만 일부 표현은 아직 강한 운영 보증처럼 읽힐 수 있어 최종 cleanup이 필요하다.
- Evidence:
  - 개선 확인:
    - `audit_roadmap.md:122`: `완전 해결` -> `위험 저감`
    - `audit_roadmap.md:126`: `완치 검증 완료` -> `완화 확인`
    - `audit_roadmap.md:127`: `원천 차단 검증 완료` -> `유실 여부 확인`
    - `audit_roadmap.md:129`: `데드락 완치` -> `데드락 위험 저감 확인`
    - `CHANGELOG.md:23`: `원천 소멸`, `보장`, `강력히 예방` 계열이 `위험을 낮췄습니다`로 완화됨
    - `app/routes/game_routes.py:761`: `근본 차단` -> `방지`
    - `app/routes/game_routes.py:1042`, `app/routes/game_routes.py:1193`: `보장` -> `정렬`
  - 잔존 검색 예:
    - `audit_roadmap.md:173`: `철저히 차단`
    - `app/config.py:28`: `강하게 차단`
    - `CHANGELOG.md:129`: historical `AP 시스템 근본 재설계`
    - `CHANGELOG.md:164`: historical `XSS 근본 원인 차단`
- Expected: 실제 검증 범위가 로컬 테스트, SQLite smoke, 정적/Node XSS 검증에 한정된 항목은 완전 해결 표현보다 완화/조건부 검증/Accepted Risk로 표현해야 한다.
- Actual: 핵심 문제 표현은 대부분 완화됐지만 일부 강한 표현은 남아 있다.
- Impact: 현재 남은 표현은 78번보다 낮은 위험이나, 최종 PASS 전에 문서 전체 용어 정책을 맞추는 편이 안전하다.
- Suggested Fix: historical changelog를 보존할지, 현재 감사 기준으로 다시 낮출지 기준을 정한다.
- Re-audit Method: `rg -n "완치|완전 해결|원천|근본|보장|무결성을 달성|치료|철저히|강력히|강하게" README.md CHANGELOG.md audit_roadmap.md app tests`

## [IMP-F004] required documentation 파일명 authority는 여전히 불명확하다

- Pass: Implementation Compliance
- Pattern: Required Inputs / Documentation Authority
- Area: required docs inventory
- Severity: Minor
- Status: Needs Spec Clarification
- Summary: 표준 문서와 AGENTS 규칙에서 요구하는 대문자 파일명이 실제 저장소의 소문자 파일명과 불일치한다.
- Evidence:
  - `IMPLEMENTATION_SUMMARY.md`: 없음
  - `LESSONS_LEARNED.md`: 없음
  - `implementation_summary.md`: 존재
  - `lessons_learned.md`: 존재
- Expected: required documentation set은 대소문자까지 포함해 하나의 authority를 가져야 한다.
- Actual: Linux 기준으로 대문자 required file은 누락 상태다.
- Impact: 자동 감사나 cross-platform 환경에서 필수 문서 누락으로 판정될 수 있다.
- Suggested Fix: 대문자 파일명을 표준으로 만들지, 소문자 파일명을 표준으로 문서화할지 결정한다.
- Re-audit Method: required docs inventory 재실행.

## [IMP-F005] `BUILD_GUIDE.md`의 Gunicorn `app = create_app()` 중복 안내는 해소됐다

- Pass: Implementation Compliance
- Pattern: Build Guide / Runtime Entry Point
- Area: `BUILD_GUIDE.md`, `run.py`
- Severity: Info
- Status: Verified
- Summary: 78번에서 지적한 "Gunicorn에 맞게 run.py 수정 필요" 안내는 현재 구현과 맞게 수정됐다.
- Evidence:
  - `run.py:46`-`run.py:48`: `from app import create_app`, `app = create_app()`
  - `BUILD_GUIDE.md:126`-`BUILD_GUIDE.md:130`: `run.py에는 이미 app = create_app()가 존재하므로 추가 수정은 필요하지 않습니다.`
- Expected: 빌드 가이드는 현재 `run.py`가 이미 Gunicorn app 객체를 제공한다는 사실을 반영해야 한다.
- Actual: 반영됐다.
- Impact: 운영자가 불필요하게 `run.py`를 수정할 위험은 줄었다.
- Suggested Fix: 없음. 단, 아래 SEC-F001의 bind 주소 회귀는 별도 수정 필요.
- Re-audit Method: `BUILD_GUIDE.md`와 `run.py` 재대조.

## [IMP-F006] `app/routes/game_routes.py`에 동작 영향은 없지만 오인 가능한 주석 들여쓰기 회귀가 있다

- Pass: Implementation Compliance
- Pattern: Readability / Comment Hygiene
- Area: `app/routes/game_routes.py`
- Severity: Minor
- Status: Needs Fix
- Summary: `diplomacy_enemy`의 TOCTOU 재검증 구간 주석이 `if` 블록보다 한 단계 더 들여쓰기되어, 코드 구조를 잘못 암시한다.
- Evidence:
  - `app/routes/game_routes.py:1185`: `# 락 대기 후 멸망 상태 재검증 (TOCTOU 방지)`
  - `app/routes/game_routes.py:1186`: `        # [v1.8.9] AP 환불 정합성...`
  - `app/routes/game_routes.py:1187`: `if park.is_destroyed or target.is_destroyed:`
  - `py_compile`은 통과했다. Python에서 주석만 과잉 들여쓰기된 경우 실행에는 영향이 없다.
- Expected: 보안/트랜잭션 주석은 실제 제어 흐름과 같은 들여쓰기 수준에 있어야 한다.
- Actual: 주석 한 줄이 과잉 들여쓰기되어 `if` 내부 주석처럼 보인다.
- Impact: 런타임 버그는 아니지만 감사자가 TOCTOU/AP 환불 경계를 읽을 때 오해할 수 있다.
- Suggested Fix: 해당 주석을 `if`와 같은 들여쓰기 수준으로 정렬한다.
- Re-audit Method: 해당 라인 수동 확인 및 `py_compile`.

## 5. Pass 2: Debug / Engineering Quality Findings

## [DBG-F001] Python 테스트와 warning-as-error 게이트는 통과한다

- Pass: Debug / Engineering Quality
- Pattern: Deterministic Test Gate
- Area: pytest
- Severity: Info
- Status: Verified
- Evidence:
  - `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q`
  - 결과: `7 passed in 0.32s`
  - `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q -W error`
  - 결과: `7 passed in 0.32s`
- Expected: 모든 회귀 테스트가 통과해야 한다.
- Actual: 통과.
- Impact: 현재 로컬 회귀 테스트 범위에서는 기능 실패가 없다.
- Suggested Fix: 없음.
- Re-audit Method: 동일 명령 재실행.

## [DBG-F002] 문법/공백 품질 게이트는 통과한다

- Pass: Debug / Engineering Quality
- Pattern: Static Quality Gate
- Area: Python syntax, whitespace
- Severity: Info
- Status: Verified
- Evidence:
  - `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m py_compile app/__init__.py app/battle_engine.py app/config.py app/game_engine.py app/models.py app/npc_engine.py app/routes/auth_routes.py app/routes/game_routes.py run.py tests/conftest.py tests/test_regression.py`: exit code `0`
  - `git diff --check`: exit code `0`
  - `git diff --cached --check`: exit code `0`
- Expected: syntax error와 whitespace error가 없어야 한다.
- Actual: 통과.
- Impact: 정적 품질 게이트에서는 차단 이슈가 없다.
- Suggested Fix: 없음.
- Re-audit Method: 동일 명령 재실행.

## [DBG-F003] DB 설정과 SQLite PRAGMA smoke는 통과한다

- Pass: Debug / Engineering Quality
- Pattern: Runtime Config / DB Portability
- Area: `app/config.py`, SQLAlchemy setup
- Severity: Info
- Status: Verified
- Evidence:
  - `DATABASE_URL=postgresql://u:p@localhost:5432/jissou_audit`: `postgresql://u:p@localhost:5432/jissou_audit`
  - `SQLALCHEMY_DATABASE_URI=postgresql://u:p@localhost:5432/jissou_uri`: `postgresql://u:p@localhost:5432/jissou_uri`
  - `import psycopg2`: `2.9.12 (dt dec pq3 ext lo64)`
  - SQLite `journal_mode`: `wal`
  - SQLite `busy_timeout`: `5000`
- Expected: 환경변수 우선순위와 SQLite 완화 설정이 실제 런타임에서 확인되어야 한다.
- Actual: smoke 범위에서 확인됐다.
- Impact: 설정 wiring은 정상이다.
- Suggested Fix: 실제 RDBMS E2E는 별도 Accepted Risk로 유지한다.
- Re-audit Method: 동일 smoke 및 실제 DB E2E.

## [DBG-F004] BUILD_GUIDE quickstart는 현재 호스트에서 `python` 명령 재현성이 낮다

- Pass: Debug / Engineering Quality
- Pattern: Build Reproducibility
- Area: `BUILD_GUIDE.md`
- Severity: Minor
- Status: Needs Fix
- Summary: 현재 호스트에는 `python3`만 있고 `python` 명령은 없다. 그런데 `BUILD_GUIDE.md`의 빠른 시작은 `python -m venv venv`, `python run.py`를 사용한다.
- Evidence:
  - `command -v python`: exit code `1`
  - `command -v python3`: `/usr/bin/python3`
  - `BUILD_GUIDE.md:17`: `python -m venv venv`
  - `BUILD_GUIDE.md:27`: `python run.py`
  - `BUILD_GUIDE.md:30`: `venv/bin/python run.py` 대안은 존재
- Expected: 로컬 Linux 환경에서 바로 재현 가능한 명령을 우선 제시해야 한다.
- Actual: 기본 quickstart의 첫 명령이 현재 호스트에서 실패할 수 있다.
- Impact: 신규 운영자가 문서대로 시작할 때 불필요한 실패를 겪을 수 있다.
- Suggested Fix: Linux/macOS 예시는 `python3 -m venv venv`를 우선하고, 활성화 후 `python`을 사용하는 형태로 분리한다.
- Re-audit Method: `command -v python`, `command -v python3`, BUILD_GUIDE 명령 재실행.

## [DBG-F005] CI/workflow 파일은 여전히 없다

- Pass: Debug / Engineering Quality
- Pattern: CI / Reproducibility
- Area: CI/CD
- Severity: Minor
- Status: Accepted Risk / Known Operational Risk
- Evidence:
  - `rg --files -g '.github/**' -g '*workflow*' -g '*ci*'`: exit code `1`, 출력 없음
- Expected: 반복 가능한 품질 게이트가 CI 또는 명시적 수동 gate로 관리되어야 한다.
- Actual: 현재는 수동 게이트 증거에 의존한다.
- Impact: 환경 차이로 인한 회귀 감지가 늦어질 수 있다.
- Suggested Fix: 최소 CI 또는 수동 gate evidence 보존 정책을 추가한다.
- Re-audit Method: workflow 파일 검색 및 CI 실행 결과 확인.

## 6. Pass 3: Security Findings

## [SEC-F001] `BUILD_GUIDE.md`가 Gunicorn을 `0.0.0.0:8000`에 바인딩하도록 바뀌어 Nginx reverse proxy 경계와 충돌한다

- Pass: Security
- Pattern: Network Exposure / Deployment Boundary
- Area: `BUILD_GUIDE.md`, `run.py`
- Severity: Major
- Status: Needs Fix / Hold
- Summary: 78번 이후 `BUILD_GUIDE.md`의 systemd Gunicorn bind 주소가 `127.0.0.1:8000`에서 `0.0.0.0:8000`으로 바뀌었다. 같은 문서의 Nginx 설정은 `proxy_pass http://127.0.0.1:8000`을 사용하므로, Gunicorn을 전체 인터페이스에 직접 노출할 이유가 없다.
- Evidence:
  - `BUILD_GUIDE.md:98`-`BUILD_GUIDE.md:104`:
    - `ExecStart=/opt/jissou-park/venv/bin/gunicorn \`
    - `--workers 2 \`
    - `--bind 0.0.0.0:8000 \`
    - `"run:app"`
  - `BUILD_GUIDE.md:153`-`BUILD_GUIDE.md:154`:
    - `location / {`
    - `proxy_pass http://127.0.0.1:8000;`
  - `git diff -- BUILD_GUIDE.md`:
    - `--bind 127.0.0.1:8000` -> `--bind 0.0.0.0:8000`
  - `run.py:8`에도 `gunicorn --bind 0.0.0.0:8000 "run:app"` 예시가 존재한다.
- Expected: Nginx reverse proxy 구성에서는 Gunicorn이 loopback에만 바인딩되어야 한다. 외부 공개는 Nginx가 담당해야 한다.
- Actual: 문서가 Gunicorn을 모든 네트워크 인터페이스에 바인딩하도록 안내한다.
- Impact: 방화벽이 별도로 닫혀 있지 않으면 포트 8000이 LAN/외부망에 직접 노출될 수 있다. Nginx의 접근 제어, TLS 종료, 헤더 정책, 정적 파일 정책을 우회하는 운영 경로가 생긴다.
- Suggested Fix: `BUILD_GUIDE.md` systemd 예시는 `--bind 127.0.0.1:8000`으로 되돌리고, 외부 바인딩이 필요한 특수 운영은 별도 위험 수용 조건과 방화벽 전제를 명시한다. `run.py` docstring의 Gunicorn 예시도 같은 정책으로 정렬한다.
- Re-audit Method:
  - `rg -n "0\\.0\\.0\\.0:8000|127\\.0\\.0\\.1:8000|gunicorn" BUILD_GUIDE.md run.py README.md`
  - 배포 가이드에서 Gunicorn bind와 Nginx `proxy_pass`가 같은 loopback 경계로 정렬됐는지 확인

## [SEC-F002] 개발 서버 직접 실행의 loopback/fail-closed 경계는 통과한다

- Pass: Security
- Pattern: Dev Server Exposure
- Area: `run.py`
- Severity: Info
- Status: Verified
- Summary: `python run.py` 직접 실행 경로는 기본 loopback으로 기동하고, 외부 바인딩은 opt-in 없이 차단된다.
- Evidence:
  - 기본 실행:
    - `timeout 3 env SECRET_KEY=smoke-secret PYTHONDONTWRITEBYTECODE=1 venv/bin/python run.py`
    - `Jissou Park Empire v1.8.9`
    - `Running on http://127.0.0.1:5000`
    - timeout exit `124`
  - 외부 바인딩 차단:
    - `timeout 3 env FLASK_RUN_HOST=0.0.0.0 SECRET_KEY=smoke-secret PYTHONDONTWRITEBYTECODE=1 venv/bin/python run.py`
    - `ValueError: CRITICAL SECURITY ERROR...`
  - 외부 바인딩 opt-in:
    - `timeout 3 env FLASK_RUN_HOST=0.0.0.0 ALLOW_UNSAFE_DEV_SERVER=1 SECRET_KEY=custom-key PYTHONDONTWRITEBYTECODE=1 venv/bin/python run.py`
    - `Debug mode: off`
    - `Running on all addresses (0.0.0.0)`
- Expected: 개발 서버는 LAN에 무심코 노출되지 않아야 한다.
- Actual: 직접 실행 경로는 요구대로 동작한다.
- Impact: 이 항목은 통과다. 단, SEC-F001의 Gunicorn import 경로는 `__main__` 가드가 실행되지 않으므로 별도 배포 문서 경계가 필요하다.
- Suggested Fix: 없음.
- Re-audit Method: 동일 서버 smoke 재실행.

## [SEC-F003] production DEBUG 강제 off와 secret 경계는 smoke 범위에서 확인됐다

- Pass: Security
- Pattern: Secret / Production Config
- Area: `app/config.py`
- Severity: Info
- Status: Verified
- Evidence:
  - `env FLASK_ENV=production DEBUG=true SECRET_KEY=prod-secret PYTHONDONTWRITEBYTECODE=1 venv/bin/python -c "from app.config import Config; print(Config.DEBUG); print(len(Config.SECRET_KEY))"`
  - 결과:
    - `False`
    - `11`
- Expected: production에서 DEBUG가 강제로 꺼져야 한다.
- Actual: 꺼진다.
- Impact: production misconfig 위험은 완화되어 있다.
- Suggested Fix: secret 누락 실패 smoke도 release checklist에 추가하면 더 명확하다.
- Re-audit Method: production DEBUG/SECRET_KEY 조합 smoke 재실행.

## [SEC-F004] XSS guard와 mutation-sensitive 테스트는 현재 확인된 sink를 잡는다

- Pass: Security
- Pattern: XSS / Mutation-Sensitive Regression
- Area: `app/static/js/game.js`, `tests/test_regression.py`
- Severity: Info
- Status: Verified with Known Residual Risk
- Evidence:
  - mutation smoke 결과:
    - `current PASS`
    - `parkName FAILS_AS_EXPECTED`
    - `targetName FAILS_AS_EXPECTED`
    - `data.error FAILS_AS_EXPECTED`
    - `err.message FAILS_AS_EXPECTED`
- Expected: 알려진 `innerHTML` sink에서 `escapeHtml` guard 제거가 테스트에 잡혀야 한다.
- Actual: 주요 guard 제거 4건이 모두 실패로 감지됐다.
- Impact: 정적/Node 결합 검증의 변별력은 확인됐다.
- Suggested Fix: 브라우저 또는 jsdom DOM E2E를 추가하면 residual risk를 줄일 수 있다.
- Re-audit Method: pytest, mutation smoke, 브라우저/jsdom E2E.

## [SEC-F005] 실제 PostgreSQL/MySQL row-lock/deadlock E2E는 아직 Accepted Risk다

- Pass: Security
- Pattern: Concurrency Boundary / External DB Validation
- Area: PostgreSQL/MySQL production target
- Severity: Major
- Status: Accepted Risk
- Evidence:
  - `README.md:57`: PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증을 Accepted Risk로 문서화
  - URI smoke와 driver import는 수행했지만 실제 DB 연결/부하/deadlock 테스트는 수행하지 않음
- Expected: Target Production 표현을 최종 PASS로 올리려면 실제 대상 DB에서 동시성 E2E가 필요하다.
- Actual: Accepted Risk로 유지된다.
- Impact: 운영 DB에서 lock timeout/deadlock 가능성을 배제할 수 없다.
- Suggested Fix: PostgreSQL/MySQL 테스트 인스턴스와 Gunicorn 다중 worker 부하 테스트를 추가한다.
- Re-audit Method: 실제 DB E2E 및 deadlock/lock timeout 로그 확인.

## 7. Cross-Pass Conflicts

## [XPF-F001] 테스트는 통과하지만 배포 문서가 보안 경계를 후퇴시킨다

- Pass: Cross-Pass
- Severity: Major
- Status: Hold
- Summary: `run.py` 직접 실행은 loopback/fail-closed로 안전하지만, `BUILD_GUIDE.md`의 Gunicorn systemd 예시는 `0.0.0.0:8000` 직접 노출을 안내한다.
- Evidence:
  - `run.py` smoke: loopback 및 fail-closed 통과
  - `BUILD_GUIDE.md:100`: `--bind 0.0.0.0:8000`
  - `BUILD_GUIDE.md:154`: `proxy_pass http://127.0.0.1:8000;`
- Impact: 개발 서버 보안 경계와 운영 배포 문서 경계가 서로 다르게 동작한다.

## [XPF-F002] 문서 품질은 개선됐지만 추적성 미정리로 PASS 근거가 약하다

- Pass: Cross-Pass
- Severity: Major
- Status: Hold
- Summary: README 다국어와 hard-boundary 표현은 개선됐으나, 변경 파일과 감사 보고서가 여전히 untracked/modified 상태다.
- Impact: PASS 판정 시점의 immutable evidence가 부족하다.

## 8. Required Fixes Before PASS

1. `BUILD_GUIDE.md`의 Gunicorn bind 주소를 Nginx reverse proxy 구성과 맞게 loopback으로 정렬한다.
2. `run.py` docstring의 Gunicorn 예시도 동일한 배포 경계로 정렬한다.
3. `audit_report_73.md`-`audit_report_79.md` 및 현재 modified 파일들의 추적성 정책을 정리한다.
4. `app/routes/game_routes.py:1186`의 과잉 들여쓰기 주석을 실제 제어 흐름과 맞춘다.
5. `IMPLEMENTATION_SUMMARY.md`/`implementation_summary.md`, `LESSONS_LEARNED.md`/`lessons_learned.md` 파일명 authority를 결정한다.
6. `BUILD_GUIDE.md` quickstart에서 현재 Linux 호스트에 없는 `python` 명령 의존을 `python3` 우선 안내로 정리한다.
7. 실제 PostgreSQL/MySQL E2E와 브라우저/jsdom DOM XSS E2E는 수행하거나 명시적 residual risk로 계속 유지한다.

## 9. Accepted Risks

| Risk | Status | Owner | Revisit Trigger |
| --- | --- | --- | --- |
| SQLite multi-worker `Database Locked` 가능성 | Accepted Risk | Project Lead Architect / Eunho Lim | DAU 100명 초과, 초당 DB 쓰기 10회 초과, locked error 주 3회 이상 |
| 실제 PostgreSQL/MySQL row-lock/deadlock E2E 미수행 | Accepted Risk | Project Lead Architect / Eunho Lim | 실제 RDBMS 이주, lock timeout/deadlock 주 1회 이상 |
| 실제 브라우저/jsdom DOM XSS E2E 미수행 | Known Residual Risk | Coder / Auditor | 브라우저/jsdom 테스트 추가 전까지 |
| CI/workflow 부재 | Known Operational Risk | Maintainer | CI 도입 또는 수동 gate evidence 아카이브 |

## 10. Needs Spec Clarification

1. 감사 보고서가 untracked 상태로 누적될 때 PASS 전 필수 커밋이 필요한지, 별도 archive 보존으로 충분한지 기준이 필요하다.
2. historical changelog의 강한 표현을 현재 감사 기준으로 모두 낮출지, 당시 릴리스 기록으로 보존할지 기준이 필요하다.
3. required documentation 파일명의 대소문자 표준을 결정해야 한다.
4. Gunicorn 운영 bind 정책을 `127.0.0.1` 고정으로 둘지, 외부 bind를 허용한다면 어떤 방화벽/TLS/reverse proxy 전제를 요구할지 명시해야 한다.
5. Node.js 정적/결합 XSS 검증을 충분한 gate로 볼지, 브라우저/jsdom DOM E2E를 필수로 볼지 결정해야 한다.

## 11. Re-audit Checklist

- [x] `AI_AUDIT_DOC_STANDARD.md` 확인
- [x] 최신 감사 보고서 번호 확인: `audit_report_78.md` 이후 `audit_report_79.md`
- [x] `test -f audit_report_79.md`: 기존 파일 없음 확인
- [x] 직전 감사 `audit_report_78.md` HOLD 사유 확인
- [x] `git status --short`
- [x] `git diff --stat`
- [x] `git diff --name-only`
- [x] `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q`: `7 passed in 0.32s`
- [x] `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q -W error`: `7 passed in 0.32s`
- [x] `git diff --check`: pass
- [x] `git diff --cached --check`: pass
- [x] `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m py_compile ...`: pass
- [x] PostgreSQL URI smoke via `DATABASE_URL`: pass
- [x] PostgreSQL URI smoke via `SQLALCHEMY_DATABASE_URI`: pass
- [x] `psycopg2` import smoke: `2.9.12`
- [x] SQLite `journal_mode`: `wal`
- [x] SQLite `busy_timeout`: `5000`
- [x] production `DEBUG=true` 강제 off smoke: `False`
- [x] loopback 개발 서버 smoke: `127.0.0.1`, `v1.8.9`
- [x] 외부 바인딩 fail-closed smoke: `ValueError`
- [x] 외부 바인딩 opt-in debug off smoke: `0.0.0.0`, `Debug mode: off`
- [x] XSS mutation smoke: 주요 guard 제거 4건 모두 `FAILS_AS_EXPECTED`
- [x] README 다국어 혼입 재검색 및 수동 확인
- [x] hard-boundary 표현 잔존 검색
- [x] Gunicorn bind 문서 검색
- [x] CI/workflow 파일 검색: 없음
- [x] required docs 파일명 inventory 확인

## 12. Final Decision

**HOLD**

실행 게이트와 주요 구현 smoke는 통과했다.

- `pytest`: 7 passed
- `pytest -W error`: 7 passed
- `py_compile`: pass
- `git diff --check`: pass
- DB config smoke: pass
- SQLite WAL/busy_timeout smoke: pass
- 개발 서버 loopback/fail-closed smoke: pass
- XSS mutation smoke: pass

78번 대비 긍정적인 변화도 있다.

- README 다국어 혼입은 대부분 해소됐다.
- hard-boundary 표현은 상당히 완화됐다.
- `BUILD_GUIDE.md`의 `run.py` 중복 수정 안내는 현재 구현과 맞게 고쳐졌다.

그러나 `BUILD_GUIDE.md`의 Gunicorn bind가 `0.0.0.0:8000`으로 바뀐 것은 Nginx reverse proxy 운영 경계와 충돌하는 새 보안 회귀다. 또한 감사 산출물/작업트리 추적성, required docs 파일명 authority, 실제 RDBMS/DOM E2E residual risk는 아직 남아 있다.

따라서 79번 재감사의 최종 판정은 **HOLD**다. 소스 코드와 기존 문서는 수정하지 않았고, 감사 결과 문서 `audit_report_79.md`만 생성했다.
