# D3D Audit Report 67

## 1. Audit Scope

- 감사 일자: 2026-06-01
- 감사 기준: `AI_AUDIT_DOC_STANDARD.md`
- 감사 유형: 재감사, 구현 중심 상세 감사, 이전 감사 요청사항 재검증
- 프로젝트 경로: `/mnt/Projects_SSD/python/JissouParkEmpire`
- 프로젝트 유형: Flask + SQLAlchemy 기반 턴제 웹 게임
- 최종 판정: **HOLD**

이번 감사는 현재 `audit_report_66.md`가 **PASS** 및 전 항목 `Verified / Fixed` 완치 선언을 포함하는 상태에서, 해당 선언이 실제 코드, 문서, 테스트, 설정, Git 상태, 실행 명령과 일치하는지 독립적으로 재검증했다.

코드, 설정, 기존 문서, 기존 감사 문서는 수정하지 않았다. 본 감사에서 생성한 파일은 이 보고서(`audit_report_67.md`)뿐이다.

## 2. Excluded Scope

- 실제 브라우저 수동 플레이 및 Playwright/Selenium/jsdom 기반 DOM E2E 테스트는 수행하지 않았다.
- PostgreSQL/MySQL 실 DB 인스턴스에서 row-lock, deadlock timeout, migration, 다중 worker 부하 테스트는 수행하지 않았다.
- 장시간 운영, 실제 사용자 세션 지속성, 실제 Nginx/Gunicorn/systemd 배포 검증은 수행하지 않았다.
- `.git/`, `.antigravitycli/`, `__pycache__/`, `stitch_shitsiseki_empire_ui_refactor/`, `venv/`, `instance/`는 감사 범위에서 제외했다.
- 수정 작업은 수행하지 않았다.

## 3. Checked Inputs

### 확인한 문서

- `AI_AUDIT_DOC_STANDARD.md`
- `AGENTS.md`
- `spec.md`
- `README.md`
- `CHANGELOG.md`
- `BUILD_GUIDE.md`
- `DESIGN_DECISIONS.md`
- `designs.md`
- `audit_roadmap.md`
- `implementation_summary.md`
- `lessons_learned.md`
- `analyst.md`
- `audit_report_65.md`
- `audit_report_66.md`

### 확인한 구현 파일

- `run.py`
- `app/__init__.py`
- `app/config.py`
- `app/models.py`
- `app/game_engine.py`
- `app/npc_engine.py`
- `app/battle_engine.py`
- `app/routes/auth_routes.py`
- `app/routes/game_routes.py`
- `app/static/js/game.js`
- `tests/conftest.py`
- `tests/test_regression.py`
- `requirements.txt`

### 실행한 검증 명령

| 명령 | 결과 |
| --- | --- |
| `venv/bin/python -m pytest -q` | `5 passed in 0.36s` |
| `venv/bin/python -m pytest -q -W error` | `5 passed in 0.35s` |
| `git diff --check` | 통과 |
| `git diff --cached --check` | 통과 |
| `rg -n "[ \t]+$" ...` | 결과 없음 |
| AST parse | `AST_OK 17 files` |
| `git ls-files tests` | `tests/conftest.py`, `tests/test_regression.py` 출력 |
| `git status --short tests audit_report_66.md` | `A  tests/conftest.py`, `A  tests/test_regression.py`, `?? audit_report_66.md` |
| clean env `python run.py` | `127.0.0.1:5000`, debug on, timeout 종료 |
| `FLASK_RUN_HOST=0.0.0.0 python run.py` | `ValueError` fail-closed |
| `FLASK_RUN_HOST=0.0.0.0 ALLOW_UNSAFE_DEV_SERVER=1 SECRET_KEY=custom-key python run.py` | `0.0.0.0`, debug off, timeout 종료 |
| `FLASK_ENV=production` + secret 없음 | `ValueError` fail-closed |
| `FLASK_ENV=production DEBUG=true SECRET_KEY=...` | `DEBUG False`, secret 적용 |
| SQLite PRAGMA 확인 | `journal_mode wal`, `busy_timeout 5000` |
| SQLAlchemy dialect compile | SQLite: `SELECT parks.id FROM parks`, PostgreSQL: `SELECT parks.id FROM parks FOR UPDATE` |
| `DATABASE_URL=postgresql://...` 설정 확인 | `Config.SQLALCHEMY_DATABASE_URI`가 여전히 `sqlite:///game.db` |

## 4. Previous Audit Request Mapping

