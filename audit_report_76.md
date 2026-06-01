# D3D Audit Report

## 0. 메타데이터

| 항목 | 내용 |
| --- | --- |
| 감사 문서 기준 | `AI_AUDIT_DOC_STANDARD.md` |
| 감사 유형 | 재감사 / 구현 중심 상세 감사 |
| 감사 산출물 | `audit_report_76.md` |
| 직전 감사 산출물 | `audit_report_75.md` |
| 감사 일자 | 2026-06-01 |
| 감사 원칙 | 기존 소스, 설정, 문서, 감사 문서 수정 없음. 본 보고서만 신규 생성. |
| 최종 판정 | **HOLD** |

## 1. Audit Scope

이번 재감사는 `AI_AUDIT_DOC_STANDARD.md`의 3-pass 모델을 기준으로 현재 구현, 테스트, 문서, 보안 경계, 직전 감사 산출물의 정합성을 다시 검증했다.

| 범위 | 확인 대상 |
| --- | --- |
| 감사 기준 | `AI_AUDIT_DOC_STANDARD.md` |
| 직전 감사 이력 | `audit_report_75.md` |
| 프로젝트 규칙 | `AGENTS.md` |
| 마스터 문서 | `spec.md`, `designs.md`, `implementation_summary.md`, `DESIGN_DECISIONS.md` |
| 운영 문서 | `README.md`, `CHANGELOG.md`, `BUILD_GUIDE.md`, `lessons_learned.md`, `audit_roadmap.md` |
| 구현 코드 | `app/config.py`, `run.py`, `app/__init__.py`, `app/models.py`, `app/game_engine.py`, `app/npc_engine.py`, `app/battle_engine.py`, `app/routes/game_routes.py`, `app/static/js/game.js` |
| 회귀 테스트 | `tests/test_regression.py`, `tests/conftest.py` |
| 실행 게이트 | pytest, warnings-as-errors, whitespace, py_compile, DB 설정 smoke, 개발 서버 smoke, XSS mutation smoke |
| 보안 경계 | XSS sink, 외부 바인딩 fail-closed, production secret/debug fail-closed, SQLite/RDBMS 동시성 Accepted Risk |

## 2. Excluded Scope

| 제외 항목 | 사유 |
| --- | --- |
| 소스 수정 | 사용자가 명시적으로 "수정은 하지 않습니다"라고 요청했다. |
| 기존 문서 수정 | 본 감사는 재감사 보고서 작성만 수행한다. |
| 실제 PostgreSQL/MySQL 인스턴스 기반 row-lock/deadlock E2E | 현재 로컬 환경에서 실제 DB 서버를 구성하지 않았다. 문서상 Accepted Risk로 분류되어 있다. |
| 실제 브라우저/jsdom DOM 실행 기반 XSS E2E | 현재 검증은 pytest, Node.js escape helper 교차 검증, 정적 sink 스캔, in-memory mutation smoke 중심이다. |
| 원격 CI 실행 | `.github/**`, workflow, ci 파일이 검색되지 않았다. |
| `.antigravitycli/`, `stitch_shitsiseki_empire_ui_refactor/` | 감사 시작 전부터 존재한 untracked 디렉터리이며 본 감사 범위 밖이다. |

## 3. Evidence Summary

### 3.1 감사 기준 확인

| 기준 | 증거 |
| --- | --- |
| 3-pass 감사 모델 | `AI_AUDIT_DOC_STANDARD.md:117-120`: Implementation, Debug/Engineering, Security pass 요구 |
| 필수 출력 | `AI_AUDIT_DOC_STANDARD.md:63-106`: 감사 요약, 범위, pass별 finding, accepted risks, final decision 요구 |
| Accepted Risk 조건 | `AI_AUDIT_DOC_STANDARD.md:203`, `AI_AUDIT_DOC_STANDARD.md:208`: owner, 사유, 만료 조건, 재검토 조건 필요 |
| Phase Gate | `AI_AUDIT_DOC_STANDARD.md:232-249`: Major는 수정 또는 Accepted Risk 필요, 최종 판정은 PASS/PASS WITH KNOWN RISKS/HOLD/REWORK |

### 3.2 현재 작업트리와 보고서 번호

| 명령 | 결과 | 감사 해석 |
| --- | --- | --- |
| `ls -1 audit_report_*.md` | `audit_report_75.md`까지 존재 | 신규 산출물은 `audit_report_76.md` |
| `test -f audit_report_76.md` | exit 1 | 작성 전 동일 파일 없음 |
| `git status --short` | `M CHANGELOG.md`, `M DESIGN_DECISIONS.md`, `M README.md`, `M lessons_learned.md`, `M tests/test_regression.py`, `?? audit_report_73.md`, `?? audit_report_74.md`, `?? audit_report_75.md`, 기타 untracked 디렉터리 | 감사 시작 전부터 수정/미추적 항목이 존재한다. 이번 보고서 작성 후 `audit_report_76.md`도 untracked가 된다. |
| `git diff --stat` | 5 files changed, 22 insertions, 22 deletions | 직전 감사 대응으로 보이는 문서/테스트 표현 정리 변경이 존재한다. |

### 3.3 현재 변경 diff 요약

