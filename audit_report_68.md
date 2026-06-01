# D3D Audit Report 68

## 1. Audit Scope

- 감사 일자: 2026-06-01
- 감사 기준: `AI_AUDIT_DOC_STANDARD.md`
- 감사 유형: 재감사, 구현 중심 상세 감사, 이전 감사문서 요청사항 재검증
- 프로젝트 경로: `/mnt/Projects_SSD/python/JissouParkEmpire`
- 프로젝트 유형: Flask + SQLAlchemy 기반 턴제 웹 게임
- 최종 판정: **HOLD**

이번 감사는 `audit_report_67.md`의 HOLD 요청사항을 기준으로 현재 구현, 문서, 테스트, 설정, 보안 경계를 다시 대조했다. `audit_report_66.md`의 PASS 선언은 최신 게이트로 보지 않고, 67번의 미해결 항목이 실제로 해소되었는지 재검증했다.

코드, 설정, 기존 문서, 기존 감사 문서는 수정하지 않았다. 본 감사에서 생성한 파일은 이 보고서(`audit_report_68.md`)뿐이다.

## 2. Excluded Scope

- 실제 브라우저 수동 플레이, Playwright/Selenium/jsdom 기반 DOM E2E 테스트는 수행하지 않았다.
- PostgreSQL/MySQL 실 DB 인스턴스에서 row-lock, lock timeout, deadlock, migration, 다중 worker 부하 테스트는 수행하지 않았다.
- 장시간 운영, 실제 사용자 세션 지속성, 실제 Nginx/Gunicorn/systemd 배포 검증은 수행하지 않았다.
- `.git/`, `.antigravitycli/`, `__pycache__/`, `stitch_shitsiseki_empire_ui_refactor/`, `venv/`, `instance/`는 감사 범위에서 제외했다.
- 수정 작업은 수행하지 않았다.

## 3. Checked Inputs and Commands

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
- `audit_report_66.md`
- `audit_report_67.md`

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
| `venv/bin/python -m pytest -q` | `7 passed in 0.33s` |
| `venv/bin/python -m pytest -q -W error` | `7 passed in 0.33s` |
| `git diff --check` | 통과 |
| `git diff --cached --check` | 통과 |
| AST parse | `AST_OK 17 files` |
| `DATABASE_URL=postgresql://...` 설정 확인 | `Config.SQLALCHEMY_DATABASE_URI`가 PostgreSQL URI로 전환됨 |
| `SQLALCHEMY_DATABASE_URI=postgresql://...` 설정 확인 | `Config.SQLALCHEMY_DATABASE_URI`가 PostgreSQL URI로 전환됨 |
| `venv/bin/python -c "import psycopg2"` | `psycopg2 2.9.12` import 확인 |
| `venv/bin/python -c "import psycopg"` | `ModuleNotFoundError`; 현재 의존성은 `psycopg2-binary` 기준 |
| SQLite PRAGMA 확인 | `journal_mode wal`, `busy_timeout 5000` |
| SQLAlchemy dialect compile | SQLite: `FOR UPDATE` 미생성, PostgreSQL: `FOR UPDATE` 생성 |
| clean env `python run.py` | `127.0.0.1:5000`, debug on, timeout 종료 |
| `FLASK_RUN_HOST=0.0.0.0 python run.py` | `ValueError` fail-closed |
| `FLASK_RUN_HOST=0.0.0.0 ALLOW_UNSAFE_DEV_SERVER=1 SECRET_KEY=custom-key python run.py` | `0.0.0.0`, debug off, timeout 종료 |
| `FLASK_ENV=production` + secret 없음 | `ValueError` fail-closed |
| `FLASK_ENV=production DEBUG=true SECRET_KEY=...` | `Config.DEBUG == False` 확인 |

## 4. Previous Audit Request Mapping