| `audit_report_66.md` 요청사항 / PASS 주장 | 현재 재감사 판정 | 근거 |
| --- | --- | --- |
| `tests/` Git 추적 포함 | **Verified for index** | `git ls-files tests`가 두 테스트 파일을 출력한다. 다만 현재 상태는 `A  tests/...`로 staged 상태이며 commit 완료는 확인하지 않았다. |
| trailing whitespace 제거 | **Verified** | `git diff --check`, `git diff --cached --check`, 전체 `rg` 공백 검색이 모두 통과했다. |
| XSS 회원가입 테스트 필드명 수정 | **Verified** | `tests/test_regression.py`가 실제 라우트 필드명 `password2`를 사용하고 `이름에 특수문자` 응답을 assert한다. |
| 외부 bind fail-closed | **Verified** | `FLASK_RUN_HOST=0.0.0.0` 단독 실행은 `ValueError`로 중단된다. |
| 외부 bind unsafe opt-in 시 debug off | **Verified** | `ALLOW_UNSAFE_DEV_SERVER=1 SECRET_KEY=custom-key`를 지정하면 `0.0.0.0`으로 뜨지만 `Debug mode: off`다. |
| fixed dev secret 외부 bind 차단 | **Verified** | 외부 bind 경로에서 secret 미지정 또는 dev 기본 키 사용 시 `ValueError` 가드가 존재한다. |
| production secret fail-closed | **Verified** | `FLASK_ENV=production` 및 secret 누락 시 `ValueError`가 발생한다. |
| `FLASK_ENV=production DEBUG=true` 차단 | **Verified** | secret 지정 시 `Config.DEBUG`가 `False`로 강제된다. |
| `spec.md`의 `run.py` host 설명 복구 | **Verified** | `spec.md`가 `127.0.0.1` 기본 bind 및 `FLASK_RUN_HOST` opt-in 구조를 설명한다. |
| XSS DOM 설명 순화 | **Still Needs Fix** | `CHANGELOG.md`, `lessons_learned.md`는 여전히 "DOM 경계 테스트", "진짜 융합형 DOM 경계 테스트"라고 설명한다. 실제 테스트는 `escapeHtml()` helper 함수 추출 실행이다. |
| SQLite/row-lock 과장 표현 제거 | **Still Needs Fix** | `README.md`, `spec.md`, `DESIGN_DECISIONS.md`, `implementation_summary.md`에 "guarantee dead-lock-free", "완벽 보증", "완전 차단", "100% 무결" 류 표현이 남아 있다. |
| 실제 구현 경로 기반 lost-update 테스트 | **Partially Improved / Still Needs Fix** | `_process_spy_missions()`를 호출하도록 개선됐지만, 테스트 기대값이 stale 20 기준과 refresh 25 기준 모두에서 `adult_count == 15`가 되어 refresh 제거 회귀를 결정적으로 잡지 못한다. |
| PostgreSQL 전환 기준과 운영 가이드 연결 | **Still Needs Fix** | `BUILD_GUIDE.md`는 `DATABASE_URL=postgresql://...`를 지시하지만 `app/config.py`는 `SQLALCHEMY_DATABASE_URI`만 읽는다. PostgreSQL driver도 `requirements.txt`에 없다. |
| `audit_report_66.md` PASS 선언 | **Rejected as Current Final Gate** | 여러 Major finding이 남아 있어 현재 증거 기준 PASS 유지 불가. |

## 5. Pass 1: Implementation Compliance Findings

## [IMP-F001] `BUILD_GUIDE.md`의 PostgreSQL 전환 경로가 실제 설정 코드와 연결되지 않음

- Pass: Implementation
- Pattern: `IMP-001`, `DOC-001`, `ARCH-001`, `DEP-001`
- Area: PostgreSQL migration, deployment config, accepted risk expiry path
- Severity: **Major**
- Status: **Needs Fix**
- Summary: SQLite multi-worker Accepted Risk의 만료 조건은 PostgreSQL 즉각 전환을 요구하지만, 운영 문서가 안내하는 `DATABASE_URL`은 현재 애플리케이션 설정에서 사용되지 않는다.
- Evidence:
  - `BUILD_GUIDE.md`: PostgreSQL 이주 방법으로 `.env`에 `DATABASE_URL=postgresql://user:password@localhost:5432/jissou_db`를 구성하라고 안내한다.
  - `app/config.py`: `SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///game.db')`.
  - 실제 확인: `DATABASE_URL=postgresql://...`를 주입해도 `Config.SQLALCHEMY_DATABASE_URI`는 `sqlite:///game.db`로 출력된다.
  - `requirements.txt`: `psycopg`, `psycopg2`, `pg8000` 등 PostgreSQL DBAPI 드라이버가 없다.
