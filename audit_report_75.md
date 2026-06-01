# D3D Audit Report

## 0. 메타데이터

| 항목 | 내용 |
| --- | --- |
| 감사 문서 기준 | `AI_AUDIT_DOC_STANDARD.md` |
| 감사 유형 | 재감사 / 구현 중심 상세 감사 |
| 감사 산출물 | `audit_report_75.md` |
| 직전 감사 산출물 | `audit_report_74.md` |
| 감사 일자 | 2026-06-01 |
| 감사 원칙 | 기존 소스, 설정, 문서, 감사 문서 수정 없음. 본 보고서만 신규 생성. |
| 최종 판정 | **HOLD** |

## 1. Audit Scope

이번 재감사는 `AI_AUDIT_DOC_STANDARD.md`의 3-pass 모델에 맞춰 현재 구현, 테스트, 문서, 보안 경계, 직전 감사 산출물의 정합성을 재확인했다.

| 범위 | 확인 대상 |
| --- | --- |
| 감사 기준 | `AI_AUDIT_DOC_STANDARD.md` |
| 직전 감사 이력 | `audit_report_74.md` |
| 구현 코드 | `app/config.py`, `run.py`, `app/static/js/game.js` |
| 회귀 테스트 | `tests/test_regression.py` |
| 운영 문서 | `README.md`, `spec.md`, `DESIGN_DECISIONS.md`, `implementation_summary.md`, `CHANGELOG.md`, `lessons_learned.md`, `BUILD_GUIDE.md` |
| 실행 게이트 | pytest, warnings-as-errors, whitespace, py_compile, 설정 smoke, 개발 서버 smoke |
| 보안 경계 | XSS sink, 외부 바인딩 fail-closed, production secret/debug fail-closed, DB 락 Accepted Risk |

## 2. Excluded Scope

| 제외 항목 | 사유 |
| --- | --- |
| 소스 수정 | 사용자가 명시적으로 "수정은 하지 않습니다"라고 요청했다. |
| 기존 문서 수정 | 본 감사는 재감사 보고서 작성만 수행한다. |
| 실제 PostgreSQL/MySQL 인스턴스 기반 row-lock/deadlock E2E | 현재 로컬 환경에서 실제 DB 서버를 구성하지 않았다. 문서상 Accepted Risk로 분류되어 있다. |
| 실제 브라우저/jsdom DOM 실행 기반 XSS E2E | 현재 검증은 정적 분석 및 in-memory mutation smoke 중심이다. |
| 원격 CI 실행 | `.github/**`, workflow, ci 파일이 검색되지 않았다. |
| `.antigravitycli/`, `stitch_shitsiseki_empire_ui_refactor/` | 감사 시작 전부터 존재한 untracked 디렉터리이며 본 감사 범위 밖이다. |

## 3. Evidence Summary

### 3.1 현재 작업트리와 보고서 번호

| 명령 | 결과 | 해석 |
| --- | --- | --- |
| `ls -1 audit_report_*.md` | `audit_report_74.md`까지 존재 | 신규 산출물은 `audit_report_75.md` |
| `git status --short` | `M CHANGELOG.md`, `M DESIGN_DECISIONS.md`, `M README.md`, `M lessons_learned.md`, `M tests/test_regression.py`, `?? audit_report_73.md`, `?? audit_report_74.md`, 기타 untracked 디렉터리 | 감사 시작 전부터 수정/미추적 항목이 존재한다. |

### 3.2 현재 변경 diff 요약