| `audit_report_67.md` 요청사항 | 현재 재감사 판정 | 근거 |
| --- | --- | --- |
| PostgreSQL 전환 경로가 `DATABASE_URL`과 연결되지 않음 | **Verified / Fixed** | `app/config.py:59-60`이 `SQLALCHEMY_DATABASE_URI`와 `DATABASE_URL`을 모두 읽고, 실제 env smoke에서 PostgreSQL URI로 전환됐다. |
| PostgreSQL driver 누락 | **Verified / Fixed** | `requirements.txt:9`에 `psycopg2-binary>=2.9.0`가 있으며 `psycopg2` import가 성공한다. 단, `psycopg` v3가 아니라 `psycopg2` 기준이다. |
| XSS 테스트/문서가 DOM 경계 검증으로 과장됨 | **Partially Improved / Still Needs Fix** | `CHANGELOG.md:15`는 정적 innerHTML 스캔으로 표현을 낮췄지만, `tests/test_regression.py:207`은 여전히 브라우저 DOM 렌더링 안전성을 증명한다고 주석화하고, 정적 스캔은 `html` 변수 대입을 추적하지 않는다. |
| SQLite/row-lock 및 deadlock-free 과장 표현 제거 | **Still Needs Fix** | `README.md:188`, `implementation_summary.md:343-349`, `implementation_summary.md:482`, `CHANGELOG.md:23`에 실 DB 검증 범위를 넘는 완전 보증형 표현이 남아 있다. |
| lost-update 테스트가 refresh 제거 회귀를 잡지 못함 | **Verified / Fixed for current mutation target** | `tests/test_regression.py:300-322`가 stale 14와 committed 25를 분리해 refresh 제거 시 최종값이 14로 남는 구조가 되었다. |
| 개발 서버 외부 bind/프로덕션 secret 보안 가드 | **Verified** | `run.py:20-62`와 실행 smoke 결과가 루프백 기본값, 외부 bind fail-closed, unsafe opt-in 시 debug off, production secret fail-closed를 지지한다. |
| `audit_report_66.md` PASS 선언 | **Superseded by 67/68 HOLD** | 67번 이후 일부 항목은 해소됐지만, 68번 기준 Major finding이 남아 있어 PASS로 복귀할 수 없다. |

## 5. Pass 1: Implementation Compliance Findings

## [IMP-F001 Re-audit #1] PostgreSQL 전환 env와 driver 경로는 현재 구현과 연결됨

- Pass: Implementation
- Pattern: `IMP-001`, `DOC-001`, `DEP-001`
- Area: PostgreSQL migration, deployment config, dependency manifest
- Severity: **Info**
- Status: **Verified**
- Summary: 67번의 PostgreSQL 전환 경로 불일치와 driver 누락 지적은 현재 구현 기준으로 해소됐다.
- Evidence:
  - `app/config.py:59-60`: `SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL') or 'sqlite:///game.db'`.
  - `requirements.txt:9`: `psycopg2-binary>=2.9.0`.
  - 실행 확인: `DATABASE_URL=postgresql://...`와 `SQLALCHEMY_DATABASE_URI=postgresql://...` 모두 `Config.SQLALCHEMY_DATABASE_URI`를 PostgreSQL URI로 전환했다.
  - 실행 확인: `psycopg2 2.9.12` import 성공.
- Expected: 문서상 PostgreSQL 전환 env가 실제 설정 코드와 DBAPI 의존성으로 연결되어야 한다.
- Actual: env fallback과 `psycopg2` driver가 존재한다.
- Impact: SQLite multi-worker Accepted Risk의 탈출 경로는 이전보다 실제 운영 가능성이 높아졌다.
- Suggested Fix: 없음. 단, `psycopg` v3가 아니라 `psycopg2`를 공식 선택으로 문서에 명확히 유지해야 한다.
- Re-audit Method: PostgreSQL URI env 주입, `psycopg2` import, Flask app config smoke를 반복한다.
- Owner: Coder / Auditor
- Notes: 실제 PostgreSQL 서버 연결 및 row-lock 동작 검증은 이번 범위에서 제외됐다.

## [IMP-F002 Re-audit #1] XSS 테스트 설명과 실제 검증 범위가 아직 완전히 일치하지 않음