- Expected: Accepted Risk 만료 시 안내된 PostgreSQL 전환 경로가 실제 코드와 의존성에서 작동해야 한다.
- Actual: 문서대로 `DATABASE_URL`만 설정하면 애플리케이션은 계속 SQLite를 사용한다. 드라이버도 누락되어 `SQLALCHEMY_DATABASE_URI=postgresql://...`를 직접 써도 런타임 실패 가능성이 높다.
- Impact: SQLite multi-worker 위험이 만료되어도 문서상 탈출 경로가 작동하지 않는다. 운영자는 PostgreSQL로 전환했다고 믿고 실제로는 SQLite 파일 DB를 계속 사용할 수 있다.
- Suggested Fix: `app/config.py`가 `DATABASE_URL`과 `SQLALCHEMY_DATABASE_URI` 중 하나를 일관되게 지원하게 하거나, 문서를 `SQLALCHEMY_DATABASE_URI` 기준으로 수정한다. PostgreSQL 대상이면 `psycopg` 계열 드라이버를 `requirements.txt`에 추가하고 실제 import/connection smoke를 수행한다.
- Re-audit Method: `DATABASE_URL=postgresql://...` 또는 문서상 공식 env를 주입했을 때 `Config.SQLALCHEMY_DATABASE_URI`가 PostgreSQL URI를 반환하는지 확인하고, 드라이버 import 및 앱 생성 smoke를 실행한다.
- Owner: Architect / Coder

## [IMP-F002] XSS 회귀 테스트 설명이 여전히 DOM 경계 검증으로 과장되어 있음

- Pass: Implementation
- Pattern: `DOC-001`, `TEST-001`, `SEC-008`
- Area: XSS documentation, test scope
- Severity: **Major**
- Status: **Needs Fix**
- Summary: `audit_report_66.md`는 문서 설명을 helper 정합성 테스트로 순화했다고 주장하지만, 실제 문서에는 여전히 DOM 경계 테스트로 읽히는 표현이 남아 있다.
- Evidence:
  - `CHANGELOG.md`: "진짜 융합형 DOM 경계 테스트를 수립"이라고 설명한다.
  - `lessons_learned.md`: "XSS DOM 경계 테스트 한계" 항목의 조치 설명이 실제 `game.js` 함수 추출 및 Node.js 실행을 DOM 경계 테스트의 대체처럼 기술한다.
  - `tests/test_regression.py`: 실제로는 `re.search()`로 `function escapeHtml(str)`만 추출해 `node -e`에서 `escapeHtml()` 결과를 출력한다.
  - `app/static/js/game.js`: 실제 위험 경로는 `contentDiv.innerHTML = html`, `attack-title.innerHTML = ...`이다.
- Expected: 문서가 helper 함수 검증, DOM 삽입 경로 검증, 브라우저 E2E 검증을 구분해야 한다.
- Actual: 일부 문서가 helper 함수 정합성 테스트를 DOM 경계 검증처럼 과장한다.
- Impact: `escapeHtml()` 호출 누락, 신규 `innerHTML` 경로 추가, DOM parser 기반 이벤트 속성 실행 회귀를 놓칠 수 있는데도 문서상 방어가 완료된 것처럼 보인다.
- Suggested Fix: 문서 표현을 "실제 static JS helper 정합성 Node.js 교차 검증"으로 낮추고, DOM 경계 검증은 후속 테스트 또는 accepted risk로 분리한다.
- Re-audit Method: `rg -n "DOM 경계|진짜 융합형 DOM|escapeHtml" CHANGELOG.md lessons_learned.md tests/test_regression.py app/static/js/game.js`.
- Owner: Architect / Coder

## [IMP-F003] SQLite/row-lock 문서에 조건부 지원과 완전 보증 표현이 혼재함

- Pass: Implementation
- Pattern: `DOC-001`, `ARCH-001`, `RISK-001`
- Area: concurrency documentation, support matrix, accepted risk
- Severity: **Major**
- Status: **Needs Fix**
- Summary: SQLite multi-worker Accepted Risk와 PostgreSQL target production 설명이 일부 정리됐지만, 다국어 README 및 설계 문서에는 여전히 실제 검증 범위를 넘어서는 완전 보증 표현이 남아 있다.
- Evidence:
  - SQLAlchemy compile 확인: SQLite는 `FOR UPDATE`를 생성하지 않고 PostgreSQL만 `FOR UPDATE`를 생성한다.
  - `README.md` 영어/일본어/중국어 support matrix: PostgreSQL/MySQL 조합에서 "guarantee dead-lock-free", "完璧に連動", "保證無死鎖" 등으로 표현한다.
  - `spec.md`: PostgreSQL/MySQL 이주시 "교착 상태 완치를 완벽 보증" 표현이 남아 있다.
  - `implementation_summary.md`: "최고 수준의 동시성 격리 무결성을 완벽하게 확보" 표현이 남아 있다.
  - `DESIGN_DECISIONS.md`: "100% 원천 차단", "완벽히 해결", "완전하게 보호" 등 다수의 절대 표현이 남아 있다.