| 파일 | 관찰 |
| --- | --- |
| `CHANGELOG.md` | `100% 동기화`, `100% 재사용`, `100% 호환` 표현이 완화되었다. |
| `DESIGN_DECISIONS.md` | `100% 재사용`, `100% 호환`, `100% 사망` 표현이 완화되었다. |
| `README.md` | 간체 FAQ의 `or` 혼입 1건이 `或`로 정리되었다. |
| `lessons_learned.md` | XSS 및 동시성 회고 표현 다수가 조건부/완화 표현으로 낮아졌다. |
| `tests/test_regression.py` | 테스트 주석의 `완벽히`, `완전히`, `철저히`, `온전히` 계열 표현이 일부 완화되었다. |
| `audit_report_73.md`, `audit_report_74.md` | 최신 HOLD 판정 이력이지만 git 기준 untracked 상태다. |

### 3.3 실행 게이트

| 명령 | 결과 | 감사 해석 |
| --- | --- | --- |
| `venv/bin/python -m pytest -q` | `7 passed in 0.33s` | 회귀 테스트 통과 |
| `venv/bin/python -m pytest -q -W error` | `7 passed in 0.33s` | warning 승격 조건 통과 |
| `git diff --check` | exit 0 | 작업트리 whitespace gate 통과 |
| `git diff --cached --check` | exit 0 | staged whitespace gate 통과 |
| `venv/bin/python -m py_compile app/*.py run.py tests/*.py` | exit 0 | Python 문법 컴파일 통과 |
| `SECRET_KEY=... DATABASE_URL=postgresql://...` 설정 smoke | PostgreSQL URI 출력 | `DATABASE_URL` 설정 경로 정상 |
| `SECRET_KEY=... SQLALCHEMY_DATABASE_URI=postgresql://...` 설정 smoke | PostgreSQL URI 출력 | `SQLALCHEMY_DATABASE_URI` 우선 경로 정상 |
| `venv/bin/python -c "import psycopg2"` | `2.9.12 (dt dec pq3 ext lo64)` | PostgreSQL 드라이버 존재 |
| SQLite PRAGMA smoke | `wal`, `5000` | `journal_mode=WAL`, `busy_timeout=5000` 주입 확인 |
| `FLASK_ENV=production DEBUG=true SECRET_KEY=prod-secret ...` | `False`, `11` | production에서 DEBUG 강제 off |
| `timeout 3 env SECRET_KEY=... venv/bin/python run.py` | `127.0.0.1:5000`, debug on, timeout 124 | loopback 개발 서버 경로 동작 |
| `timeout 3 env FLASK_RUN_HOST=0.0.0.0 SECRET_KEY=... venv/bin/python run.py` | ValueError | 비루프백 외부 바인딩 기본 차단 |
| `timeout 3 env FLASK_RUN_HOST=0.0.0.0 ALLOW_UNSAFE_DEV_SERVER=1 SECRET_KEY=custom-key venv/bin/python run.py` | `0.0.0.0`, debug off, timeout 124 | 명시 opt-in 시에도 debug off 유지 |
| `command -v python` | exit 1 | 현재 shell에는 `python` alias 없음 |
| `command -v python3` | `/usr/bin/python3` | `python3` 경로 존재 |
| `rg --files -g '.github/**' -g '*workflow*' -g '*ci*'` | exit 1 | CI/workflow 파일 미확인 |

### 3.4 XSS mutation smoke

`app/static/js/game.js`를 파일에 쓰지 않고 메모리에서 변형하여 현재 `tests/test_regression.py`의 정적 스캔 로직과 동일한 규칙을 적용했다.

| 변형 | 결과 |
| --- | --- |
| `escapeHtml(parkName)` 제거 | `FAILS_AS_EXPECTED parkName` |
| `escapeHtml(targetName)` 제거 | `FAILS_AS_EXPECTED targetName` |
| `escapeHtml(data.error || I18N.scoutFail)` 제거 | `FAILS_AS_EXPECTED data.error || I18N.scoutFail` |
| `escapeHtml(err.message)` 제거 | `FAILS_AS_EXPECTED err.message` |

## 4. Pass 1: Implementation Compliance Findings

## [IMP-075-F001] 감사 산출물과 문서 수정분이 아직 추적성 정리 전 상태임