- Pass: Implementation
- Pattern: `DOC-001`, `TEST-001`, `SEC-008`
- Area: XSS documentation, frontend test scope
- Severity: **Major**
- Status: **Needs Fix**
- Summary: 67번 이후 `CHANGELOG.md`의 표현은 정적 스캔으로 일부 낮아졌지만, 테스트 주석과 검증 방식은 여전히 실제 브라우저 DOM 안전성을 증명하는 수준으로 읽힌다.
- Evidence:
  - `CHANGELOG.md:15`: Node.js 기반 `escapeHtml` 헬퍼 교차 검증 및 정적 `innerHTML` 스캔으로 기술되어 이전보다 정직해졌다.
  - `tests/test_regression.py:207`: Python 모방 검증이 "브라우저 DOM 렌더링 시 XSS가 성립하지 않음"을 증명한다고 설명한다.
  - `tests/test_regression.py:366-397`: 정규식으로 `innerHTML` 대입문을 훑지만 `value_stripped in ('html', 'errorHtml')`인 경우 검사를 건너뛴다.
  - `app/static/js/game.js:104-131`: 실제 정찰 모달 HTML은 `let html = ...`, `html += ...`, `contentDiv.innerHTML = html` 경로로 만들어진다.
- Expected: 문서는 helper 함수 검증, 정적 소스 스캔, 실제 DOM 삽입 경로 검증을 구분해야 한다.
- Actual: 일부 설명은 helper/정적 스캔만으로 DOM 렌더링 안전성이 증명된 것처럼 읽힌다.
- Impact: 신규 보간값이 `html` builder에 추가되거나 기존 `escapeHtml(parkName)`이 제거되어도 현재 설명만 읽으면 검증이 충분하다고 오판할 수 있다.
- Suggested Fix: 문서와 주석을 "helper 정합성 + 제한적 정적 스캔"으로 낮추고, DOM 경계 검증은 jsdom/브라우저 테스트 또는 명시적 accepted risk로 분리한다.
- Re-audit Method: `rg -n "DOM 렌더링|DOM 경계|innerHTML|escapeHtml|XSS" CHANGELOG.md lessons_learned.md tests/test_regression.py app/static/js/game.js`로 표현과 실제 테스트 경로를 재대조한다.
- Owner: Architect / Coder

## [IMP-F003 Re-audit #1] 동시성 지원 문서에 실 DB 미검증 범위를 넘는 완전 보증 표현이 남아 있음

- Pass: Implementation
- Pattern: `DOC-001`, `ARCH-001`, `RISK-001`
- Area: concurrency documentation, support matrix, accepted risk
- Severity: **Major**
- Status: **Needs Fix**
- Summary: `spec.md`와 `DESIGN_DECISIONS.md`에는 PostgreSQL/MySQL 실 DB 미검증 Accepted Risk가 비교적 명확하지만, 사용자-facing 및 구현 요약 문서에는 deadlock-free 보증처럼 읽히는 표현이 남아 있다.
- Evidence:
  - `README.md:188`: 중국어 간체 support matrix가 "完美结合，保证无死锁的高性能并发"라고 표현한다.
  - `implementation_summary.md:343-345`: "영구 교착 상태 완전 예방", "교착 상태 ... 완전 해소"라고 표현한다.
  - `implementation_summary.md:482`: 실제 RDBMS 이주 시 "어떠한 교착 상태(Deadlock) 없이 고성능 동시 처리를 지원"한다고 표현한다.
  - `CHANGELOG.md:23`: NPC 공격 데드락과 DB 커넥션 고갈 결함을 "완전 종식"했다고 표현한다.
  - SQLAlchemy compile 확인: SQLite dialect는 `FOR UPDATE`를 생성하지 않고 PostgreSQL dialect만 `FOR UPDATE`를 생성한다.
- Expected: 실제 PostgreSQL/MySQL 통합 테스트가 제외 범위라면 "설계상 예방", "위험 감소", "Target Production", "실 DB 검증 필요" 수준으로 제한해야 한다.
- Actual: 일부 문서가 실 DB deadlock-free 보증으로 읽힌다.
- Impact: 운영자가 PostgreSQL/MySQL 이주 후 별도 부하/교착 테스트 없이 안전하다고 오판할 수 있다.
- Suggested Fix: README 전 언어, `implementation_summary.md`, `CHANGELOG.md`, 필요 시 `DESIGN_DECISIONS.md`의 절대 보증 표현을 조건부 설계 표현으로 낮춘다.
- Re-audit Method: `rg -n "완벽|완전|어떠한 교착|guarantee|completely|完美|保证无死锁|保證無死鎖|deadlock-free" README.md spec.md DESIGN_DECISIONS.md implementation_summary.md CHANGELOG.md BUILD_GUIDE.md lessons_learned.md`.
- Owner: Architect