| 파일 | 관찰 |
| --- | --- |
| `CHANGELOG.md` | `100% 동기화`, `100% 재사용`, `100% 호환` 표현이 완화되었다. |
| `DESIGN_DECISIONS.md` | `100% 재사용`, `100% 호환`, `100% 사망` 표현이 완화되었다. |
| `README.md` | 간체 FAQ의 `or` 혼입 1건이 `或`로 정리되었다. |
| `lessons_learned.md` | XSS 및 동시성 회고 표현 다수가 조건부/완화 표현으로 낮아졌다. |
| `tests/test_regression.py` | 테스트 주석의 `완벽히`, `완전히`, `철저히`, `온전히` 계열 표현이 일부 완화되었다. |

### 3.4 실행 게이트

| 명령 | 결과 | 감사 해석 |
| --- | --- | --- |
| `venv/bin/python -m pytest -q` | `7 passed in 0.33s` | 회귀 테스트 통과 |
| `venv/bin/python -m pytest -q -W error` | `7 passed in 0.33s` | warning 승격 조건 통과 |
| `git diff --check` | exit 0 | 작업트리 whitespace gate 통과 |
| `git diff --cached --check` | exit 0 | staged whitespace gate 통과 |
| `venv/bin/python -m py_compile app/*.py run.py tests/*.py` | exit 0 | Python 문법 컴파일 통과 |
| `DATABASE_URL=postgresql://...` 설정 smoke | `postgresql://u:p@localhost:5432/jissou_audit` | `DATABASE_URL` 설정 경로 정상 |
| `SQLALCHEMY_DATABASE_URI=postgresql://...` 설정 smoke | `postgresql://u:p@localhost:5432/jissou_uri` | `SQLALCHEMY_DATABASE_URI` 우선 경로 정상 |
| `venv/bin/python -c "import psycopg2"` | `2.9.12 (dt dec pq3 ext lo64)` | PostgreSQL 드라이버 존재 |
| SQLite PRAGMA smoke | `wal`, `5000` | `journal_mode=WAL`, `busy_timeout=5000` 주입 확인 |
| `FLASK_ENV=production DEBUG=true SECRET_KEY=prod-secret ...` | `False`, `11` | production에서 DEBUG 강제 off 및 secret 반영 확인 |
| `timeout 3 env SECRET_KEY=smoke-secret venv/bin/python run.py` | `127.0.0.1:5000`, debug on, timeout 124 | loopback 개발 서버 경로 동작 |
| `timeout 3 env FLASK_RUN_HOST=0.0.0.0 SECRET_KEY=smoke-secret venv/bin/python run.py` | ValueError | 비루프백 외부 바인딩 기본 차단 |
| `timeout 3 env FLASK_RUN_HOST=0.0.0.0 ALLOW_UNSAFE_DEV_SERVER=1 SECRET_KEY=custom-key venv/bin/python run.py` | `0.0.0.0`, debug off, timeout 124 | 명시 opt-in 시에도 debug off 유지 |
| `command -v python` | exit 1 | 현재 shell에는 `python` alias 없음 |
| `command -v python3` | `/usr/bin/python3` | `python3` 경로 존재 |
| `rg --files -g '.github/**' -g '*workflow*' -g '*ci*'` | exit 1 | CI/workflow 파일 미확인 |

### 3.5 XSS mutation smoke

`app/static/js/game.js`를 파일에 쓰지 않고 메모리에서 변형했다. `tests/test_regression.py::test_static_js_inner_html_xss_protection`을 import하고 `open()`만 monkeypatch하여 현재 정적 스캔이 guard 제거를 잡는지 확인했다.

| 변형 | 결과 |
| --- | --- |
| 현재 원본 | `current PASS` |
| `escapeHtml(parkName)` 제거 | `FAILS_AS_EXPECTED` |
| `escapeHtml(targetName)` 제거 | `FAILS_AS_EXPECTED` |
| `escapeHtml(data.error || I18N.scoutFail)` 제거 | `FAILS_AS_EXPECTED` |
| `escapeHtml(err.message)` 제거 | `FAILS_AS_EXPECTED` |

### 3.6 감사 중 실패/보정한 명령

| 실패 명령 유형 | 결과 | 해석 |
| --- | --- | --- |
| inline Python regex mutation smoke 1차 시도 | shell quoting 오류 | 감사 harness 작성 실수이며 프로젝트 결함으로 분류하지 않는다. 이후 import+open monkeypatch 방식으로 동일 목적을 검증했다. |
| `tests/test_regression.py` 직접 import without `SECRET_KEY` | `ValueError: SECRET_KEY ... 누락` | 프로젝트의 fail-closed 정책이 import 단계에서 작동했다. 이후 `SECRET_KEY=smoke-secret` 환경으로 재실행했다. |
| `rg ... IMPLEMENTATION_SUMMARY.md ...` | 대문자 파일 없음으로 exit 2 | 감사자가 대문자 파일명도 함께 검색한 결과다. `AI_AUDIT_DOC_STANDARD.md`와 로컬 `AGENTS.md`의 Required Files는 현재 소문자 `implementation_summary.md`를 기준으로 하므로 독립 결함으로 분류하지 않는다. |