- Status: **Needs Fix**
- Severity: **Major**
- Re-audit Mapping: `IMP-074-F001`, `DBG-074-F004`
- Evidence:
  - `git status --short`: `M CHANGELOG.md`, `M DESIGN_DECISIONS.md`, `M README.md`, `M lessons_learned.md`, `M tests/test_regression.py`
  - `git status --short`: `?? audit_report_73.md`, `?? audit_report_74.md`
  - 이번 감사로 `audit_report_75.md`도 새 untracked 산출물이 된다.
- Expected:
  - 감사 기준 산출물과 구현/문서 변경은 의도와 추적 상태가 명확해야 한다.
- Actual:
  - 실행 게이트는 통과하지만, 수정된 문서·테스트와 최신 감사 보고서들이 아직 추적성 정리 전 상태다.
- Impact:
  - 다른 작업자가 clean base, 수정 의도, 최신 canonical 감사 판정을 구분하기 어렵다.
  - 추적 파일만 기준으로 검토하면 최신 HOLD 판정과 관련 문서 개선 내용을 놓칠 수 있다.
- Suggested Fix:
  - 의도한 변경이라면 관련 문서·테스트·감사 보고서를 추적 대상으로 정리한다.
  - 의도하지 않은 변경이면 별도 사용자 확인 후 처리한다.
- Re-audit Method:
  - `git status --short`로 최신 감사 보고서와 수정 파일의 추적 상태를 확인한다.

## [IMP-075-F002] 절대 보증 표현 정리는 상당 부분 진행됐으나 historical/대안 라벨 표현이 남아 있음

- Status: **Needs Spec Clarification / Minor Needs Fix**
- Severity: **Moderate**
- Re-audit Mapping: `IMP-074-F002`
- Evidence:
  - `CHANGELOG.md`, `tests/test_regression.py`, `README.md`의 직전 주요 지적 표현은 대부분 완화되었다.
  - `lessons_learned.md:86`: "`replace_existing=True`로 완화, 완전 차단은 별도 락 필요" 표현이 남아 있다. 이는 과대 보증이 아니라 미완전성을 설명하는 문맥이다.
  - `lessons_learned.md:180`: "상태 머신의 결함을 완전 무결하게 제거" 표현이 남아 있다. 이는 historical narrative이지만 운영 보증처럼 읽힐 수 있다.
  - `DESIGN_DECISIONS.md:133`, `DESIGN_DECISIONS.md:640`, `DESIGN_DECISIONS.md:662`: "불완전" 표현이 남아 있다. 이는 한계 설명으로 과대 보증이 아니다.
  - `DESIGN_DECISIONS.md:157`, `DESIGN_DECISIONS.md:251`, `DESIGN_DECISIONS.md:344`: "완전 무적", "라우트 완전 삭제", "완전 제외"는 대안/옵션 라벨 문맥이다.
- Expected:
  - `AI_AUDIT_DOC_STANDARD.md`의 `SEC-005`와 Phase Gate 기준에 따라 문서는 hard boundary, 테스트 범위, 설계적 완화, historical narrative를 구분해야 한다.
- Actual:
  - 운영 보증으로 읽힐 가능성이 높은 표현은 크게 줄었다.
  - 남은 표현의 상당수는 false positive 또는 historical/대안 라벨 성격이지만, `lessons_learned.md:180`은 여전히 범위 제한이 필요하다.
- Impact:
  - 현재 검색 결과만으로는 PASS/HOLD를 결정하기 어렵고, historical 문구를 어느 수준까지 gate로 볼지 기준이 필요하다.
- Suggested Fix:
  - `lessons_learned.md:180`의 표현을 조건부 회고 표현으로 낮춘다.
  - 대안 라벨과 한계 설명 문구는 false positive로 분류하는 감사 기준을 명시한다.
- Re-audit Method:
  - 절대 표현 검색 후 운영 보증, historical narrative, false positive 라벨을 별도 표로 분류한다.

