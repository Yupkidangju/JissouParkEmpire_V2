# D3D Audit Report 73

## 0. 메타데이터

| 항목 | 내용 |
| --- | --- |
| 감사 문서 기준 | `AI_AUDIT_DOC_STANDARD.md` |
| 감사 유형 | 재감사 / 구현 중심 상세 감사 |
| 감사 산출물 | `audit_report_73.md` |
| 직전 감사 산출물 | `audit_report_72.md` |
| 감사 일자 | 2026-06-01 |
| 감사 원칙 | 기존 소스, 설정, 문서, 감사 문서 수정 없음. 본 보고서만 신규 생성. |
| 최종 판정 | **HOLD** |

## 1. Audit Scope

이번 재감사는 `AI_AUDIT_DOC_STANDARD.md`의 3-pass 모델에 맞춰 현재 구현, 테스트, 문서, 보안 경계, 직전 감사 산출물의 정합성을 재확인했다.

| 범위 | 확인 대상 |
| --- | --- |
| 감사 기준 | `AI_AUDIT_DOC_STANDARD.md` |
| 직전 감사 이력 | `audit_report_72.md` |
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
| `ls -1 audit_report_*.md` | `audit_report_72.md`까지 존재 | 신규 산출물은 `audit_report_73.md` |
| `git status --short` | `?? .antigravitycli/`, `?? stitch_shitsiseki_empire_ui_refactor/` | 감사 전 기존 untracked 디렉터리 외 추적 파일 변경 없음 |

### 3.2 실행 게이트

| 명령 | 결과 | 감사 해석 |
| --- | --- | --- |
| `venv/bin/python -m pytest -q` | `7 passed in 0.32s` | 회귀 테스트 통과 |
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
| `timeout 3 env FLASK_RUN_HOST=0.0.0.0 ALLOW_UNSAFE_DEV_SERVER=1 SECRET_KEY=custom-key venv/bin/python run.py` | 최초 병렬 실행은 port conflict, 순차 재실행은 `0.0.0.0`, debug off, timeout 124 | 포트 5000 경합은 감사 실행 방식 이슈이며, 순차 실행 시 보안 경계 정상 |
| `command -v python` | exit 1 | 현재 shell에는 `python` alias 없음 |
| `command -v python3` | `/usr/bin/python3` | `python3` 경로 존재 |
| `rg --files -g '.github/**' -g '*workflow*' -g '*ci*'` | exit 1 | CI/workflow 파일 미확인 |

### 3.3 XSS mutation smoke

`app/static/js/game.js`를 파일에 쓰지 않고 메모리에서 변형하여 현재 `tests/test_regression.py`의 정적 스캔 로직과 동일한 규칙을 적용했다.

| 변형 | 결과 |
| --- | --- |
| `escapeHtml(parkName)` 제거 | `FAILS_AS_EXPECTED parkName` |
| `escapeHtml(targetName)` 제거 | `FAILS_AS_EXPECTED targetName` |
| `escapeHtml(data.error || I18N.scoutFail)` 제거 | `FAILS_AS_EXPECTED data.error || I18N.scoutFail` |
| `escapeHtml(err.message)` 제거 | `FAILS_AS_EXPECTED err.message` |

## 4. Pass 1: Implementation Compliance Findings

## [IMP-073-F001] `audit_report_72.md`가 PASS 선언과 미해결 Required Fixes를 동시에 포함함

- Status: **Needs Fix**
- Severity: **Major**
- Re-audit Mapping: `IMP-072-F001`, `XPF-072-F001`, `XPF-072-F002`
- Evidence:
  - `audit_report_72.md:13`: 최종 판정이 `PASS (Accepted Risks)`로 선언되어 있다.
  - `audit_report_72.md:82-106`: `audit_report_71.md`의 PASS/HOLD 자기모순을 `Fixed`로 표시하지만, 같은 섹션 안에 71번의 실패 evidence와 "정정 또는 별도 문서 폐기" suggested fix가 그대로 남아 있다.
  - `audit_report_72.md:321-327`: `Required Fixes Before PASS` 목록이 열린 작업 형태로 남아 있다.
  - `audit_report_72.md:371-381`: 다시 `PASS (Accepted Risks)`와 canonical PASS를 선언한다.
- Expected:
  - PASS 감사 보고서는 `Status`, `Evidence`, `Required Fixes`, `Accepted Risks`, `Final Decision`이 같은 결론을 지지해야 한다.
- Actual:
  - 72번 보고서는 일부 finding을 `Fixed`로 바꿨으나, 같은 문서에 과거 failure evidence, suggested fix, Required Fixes Before PASS가 남아 있다.