## 4. Pass 1: Implementation Compliance Findings

## [IMP-076-F001] 감사 산출물과 문서/테스트 수정분이 아직 추적성 정리 전 상태임

- Pass: Implementation
- Pattern: Documentation artifact traceability
- Area: Git state / audit history
- Severity: **Major**
- Status: **Needs Fix**
- Re-audit Mapping: `IMP-075-F001`, `DBG-075-F004`
- Summary:
  - 구현 실행 게이트는 통과하지만 최신 감사 보고서와 문서/테스트 수정분이 git 기준으로 정리되지 않았다.
- Evidence:
  - `git status --short`: `M CHANGELOG.md`, `M DESIGN_DECISIONS.md`, `M README.md`, `M lessons_learned.md`, `M tests/test_regression.py`
  - `git status --short`: `?? audit_report_73.md`, `?? audit_report_74.md`, `?? audit_report_75.md`
  - 이번 감사로 `audit_report_76.md`도 신규 untracked 산출물이 된다.
- Expected:
  - 감사 기준 산출물과 구현/문서 변경은 의도와 추적 상태가 명확해야 한다.
- Actual:
  - 수정된 문서·테스트와 최신 감사 보고서들이 아직 추적성 정리 전 상태다.
- Impact:
  - clean base, 수정 의도, 최신 canonical 감사 판정을 구분하기 어렵다.
  - 추적 파일만 기준으로 검토하면 최신 HOLD 판정과 관련 문서 개선 내용을 놓칠 수 있다.
- Suggested Fix:
  - 의도한 변경이라면 관련 문서·테스트·감사 보고서를 추적 대상으로 정리한다.
  - 의도하지 않은 변경이면 별도 사용자 확인 후 처리한다.
- Re-audit Method:
  - `git status --short`로 최신 감사 보고서와 수정 파일의 추적 상태를 확인한다.
- Owner:
  - Human / Auditor

## [IMP-076-F002] 런타임 시작 배너 버전이 문서 버전과 불일치함

- Pass: Implementation
- Pattern: Runtime/documentation drift
- Area: `run.py`, release metadata
- Severity: **Major**
- Status: **Needs Fix**
- Summary:
  - 현재 문서의 기준 버전은 `v1.8.9`인데, 실제 서버 시작 배너는 `v0.1.0`을 출력한다.
- Evidence:
  - `spec.md:3`: `문서 버전: v1.8.9`
  - `CHANGELOG.md:12`: `## [1.8.9] - 2026-06-01`
  - `implementation_summary.md:3`: `문서 버전: v1.8.9`
  - `DESIGN_DECISIONS.md:3`: `문서 버전: v1.8.9`
  - `run.py:52`: `print("  Jissou Park Empire v0.1.0")`
  - 개발 서버 smoke 출력: `Jissou Park Empire v0.1.0`
- Expected:
  - 사용자-facing 런타임 배너 또는 릴리즈 표시가 현재 문서/CHANGELOG 기준과 일치하거나, 별도 앱 내부 프로토콜 버전임을 명확히 설명해야 한다.
- Actual:
  - 런타임은 `v0.1.0`, 문서는 `v1.8.9`로 분리되어 있으며 분리 사유가 명시되지 않았다.
- Impact:
  - 운영자와 감사자가 실행 중인 빌드가 최신 v1.8.9인지 판단하기 어렵다.
  - 배포/재감사 시 "문서상 최신 기능이 실제 실행 바이너리에 반영됐는가"를 혼동할 수 있다.
- Suggested Fix:
  - 중앙 버전 상수를 두고 `run.py`, `spec.md`, `CHANGELOG.md`, `implementation_summary.md`가 같은 값을 참조하도록 정리한다.
  - `v0.1.0`이 앱 내부 프로토콜 버전이라면 배너 라벨을 `App scaffold version` 등으로 분리한다.
- Re-audit Method:
  - `timeout 3 env SECRET_KEY=... venv/bin/python run.py` 출력과 문서 버전 검색 결과를 비교한다.
- Owner:
  - Architect / Coder

## [IMP-076-F003] 절대 보증 표현 정리는 부분 완료됐지만 README 다국어 섹션과 designs/source comments에 과대 보증이 여전히 남아 있음

- Pass: Implementation
- Pattern: SEC-005 style hard-boundary overclaim / documentation drift
- Area: README, designs, comments
- Severity: **Major**
- Status: **Needs Fix**
- Re-audit Mapping: `IMP-075-F002`
- Summary:
  - 직전 지적의 일부 한국어 표현은 완화됐지만, 다국어 README와 `designs.md`, 일부 소스/테스트 주석에는 "완벽/완전/Fully resolved/完全" 계열의 hard-boundary 표현이 여전히 존재한다.
