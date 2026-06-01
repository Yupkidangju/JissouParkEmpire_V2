# D3D Audit Report - audit_report_80.md

## 0. 감사 요약

- 감사 기준: `AI_AUDIT_DOC_STANDARD.md`
- 감사 방식: 재감사, 구현 중심 3-Pass 감사
- 감사 대상 경로: `/mnt/Projects_SSD/python/JissouParkEmpire`
- 직전 감사 문서: `audit_report_79.md`
- 새 보고서 번호: `audit_report_80.md`
- 감사일: 2026-06-02
- 최종 판정: **HOLD**

79번 재감사의 주요 차단 사유였던 `BUILD_GUIDE.md` Gunicorn `0.0.0.0:8000` 노출 안내와 `app/routes/game_routes.py`의 주석 들여쓰기 회귀는 현재 트리에서 해소됐다. `BUILD_GUIDE.md`와 `run.py` 모두 Nginx 뒤 Gunicorn bind를 `127.0.0.1:8000`으로 안내하며, TOCTOU/AP 환불 주석도 실제 제어 흐름과 같은 들여쓰기 수준으로 복구됐다.

구현 실행 게이트도 양호하다. `pytest`, `-W error`, `py_compile`, `git diff --check`, DB 설정 smoke, SQLite PRAGMA smoke, 서버 바인딩 smoke, XSS mutation smoke가 모두 통과했다.

그러나 최종 PASS로 전환할 수는 없다. 감사 산출물과 modified 파일 추적성이 아직 정리되지 않았고, README 다국어 섹션에는 한국어에서 완화된 동시성 보증 표현이 영어/일본어/번체/간체 섹션에 강한 표현으로 남아 있다. 실제 PostgreSQL/MySQL row-lock/deadlock E2E가 수행되지 않은 상태에서 `strongly prevent`, `高度預防`, `高度预防` 계열 표현은 Accepted Risk와 충돌한다. required docs 파일명 authority, CI 부재, 실제 RDBMS/DOM E2E residual risk도 계속 남아 있다.

## 1. Audit Scope

### 1.1 포함 범위

- 감사 표준: `AI_AUDIT_DOC_STANDARD.md`
- 직전 감사: `audit_report_79.md`
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
- Gunicorn 실제 기동 및 포트 노출 실측: 문서/설정 정합성 감사와 `run.py` smoke로 대체
- `.antigravitycli/`, `stitch_shitsiseki_empire_ui_refactor/`: 현재 감사 대상 변경 범위 밖

## 3. 직전 감사 요청사항 재확인

79번 보고서의 PASS 전 요구사항은 다음이었다.

1. `BUILD_GUIDE.md`의 Gunicorn bind 주소를 Nginx reverse proxy 구성과 맞게 loopback으로 정렬
2. `run.py` docstring의 Gunicorn 예시도 동일한 배포 경계로 정렬
3. `audit_report_73.md`-`audit_report_79.md` 및 현재 modified 파일들의 추적성 정책 정리
4. `app/routes/game_routes.py:1186`의 과잉 들여쓰기 주석 정렬
5. required docs 파일명 authority 결정
6. `BUILD_GUIDE.md` quickstart의 `python` 명령 의존 정리
7. 실제 PostgreSQL/MySQL E2E와 브라우저/jsdom DOM XSS E2E 수행 또는 residual risk 유지

### 3.1 80번 재감사 판정 매트릭스