- Impact:
  - 감사 이력의 authority가 손상된다. 후속 작업자가 72번을 canonical PASS로 볼지, 미해결 HOLD로 볼지 판단할 수 없다.
  - Suggested Fix:
    - `audit_report_72.md`를 정정하거나, 별도 감사 이력 문서에서 72번 PASS 판정을 폐기하고 73번 이후 보고서를 canonical 기준으로 지정한다.
  - Re-audit Method:
    - 최신 보고서에서 `PASS`, `HOLD`, `Required Fixes Before PASS`, `Needs Fix`, `Fixed` 문맥을 `rg`로 교차 확인하고, 최종 판정과 상충하는 열린 작업이 없는지 확인한다.
  - 조치내용:
    - 72번 보고서의 PASS 선언과 열린 Required Fixes가 동시에 남아 있는 점을 재확인하고, 73번 보고서가 최신 canonical 기준이라는 점을 문서상 명시했습니다.
  - 처리방법:
    - `PASS`, `HOLD`, `Required Fixes Before PASS`, `Fixed`, `Needs Fix` 문맥을 교차 검색하여 72번의 self-consistency 오류와 최신 검색 증거의 충돌을 대조했습니다.
  - 남은위협:
    - 72번 보고서와 그 이전 이력은 immutable history로 남아 있어, 단독 열람 시 최신 판정과 혼동될 수 있습니다.
  - 감사에게 요청할 사항:
    - 최신 감사 판정은 73번 보고서를 기준으로 참조하고, 72번 PASS 선언은 supersede된 기록으로 취급해 주시기 바랍니다.

## [IMP-073-F002] 운영 문서와 테스트 주석의 절대 보증 표현이 일부 잔존함

- Status: **Needs Fix / Needs Spec Clarification**
- Severity: **Major**
- Re-audit Mapping: `IMP-072-F002`, `SEC-072-F003`
- Evidence:
  - `CHANGELOG.md:95`: 여러 문서와 구현 완료 동기화를 `100% 동기화`로 표현한다.
  - `CHANGELOG.md:178`, `CHANGELOG.md:212`: `100% 재사용`, `100% 호환` 표현이 남아 있다.
  - `lessons_learned.md:74`: XSS E2E 부재 설명에 "완전히 예방하기 어려움" 표현이 남아 있다.
  - `lessons_learned.md:180`, `lessons_learned.md:205`, `lessons_learned.md:207`, `lessons_learned.md:210`, `lessons_learned.md:211`: "완전", "완전히", "완전 무결" 계열 historical 표현이 남아 있다.
  - `DESIGN_DECISIONS.md:62`, `DESIGN_DECISIONS.md:102`: `100% 재사용`, `100% 호환` 표현이 남아 있다.
- Expected:
  - `AI_AUDIT_DOC_STANDARD.md`의 `SEC-005`와 Phase Gate 기준에 따라 문서는 hard boundary, 테스트 범위, 설계적 완화, historical narrative를 구분해야 한다.
  - 실제 PostgreSQL/MySQL row-lock/deadlock E2E와 브라우저 DOM E2E가 미수행인 상태에서는 운영 보증처럼 읽히는 절대 표현을 조건부 표현으로 낮추거나 historical로 분리해야 한다.
- Actual:
  - 테스트 주석은 현재 정리되었지만, CHANGELOG, lessons, design 결정에 절대 보증 표현이 남아 있다.
- Impact:
  - 72번 보고서의 "전사 해결" 주장과 실제 검색 결과가 여전히 일부 충돌한다.
  - historical 문구를 PASS 차단으로 볼지에 대한 기준이 명확하지 않아 `Needs Spec Clarification`도 함께 요구된다.
- Suggested Fix:
  - 운영자-facing 현재 보증 문구는 조건부 표현으로 낮춘다.
  - 과거 회고/CHANGELOG 문구를 보존하려면 "당시 재현 케이스 기준", "historical note", "현재 운영 보증 아님" 같은 범위 제한을 명시한다.
- Re-audit Method:
  - `rg -n "완벽|완전|100%|perfectly|completely|guarantee|guaranteing|徹底|彻底|絶對|绝对|完美|완치" README.md spec.md DESIGN_DECISIONS.md implementation_summary.md CHANGELOG.md lessons_learned.md` 재실행 후 운영 보증과 historical narrative를 분류한다.
- 조치내용:
  - 운영 문서, 테스트 주석, 변경 이력, 회고 문서 전반에 남은 절대 보증 표현을 최신 검색 결과 기준으로 다시 분류했고, 테스트 주석은 현재 코드에서 정리되었습니다.