- Evidence:
  - `README.md:290`: `Fully resolved`, `permanently stored`
  - `README.md:318`: 일본어 섹션 `すべて解決`, `完全に遮断`, `完璧に防ぎ`
  - `README.md:320`: 일본어 섹션 `完全に解決`, `完全に排除`, `完全に解放`, `完全に遮断`
  - `README.md:348`, `README.md:376`: 중국어 섹션 `永久`, `完全`, `全方位`
  - `designs.md:354`: `AP 증발 및 누수 완벽 차단`
  - `designs.md:442`: `데드락(Deadlock)이 완벽히 방지`
  - `designs.md:449`: `DEADLOCK-F005`을 `완전히 해소`
  - `designs.md:458`: `영구적인 교착 상태 및 커넥션 풀 고갈을 완전 차단`
  - `designs.md:460`: 실제 RDBMS 이주 시 `완벽한 정합성`과 `완벽하게 보장`
  - `app/config.py:28`: 디버그 노출 위협을 `완벽히 소멸`한다고 주석화
  - `tests/conftest.py:8`, `tests/conftest.py:24`: `완벽한 인메모리 격리`
  - 반대 증거: `README.md:98`, `README.md:131`, `README.md:163`, `README.md:195`, `spec.md:779`, `implementation_summary.md:483-498`은 PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증을 Accepted Risk로 명시한다.
- Expected:
  - 문서와 주석은 구현이 검증한 범위와 Accepted Risk를 구분해야 한다.
  - 실제 RDBMS E2E, 브라우저 DOM E2E, regex 기반 XSS scanner 한계가 남아 있으면 "완전/완벽/fully resolved" 계열의 운영 보증 표현은 낮춰야 한다.
- Actual:
  - 일부 표현은 완화됐지만 다국어 README와 설계 문서에는 아직 검증 범위를 초과하는 보증 문구가 남아 있다.
- Impact:
  - 사용자가 "실 DB/브라우저/모든 동시성 조건에서 완전 해결"로 오해할 수 있다.
  - Accepted Risk와 hard-boundary claim이 충돌한다.
- Suggested Fix:
  - 다국어 README의 v1.8.9 FAQ 표현을 한국어 섹션처럼 "고도 완화/강하게 예방/회귀 테스트 범위 내 검증"으로 낮춘다.
  - `designs.md`와 소스/테스트 주석의 절대 보증 표현도 "현재 검증 범위", "설계상 완화", "Accepted Risk 전제"를 포함하도록 정리한다.
  - 절대 표현 검색 결과에서 게임 내 대사나 대안 라벨은 false positive로 분류하는 기준을 문서화한다.
- Re-audit Method:
  - `rg -n "Fully resolved|fully|completely|perfect|permanent|permanently|complete|완전히|완벽|완전|完全|すべて解決|永久|全方位|彻底|絕對|绝对" ...`
  - 결과를 운영 보증, historical narrative, 게임 대사, 대안 라벨, false positive로 분류한다.
- Owner:
  - Architect / Documentation maintainer

## [IMP-076-F004] README 간체 FAQ의 `or` 혼입은 해소됨

- Pass: Implementation
- Pattern: Multilingual README consistency
- Area: `README.md`
- Severity: **Info**
- Status: **Verified**
- Re-audit Mapping: `IMP-075-F003`
- Evidence:
  - `README.md` diff에서 간체 FAQ의 `轮次同步中断 or 陷入无限循环吗？`가 `轮次同步中断或陷入无限循环吗？`로 정리되었다.
  - `rg -n "\b(and|or|the|to|with|without|fixed|supports?|requirements?)\b" README.md` 결과는 영어 섹션 및 명령/용어 문맥 중심이다.
- Expected:
  - README의 각 언어 섹션은 해당 언어로 자연스럽게 읽혀야 한다.
- Actual:
  - 직전 지적된 간체 FAQ 영어 접속사 혼입은 현재 해소되었다.
- Suggested Fix:
  - 없음.
- Re-audit Method:
  - README 다국어 섹션별 외국어 혼입 검색 및 문맥 검토.
- Owner:
  - Auditor

## [IMP-076-F005] PostgreSQL/MySQL Accepted Risk support matrix 전파는 유지됨

- Pass: Implementation
- Pattern: Accepted Risk documentation
- Area: README/spec/design/implementation summary
- Severity: **Info**
- Status: **Verified**
- Evidence:
  - `README.md:57`, `README.md:98`, `README.md:131`, `README.md:163`, `README.md:195`에 PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증 Accepted Risk가 다국어로 존재한다.
  - `spec.md:779`, `DESIGN_DECISIONS.md:40`, `implementation_summary.md:483`, `implementation_summary.md:494-498`에 owner, 수용 사유, 만료 조건, 재검토 조건 축이 존재한다.
- Expected:
  - Accepted Risk는 위험 설명, 영향 범위, 책임자, 만료 조건, 재검토 조건을 가져야 한다.
- Actual:
  - support matrix 자체는 현재도 충족한다.
- Suggested Fix:
  - 없음. 단, `IMP-076-F003`의 과대 보증 문구는 이 Accepted Risk와 충돌하지 않도록 낮춰야 한다.
- Re-audit Method:
  - support matrix와 Accepted Risk 세부 규격 검색.
- Owner:
  - Auditor

## 5. Pass 2: Debug / Engineering Quality Findings

## [DBG-076-F001] 로컬 테스트와 수동 품질 게이트는 통과함