## 6. Pass 2: Debug / Engineering Quality Findings

## [DBG-F001 Re-audit #1] lost-update 회귀 테스트는 현재 refresh 제거 mutation에 민감해짐

- Pass: Debug / Engineering Quality
- Pattern: `TEST-001`, `CONC-001`
- Area: SQLite concurrency regression, mutation sensitivity
- Severity: **Info**
- Status: **Verified**
- Summary: 67번에서 지적한 `_process_spy_missions()` refresh 제거 회귀 미검출 문제는 현재 테스트 데이터 구성 기준으로 해소됐다.
- Evidence:
  - `tests/test_regression.py:300-308`: 세션 A와 세션 B가 동일 row를 stale 14 상태로 읽는다.
  - `tests/test_regression.py:310-312`: 세션 A가 `adult_count = 25`로 commit한다.
  - `tests/test_regression.py:314-318`: 세션 B의 stale 객체로 `_process_spy_missions(park_b)`를 호출한다.
  - `tests/test_regression.py:320-322`: refresh가 유지되면 25에서 overcrowding이 실행되어 15가 되고, refresh가 제거되면 stale 14가 cap 이하라 14로 남아 assertion이 실패하는 구조다.
- Expected: 핵심 회귀인 refresh 제거 시 테스트가 실패해야 한다.
- Actual: 현재 값 설계는 stale path와 refreshed path의 최종 관측값을 다르게 만든다.
- Impact: 67번의 테스트 판별력 부족은 현재 타겟 mutation에 대해서는 해소됐다.
- Suggested Fix: 없음. 후속으로 실제 DB별 통합 테스트를 추가하면 더 강해진다.
- Re-audit Method: `_process_spy_missions()`의 최종 `db.session.refresh(park)`를 임시 제거하는 mutation에서 `test_sqlite_lost_update_race_condition()`이 실패하는지 확인한다.
- Owner: Coder / Auditor

## [DBG-F002 Re-audit #1] `innerHTML = html` builder 변수 경로를 정적 스캔이 추적하지 못함

- Pass: Debug / Engineering Quality
- Pattern: `TEST-001`, `FRONTEND-001`, `SEC-008`
- Area: frontend regression testing, static analysis blind spot
- Severity: **Major**
- Status: **Needs Fix**
- Summary: 새 `test_static_js_inner_html_xss_protection()`은 `innerHTML` 대입문을 스캔하지만, 실제 위험한 동적 문자열이 담긴 `html` 변수를 검사하지 않고 건너뛴다.
- Evidence:
  - `tests/test_regression.py:376`: `([a-zA-Z0-9_\-\.]+)\.innerHTML\s*=\s*(.*?)(?=\n|;)` 정규식으로 대입문 우변만 추출한다.
  - `tests/test_regression.py:383`: 우변이 `html` 또는 `errorHtml`이면 `continue`한다.
  - `app/static/js/game.js:104-131`: 동적 보간은 `let html = ...`와 `html += ...`에서 발생하고, 최종 대입은 `contentDiv.innerHTML = html`이다.
  - 현재 소스의 `parkName`은 `app/static/js/game.js:105`에서 `escapeHtml(parkName)`으로 안전하게 감싸져 있으나, 이 호출을 제거하는 mutation을 현재 정적 스캔이 직접 추적한다고 볼 수 없다.