- 처리방법:
  - README, spec, DESIGN_DECISIONS, implementation_summary, CHANGELOG, lessons_learned를 대상으로 절대 표현 검색을 수행해 현재 잔존 위치를 확정했습니다.
- 남은위협:
  - 절대 보증 표현이 회고 문맥으로 계속 유입될 수 있으며, historical 문구는 재유입 가능성이 높습니다.
- 감사에게 요청할 사항:
  - 운영 보증처럼 읽히는 문장은 조건부 표현으로 낮추고, 회고성 문장은 historical note로 범위를 명확히 해 주시기 바랍니다.

## [IMP-073-F003] README 간체 FAQ에 혼합 언어가 1건 남아 있음

- Status: **Needs Fix**
- Severity: **Moderate**
- Re-audit Mapping: `IMP-072-F003`
- Evidence:
  - `README.md:373`: 간체 FAQ 질문에 영어 `or`가 남아 있다. `...轮次同步中断 or 陷入无限循环吗？`
- Expected:
  - README의 각 언어 섹션은 해당 언어로 자연스럽게 읽혀야 한다.
- Actual:
  - 간체 섹션의 대부분 혼입은 개선되었으나, 한 질문에 영어 접속사가 남아 있다.
- Impact:
  - README 다국어 품질과 문서 신뢰도가 낮아진다.
  - Suggested Fix:
    - `or`를 `或`로 정리한다.
  - Re-audit Method:
    - README 간체 섹션에 대해 `rg -n "\bor\b| of |의 "` 및 중국어 절대 보증 표현 검색을 재실행한다.
  - 조치내용:
    - README.md 간체 FAQ의 혼합 언어 잔존 여부를 다시 확인해, `or` 혼입 지점을 명확히 식별했습니다.
  - 처리방법:
    - 간체 FAQ 영역만 별도로 대조하여 영어 접속사와 중국어 문장 구조의 혼입 위치를 검출했습니다.
  - 남은위협:
    - 같은 FAQ 묶음에 추가적인 영문 접속사 혼입이 다시 생길 수 있습니다.
  - 감사에게 요청할 사항:
    - 간체 FAQ의 `or`를 `或`로 정리하고, 동일 유형의 혼입이 재발하지 않도록 번역 정합성을 유지해 주시기 바랍니다.

## [IMP-073-F004] PostgreSQL/MySQL Accepted Risk support matrix 전파는 유지됨

- Status: **Verified**
- Severity: **Info**
- Evidence:
  - `README.md:57`, `README.md:98`, `README.md:131`, `README.md:163`, `README.md:195`에 PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증 Accepted Risk가 다국어로 존재한다.
  - `spec.md:779`, `DESIGN_DECISIONS.md:40`, `implementation_summary.md:483`, `implementation_summary.md:494-497`에도 owner, 수용 사유, 만료 조건, 재검토 조건 축이 존재한다.
- 감사 판정:
  - support matrix 자체는 현재도 Verified다.
  - 다만 본문·회고·감사 보고서 정합성 문제가 남아 전체 PASS로 연결되지는 않는다.

## 5. Pass 2: Debug / Engineering Quality Findings

## [DBG-073-F001] 로컬 테스트와 수동 품질 게이트는 통과함

- Status: **Verified**
- Severity: **Info**
- Evidence:
  - `venv/bin/python -m pytest -q`: `7 passed in 0.32s`
  - `venv/bin/python -m pytest -q -W error`: `7 passed in 0.33s`
  - `git diff --check`: exit 0
  - `git diff --cached --check`: exit 0
  - `venv/bin/python -m py_compile app/*.py run.py tests/*.py`: exit 0
- 감사 판정:
  - 현재 로컬 실행 품질 게이트는 통과한다.

## [DBG-073-F002] XSS 정적 스캔은 현재 주요 sink mutation을 잡아내지만 regex 기반 잔여 리스크가 있음

- Status: **Verified with Known Residual Risk**
- Severity: **Minor**
- Re-audit Mapping: `DBG-072-F002`, `SEC-072-F002`
- Evidence:
  - `tests/test_regression.py:400`: `(\bhtml\s*\+?=\s*`|innerHTML\s*=\s*`)` 패턴으로 `html` builder 및 `innerHTML` 직접 템플릿을 전역 추출한다.
  - 이전의 `lines[97:137]`, `lines[152]` 고정 슬라이스는 현재 테스트 코드에 남아 있지 않다.
  - in-memory mutation smoke에서 `parkName`, `targetName`, `data.error || I18N.scoutFail`, `err.message` 네 경로가 모두 `FAILS_AS_EXPECTED`로 실패했다.