| 79번 요구사항 | 80번 상태 | 판정 |
| --- | --- | --- |
| Gunicorn bind loopback 정렬 | `BUILD_GUIDE.md:100`, `run.py:8`, `BUILD_GUIDE.md:154` 모두 `127.0.0.1:8000` 경계로 정렬 | **Verified** |
| `run.py` docstring 정렬 | `gunicorn --bind 127.0.0.1:8000 "run:app"`로 정렬 | **Verified** |
| 감사 산출물/작업트리 추적성 | `audit_report_73.md`-`audit_report_79.md` untracked, 15개 tracked 파일 modified | **Needs Fix / HOLD** |
| `game_routes.py` 주석 들여쓰기 | `app/routes/game_routes.py:1186`이 `if`와 같은 레벨로 복구 | **Verified** |
| required docs 파일명 authority | `IMPLEMENTATION_SUMMARY.md`, `LESSONS_LEARNED.md`는 여전히 없음 | **Needs Spec Clarification** |
| `BUILD_GUIDE.md` quickstart `python` 의존 | 현재 호스트에서 `python` 없음, 문서에는 `python -m venv`, `python run.py` 유지 | **Needs Fix** |
| 실제 RDBMS/DOM E2E | 미수행, Accepted/Known Residual Risk 유지 | **Accepted Risk / Residual Risk** |

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
    - `?? audit_report_79.md`
  - `git diff --stat`: 15 files changed, 203 insertions, 207 deletions
- Expected: PASS 전에는 감사 대상 변경과 감사 보고서의 보존/추적 정책이 명확해야 한다.
- Actual: 변경 파일과 감사 보고서가 여전히 untracked/modified 상태다.
- Impact: 이후 재감사에서 어떤 변경이 실제 구현 수정이고 어떤 변경이 감사 대응인지 구분하기 어렵다. 감사 증거의 immutable chain이 약하다.
- Suggested Fix: 감사 보고서 73-80 및 현재 변경 파일을 커밋, 별도 브랜치, 또는 명시적 immutable archive 정책으로 정리한다.
- Re-audit Method: `git status --short`, `git diff --stat`, 최신 `audit_report_*.md` 연속성 확인.

## [IMP-F002] 79번 Gunicorn 외부 노출 문서 회귀는 해소됐다

- Pass: Implementation Compliance
- Pattern: Build Guide / Runtime Entry Point / Deployment Boundary
- Area: `BUILD_GUIDE.md`, `run.py`
- Severity: Info
- Status: Verified
- Summary: 79번에서 HOLD로 분류한 `BUILD_GUIDE.md`의 `--bind 0.0.0.0:8000` 회귀는 현재 `127.0.0.1:8000`으로 되돌아와 Nginx reverse proxy 경계와 정렬됐다.
- Evidence:
  - `BUILD_GUIDE.md:98`-`BUILD_GUIDE.md:104`:
    - `ExecStart=/opt/jissou-park/venv/bin/gunicorn \`
    - `--workers 2 \`
    - `--bind 127.0.0.1:8000 \`
    - `"run:app"`
  - `BUILD_GUIDE.md:154`: `proxy_pass http://127.0.0.1:8000;`
  - `run.py:8`: `gunicorn --bind 127.0.0.1:8000 "run:app"  # Nginx 뒤에서 사용하는 프로덕션 서버`
  - `rg -n "0\\.0\\.0\\.0:8000|127\\.0\\.0\\.1:8000|gunicorn" BUILD_GUIDE.md run.py README.md` 결과에서 `0.0.0.0:8000`은 발견되지 않음.
- Expected: Nginx reverse proxy 구성에서는 Gunicorn이 loopback에만 바인딩되어야 한다.
- Actual: 문서와 `run.py` 예시가 loopback으로 정렬됐다.
- Impact: 79번의 배포 문서 보안 회귀는 해소됐다.
- Suggested Fix: 없음.
- Re-audit Method: Gunicorn bind 문자열 검색과 BUILD_GUIDE/Nginx proxy 대조.

## [IMP-F003] `app/routes/game_routes.py` 주석 들여쓰기 회귀는 해소됐다