- Pass: Debug / Engineering Quality
- Pattern: Deterministic local gate
- Area: tests / formatting / compile
- Severity: **Info**
- Status: **Verified**
- Evidence:
  - `venv/bin/python -m pytest -q`: `7 passed in 0.33s`
  - `venv/bin/python -m pytest -q -W error`: `7 passed in 0.33s`
  - `git diff --check`: exit 0
  - `git diff --cached --check`: exit 0
  - `venv/bin/python -m py_compile app/*.py run.py tests/*.py`: exit 0
  - `BUILD_GUIDE.md:315-336`: 수동 품질 게이트 명령과 운영 책임자/실행 주기 문서화
- Expected:
  - 현재 변경 상태에서 테스트, warning gate, whitespace, syntax gate가 재현 가능하게 통과해야 한다.
- Actual:
  - 모두 통과한다.
- Impact:
  - 구현 자체의 현재 로컬 실행 안정성은 양호하다.
- Suggested Fix:
  - 없음.
- Re-audit Method:
  - 동일 명령 재실행.
- Owner:
  - Auditor

## [DBG-076-F002] XSS 정적 스캔은 현재 주요 sink mutation을 잡아내지만 regex 기반 잔여 리스크가 있음

- Pass: Debug / Engineering Quality
- Pattern: Mutation-sensitive security regression
- Area: `tests/test_regression.py`, `app/static/js/game.js`
- Severity: **Minor**
- Status: **Verified with Known Residual Risk**
- Re-audit Mapping: `DBG-075-F002`, `SEC-075-F002`
- Evidence:
  - `app/static/js/game.js:105`: `${escapeHtml(parkName)}`
  - `app/static/js/game.js:133`: `${escapeHtml(data.error || I18N.scoutFail)}`
  - `app/static/js/game.js:136`: `${escapeHtml(err.message)}`
  - `app/static/js/game.js:153`: `${escapeHtml(targetName)}`
  - `tests/test_regression.py:376-433`: `innerHTML` 대입 및 `html` builder 백틱 템플릿을 regex로 전수 스캔한다.
  - in-memory mutation smoke에서 `parkName`, `targetName`, `data.error || I18N.scoutFail`, `err.message` guard 제거가 모두 `FAILS_AS_EXPECTED`로 실패했다.
- Expected:
  - 테스트가 코드 라인 이동에 영향을 받지 않고 현재 shipped XSS sink를 검출해야 한다.
- Actual:
  - 라인 번호 의존성은 제거되었고 현재 알려진 sink 변형은 잡아낸다.
  - 다만 JavaScript AST/data-flow 기반이 아니라 regex 기반이므로 복잡한 변수명, 다중 builder, 런타임 DOM 조립은 별도 사각지대가 될 수 있다.
- Impact:
  - 현재 알려진 sink에 대한 회귀 방어는 동작한다.
  - 브라우저 DOM 실행 관점의 hard security proof는 아니다.
- Suggested Fix:
  - 장기적으로 jsdom/Playwright 또는 JS AST 기반 sink 추적을 도입한다.
- Re-audit Method:
  - `pytest` 재실행 및 guard 제거 mutation smoke 재실행.
- Owner:
  - Coder / Auditor

## [DBG-076-F003] DB 설정과 SQLite PRAGMA 경로는 현재 구현과 smoke 결과가 일치함

- Pass: Debug / Engineering Quality
- Pattern: Runtime config verification
- Area: `app/config.py`, `app/models.py`
- Severity: **Info**
- Status: **Verified**
- Evidence:
  - `app/config.py:60`: `SQLALCHEMY_DATABASE_URI` 또는 `DATABASE_URL` 또는 `sqlite:///game.db` 순으로 DB URI를 결정한다.
  - `app/models.py:533-545`: SQLite 연결 시 `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`을 적용한다.
  - `DATABASE_URL=postgresql://...` smoke 결과: `postgresql://u:p@localhost:5432/jissou_audit`
  - `SQLALCHEMY_DATABASE_URI=postgresql://...` smoke 결과: `postgresql://u:p@localhost:5432/jissou_uri`
  - SQLite PRAGMA smoke 결과: `wal`, `5000`
- Expected:
  - 문서화된 DB 전환 경로와 SQLite 완화 설정이 실제 런타임에서 반영되어야 한다.
- Actual:
  - 설정 경로와 PRAGMA 적용은 현재 확인 범위에서 일치한다.
- Impact:
  - SQLite 기본 실행과 RDBMS 전환 설정의 구현 진입점은 정상이다.
- Suggested Fix:
  - 실제 PostgreSQL/MySQL row-lock/deadlock E2E는 별도 Accepted Risk로 유지한다.
- Re-audit Method:
  - 동일 smoke 명령 재실행.
- Owner:
  - Auditor

## [DBG-076-F004] CI 부재는 수동 품질 게이트 문서로 완화되었으나 자동 차단은 없음

- Pass: Debug / Engineering Quality
- Pattern: Build gate automation
- Area: CI/CD
- Severity: **Minor**
- Status: **Accepted Risk / Known Operational Risk**
- Re-audit Mapping: `DBG-075-F003`
- Evidence:
  - `rg --files -g '.github/**' -g '*workflow*' -g '*ci*'`: exit 1
  - `BUILD_GUIDE.md:315-336`: 수동 품질 게이트 및 자가 진단 운영 지침이 존재한다.
  - `BUILD_GUIDE.md:325-328`: `pytest -q -W error`, `git diff --check`, `git diff --cached --check`, `py_compile` 실행 명령이 명시되어 있다.