## [IMP-075-F003] README 간체 FAQ의 `or` 혼입은 해소됨

- Status: **Verified**
- Severity: **Info**
- Re-audit Mapping: `IMP-074-F003`
- Evidence:
  - `README.md` diff에서 간체 FAQ의 `轮次同步中断 or 陷入无限循环吗？`가 `轮次同步中断或陷入无限循环吗？`로 정리되었다.
  - `rg -n "\bor\b| of |의 " README.md` 결과는 영어 섹션의 정상 영문 문장과 영어 support matrix 문맥만 잡았다.
- Expected:
  - README의 각 언어 섹션은 해당 언어로 자연스럽게 읽혀야 한다.
- Actual:
  - 직전 지적된 간체 FAQ 영어 접속사 혼입은 현재 해소되었다.
- 감사 판정:
  - 해당 항목은 Verified다.

## [IMP-075-F004] PostgreSQL/MySQL Accepted Risk support matrix 전파는 유지됨

- Status: **Verified**
- Severity: **Info**
- Evidence:
  - `README.md:57`, `README.md:98`, `README.md:131`, `README.md:163`, `README.md:195`에 PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증 Accepted Risk가 다국어로 존재한다.
  - `spec.md:779`, `DESIGN_DECISIONS.md:40`, `implementation_summary.md:483`, `implementation_summary.md:494-497`에도 owner, 수용 사유, 만료 조건, 재검토 조건 축이 존재한다.
- 감사 판정:
  - support matrix 자체는 현재도 Verified다.

## 5. Pass 2: Debug / Engineering Quality Findings

## [DBG-075-F001] 로컬 테스트와 수동 품질 게이트는 통과함

- Status: **Verified**
- Severity: **Info**
- Evidence:
  - `venv/bin/python -m pytest -q`: `7 passed in 0.33s`
  - `venv/bin/python -m pytest -q -W error`: `7 passed in 0.33s`
  - `git diff --check`: exit 0
  - `git diff --cached --check`: exit 0
  - `venv/bin/python -m py_compile app/*.py run.py tests/*.py`: exit 0
- 감사 판정:
  - 현재 로컬 실행 품질 게이트는 통과한다.

## [DBG-075-F002] XSS 정적 스캔은 현재 주요 sink mutation을 잡아내지만 regex 기반 잔여 리스크가 있음

- Status: **Verified with Known Residual Risk**
- Severity: **Minor**
- Re-audit Mapping: `DBG-074-F002`, `SEC-074-F002`
- Evidence:
  - `tests/test_regression.py`의 정적 스캔은 `html` builder 및 `innerHTML` 직접 템플릿을 전역 추출한다.
  - 이전의 `lines[97:137]`, `lines[152]` 고정 슬라이스는 현재 테스트 코드에 남아 있지 않다.
  - in-memory mutation smoke에서 `parkName`, `targetName`, `data.error || I18N.scoutFail`, `err.message` 네 경로가 모두 `FAILS_AS_EXPECTED`로 실패했다.
- Expected:
  - 테스트가 코드 라인 이동에 영향을 받지 않고 현재 shipped XSS sink를 검출해야 한다.
- Actual:
  - 라인 번호 의존성은 제거되었고 현재 알려진 sink 변형은 잡아낸다.
  - 다만 JavaScript AST/data-flow 기반이 아니라 regex 기반이므로 복잡한 변수명, 다중 builder, 런타임 DOM 조립은 별도 사각지대가 될 수 있다.
- Suggested Fix:
  - 장기적으로 jsdom/Playwright 또는 JS AST 기반 sink 추적을 도입한다.

## [DBG-075-F003] CI 부재는 수동 품질 게이트 문서로 완화되었으나 자동 차단은 없음