- Expected: 실제 PostgreSQL/MySQL 통합 테스트가 제외 범위라면 "설계상 예방", "기대", "대상 조합" 수준으로 제한해야 한다.
- Actual: 실 DB row-lock/deadlock 검증 없이 deadlock-free 또는 완전 보증 문구가 남아 있다.
- Impact: 운영자가 실 DB 이주 후 별도 부하/교착 테스트 없이 안전하다고 오판할 수 있다.
- Suggested Fix: 모든 언어의 README와 핵심 설계 문서에서 절대 보증 표현을 제거하고, 실 DB 통합 테스트 전까지 "목표/설계 의도/검증 필요"로 표현한다.
- Re-audit Method: `rg -n "완벽|100%|완전|guarantee|completely|完璧|保證|徹底" README.md spec.md DESIGN_DECISIONS.md implementation_summary.md BUILD_GUIDE.md CHANGELOG.md lessons_learned.md`.
- Owner: Architect

## [IMP-F004] `audit_report_66.md`의 PASS 선언이 현재 증거와 충돌함

- Pass: Implementation
- Pattern: `AUDIT-RECHECK`, `PHASE-GATE`
- Area: audit record, final decision
- Severity: **Major**
- Status: **Rejected as Current Gate**
- Summary: 66번 보고서는 모든 Required Fixes가 완치되었다고 선언하지만, 현재 재감사는 PostgreSQL 전환 경로 불일치, XSS 문서 과장, 동시성 문서 과장, lost-update 테스트 판별력 부족을 확인했다.
- Evidence:
  - `audit_report_66.md`: 최종 판정 PASS.
  - `BUILD_GUIDE.md`와 `app/config.py`: PostgreSQL env 이름 불일치.
  - `CHANGELOG.md`, `lessons_learned.md`: DOM 경계 테스트 표현 잔존.
  - `tests/test_regression.py`: lost-update 검증 기대값이 refresh 회귀를 구분하지 못함.
- Expected: PASS는 Critical/Major finding이 없거나 명시적 Accepted Risk가 완전해야 한다.
- Actual: Major finding이 남아 있다.
- Impact: 최신 감사 보고서만 읽으면 배포 가능 상태로 오판할 수 있다.
- Suggested Fix: 67번 보고서를 최신 gate로 삼고, Required Fixes 처리 후 68번에서 재감사한다.
- Re-audit Method: 본 보고서의 Re-audit Checklist를 재실행한다.
- Owner: Auditor

## 6. Pass 2: Debug / Engineering Quality Findings

## [DBG-F001] lost-update 회귀 테스트가 refresh 제거 회귀를 결정적으로 검출하지 못함

- Pass: Debug / Engineering Quality
- Pattern: `TEST-001`, `CONC-001`
- Area: SQLite concurrency regression, mutation sensitivity
- Severity: **Major**
- Status: **Needs Fix**
- Summary: `test_sqlite_lost_update_race_condition()`은 실제 `_process_spy_missions()`를 호출하도록 개선됐지만, 현재 데이터 구성은 refresh가 없어도 같은 최종값이 나올 수 있다.
- Evidence:
  - 테스트는 `park_b.adult_count = 20`, `population_cap = 15`로 시작한다.
  - 독립 세션 A가 `adult_count = 25`로 commit한다.
  - 세션 B의 stale 객체가 20인 상태에서 `_process_spy_missions(park_b)`를 호출한다.
  - 함수 내부 refresh가 유지되면 25에서 overcrowding 후 15가 된다.
  - refresh가 제거되어 stale 20으로 overcrowding해도 15가 된다.
  - 테스트의 최종 assertion은 `park_b.adult_count == 15`뿐이다.
- Expected: 회귀 테스트는 `_process_spy_missions()` 내부 `db.session.refresh(park)`가 제거되면 실패해야 한다.
- Actual: 현재 값 설계는 refreshed path와 stale path 모두 같은 final count로 수렴한다.
- Impact: 핵심 회귀인 refresh 제거, stale overwrite 재도입, SQLite `with_for_update()` no-op 의존 회귀를 놓칠 수 있다.
- Suggested Fix: 최신 값과 stale 값이 서로 다른 관측 가능한 결과를 만들도록 테스트 데이터를 설계한다. 예를 들어 event log의 탈주 수, 다른 population fields, target cap, 또는 명시적 version/timestamp를 assert한다.
- Re-audit Method: `_process_spy_missions()`의 최종 `db.session.refresh(park)`를 임시 제거하는 mutation에서 테스트가 실패하는지 확인한다.
- Owner: Coder / Auditor