- Pass: Implementation Compliance
- Pattern: Readability / Comment Hygiene
- Area: `app/routes/game_routes.py`
- Severity: Info
- Status: Verified
- Summary: 79번에서 지적한 TOCTOU/AP 환불 주석의 과잉 들여쓰기가 복구되어 실제 `if` 제어 흐름과 같은 레벨에 위치한다.
- Evidence:
  - `app/routes/game_routes.py:1185`: `# 락 대기 후 멸망 상태 재검증 (TOCTOU 방지)`
  - `app/routes/game_routes.py:1186`: `# [v1.8.9] AP 환불 정합성...`
  - `app/routes/game_routes.py:1187`: `if park.is_destroyed or target.is_destroyed:`
  - `py_compile` 통과.
- Expected: 보안/트랜잭션 주석은 실제 제어 흐름과 같은 들여쓰기 수준에 있어야 한다.
- Actual: 같은 수준으로 정렬됐다.
- Impact: 코드 독해와 감사 가능성이 개선됐다.
- Suggested Fix: 없음.
- Re-audit Method: 해당 라인 수동 확인 및 `py_compile`.

## [IMP-F004] README 다국어 섹션에 동시성 과보증 표현이 남아 있다

- Pass: Implementation Compliance
- Pattern: User-Facing Documentation / Claim Strength Alignment
- Area: `README.md`
- Severity: Major
- Status: Needs Fix / Hold
- Summary: 한국어 동시성 매트릭스는 `위험을 낮추는 방향`과 Accepted Risk를 함께 명시해 완화됐지만, 영어/일본어/번체/간체 섹션에는 실제 RDBMS E2E 미수행 상태와 충돌하는 강한 표현이 남아 있다.
- Evidence:
  - `README.md:57`: 한국어는 `교착 상태(Deadlock) 위험을 낮추는 방향이지만, 실제 검증은 별도 Accepted Risk 범주로 관리합니다.`로 완화됨.
  - `README.md:98`: 영어는 `strongly prevent deadlocks and support concurrency`라고 표현.
  - `README.md:131`: 일본어는 `強力に連動し, デッドロックを高度に防ぐ`라고 표현.
  - `README.md:163`: 번체는 `強力結合, 高度預防死鎖`라고 표현.
  - `README.md:195`: 간체는 `强力结合, 高度预防死锁`라고 표현.
  - 같은 줄들에서 모두 `PostgreSQL/MySQL Real Instance Unverified` 또는 `Accepted Risk`도 함께 적고 있어 문장 내부에서 보증 강도와 검증 상태가 충돌한다.
  - 영어 FAQ에도 강한 표현이 남아 있다:
    - `README.md:278`: `highly blocking zombie actions and TOCTOU flaws`
    - `README.md:280`: `Resource leakage is highly prevented`
    - `README.md:282`: `strongly blocks duplicate records`, `highly prevent deadlocks`, `ensuring no contradictory states occur`
- Expected: 실제 PostgreSQL/MySQL row-lock/deadlock E2E가 없는 상태에서는 모든 언어 섹션이 `위험 감소`, `설계상 완화`, `Accepted Risk` 수준으로 동일하게 정렬되어야 한다.
- Actual: 한국어와 일부 release note는 완화됐지만 다른 언어 섹션에는 강한 보증 표현이 남아 있다.
- Impact: README는 사용자-facing 문서이므로, 다국어 섹션 간 보안/동시성 보증 수준이 다르면 운영자가 실제 검증 범위를 오해할 수 있다.
- Suggested Fix: 영어/일본어/번체/간체 섹션의 동시성 매트릭스와 FAQ를 한국어 기준과 같은 강도로 낮춘다. 예: `strongly prevent` -> `reduce the risk of`, `高度預防` -> `降低風險`, `确保/ensuring` -> `helps avoid`.
- Re-audit Method:
  - `rg -n "strongly|highly|高度|強力|强力|保证|確保|보장|確実|완전|완치|원천" README.md`
  - 한국어/영어/일본어/번체/간체 동시성 매트릭스 수동 대조.

## [IMP-F005] required documentation 파일명 authority는 여전히 불명확하다

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

## 5. Pass 2: Debug / Engineering Quality Findings

## [DBG-F001] Python 테스트와 warning-as-error 게이트는 통과한다