- Status: **Accepted Risk / Known Operational Risk**
- Severity: **Minor**
- Evidence:
  - `rg --files -g '.github/**' -g '*workflow*' -g '*ci*'`: exit 1
  - `BUILD_GUIDE.md:315-336`: 수동 품질 게이트 및 자가 진단 운영 지침이 존재한다.
  - `BUILD_GUIDE.md:325-328`: `pytest -q -W error`, `git diff --check`, `git diff --cached --check`, `py_compile` 실행 명령이 명시되어 있다.
- Expected:
  - CI가 없다면 수동 gate의 책임자, 명령, 실행 주기가 문서화되어야 한다.
- Actual:
  - 문서화는 되었지만 자동 PR/commit 차단은 없다.
- Suggested Fix:
  - 현재 정책을 유지한다면 Accepted Risk로 두고, 향후 GitHub Actions 등 자동화 도입을 별도 Phase로 잡는다.

## [DBG-075-F004] dirty worktree가 계속 존재함

- Status: **Needs Fix / Operational**
- Severity: **Moderate**
- Evidence:
  - `git status --short`: 문서 4개와 `tests/test_regression.py`가 modified 상태다.
  - `git status --short`: `audit_report_73.md`, `audit_report_74.md`가 untracked 상태다.
- Expected:
  - 감사 기준 산출물과 테스트 변경은 추적 상태가 명확해야 한다.
- Actual:
  - 문서·테스트 변경과 직전 감사 보고서가 아직 작업트리에 남아 있다.
- Impact:
  - 이후 감사자가 clean base와 새 변경을 구분하기 어렵다.
- Suggested Fix:
  - 의도한 변경이라면 추적/커밋 대상으로 정리하고, 의도하지 않은 변경이라면 별도 사용자 확인 후 처리한다.

## 6. Pass 3: Security Findings

## [SEC-075-F001] 외부 바인딩과 production debug/secret 경계는 fail-closed로 동작함

- Status: **Verified**
- Severity: **Info**
- Evidence:
  - `FLASK_RUN_HOST=0.0.0.0 SECRET_KEY=... venv/bin/python run.py`는 ValueError로 실패했다.
  - `FLASK_RUN_HOST=0.0.0.0 ALLOW_UNSAFE_DEV_SERVER=1 SECRET_KEY=custom-key venv/bin/python run.py`는 외부 바인딩이 가능하지만 debug mode는 off였다.
  - `FLASK_ENV=production DEBUG=true SECRET_KEY=prod-secret ...`에서 `Config.DEBUG`는 `False`였다.
  - `app/config.py`는 production 또는 non-debug secret 누락 시 import 단계에서 ValueError로 실패하도록 구성되어 있다.
- 감사 판정:
  - 외부 노출과 production secret/debug hard boundary는 현재 구현과 smoke 결과가 같은 결론을 지지한다.

## [SEC-075-F002] 현재 식별된 XSS sink는 escapeHtml로 보호되고 mutation에서 검출됨

- Status: **Verified with Known Residual Risk**
- Severity: **Minor**
- Evidence:
  - `app/static/js/game.js:104`: `${escapeHtml(parkName)}`
  - `app/static/js/game.js:133`: `${escapeHtml(data.error || I18N.scoutFail)}`
  - `app/static/js/game.js:136`: `${escapeHtml(err.message)}`
  - `app/static/js/game.js:153`: `${escapeHtml(targetName)}`
  - in-memory mutation smoke에서 네 경로 모두 guard 제거 시 실패했다.
- Expected:
  - 사용자 또는 API 유래 문자열이 `innerHTML` sink에 들어갈 때 escape/sanitize가 강제되어야 한다.
- Actual:
  - 현재 확인된 shipped sink는 escapeHtml로 감싸져 있고 회귀 테스트도 주요 guard 제거를 잡아낸다.
- Impact:
  - 현재 알려진 XSS 재현 경로는 막혀 있다.
  - 실제 브라우저 DOM E2E 및 AST/data-flow 검증은 아직 없다.