## [DBG-F002] XSS 테스트는 실제 DOM 삽입 경로를 실행하지 않음

- Pass: Debug / Engineering Quality
- Pattern: `TEST-001`, `FRONTEND-001`, `SEC-008`
- Area: frontend regression testing
- Severity: **Major**
- Status: **Needs Fix**
- Summary: `test_xss_escape_html()`은 회원가입 입력 가드와 helper 함수 정합성은 검증하지만, `game.js`의 실제 `innerHTML` 삽입 경로를 실행하지 않는다.
- Evidence:
  - `app/static/js/game.js`: `contentDiv.innerHTML = html`, error branch `innerHTML`, `attack-title.innerHTML` 사용.
  - `tests/test_regression.py`: `escapeHtml()` 함수 문자열을 정규식으로 추출해 Node.js에서 함수만 실행한다.
  - 테스트는 DOM element, click handler, fetch mock, modal rendering, `innerHTML` 결과를 검증하지 않는다.
- Expected: "DOM 경계" 회귀 테스트는 실제 DOM 생성 또는 최소 jsdom 기반 DOM 삽입 결과를 검증해야 한다.
- Actual: helper 함수 단독 테스트다.
- Impact: 특정 삽입 지점에서 `escapeHtml()` 호출이 빠져도 helper 테스트는 통과할 수 있다.
- Suggested Fix: jsdom 또는 브라우저 테스트를 추가해 scout/attack modal 경로에 악성 `parkName`, `data.error`, `err.message`가 들어와도 실행 가능한 HTML/event handler가 생성되지 않는지 검증한다.
- Re-audit Method: `parkName` 또는 `attack-title` 경로에서 `escapeHtml()` 호출을 제거하는 mutation에서 테스트가 실패하는지 확인한다.
- Owner: Coder

## [DBG-F003] tests는 Git index에 추가됐지만 release commit 완료 상태는 아님

- Pass: Debug / Engineering Quality
- Pattern: `GIT-001`, `TEST-001`
- Area: release reproducibility
- Severity: **Minor**
- Status: **Known Issue**
- Summary: 이전 감사의 "untracked tests" 문제는 Git index 기준으로 해소됐다. 그러나 현재 상태는 `A  tests/...` staged 상태이며 commit 완료 상태는 아니다.
- Evidence:
  - `git ls-files tests`: 두 테스트 파일 출력.
  - `git status --short tests audit_report_66.md`: `A  tests/conftest.py`, `A  tests/test_regression.py`.
- Expected: 배포/공유 기준에서는 commit까지 완료되어야 다른 환경에서 재현 가능하다.
- Actual: 현재 로컬 index에 추가된 상태까지만 확인됐다.
- Impact: commit 전에는 작업트리 정리나 다른 checkout 과정에서 테스트 포함 상태가 흔들릴 수 있다.
- Suggested Fix: 구현 수정 완료 후 테스트 파일을 포함해 커밋한다. 본 감사에서는 수정/커밋을 수행하지 않는다.
- Re-audit Method: `git status --short tests`가 clean이거나 대상 commit에 포함되어 있는지 확인한다.
- Owner: Human / Coder

## 7. Pass 3: Security Findings

## [SEC-F001] PostgreSQL 전환 문서가 작동하지 않아 SQLite Accepted Risk의 탈출 경로가 깨짐

- Pass: Security
- Pattern: `SEC-002`, `ARCH-001`, `RISK-001`
- Area: data integrity boundary, operational fallback
- Severity: **Major**
- Status: **Needs Fix**
- Summary: SQLite multi-worker 위험 수용은 PostgreSQL 전환 조건으로 관리되지만, 실제 PostgreSQL 전환 env와 의존성이 불완전해 위험 수용의 만료 조건을 실행할 수 없다.
- Evidence:
  - Accepted Risk 문서: `Database Locked` 주 3회, DAU 100 초과, 초당 write 10회 이상이면 PostgreSQL 전환.
  - `BUILD_GUIDE.md`: `DATABASE_URL=postgresql://...` 안내.
  - `app/config.py`: `DATABASE_URL` 미사용.
  - `requirements.txt`: PostgreSQL 드라이버 미포함.
- Expected: Accepted Risk의 expiry/remediation path는 실제로 실행 가능해야 한다.
- Actual: 문서대로 전환해도 SQLite 유지 또는 드라이버 누락으로 실패 가능성이 높다.
- Impact: 데이터 정합성 위험이 임계치를 넘어도 운영자가 안전한 DB로 전환하지 못한다.
- Suggested Fix: PostgreSQL 전환을 실제 코드와 의존성으로 지원하거나, Accepted Risk 만료 시 수동 코드 변경이 필요하다고 명확히 기록한다.
- Re-audit Method: PostgreSQL URI를 공식 env로 주입해 앱 설정이 PostgreSQL로 바뀌고, driver import가 성공하는지 확인한다.
- Owner: Architect / Coder