- Pass: Debug / Engineering Quality
- Pattern: Deterministic Test Gate
- Area: pytest
- Severity: Info
- Status: Verified
- Evidence:
  - `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q`
  - 결과: `7 passed in 0.34s`
  - `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q -W error`
  - 결과: `7 passed in 0.34s`
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

## [SEC-F001] 개발 서버 직접 실행의 loopback/fail-closed 경계는 통과한다

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
- Impact: 개발 서버 직접 실행 경계는 통과다.
- Suggested Fix: 없음.
- Re-audit Method: 동일 서버 smoke 재실행.

## [SEC-F002] production DEBUG 강제 off와 secret 경계는 smoke 범위에서 확인됐다

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

## [SEC-F003] XSS guard와 mutation-sensitive 테스트는 현재 확인된 sink를 잡는다

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

## [SEC-F004] 실제 PostgreSQL/MySQL row-lock/deadlock E2E는 아직 Accepted Risk다

- Pass: Security
- Pattern: Concurrency Boundary / External DB Validation
- Area: PostgreSQL/MySQL production target
- Severity: Major
- Status: Accepted Risk
- Evidence:
  - `README.md:57`: PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증을 Accepted Risk로 문서화
  - PostgreSQL URI smoke와 driver import는 수행했지만 실제 DB 연결/부하/deadlock 테스트는 수행하지 않음
- Expected: Target Production 표현을 최종 PASS로 올리려면 실제 대상 DB에서 동시성 E2E가 필요하다.
- Actual: Accepted Risk로 유지된다.
- Impact: 운영 DB에서 lock timeout/deadlock 가능성을 배제할 수 없다.
- Suggested Fix: PostgreSQL/MySQL 테스트 인스턴스와 Gunicorn 다중 worker 부하 테스트를 추가한다.
- Re-audit Method: 실제 DB E2E 및 deadlock/lock timeout 로그 확인.

## 7. Cross-Pass Conflicts

## [XPF-F001] 구현 게이트는 통과하지만 README 다국어 보증 강도는 실제 검증 범위와 충돌한다

- Pass: Cross-Pass
- Severity: Major
- Status: Hold
- Summary: 로컬 테스트와 smoke는 통과하지만 실제 PostgreSQL/MySQL row-lock/deadlock E2E는 없다. 그럼에도 README 영어/일본어/번체/간체 섹션은 강한 deadlock 예방 표현을 유지한다.
- Evidence:
  - 테스트/설정 smoke: pass
  - 실제 RDBMS E2E: 미수행
  - `README.md:98`, `README.md:131`, `README.md:163`, `README.md:195`: 강한 예방 표현과 Accepted Risk가 같은 셀에 공존
- Impact: 문서-구현-테스트 authority가 충돌한다.

## [XPF-F002] 79번 보안 회귀는 해소됐지만 추적성 미정리로 PASS 근거가 약하다

- Pass: Cross-Pass
- Severity: Major
- Status: Hold
- Summary: Gunicorn bind와 주석 들여쓰기는 수정됐으나, 변경 파일과 감사 보고서가 여전히 untracked/modified 상태다.
- Impact: PASS 판정 시점의 immutable evidence가 부족하다.

## 8. Required Fixes Before PASS

1. `audit_report_73.md`-`audit_report_80.md` 및 현재 modified 파일들의 추적성 정책을 정리한다.
2. README 영어/일본어/번체/간체 섹션의 동시성/보안 과보증 표현을 한국어 섹션과 같은 Accepted Risk 강도로 낮춘다.
3. `IMPLEMENTATION_SUMMARY.md`/`implementation_summary.md`, `LESSONS_LEARNED.md`/`lessons_learned.md` 파일명 authority를 결정한다.
4. `BUILD_GUIDE.md` quickstart에서 현재 Linux 호스트에 없는 `python` 명령 의존을 `python3` 우선 안내로 정리한다.
5. 실제 PostgreSQL/MySQL E2E와 브라우저/jsdom DOM XSS E2E는 수행하거나 명시적 residual risk로 계속 유지한다.
6. CI/workflow 부재를 수동 gate evidence 정책 또는 최소 CI로 보완한다.