- Expected: `innerHTML`에 대입되는 builder 변수의 정의부와 누적 `+=` 구간까지 추적하거나, 실제 DOM/jsdom 경로를 실행해야 한다.
- Actual: `html` 변수 대입을 신뢰하고 건너뛰므로 builder 내부 보간 누락 회귀를 놓칠 수 있다.
- Impact: XSS 방어 회귀 테스트가 "모든 innerHTML 동적 대입문"을 커버한다는 주장과 달리, 가장 중요한 정찰 모달 builder 경로에 사각지대가 남는다.
- Suggested Fix: `html` 변수의 `let html =`와 `html +=` 템플릿 리터럴을 별도로 파싱해 모든 `${...}` 보간이 `escapeHtml`, `parseInt`, `parseFloat`, 서버 신뢰 숫자 allowlist 중 하나인지 검증한다. 더 좋은 방법은 jsdom 또는 브라우저 테스트로 버튼 클릭, fetch mock, `contentDiv.innerHTML` 결과를 실행 검증하는 것이다.
- Re-audit Method: `app/static/js/game.js:105`의 `escapeHtml(parkName)`을 임시 제거하는 mutation에서 `test_static_js_inner_html_xss_protection()`이 실패하는지 확인한다.
- Owner: Coder / Auditor

## [DBG-F003] 기본 품질 게이트는 통과함

- Pass: Debug / Engineering Quality
- Pattern: `BUILD-001`, `TEST-001`
- Area: pytest, warnings, whitespace, syntax
- Severity: **Info**
- Status: **Verified**
- Summary: 현재 테스트와 기본 정적 품질 게이트는 통과한다.
- Evidence:
  - `venv/bin/python -m pytest -q`: `7 passed in 0.33s`.
  - `venv/bin/python -m pytest -q -W error`: `7 passed in 0.33s`.
  - `git diff --check`: 통과.
  - `git diff --cached --check`: 통과.
  - AST parse: `AST_OK 17 files`.
- Expected: 재감사 대상 변경이 최소한의 자동화 게이트를 통과해야 한다.
- Actual: 기본 게이트는 통과한다.
- Impact: HOLD 사유는 현재 테스트 실패가 아니라 테스트 범위와 문서 보증 범위 불일치다.
- Suggested Fix: 없음.
- Re-audit Method: 동일 명령을 반복한다.
- Owner: Auditor

## 7. Pass 3: Security Findings

## [SEC-F001 Re-audit #1] 개발 서버 외부 노출 및 프로덕션 secret 가드는 현재 동작함

- Pass: Security
- Pattern: `SEC-001`, `SEC-002`, `CONFIG-001`
- Area: Flask dev server, bind address, debug console, secret key
- Severity: **Info**
- Status: **Verified**
- Summary: 67번에서 Verified였던 외부 bind 및 production secret hard boundary는 현재도 유효하다.
- Evidence:
  - `run.py:20-27`: 루프백 bind일 때만 `DEBUG=true`와 개발용 secret fallback을 주입한다.
  - `run.py:28-44`: 외부 bind는 `ALLOW_UNSAFE_DEV_SERVER`와 커스텀 secret 없이는 `ValueError`로 fail-closed한다.
  - `run.py:56-62`: 외부 bind에서는 `run_debug = False`로 강제된다.
  - 실행 확인: `FLASK_RUN_HOST=0.0.0.0` 단독 실행은 `ValueError`.
  - 실행 확인: unsafe opt-in과 custom secret을 함께 주입하면 `0.0.0.0`으로 뜨되 debug off.
  - 실행 확인: `FLASK_ENV=production`에서 secret 누락은 `ValueError`, `DEBUG=true` 주입은 `Config.DEBUG == False`.
- Expected: 기본 개발 실행은 루프백만 열고, 외부 bind와 production은 hard fail 또는 debug off로 동작해야 한다.
- Actual: 현재 실행 smoke가 기대 동작과 일치한다.
- Impact: 이전 LAN debug console 노출 위험은 현재 구현 기준으로 해소됐다.
- Suggested Fix: 없음.
- Re-audit Method: 동일 env smoke 명령을 반복한다.
- Owner: Coder / Auditor

## [SEC-F002 Re-audit #1] XSS 방어 구현은 현재 소스상 안전해 보이나, 브라우저 경계 검증은 아직 부족함