## [SEC-F002] 외부 bind 개발 서버 방어는 현재 구현 기준 통과

- Pass: Security
- Pattern: `SEC-001`, `SEC-002`
- Area: dev server bind, debugger exposure
- Severity: **Info**
- Status: **Verified**
- Summary: 이전 보안 finding이었던 `0.0.0.0` + debug + fixed dev secret 노출은 현재 구현에서 기본적으로 차단된다.
- Evidence:
  - clean env `python run.py`: `Running on http://127.0.0.1:5000`, debug on.
  - `FLASK_RUN_HOST=0.0.0.0 python run.py`: `ValueError` fail-closed.
  - `FLASK_RUN_HOST=0.0.0.0 ALLOW_UNSAFE_DEV_SERVER=1 SECRET_KEY=custom-key python run.py`: `Debug mode: off`, `Running on all addresses`.
  - `run.py`: non-loopback host에서 `ALLOW_UNSAFE_DEV_SERVER`를 요구하고, `run_debug = False`로 강제한다.
- Expected: 외부 bind는 명시 opt-in과 debug off가 필요하다.
- Actual: 현재 구현은 이 기준을 만족한다.
- Impact: 이전의 LAN debugger 노출 위험은 기본 경로에서 해소됐다.
- Suggested Fix: 없음. 다만 README/BUILD_GUIDE에 unsafe dev server opt-in 정책을 더 명확히 안내할 수 있다.
- Re-audit Method: 위 3개 실행 경로를 반복 확인한다.
- Owner: Coder

## [SEC-F003] production secret fail-closed 및 DEBUG 강제 off는 현재 구현 기준 통과

- Pass: Security
- Pattern: `SEC-001`, `SEC-002`
- Area: secret handling, production boundary
- Severity: **Info**
- Status: **Verified**
- Summary: production secret 누락과 `DEBUG=true` 오설정에 대한 fail-closed 경계는 현재 동작한다.
- Evidence:
  - `FLASK_ENV=production` + secret 없음: `ValueError`.
  - `FLASK_ENV=production DEBUG=true SECRET_KEY=prod-secret`: `DEBUG False`, secret 적용.
  - `app/config.py`: `_is_explicit_production`이면 `DEBUG = False`.
- Expected: production에서는 임시 secret fallback과 debug mode가 허용되지 않아야 한다.
- Actual: 현재 구현은 이 기준을 만족한다.
- Impact: production secret 경계는 이전보다 안전하다.
- Suggested Fix: 없음.
- Re-audit Method: 동일 env smoke를 반복한다.
- Owner: Coder

## 8. Cross-Pass Conflicts

## [XPF-F001] 테스트 PASS와 최종 감사 PASS가 충돌함

- Pass: Cross-Pass
- Pattern: `TEST-001`, `PHASE-GATE`
- Area: final decision
- Severity: **Major**
- Status: **Hold**
- Summary: `pytest`, whitespace, AST, bind security smoke는 통과했지만, 문서-구현 drift와 테스트 판별력 문제가 남아 있어 최종 PASS는 불가하다.
- Evidence:
  - `pytest -q`: `5 passed`.
  - `pytest -q -W error`: `5 passed`.
  - `git diff --check` 및 `git diff --cached --check`: 통과.
  - 하지만 `DATABASE_URL` 전환 불일치, XSS DOM 문서 과장, lost-update 테스트 mutation sensitivity 부족이 남아 있다.
- Expected: D3D PASS는 문서, 코드, 테스트, 설정, 위험 수용이 같은 결론을 지지해야 한다.
- Actual: 테스트 통과만으로는 남은 Major finding을 닫을 수 없다.
- Suggested Fix: Required Fixes 처리 후 재감사한다.
- Re-audit Method: 본 보고서의 Re-audit Checklist를 재실행한다.
- Owner: Auditor

## [XPF-F002] SQLite Accepted Risk의 만료 조건과 PostgreSQL 전환 구현이 충돌함

- Pass: Cross-Pass
- Pattern: `RISK-001`, `ARCH-001`
- Area: accepted risk, deployment guide, config
- Severity: **Major**
- Status: **Needs Fix**
- Summary: Accepted Risk는 "조건 초과 시 PostgreSQL 즉각 전환"을 전제로 하지만, 전환 env와 의존성은 현재 작동하지 않는다.
- Evidence:
  - `README.md`, `spec.md`, `BUILD_GUIDE.md`: PostgreSQL 전환 조건 기록.
  - `BUILD_GUIDE.md`: `DATABASE_URL` 안내.
  - `app/config.py`: `DATABASE_URL` 미사용.
  - `requirements.txt`: PostgreSQL driver 미포함.