- Suggested Fix:
  - 보안 hard boundary로 승격하려면 jsdom/Playwright 기반 렌더링 테스트 또는 DOMPurify 같은 검증된 sanitizer 도입을 검토한다.

## [SEC-075-F003] 실제 RDBMS row-lock/deadlock E2E 미검증은 Accepted Risk로 유지됨

- Status: **Accepted Risk**
- Severity: **Minor**
- Evidence:
  - 실제 PostgreSQL/MySQL 인스턴스 기반 row-lock/deadlock E2E는 이번 감사에서도 수행하지 않았다.
  - support matrix 및 주요 설계 문서에는 owner, 수용 사유, 만료 조건, 재검토 조건이 존재한다.
- Expected:
  - `Accepted Risk`는 위험 설명, 영향 범위, owner, 만료 조건, 재검토 조건을 가져야 한다.
- Actual:
  - 해당 Accepted Risk 축은 문서화되어 있다.
- Suggested Fix:
  - 실제 PostgreSQL/MySQL 이주 시 다중 worker 부하/교착 검증 스위트를 추가하고 Accepted Risk를 종료한다.

## 7. Cross-Pass Conflicts

## [XPF-075-F001] 실행 게이트 PASS와 작업트리/추적성 HOLD가 충돌함

- Status: **Needs Fix**
- Severity: **Major**
- Related Findings: `DBG-075-F001`, `DBG-075-F004`, `IMP-075-F001`
- Conflict:
  - pytest, warning gate, whitespace, py_compile, 설정 smoke, 주요 보안 smoke는 통과한다.
  - 그러나 최신 감사 보고서와 문서/테스트 변경이 아직 추적성 정리 전 상태다.
- Resolution:
  - `AI_AUDIT_DOC_STANDARD.md` 기준상 Pass 2 통과는 전체 PASS를 보장하지 않는다.
  - 감사 이력 및 작업트리 추적성 문제가 남아 있으므로 전체 판정은 HOLD다.

## [XPF-075-F002] 문서 표현 정리의 부분 완료와 historical 기준 부재가 충돌함

- Status: **Needs Spec Clarification**
- Severity: **Moderate**
- Related Findings: `IMP-075-F002`
- Conflict:
  - 과대 보증 표현의 대부분은 완화되었고 README 간체 FAQ 혼입도 해소되었다.
  - 그러나 lessons/design의 historical/대안 라벨 표현을 PASS 차단으로 볼지 false positive로 볼지 기준이 아직 없다.
- Resolution:
  - 남은 표현은 즉시 Critical/Major 구현 결함이라기보다 감사 기준 명확화 대상이다.

## 8. Required Fixes Before PASS

1. `audit_report_73.md`, `audit_report_74.md`, 본 `audit_report_75.md`를 최신 감사 산출물로 추적하거나, 별도 감사 이력 문서에서 최신 canonical 보고서를 명시한다.
2. 현재 modified 상태인 `CHANGELOG.md`, `DESIGN_DECISIONS.md`, `README.md`, `lessons_learned.md`, `tests/test_regression.py` 변경을 의도 변경으로 정리한다.
3. `lessons_learned.md:180`의 "완전 무결" 회고 표현을 조건부 또는 historical note로 낮춘다.
4. 절대 표현 검색에서 잡히는 대안 라벨/한계 설명/false positive를 어떤 기준으로 허용할지 명시한다.
5. XSS 검증을 현재 regex 정적 스캔의 Known Residual Risk로 유지할지, jsdom/브라우저/AST 기반 hard gate로 승격할지 명세화한다.
6. 실제 PostgreSQL/MySQL row-lock/deadlock E2E가 수행되기 전까지 Accepted Risk owner/expiry/recheck를 유지한다.

## 9. Accepted Risks