- Pass: Security
- Pattern: `SEC-008`, `FRONTEND-001`, `TEST-001`
- Area: XSS, frontend rendering boundary
- Severity: **Major**
- Status: **Needs Fix**
- Summary: 현재 확인한 `game.js`의 주요 사용자 입력 보간은 `escapeHtml()`을 사용하지만, 테스트가 실제 DOM 삽입 경로를 실행하지 않아 보안 회귀 차단력은 제한적이다.
- Evidence:
  - `app/static/js/game.js:105`: `parkName`은 `escapeHtml(parkName)`으로 렌더링된다.
  - `app/static/js/game.js:133`: 실패 메시지 `data.error`는 `escapeHtml(data.error || I18N.scoutFail)`로 렌더링된다.
  - `app/static/js/game.js:136`: 예외 메시지 `err.message`는 `escapeHtml(err.message)`로 렌더링된다.
  - `app/static/js/game.js:153`: `targetName`은 `escapeHtml(targetName)`으로 렌더링된다.
  - `tests/test_regression.py:237-262`: 실제 `game.js`에서 `escapeHtml()` 함수만 추출해 Node.js에서 실행한다.
  - `tests/test_regression.py:366-397`: 정적 `innerHTML` 스캔은 존재하지만 builder 변수 추적은 없다.
- Expected: XSS 보안 게이트는 실제 sink(`innerHTML`)에 도달하는 데이터 흐름을 검증해야 한다.
- Actual: 현재 테스트는 helper 함수 정합성 및 제한적 정적 스캔에 머문다.
- Impact: 신규 sink 또는 builder 내부 미이스케이프 보간이 추가되면 자동 테스트가 놓칠 수 있다.
- Suggested Fix: `innerHTML` sink 단위 데이터 흐름 테스트 또는 jsdom/브라우저 기반 E2E를 추가한다. 최소한 `html` builder 변수의 템플릿 보간을 정적으로 추적해야 한다.
- Re-audit Method: `escapeHtml(parkName)`, `escapeHtml(targetName)`, `escapeHtml(data.error)`, `escapeHtml(err.message)` 중 하나를 임시 제거하는 mutation에서 테스트가 실패하는지 확인한다.
- Owner: Coder / Auditor

## [SEC-F003] PostgreSQL/MySQL 실 row-lock 및 deadlock 검증은 Accepted Risk로만 존재함

- Pass: Security
- Pattern: `RISK-001`, `CONC-001`, `DEPLOY-001`
- Area: database locking, production migration, operational safety
- Severity: **Major**
- Status: **Accepted Risk**
- Summary: 실제 PostgreSQL/MySQL 인스턴스 기반 row-lock/deadlock 검증은 수행되지 않았고, 이는 `spec.md` 및 `DESIGN_DECISIONS.md`에서 Accepted Risk로 다뤄진다. 다만 다른 문서의 완전 보증 표현은 이 위험 수용과 충돌한다.
- Evidence:
  - `spec.md:779`: PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증 Accepted Risk와 책임자, 수용 사유, 만료 조건, 재검토 조건을 기록한다.
  - `DESIGN_DECISIONS.md:40`: 동일 Accepted Risk 세부 규격을 기록한다.
  - 이번 감사 제외 범위: 실제 PostgreSQL/MySQL 서버 연결, 다중 worker 부하, deadlock E2E 검증 미수행.
  - `implementation_summary.md:482`와 `README.md:188`은 해당 위험 수용보다 강한 보증처럼 읽힌다.
- Expected: Accepted Risk가 존재하면 모든 사용자-facing 문서도 같은 제한 조건을 반영해야 한다.
- Actual: 권위 문서 일부에는 위험 수용이 있지만, 다른 문서에는 보증형 표현이 남아 있다.
- Impact: 운영자가 Accepted Risk를 인지하지 못하고 production DB 이주 후 검증 없이 배포할 수 있다.
- Suggested Fix: 실 DB 통합 테스트를 추가하거나, 모든 운영 문서에 동일한 owner, 사유, 만료 조건, 재검토 조건을 전파한다.
- Re-audit Method: PostgreSQL service를 띄워 canonical lock 경로와 deadlock 회피 경로를 실행하거나, 문서 전수 검색으로 Accepted Risk 일관성을 확인한다.
- Owner: Architect / Human

## 8. Cross-Pass Conflicts

## [XPF-F001] 테스트 통과와 XSS 보안 커버리지 사이의 충돌