- Expected: Accepted Risk의 mitigation은 실행 가능해야 한다.
- Actual: mitigation path가 문서상 존재하지만 구현상 막혀 있다.
- Suggested Fix: 공식 DB URI env를 하나로 통일하고 driver 및 smoke test를 추가한다.
- Re-audit Method: PostgreSQL URI env 주입 시 SQLite가 아닌 PostgreSQL 설정이 선택되는지 확인한다.
- Owner: Architect / Coder

## [XPF-F003] "DOM 경계 테스트" 표현과 helper-only 테스트 구현이 충돌함

- Pass: Cross-Pass
- Pattern: `DOC-001`, `TEST-001`, `SEC-008`
- Area: frontend security verification
- Severity: **Major**
- Status: **Needs Fix**
- Summary: 구현은 helper 함수 단위 검증인데 문서 일부는 DOM 경계까지 검증한 것처럼 설명한다.
- Evidence:
  - 테스트: `escapeHtml()` 추출 및 Node.js 실행.
  - 실제 DOM 경로: `innerHTML` assignment.
  - 문서: `CHANGELOG.md` "DOM 경계 테스트".
- Expected: 검증 범위가 문서에 정확히 표현되어야 한다.
- Actual: 문서가 테스트보다 넓은 보증을 주장한다.
- Suggested Fix: 문서 표현을 낮추거나 실제 DOM 테스트를 추가한다.
- Re-audit Method: 문서 검색 및 mutation test.
- Owner: Architect / Coder

## 9. Required Fixes Before PASS

1. `BUILD_GUIDE.md`의 PostgreSQL 전환 env와 `app/config.py`의 DB URI env를 일치시킨다.
2. PostgreSQL을 Target Production으로 유지하려면 `requirements.txt`에 PostgreSQL DBAPI 드라이버를 추가하고 설정 smoke를 수행한다.
3. `DATABASE_URL=postgresql://...` 또는 공식 env 주입 시 실제 `Config.SQLALCHEMY_DATABASE_URI`가 PostgreSQL URI로 바뀌는 회귀 테스트를 추가한다.
4. `CHANGELOG.md`, `lessons_learned.md`의 "DOM 경계 테스트" 표현을 helper 정합성 검증으로 낮추거나 jsdom/브라우저 DOM 테스트를 추가한다.
5. `README.md`, `spec.md`, `DESIGN_DECISIONS.md`, `implementation_summary.md`의 PostgreSQL/MySQL deadlock-free, 완벽 보증, 100% 차단 표현을 실제 검증 범위에 맞게 낮춘다.
6. `test_sqlite_lost_update_race_condition()`이 refresh 제거 회귀를 실제로 실패시키도록 관측값을 재설계한다.
7. lost-update 테스트에 mutation-sensitive assertion을 추가한다. 예: 최신 25 기준의 탈주 이벤트 수, 별도 필드 보존, version counter, 또는 stale path와 refreshed path가 다른 final state를 만들도록 구성.
8. DOM XSS 방어는 `innerHTML` 삽입 지점별로 `escapeHtml()` 호출 누락 mutation을 잡는 테스트를 추가한다.
9. PostgreSQL/MySQL row-lock/deadlock 검증을 제외 범위로 유지한다면 이를 별도 Accepted Risk로 owner, expiry, review trigger와 함께 기록한다.
10. staged 상태의 `tests/`와 신규 감사 문서가 실제 release commit에 포함되는지 최종 릴리즈 전 확인한다.

## 10. Accepted Risks

### SQLite + Gunicorn multi-worker

- Status: **Accepted Risk 형식은 부분 충족이나 mitigation path 불완전**
- Owner: 문서상 `Project Lead Architect / Eunho Lim`.
- Expiry: DAU 100명 초과 또는 초당 평균 10회 이상 DB 쓰기 요청.
- Review Trigger: `Database Locked` 주 3회 이상 또는 데이터 정합성 사고.
- Constraint: Gunicorn workers 최대 2개, sync worker, thread 1.
- 감사 판정: owner/expiry/review 형식은 있다. 그러나 PostgreSQL 전환 경로가 실제 코드와 맞지 않아 mitigation path가 불완전하다.

### PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증

- Status: **Accepted Risk로 보기 어려움**
- Reason: 실 DB 테스트가 제외 범위인 것은 기록되어 있으나, "Target Production" 문서가 여전히 강한 보증을 제공한다. owner, expiry, review trigger를 가진 독립 Accepted Risk로 정리되어 있지 않다.