- Expected:
  - CI가 없다면 수동 gate의 책임자, 명령, 실행 주기가 문서화되어야 한다.
- Actual:
  - 문서화는 되었지만 자동 PR/commit 차단은 없다.
- Impact:
  - 로컬에서 명령을 실행하지 않으면 regression이 자동으로 차단되지 않는다.
- Suggested Fix:
  - 현재 정책을 유지한다면 Accepted Risk로 두고, 향후 GitHub Actions 등 자동화 도입을 별도 Phase로 잡는다.
- Re-audit Method:
  - CI 파일 검색 및 `BUILD_GUIDE.md` 수동 gate 최신성 검토.
- Owner:
  - Project maintainer

## 6. Pass 3: Security Findings

## [SEC-076-F001] 외부 바인딩과 production debug/secret 경계는 fail-closed로 동작함

- Pass: Security
- Pattern: Network exposure / debug hardening
- Area: `run.py`, `app/config.py`
- Severity: **Info**
- Status: **Verified**
- Re-audit Mapping: `SEC-075-F001`
- Evidence:
  - `run.py:22`: 기본 `FLASK_RUN_HOST`는 `127.0.0.1`
  - `run.py:31-43`: 비루프백 외부 바인딩에서 `ALLOW_UNSAFE_DEV_SERVER` 및 실제 secret 없으면 `ValueError`
  - `run.py:58-62`: 비루프백이면 `run_debug = False`
  - `app/config.py:39-52`: production이면 DEBUG 강제 off 및 secret 누락 시 `ValueError`
  - loopback smoke: `Running on http://127.0.0.1:5000`, debug on, timeout 124
  - 외부 바인딩 smoke: ValueError로 즉시 실패
  - opt-in 외부 바인딩 smoke: `Running on all addresses (0.0.0.0)`, debug off, timeout 124
  - production debug smoke: `False`, secret length `11`
- Expected:
  - Flask 개발 서버가 기본적으로 LAN에 노출되지 않고, 비루프백 노출 시 명시 opt-in 및 debug off가 강제되어야 한다.
- Actual:
  - 현재 확인 범위에서 fail-closed로 동작한다.
- Impact:
  - 개발 서버 디버거 LAN 노출 위험은 기본 경로에서 차단된다.
- Suggested Fix:
  - 없음.
- Re-audit Method:
  - 동일 서버 smoke 3종 및 production config smoke 재실행.
- Owner:
  - Auditor

## [SEC-076-F002] 현재 식별된 XSS sink는 escapeHtml로 보호되고 mutation에서 검출됨

- Pass: Security
- Pattern: DOM XSS sink protection
- Area: `app/static/js/game.js`, `tests/test_regression.py`
- Severity: **Minor**
- Status: **Verified with Known Residual Risk**
- Re-audit Mapping: `SEC-075-F002`
- Evidence:
  - `app/static/js/game.js:105`: `${escapeHtml(parkName)}`
  - `app/static/js/game.js:133`: `${escapeHtml(data.error || I18N.scoutFail)}`
  - `app/static/js/game.js:136`: `${escapeHtml(err.message)}`
  - `app/static/js/game.js:153`: `${escapeHtml(targetName)}`
  - mutation smoke: 네 guard 제거 모두 `FAILS_AS_EXPECTED`
  - `tests/test_regression.py:253`: Node.js로 실제 `escapeHtml` 함수 소스를 실행한다.
- Expected:
  - 사용자 또는 API 유래 문자열이 `innerHTML` sink에 들어갈 때 escape/sanitize가 강제되어야 한다.
- Actual:
  - 현재 확인된 shipped sink는 escapeHtml로 감싸져 있고 회귀 테스트도 주요 guard 제거를 잡아낸다.
- Impact:
  - 현재 알려진 XSS 재현 경로는 막혀 있다.
  - 실제 브라우저 DOM E2E 및 AST/data-flow 검증은 아직 없다.
- Suggested Fix:
  - 보안 hard boundary로 승격하려면 jsdom/Playwright 기반 렌더링 테스트 또는 DOMPurify 같은 검증된 sanitizer 도입을 검토한다.
- Re-audit Method:
  - pytest, Node.js helper extraction, mutation smoke, 브라우저 DOM E2E 여부를 함께 확인한다.
- Owner:
  - Coder / Security auditor

## [SEC-076-F003] 실제 RDBMS row-lock/deadlock E2E 미검증은 Accepted Risk로 유지됨

- Pass: Security
- Pattern: Concurrency boundary
- Area: PostgreSQL/MySQL row-lock/deadlock
- Severity: **Minor**
- Status: **Accepted Risk**
- Re-audit Mapping: `SEC-075-F003`
- Evidence:
  - 실제 PostgreSQL/MySQL 인스턴스 기반 row-lock/deadlock E2E는 이번 감사에서도 수행하지 않았다.
  - `README.md:57`, `README.md:98`, `README.md:131`, `README.md:163`, `README.md:195`에 다국어 Accepted Risk가 존재한다.
  - `implementation_summary.md:494-498`: owner, 수용 사유, 만료 조건, 재검토 조건 명시.
  - `spec.md:779`, `DESIGN_DECISIONS.md:40`: 동일 위험을 문서화한다.