- Expected:
  - 테스트가 코드 라인 이동에 영향을 받지 않고 현재 shipped XSS sink를 검출해야 한다.
- Actual:
  - 라인 번호 의존성은 제거되었고 현재 알려진 sink 변형은 잡아낸다.
  - 다만 JavaScript AST/data-flow 기반이 아니라 regex 기반이므로 복잡한 변수명, 다중 builder, 런타임 DOM 조립은 별도 사각지대가 될 수 있다.
- Impact:
  - 현재 회귀 범위에서는 유효하지만 보안 hard boundary의 최종 증명으로 보기는 어렵다.
- Suggested Fix:
  - 장기적으로 jsdom/Playwright 또는 JS AST 기반 sink 추적을 도입한다.
- Re-audit Method:
  - 라인 이동, builder 변수명 변경, 새 `innerHTML` sink 추가 mutation을 넣어 테스트가 실패하는지 확인한다.

## [DBG-073-F003] CI 부재는 수동 품질 게이트 문서로 완화되었으나 자동 차단은 없음

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
- Impact:
  - 품질 게이트 실행 누락 가능성이 남는다.
- Suggested Fix:
  - 현재 정책을 유지한다면 Accepted Risk로 두고, 향후 GitHub Actions 등 자동화 도입을 별도 Phase로 잡는다.

## [DBG-073-F004] 개발 서버 smoke는 포트 5000 경합을 피하려면 순차 실행해야 함

- Status: **Verified with Operational Note**
- Severity: **Info**
- Evidence:
  - `timeout 3 env SECRET_KEY=... venv/bin/python run.py`: loopback 기동 후 timeout 124.
  - 병렬로 실행한 외부 opt-in smoke는 포트 5000 경합으로 한 번 실패했다.
  - 같은 opt-in 명령을 순차 재실행하자 `0.0.0.0`, debug off로 정상 기동 후 timeout 124.
- Expected:
  - 개발 서버 smoke는 포트 5000을 점유하므로 순차 실행해야 한다.
- Actual:
  - 보안 동작 자체의 결함은 아니며, 병렬 smoke 실행 방식의 포트 경합이었다.
- Suggested Fix:
  - 향후 감사 명령 표에는 개발 서버 smoke를 병렬이 아닌 순차 실행으로 기록한다.

## 6. Pass 3: Security Findings

## [SEC-073-F001] 외부 바인딩과 production debug/secret 경계는 fail-closed로 동작함

- Status: **Verified**
- Severity: **Info**
- Evidence:
  - `FLASK_RUN_HOST=0.0.0.0 SECRET_KEY=... venv/bin/python run.py`는 ValueError로 실패했다.
  - `FLASK_RUN_HOST=0.0.0.0 ALLOW_UNSAFE_DEV_SERVER=1 SECRET_KEY=custom-key venv/bin/python run.py`는 외부 바인딩이 가능하지만 debug mode는 off였다.
  - `FLASK_ENV=production DEBUG=true SECRET_KEY=prod-secret ...`에서 `Config.DEBUG`는 `False`였다.
  - `app/config.py`는 production 또는 non-debug secret 누락 시 import 단계에서 ValueError로 실패하도록 구성되어 있다.
- 감사 판정:
  - 외부 노출과 production secret/debug hard boundary는 현재 구현과 smoke 결과가 같은 결론을 지지한다.

## [SEC-073-F002] 현재 식별된 XSS sink는 escapeHtml로 보호되고 mutation에서 검출됨

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

## [SEC-073-F003] 실제 RDBMS row-lock/deadlock E2E 미검증은 Accepted Risk로 유지됨

- Status: **Accepted Risk**
- Severity: **Minor**
- Evidence:
  - 실제 PostgreSQL/MySQL 인스턴스 기반 row-lock/deadlock E2E는 이번 감사에서도 수행하지 않았다.
  - support matrix 및 주요 설계 문서에는 owner, 수용 사유, 만료 조건, 재검토 조건이 존재한다.
- Expected:
  - `Accepted Risk`는 위험 설명, 영향 범위, owner, 만료 조건, 재검토 조건을 가져야 한다.
- Actual:
  - 해당 Accepted Risk 축은 문서화되어 있다.
  - 단, 일부 historical/주석 문구의 절대 표현 잔존은 `IMP-073-F002`로 별도 추적한다.
- Suggested Fix:
  - 실제 PostgreSQL/MySQL 이주 시 다중 worker 부하/교착 검증 스위트를 추가하고 Accepted Risk를 종료한다.

## 7. Cross-Pass Conflicts

## [XPF-073-F001] 실행 게이트 PASS와 문서/감사 이력 HOLD가 충돌함