### 외부 bind 개발 서버

- Status: **Verified / controlled**
- Reason: non-loopback host는 기본 fail-closed이고, unsafe opt-in 시에도 debug off가 강제된다.

### DOM XSS E2E 미검증

- Status: **Accepted Risk로 보기 어려움**
- Reason: helper 정합성 테스트는 존재하지만 실제 DOM 삽입 경로 검증이 없고, 문서 일부가 DOM 경계 검증처럼 표현한다.

## 11. Needs Spec Clarification

- 공식 DB 설정 환경변수는 `DATABASE_URL`인가, `SQLALCHEMY_DATABASE_URI`인가?
- PostgreSQL/MySQL target production은 현재 Phase에서 실제 연결 가능한 지원 범위인가, 후속 이주 목표인가?
- PostgreSQL/MySQL row-lock/deadlock 검증 없이 "deadlock-free" 또는 동등 표현을 문서에 남길 수 있는가?
- XSS 회귀의 PASS 기준은 helper 함수 정합성인가, 실제 DOM 삽입 경로 실행인가?
- SQLite lost-update 방어는 `refresh()` 호출 존재만으로 충분한가, mutation-sensitive regression test가 필수인가?
- 감사 보고서와 테스트 파일은 staged 상태만으로 D3D Git Inclusion Strategy를 만족하는가, commit까지 완료되어야 하는가?

## 12. Re-audit Checklist

- `venv/bin/python -m pytest -q`
- `venv/bin/python -m pytest -q -W error`
- `git diff --check`
- `git diff --cached --check`
- `rg -n "[ \t]+$" tests app/static/js/game.js app/*.py app/routes/*.py spec.md README.md CHANGELOG.md BUILD_GUIDE.md DESIGN_DECISIONS.md designs.md implementation_summary.md lessons_learned.md audit_roadmap.md analyst.md run.py`
- `git ls-files tests`
- clean env `python run.py`
- `FLASK_RUN_HOST=0.0.0.0 python run.py`
- `FLASK_RUN_HOST=0.0.0.0 ALLOW_UNSAFE_DEV_SERVER=1 SECRET_KEY=custom-key python run.py`
- production secret 누락 fail-closed test
- `FLASK_ENV=production DEBUG=true SECRET_KEY=...` DEBUG false 확인
- SQLite PRAGMA `journal_mode`, `busy_timeout` 확인
- SQLite/PostgreSQL `with_for_update()` SQL compile 확인
- 공식 PostgreSQL env 주입 시 Config DB URI 확인
- PostgreSQL driver import smoke
- XSS helper mutation test
- DOM insertion mutation test 또는 jsdom/브라우저 테스트
- `_process_spy_missions()` refresh 제거 mutation test

## 13. Final Decision

**HOLD**

이번 재감사에서 확인된 개선은 명확하다.

- `tests/`는 Git index에 추가되어 `git ls-files tests`에 잡힌다.
- `pytest -q`와 `pytest -q -W error`는 모두 통과한다.
- `git diff --check`, `git diff --cached --check`, 전체 trailing whitespace 검색은 통과한다.
- `run.py`는 기본 루프백 bind로 기동하며, 외부 bind는 기본 fail-closed다.
- unsafe 외부 bind opt-in 시에도 debug mode가 꺼진다.
- production secret fail-closed 및 `DEBUG=false` 강제 경계는 동작한다.
- XSS 회원가입 테스트는 실제 `password2` 필드와 위험문자 메시지를 검증하도록 개선됐다.

그러나 PASS는 불가하다.

1. PostgreSQL 전환 문서가 `DATABASE_URL`을 안내하지만 실제 설정 코드는 `SQLALCHEMY_DATABASE_URI`만 읽는다.
2. PostgreSQL driver가 `requirements.txt`에 없어 Target Production 전환 경로가 완성되지 않았다.
3. XSS 테스트는 helper 함수 검증인데 `CHANGELOG.md`와 `lessons_learned.md`에는 DOM 경계 테스트처럼 남아 있다.
4. lost-update 테스트는 `_process_spy_missions()`를 호출하지만 refresh 제거 회귀를 결정적으로 실패시키지 못한다.
5. SQLite/row-lock 관련 문서에는 실 DB 미검증 상태에서 deadlock-free, 완벽 보증, 100% 차단 류 표현이 남아 있다.

따라서 `audit_report_66.md`의 PASS 선언은 현재 증거 기준으로 유지할 수 없다. 다음 재감사는 위 Required Fixes 처리 후 `audit_report_68.md`에서 수행해야 한다.