- Expected:
  - `Accepted Risk`는 위험 설명, 영향 범위, owner, 만료 조건, 재검토 조건을 가져야 한다.
- Actual:
  - 해당 Accepted Risk 축은 문서화되어 있다.
- Impact:
  - 실제 PostgreSQL/MySQL 운영 전까지 동시성 안전성은 설계 및 SQLite/단위 회귀 테스트 수준으로만 증명된다.
- Suggested Fix:
  - 실제 PostgreSQL/MySQL 이주 시 다중 worker 부하/교착 검증 스위트를 추가하고 Accepted Risk를 종료한다.
- Re-audit Method:
  - 실제 DB 인스턴스 기반 E2E 결과와 Accepted Risk expiry 충족 여부를 확인한다.
- Owner:
  - Project Lead Architect / Eunho Lim

## 7. Cross-Pass Conflicts

## [XPF-076-F001] 실행 게이트 PASS와 작업트리/추적성 HOLD가 충돌함

- Pass: Cross-Pass
- Severity: **Major**
- Status: **Needs Fix**
- Related Findings: `DBG-076-F001`, `IMP-076-F001`
- Conflict:
  - pytest, warning gate, whitespace, py_compile, 설정 smoke, 서버 보안 smoke, XSS mutation smoke는 통과한다.
  - 그러나 최신 감사 보고서와 문서/테스트 변경이 아직 추적성 정리 전 상태다.
- Resolution:
  - `AI_AUDIT_DOC_STANDARD.md` 기준상 Pass 2 통과는 전체 PASS를 보장하지 않는다.
  - 감사 이력 및 작업트리 추적성 문제가 남아 있으므로 전체 판정은 HOLD다.

## [XPF-076-F002] Accepted Risk와 다국어/설계 문서의 절대 보증 표현이 충돌함

- Pass: Cross-Pass
- Severity: **Major**
- Status: **Needs Fix**
- Related Findings: `IMP-076-F003`, `SEC-076-F002`, `SEC-076-F003`
- Conflict:
  - 문서는 PostgreSQL/MySQL 실 DB 검증과 브라우저 DOM E2E 미수행을 Accepted Risk 또는 Known Residual Risk로 명시한다.
  - 동시에 README 다국어 FAQ와 `designs.md` 일부는 "완전/완벽/Fully resolved/完全" 계열의 표현으로 hard-boundary처럼 읽힌다.
- Resolution:
  - 검증 범위보다 강한 문구를 낮추거나, 해당 claim을 증명하는 실제 E2E를 추가해야 한다.

## [XPF-076-F003] 문서 릴리즈 버전과 런타임 배너 버전이 충돌함

- Pass: Cross-Pass
- Severity: **Major**
- Status: **Needs Fix**
- Related Findings: `IMP-076-F002`
- Conflict:
  - 문서 authority는 `v1.8.9`다.
  - 실행 진입점은 `Jissou Park Empire v0.1.0`을 출력한다.
- Resolution:
  - 단일 버전 source of truth를 만들거나, 런타임 배너의 버전 의미를 문서와 분리해 명확히 표시해야 한다.

## 8. Required Fixes Before PASS

1. `audit_report_73.md`, `audit_report_74.md`, `audit_report_75.md`, 본 `audit_report_76.md`를 최신 감사 산출물로 추적하거나, 별도 감사 이력 문서에서 최신 canonical 보고서를 명시한다.
2. 현재 modified 상태인 `CHANGELOG.md`, `DESIGN_DECISIONS.md`, `README.md`, `lessons_learned.md`, `tests/test_regression.py` 변경을 의도 변경으로 정리한다.
3. `run.py`의 사용자-facing 시작 배너 `v0.1.0`과 문서 기준 `v1.8.9`의 의미를 일치시키거나 분리 표기한다.
4. README 다국어 FAQ, `designs.md`, 소스/테스트 주석의 절대 보증 표현을 현재 검증 범위에 맞게 낮춘다.
5. 절대 표현 검색 결과에서 게임 대사, CSS 퍼센트, 대안 라벨, 한계 설명을 어떤 기준으로 false positive 처리할지 명시한다.
6. XSS 검증을 현재 regex 정적 스캔의 Known Residual Risk로 유지할지, jsdom/브라우저/AST 기반 hard gate로 승격할지 명세화한다.
7. 실제 PostgreSQL/MySQL row-lock/deadlock E2E가 수행되기 전까지 Accepted Risk owner/expiry/recheck를 유지한다.

## 9. Accepted Risks