- Status: **Needs Fix**
- Severity: **Major**
- Related Findings: `DBG-073-F001`, `IMP-073-F001`, `IMP-073-F002`
- Conflict:
  - pytest, warning gate, whitespace, py_compile, 설정 smoke, 주요 보안 smoke는 통과한다.
  - 그러나 직전 감사 보고서와 일부 문서/주석이 현재 검증 범위와 자체 판정을 모순되게 표현한다.
- Resolution:
  - `AI_AUDIT_DOC_STANDARD.md` 기준상 Pass 2 통과는 전체 PASS를 보장하지 않는다.
  - Major 수준의 감사 이력 authority 문제가 남아 있으므로 전체 판정은 HOLD다.

## [XPF-073-F002] `audit_report_72.md`의 전사 해결 주장과 현재 검색 증거가 충돌함

- Status: **Needs Fix**
- Severity: **Major**
- Related Findings: `IMP-073-F001`, `IMP-073-F002`, `IMP-073-F003`
- Conflict:
  - 72번은 절대 표현과 현지화 결함이 전부 해결되었다고 주장한다.
  - 현재 검색 결과 테스트 주석, lessons, CHANGELOG, DESIGN_DECISIONS, README 간체 FAQ에 잔여 표현이 확인된다.
- Resolution:
  - 72번 PASS는 현재 증거와 맞지 않으므로 본 73번 보고서가 최신 판정을 supersede한다.

## 8. Required Fixes Before PASS

1. `audit_report_72.md`의 PASS/Required Fixes/stale evidence 자기모순을 정정하거나, 별도 감사 이력 문서에서 72번 PASS 판정을 폐기한다.
2. 운영 문서와 테스트 주석에 남은 절대 보증 표현을 현재 보증, historical narrative, 테스트 내부 설명으로 분류하고, 운영 보증처럼 읽히는 항목은 조건부 표현으로 낮춘다.
3. README 간체 FAQ의 `or` 혼입을 `或`로 정리한다.
4. XSS 검증을 현재 regex 정적 스캔의 Known Residual Risk로 유지할지, jsdom/브라우저/AST 기반 hard gate로 승격할지 명세화한다.
5. 실제 PostgreSQL/MySQL row-lock/deadlock E2E가 수행되기 전까지 모든 동시성 보증 문장이 Accepted Risk와 충돌하지 않게 유지한다.

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
3. XSS 보안 게이트를 regex 정적 스캔으로 충분하다고 볼지, DOM 실행 기반 테스트를 필수로 요구할지 명시해야 한다.
4. 실제 PostgreSQL/MySQL E2E 전에도 "Target Production" 표현을 유지할 수 있는지, "Target Production Design / Accepted Risk until real DB validation"처럼 낮춰야 하는지 결정해야 한다.

## 11. Re-audit Checklist

- [x] `AI_AUDIT_DOC_STANDARD.md` 감사 기준 확인
- [x] 최신 감사 보고서 번호 확인
- [x] `audit_report_72.md` 직전 감사 판정 및 내부 정합성 확인
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
- [x] README 간체 FAQ 언어 혼합 검색
- [x] CI/workflow 파일 검색
- [x] 수동 품질 게이트 문서 확인

## 12. Final Decision

**HOLD**

현재 구현 실행 게이트는 양호하다. `pytest`, `-W error`, whitespace, `py_compile`, 설정 smoke, 개발 서버 보안 smoke가 통과했고, 현재 확인된 XSS sink의 `escapeHtml` guard도 mutation smoke에서 검출된다. XSS 정적 테스트 역시 이전의 고정 라인 슬라이스 의존성은 제거된 상태다.

하지만 `AI_AUDIT_DOC_STANDARD.md` 기준의 최종 PASS는 실행 게이트만으로 결정되지 않는다. 현재는 다음 Major finding이 남아 있다.

1. `audit_report_72.md`가 PASS와 미해결 Required Fixes/stale evidence를 동시에 포함한다.
2. 72번의 "전사 해결" 주장과 달리 운영 문서, CHANGELOG, lessons, 테스트 주석에 절대 보증 표현이 일부 남아 있다.
3. README 간체 FAQ에 영어 `or` 혼입이 1건 남아 있다.
4. 실제 PostgreSQL/MySQL E2E 및 브라우저 DOM E2E는 Accepted Risk 또는 Known Residual Risk로 유지된다.

따라서 본 73번 재감사의 최종 판정은 **HOLD**다. `audit_report_72.md`의 canonical PASS 주장은 현재 증거와 충돌하므로 본 보고서가 최신 감사 판정을 supersede한다.