## 9. Accepted Risks

| Risk | Status | Owner | Revisit Trigger |
| --- | --- | --- | --- |
| SQLite multi-worker `Database Locked` 가능성 | Accepted Risk | Project Lead Architect / Eunho Lim | DAU 100명 초과, 초당 DB 쓰기 10회 초과, locked error 주 3회 이상 |
| 실제 PostgreSQL/MySQL row-lock/deadlock E2E 미수행 | Accepted Risk | Project Lead Architect / Eunho Lim | 실제 RDBMS 이주, lock timeout/deadlock 주 1회 이상 |
| 실제 브라우저/jsdom DOM XSS E2E 미수행 | Known Residual Risk | Coder / Auditor | 브라우저/jsdom 테스트 추가 전까지 |
| CI/workflow 부재 | Known Operational Risk | Maintainer | CI 도입 또는 수동 gate evidence 아카이브 |

## 10. Needs Spec Clarification

1. 감사 보고서가 untracked 상태로 누적될 때 PASS 전 필수 커밋이 필요한지, 별도 archive 보존으로 충분한지 기준이 필요하다.
2. historical changelog와 README release note의 강한 표현을 현재 감사 기준으로 모두 낮출지, 당시 릴리스 기록으로 보존할지 기준이 필요하다.
3. required documentation 파일명의 대소문자 표준을 결정해야 한다.
4. Node.js 정적/결합 XSS 검증을 충분한 gate로 볼지, 브라우저/jsdom DOM E2E를 필수로 볼지 결정해야 한다.
5. 실제 PostgreSQL/MySQL E2E 전에도 다국어 README에서 `Target Production` 표현을 유지할 수 있는지, `Target Production Design / Accepted Risk`로 제한할지 결정해야 한다.

## 11. Re-audit Checklist

- [x] `AI_AUDIT_DOC_STANDARD.md` 확인
- [x] 최신 감사 보고서 번호 확인: `audit_report_79.md` 이후 `audit_report_80.md`
- [x] `test -f audit_report_80.md`: 기존 파일 없음 확인
- [x] 직전 감사 `audit_report_79.md` HOLD 사유 확인
- [x] `git status --short`
- [x] `git diff --stat`
- [x] `git diff --name-only`
- [x] `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q`: `7 passed in 0.34s`
- [x] `env PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -q -W error`: `7 passed in 0.34s`
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
- [x] README 다국어 혼입 및 hard-boundary 표현 재검색
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

79번 대비 긍정적인 변화도 있다.

- `BUILD_GUIDE.md`와 `run.py`의 Gunicorn bind가 `127.0.0.1:8000`으로 정렬되어 79번의 외부 노출 회귀가 해소됐다.
- `app/routes/game_routes.py`의 TOCTOU/AP 환불 주석 들여쓰기 회귀가 해소됐다.
- `run.py` 배너와 docstring 버전은 `v1.8.9`로 정렬되어 있다.

하지만 PASS 차단 사유가 남아 있다.

1. 감사 보고서와 modified 파일 추적성이 아직 정리되지 않았다.
2. README 영어/일본어/번체/간체 섹션에 실제 RDBMS E2E 미수행과 충돌하는 과보증 표현이 남아 있다.
3. required documentation 파일명의 대소문자 authority가 불명확하다.
4. `BUILD_GUIDE.md` quickstart는 현재 Linux 호스트에 없는 `python` 명령을 우선 사용한다.
5. 실제 RDBMS row-lock/deadlock E2E와 브라우저 DOM XSS E2E는 여전히 residual risk다.

따라서 80번 재감사의 최종 판정은 **HOLD**다. 소스 코드와 기존 문서는 수정하지 않았고, 감사 결과 문서 `audit_report_80.md`만 생성했다.