| Risk | Status | Owner | Expiry / Recheck |
| --- | --- | --- | --- |
| PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증 | **Accepted Risk 문서화됨** | Project Lead Architect / Eunho Lim | 실제 PostgreSQL/MySQL 이주 및 다중 worker 부하/교착 검증 최초 통과 시 만료 |
| SQLite multi-worker `Database Locked` 가능성 | **Accepted Risk 문서화됨** | Project Lead Architect / Eunho Lim | DAU 100명 초과, 초당 DB 쓰기 10회 초과, 또는 locked error 주 3회 이상 감지 시 PostgreSQL 전환 |
| 실제 브라우저/jsdom DOM XSS E2E 미수행 | **Known Residual Risk** | Coder / Auditor | jsdom/브라우저 테스트 또는 AST/data-flow 기반 정적 분석 추가 시 해소 |
| CI 부재 | **Manual gate로 완화된 Known Operational Risk** | Project maintainer | CI 도입 또는 수동 gate 실행 증적 아카이빙 시 완화 강화 |

## 10. Needs Spec Clarification

1. 이전 감사 보고서를 immutable history로 보존할 경우, 잘못된 PASS/HOLD 판정을 최신 보고서가 supersede하는 것만으로 충분한지, 별도 감사 이력 정정 문서가 필요한지 기준이 필요하다.
2. `run.py`의 `v0.1.0` 배너가 실제 앱 릴리즈 버전인지, 초기 scaffold 버전인지, 혹은 문서 버전과 별개인 내부 프로토콜 버전인지 명확히 해야 한다.
3. README 다국어 섹션의 "Fully resolved", "完全", "永久" 계열 표현을 현재 보안 hard boundary claim으로 볼지 historical release note로 볼지 결정해야 한다.
4. 절대 표현 검색에서 게임 대사, CSS `100%`, 대안 라벨, "불완전" 한계 설명을 어떻게 false positive로 분류할지 기준이 필요하다.
5. XSS 보안 게이트를 regex 정적 스캔으로 충분하다고 볼지, DOM 실행 기반 테스트를 필수로 요구할지 명시해야 한다.
6. 실제 PostgreSQL/MySQL E2E 전에도 "Target Production" 표현을 유지할 수 있는지, "Target Production Design / Accepted Risk until real DB validation"처럼 낮춰야 하는지 결정해야 한다.

## 11. Re-audit Checklist

- [x] `AI_AUDIT_DOC_STANDARD.md` 감사 기준 확인
- [x] 최신 감사 보고서 번호 확인
- [x] `audit_report_75.md` 직전 감사 판정 및 HOLD 사유 확인
- [x] `git status --short`
- [x] `git diff --stat`
- [x] `git diff -- README.md CHANGELOG.md DESIGN_DECISIONS.md lessons_learned.md tests/test_regression.py`
- [x] `venv/bin/python -m pytest -q`
- [x] `venv/bin/python -m pytest -q -W error`
- [x] `git diff --check`
- [x] `git diff --cached --check`
- [x] `venv/bin/python -m py_compile app/*.py run.py tests/*.py`
- [x] PostgreSQL URI 설정 smoke
- [x] `psycopg2` import smoke
- [x] SQLite `journal_mode` 및 `busy_timeout` smoke
- [x] production DEBUG 강제 off smoke
- [x] loopback 개발 서버 smoke
- [x] 외부 바인딩 fail-closed smoke
- [x] 외부 바인딩 opt-in debug off smoke
- [x] XSS 주요 sink in-memory mutation smoke
- [x] README 다국어 support matrix Accepted Risk 확인
- [x] 절대 보증 표현 잔존 검색
- [x] README 언어 혼합 검색
- [x] 런타임 배너 버전과 문서 버전 비교
- [x] CI/workflow 파일 검색
- [x] 수동 품질 게이트 문서 확인

## 12. Final Decision

**HOLD**

현재 구현 실행 게이트는 양호하다. `pytest`, `-W error`, whitespace, `py_compile`, DB 설정 smoke, 개발 서버 보안 smoke가 통과했고, 현재 확인된 XSS sink의 `escapeHtml` guard도 mutation smoke에서 검출된다. `DATABASE_URL`/`SQLALCHEMY_DATABASE_URI` 전환, SQLite WAL/busy_timeout, 외부 바인딩 fail-closed, production DEBUG 강제 off도 현재 확인 범위에서 구현과 실행 결과가 일치한다.

그러나 `AI_AUDIT_DOC_STANDARD.md` 기준의 최종 PASS는 실행 게이트만으로 결정되지 않는다. 이번 76번 재감사에서 남은 차단 사유는 다음과 같다.

1. 최신 감사 보고서 73·74·75 및 이번 76번이 아직 추적성 정리 전 상태다.
2. 문서 4개와 테스트 1개가 modified 상태로 남아 있어 clean base와 의도 변경 구분이 필요하다.
3. `run.py` 시작 배너는 `v0.1.0`이지만 문서 기준 버전은 `v1.8.9`다.
4. README 다국어 섹션과 `designs.md`, 일부 주석에 검증 범위를 초과하는 절대 보증 표현이 남아 있다.
5. 실제 PostgreSQL/MySQL E2E 및 브라우저 DOM E2E는 Accepted Risk 또는 Known Residual Risk로 유지된다.

따라서 본 76번 재감사의 최종 판정은 **HOLD**다. HOLD 사유는 현재 로컬 구현 실행 실패가 아니라 감사 산출물 추적성, 런타임 버전 표시 drift, 문서 hard-boundary 표현 정합성, 실제 외부 E2E 미검증 리스크에 집중된다.