| Risk | Status | Owner | Expiry / Recheck |
| --- | --- | --- | --- |
| PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증 | **Accepted Risk 문서화됨** | Project Lead Architect / Eunho Lim | 실제 PostgreSQL/MySQL 이주 및 다중 worker 부하/교착 검증 최초 통과 시 만료 |
| SQLite multi-worker `Database Locked` 가능성 | **Accepted Risk 문서화됨** | Project Lead Architect / Eunho Lim | DAU 100명 초과, 초당 DB 쓰기 10회 초과, 또는 locked error 주 3회 이상 감지 시 PostgreSQL 전환 |
| 실제 브라우저/jsdom DOM XSS E2E 미수행 | **Known Residual Risk** | Coder / Auditor | jsdom/브라우저 테스트 또는 AST/data-flow 기반 정적 분석 추가 시 해소 |
| CI 부재 | **Manual gate로 완화된 Known Operational Risk** | Project maintainer | CI 도입 또는 수동 gate 실행 증적 아카이빙 시 완화 강화 |

## 10. Needs Spec Clarification

1. 이전 감사 보고서를 immutable history로 보존할 경우, 잘못된 PASS 판정을 최신 보고서가 supersede하는 것만으로 충분한지, 별도 감사 이력 정정 문서가 필요한지 기준이 필요하다.
2. `CHANGELOG.md`와 `lessons_learned.md`의 과거 과장 표현을 historical narrative로 허용할지, 현재 운영 문서와 동일하게 모두 조건부 표현으로 낮출지 결정해야 한다.
3. 절대 표현 검색에서 "불완전", "완전 삭제", "완전 제외", "완전 무적"처럼 한계 설명 또는 대안 라벨인 표현을 어떻게 false positive로 분류할지 기준이 필요하다.
4. XSS 보안 게이트를 regex 정적 스캔으로 충분하다고 볼지, DOM 실행 기반 테스트를 필수로 요구할지 명시해야 한다.
5. 실제 PostgreSQL/MySQL E2E 전에도 "Target Production" 표현을 유지할 수 있는지, "Target Production Design / Accepted Risk until real DB validation"처럼 낮춰야 하는지 결정해야 한다.

## 11. Re-audit Checklist

- [x] `AI_AUDIT_DOC_STANDARD.md` 감사 기준 확인
- [x] 최신 감사 보고서 번호 확인
- [x] `audit_report_74.md` 직전 감사 판정 및 내부 정합성 확인
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
- [x] CI/workflow 파일 검색
- [x] 수동 품질 게이트 문서 확인

## 12. Final Decision

**HOLD**

현재 구현 실행 게이트는 양호하다. `pytest`, `-W error`, whitespace, `py_compile`, 설정 smoke, 개발 서버 보안 smoke가 통과했고, 현재 확인된 XSS sink의 `escapeHtml` guard도 mutation smoke에서 검출된다. README 간체 FAQ의 직전 `or` 혼입은 해소되었고, 문서/테스트 주석의 절대 보증 표현도 상당 부분 완화되었다.

하지만 `AI_AUDIT_DOC_STANDARD.md` 기준의 최종 PASS는 실행 게이트만으로 결정되지 않는다. 현재는 다음 finding이 남아 있다.

1. 최신 감사 보고서 73·74 및 이번 75번이 아직 추적성 정리 전 상태다.
2. 문서 4개와 테스트 1개가 modified 상태로 남아 있어 clean base와 의도 변경 구분이 필요하다.
3. `lessons_learned.md:180`에 운영 보증처럼 읽힐 수 있는 historical 과대 표현이 남아 있다.
4. 절대 표현 검색 결과의 false positive 기준이 명확하지 않다.
5. 실제 PostgreSQL/MySQL E2E 및 브라우저 DOM E2E는 Accepted Risk 또는 Known Residual Risk로 유지된다.

따라서 본 75번 재감사의 최종 판정은 **HOLD**다. 다만 HOLD 사유는 현재 구현 실패가 아니라 감사 산출물 추적성, dirty worktree 정리, historical 문구 기준 명확화에 집중된다.