- Pass: Cross-Pass
- Pattern: `TEST-001`, `SEC-008`
- Area: automated gate interpretation
- Severity: **Major**
- Status: **Hold**
- Summary: `pytest`는 7개 테스트를 모두 통과하지만, 가장 중요한 `innerHTML = html` builder 경로는 테스트가 직접 추적하지 않는다.
- Evidence:
  - `venv/bin/python -m pytest -q`: `7 passed`.
  - `tests/test_regression.py:383`: `html` 변수 대입을 건너뛴다.
  - `app/static/js/game.js:104-131`: 정찰 모달의 동적 HTML builder 경로가 존재한다.
- Expected: PASS 판정은 테스트 성공뿐 아니라 테스트가 위험 경로를 실제로 커버한다는 증거를 필요로 한다.
- Actual: 테스트 성공은 존재하지만 sink/data-flow 커버리지 증거가 부족하다.
- Impact: 자동화 결과만으로 XSS 회귀 방어 완료를 선언하면 위험하다.
- Suggested Fix: `html` builder 변수 추적 또는 jsdom E2E를 추가한다.
- Re-audit Method: XSS mutation test를 수행한다.
- Owner: Auditor / Coder

## [XPF-F002] Accepted Risk와 사용자-facing deadlock-free 표현 사이의 충돌

- Pass: Cross-Pass
- Pattern: `DOC-001`, `RISK-001`
- Area: documentation authority, production safety
- Severity: **Major**
- Status: **Hold**
- Summary: 권위 문서 일부는 실 DB 미검증을 Accepted Risk로 인정하지만, README와 구현 요약 일부는 이를 조건부 위험이 아니라 보증으로 표현한다.
- Evidence:
  - `spec.md:779`, `DESIGN_DECISIONS.md:40`: PostgreSQL/MySQL 실 DB 검증 미수행 Accepted Risk.
  - `README.md:188`: "保证无死锁".
  - `implementation_summary.md:482`: "어떠한 교착 상태 없이".
- Expected: 동일 위험은 모든 주요 문서에서 같은 강도로 표현되어야 한다.
- Actual: 문서별 위험 강도가 다르다.
- Impact: 운영 의사결정자가 어떤 문서를 읽느냐에 따라 상반된 판단을 하게 된다.
- Suggested Fix: `spec.md`와 `DESIGN_DECISIONS.md`의 Accepted Risk 문구를 README 및 구현 요약까지 전파한다.
- Re-audit Method: 다국어 support matrix와 구현 요약의 동시성 섹션을 전수 검색한다.
- Owner: Architect

## 9. Required Fixes Before PASS

1. `test_static_js_inner_html_xss_protection()`이 `html` 또는 `errorHtml` 변수 대입을 무조건 건너뛰지 않도록 수정한다. 최소 기준은 `let html =`와 `html +=` 템플릿 리터럴의 모든 `${...}` 보간 검증이다.
2. `escapeHtml(parkName)` 제거, `escapeHtml(targetName)` 제거, `escapeHtml(data.error)` 제거 같은 mutation에서 테스트가 실패하는지 확인한다.
3. DOM 경계 검증을 주장하려면 jsdom 또는 브라우저 기반 테스트로 fetch mock, 버튼 클릭, modal `innerHTML` sink를 실행 검증한다. 그 전까지는 문서 표현을 "helper 정합성 + 제한적 정적 스캔"으로 낮춘다.
4. `README.md` 전 언어, `implementation_summary.md`, `CHANGELOG.md`에서 "보장", "어떠한 교착 상태 없이", "완전 예방", "완전 종식", "保证无死锁" 같은 실 DB 미검증 범위 초과 표현을 조건부 설계 표현으로 낮춘다.
5. PostgreSQL/MySQL을 Target Production으로 유지하려면 실 DB row-lock/deadlock smoke 또는 부하 테스트를 추가한다. 즉시 추가하지 않는다면 모든 운영 문서에 동일한 Accepted Risk 세부 조건을 전파한다.
6. `tests/test_regression.py`의 "브라우저 DOM 렌더링 시 XSS가 성립하지 않음", "100% 그린 패스" 등 감사 범위보다 강한 주석을 실제 검증 범위에 맞게 낮춘다.

## 10. Accepted Risks

| Risk | Status | Owner | Expiry / Recheck |
| --- | --- | --- | --- |
| 실제 브라우저 DOM E2E 미수행 | **Not Accepted for PASS** | Coder / Auditor | XSS sink mutation test 또는 jsdom/브라우저 테스트 추가 전까지 HOLD |
| PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증 | **Accepted Risk in `spec.md` and `DESIGN_DECISIONS.md`, documentation drift remains** | Project Lead Architect / Eunho Lim | 프로덕션 DB 이주 완료 및 다중 스레드 부하/교착 검증 최초 수행 시 만료 |
| SQLite multi-worker `Database Locked` 가능성 | **Accepted Risk** | Project Lead Architect / Eunho Lim | DAU 100명 초과, 초당 DB 쓰기 10회 초과, 또는 locked error 주 3회 이상 감지 시 PostgreSQL 전환 |

## 11. Needs Spec Clarification

- 정적 Regex 기반 XSS 스캔을 이번 Phase의 최종 보안 게이트로 인정할지, 아니면 DOM/jsdom/브라우저 기반 sink 실행 검증을 필수로 요구할지 명확히 해야 한다.
- PostgreSQL/MySQL "Target Production" 판정을 실 DB 통합 테스트 없이 Accepted Risk 문서화만으로 유지할지, 아니면 CI 또는 수동 검증 절차를 필수 게이트로 둘지 명확히 해야 한다.
- 문서에서 "완전 해결", "완전 차단" 같은 표현을 과거 특정 결함의 코드 경로에 한정해 허용할지, 운영 보증처럼 읽힐 가능성이 있으면 전부 조건부 표현으로 제한할지 기준이 필요하다.

## 12. Re-audit Checklist

- [ ] `venv/bin/python -m pytest -q`
- [ ] `venv/bin/python -m pytest -q -W error`
- [ ] `git diff --check`
- [ ] `git diff --cached --check`
- [ ] `DATABASE_URL=postgresql://...` 및 `SQLALCHEMY_DATABASE_URI=postgresql://...` 설정 smoke
- [ ] `venv/bin/python -c "import psycopg2"` driver smoke
- [ ] `escapeHtml(parkName)` 제거 mutation에서 XSS 테스트 실패 확인
- [ ] `escapeHtml(targetName)` 제거 mutation에서 XSS 테스트 실패 확인
- [ ] `contentDiv.innerHTML = html` builder의 `let html` 및 `html +=` 보간 추적 확인
- [ ] `rg -n "완벽|완전|어떠한 교착|guarantee|completely|完美|保证无死锁|保證無死鎖|deadlock-free" README.md spec.md DESIGN_DECISIONS.md implementation_summary.md CHANGELOG.md BUILD_GUIDE.md lessons_learned.md`
- [ ] PostgreSQL/MySQL 실 DB row-lock/deadlock 테스트 수행 또는 모든 운영 문서에 Accepted Risk 세부 조건 반영 확인
- [ ] `run.py` 외부 bind fail-closed 및 production secret fail-closed smoke 재실행

## 13. Final Decision

**HOLD**

67번 HOLD 항목 중 PostgreSQL env/driver 경로와 lost-update 회귀 테스트 판별력은 현재 증거 기준으로 해소됐다. 개발 서버 외부 bind, production debug/secret 보안 가드도 계속 유효하다. 기본 테스트와 whitespace 게이트도 통과한다.

그러나 PASS로 전환하기에는 다음 Major 항목이 남아 있다.

- XSS 정적 스캔이 `innerHTML = html` builder 변수의 정의 및 누적 보간을 추적하지 못한다.
- 테스트와 일부 주석/문서가 실제 DOM sink 실행 검증보다 강한 보안 보증처럼 읽힌다.
- PostgreSQL/MySQL 실 DB 미검증 Accepted Risk와 다국어 README/구현 요약의 deadlock-free 보증 표현이 충돌한다.

따라서 이번 재감사의 최종 판정은 **HOLD**이며, 다음 재감사는 XSS builder 변수 mutation 테스트와 동시성 문서 표현 정렬을 우선 확인해야 한다.
