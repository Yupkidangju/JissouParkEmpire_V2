# D3D Audit Report 62

## 1. Audit Scope

- 감사 일자: 2026-06-01
- 감사 기준: `AI_AUDIT_DOC_STANDARD.md`
- 감사 유형: 재감사, 구현 중심 상세 감사
- 프로젝트 경로: `/mnt/Projects_SSD/python/JissouParkEmpire`
- 프로젝트 유형: Flask + SQLAlchemy 기반 턴제 웹 게임
- 최종 판정: **HOLD**

이번 감사는 코드 수정 없이 현재 워크트리의 문서, 구현, 설정, 테스트 가능성을 대조했다. 이전 감사는 최신 순으로 `audit_report_61.md`, `audit_report_59.md`, `audit_report_58.md`, `audit_report_57.md`를 확인했다. `audit_report_60.md`는 현재 파일 목록에서 확인되지 않았다.

## 2. Excluded Scope

- 실제 서버 장시간 구동 및 브라우저 수동 플레이는 제외했다.
- `create_app()` 직접 실행은 제외했다. 앱 팩토리가 `db.create_all()` 및 NPC 초기화를 수행해 `instance/game.db`에 쓰기 부작용을 만들 수 있기 때문이다.
- 실제 병렬 HTTP 부하 테스트는 제외했다. 대신 호출 경로, 트랜잭션 경계, SQLAlchemy 컴파일 결과, 문서-코드 증거로 판정했다.
- 코드 수정, 설정 수정, 문서 동기화 수정은 수행하지 않았다. 본 보고서 파일만 생성했다.

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
- `audit_report_57.md`
- `audit_report_58.md`
- `audit_report_59.md`
- `audit_report_61.md`

### 확인한 주요 구현 파일

- `app/config.py`
- `app/__init__.py`
- `app/game_engine.py`
- `app/npc_engine.py`
- `app/battle_engine.py`
- `app/routes/auth_routes.py`
- `app/routes/game_routes.py`
- `app/static/js/game.js`
- `app/templates/dashboard.html`
- `run.py`
- `requirements.txt`

### 실행한 검증 명령

- `venv/bin/python -c "... ast.parse ..."`: `AST_OK 15 files`
- `venv/bin/python -c "... import flask, flask_sqlalchemy, flask_login, flask_wtf, werkzeug, apscheduler ..."`: `IMPORT_OK`
- `git diff --check`: 실패, trailing whitespace 존재
- `find ... tests/pytest...`: 테스트 파일 및 pytest 설정 미검출
- `git ls-files ... tests/pytest...`: 추적된 테스트 파일 및 pytest 설정 미검출
- SQLAlchemy SQLite dialect 확인: `select(...).with_for_update()` 컴파일 결과에 `FOR UPDATE` 없음

## 4. Previous Audit Mapping

| 이전 보고서 | 이전 finding | 현재 재감사 판정 |
| --- | --- | --- |
| `audit_report_57.md` | NPC 공격 내부 `commit()`이 nested savepoint를 깨뜨려 `ResourceClosedError`와 AP 미소모 루프를 유발 | `_npc_attack`, `_npc_cunning_attack`은 `flush()`로 바뀌어 직접 원인은 완화됐다. 단, 회귀 테스트가 없어 Verified로 닫을 수 없다. |
| `audit_report_58.md` | AP 환불 commit 누락 의심 | 이전 보고서 자체가 False Positive로 철회됐다. 현재 `refund_ap()` 내부 commit과 라우터 후속 commit은 존재한다. |
| `audit_report_59.md` | 밀사 처리 후 overcrowding의 무락 `refresh()` + 인메모리 변경으로 Lost Update 가능 | 코드상 재락 시도는 추가됐지만 기본 SQLite에서 `with_for_update()`가 no-op이므로 기본 실행 구성에서는 해결로 볼 수 없다. |
| `audit_report_61.md` | NPC 공격 시 선점 NPC 락과 `execute_battle()` canonical lock의 락 순서 역전 교착 상태 | **미해결.** `process_npc_turn()` 내부 선점 락은 제거됐지만 호출자인 `_sync_npc_turns()`가 NPC를 먼저 락한 상태로 `process_npc_turn()`을 호출한다. |

## 5. Pass 1: Implementation Compliance Findings

## [IMP-F001] `audit_report_61.md`의 NPC 공격 락 순서 역전이 호출자 레벨에서 그대로 남아 있음

- Pass: Implementation
- Pattern: `IMP-001`, `IMP-004`, 재감사 규칙
- Area: NPC 턴 동기화, 전투 트랜잭션, 문서-구현 정합성
- Severity: **Critical**
- Status: **Needs Fix**
- Related Previous Finding: `audit_report_61.md` `[DEADLOCK-F005]`
- Summary: v1.8.9 문서는 `process_npc_turn()` 최상단 비관적 락 제거로 NPC 공격 데드락이 완치됐다고 선언한다. 그러나 실제 호출 경로에서는 `_sync_npc_turns()`가 NPC 행을 `with_for_update()`로 먼저 잡은 뒤 `process_turn(npc_park)`와 `process_npc_turn(npc_park)`를 호출하고, 그 안에서 `_npc_attack()`이 `execute_battle()`을 호출한다. 따라서 행 락을 실제 지원하는 DB에서는 여전히 `NPC -> Player` 순서가 발생한다.
- Evidence:
  - `app/game_engine.py:183-197`: `_sync_npc_turns()`가 `npc_park = ...with_for_update().first()`로 NPC를 먼저 잠근 뒤 `process_npc_turn(npc_park)`을 호출하고 마지막에 commit한다.
  - `app/npc_engine.py:39-41`: `process_npc_turn()` 내부의 최상단 락만 제거되고 `refresh()`만 수행한다.
  - `app/npc_engine.py:292-304`: NPC 공격 함수가 `execute_battle()` 호출 후 AP를 차감한다.
  - `app/battle_engine.py:39-44`: `execute_battle()`은 두 공원 ID를 정렬해 `with_for_update()`를 수행한다.
  - `README.md:211-212`, `CHANGELOG.md:15`, `designs.md:451-457`, `audit_roadmap.md:129`: 문서는 `process_npc_turn()` 락 제거만으로 완전 해결됐다고 주장한다.
- Expected: NPC 공격으로 전투에 진입하기 전에는 공격자 NPC 또는 방어자 Player 어느 한쪽도 정렬 순서 밖에서 선점 락을 보유하지 않아야 한다.
- Actual: `_sync_npc_turns()`가 NPC를 먼저 락한 상태에서 `execute_battle()`의 정렬 락 재획득 경로로 진입한다.
- Impact: PostgreSQL/MySQL 등 `FOR UPDATE` 행 락이 실제 작동하는 DB로 전환하거나 문서의 Gunicorn 다중 워커 주장을 실현하면, `Player.id < NPC.id` 상황에서 기존 `[DEADLOCK-F005]`가 재발할 수 있다. DB 커넥션 고갈 및 턴 처리 정지로 이어질 수 있다.
- Suggested Fix: `_sync_npc_turns()`의 외부 NPC 선점 락 범위를 분리한다. 특히 공격 가능 행동은 NPC 락을 보유한 상태로 `execute_battle()`에 진입하지 않도록 턴 진행과 NPC 행동 의사결정, 전투 실행 트랜잭션을 분리하거나, 전투에 필요한 두 공원을 최초 락 획득 시점부터 canonical order로 잡도록 구조를 바꾼다.
- Re-audit Method: `Player.id < NPC.id` 및 `NPC.id < Player.id` 양방향 fixture로 NPC 공격과 플레이어 공격/교역/외교를 병렬 실행하고, DB row-lock 지원 엔진에서 deadlock timeout 또는 connection pool 고갈이 없는지 확인한다. 정적 검증으로는 `_sync_npc_turns()`에서 `process_npc_turn()` 호출 전 선점된 NPC row lock이 없는지 확인한다.
- Owner: Coder
- Notes: 이전 수정은 함수 내부의 한 지점만 제거했고, 실제 호출 그래프의 상위 락 보유 상태를 제거하지 못했다.

## [IMP-F002] 문서의 `escapeHtml()` 기반 XSS 완료 주장이 현재 정찰/공격 모달 구현과 충돌함

- Pass: Implementation
- Pattern: `IMP-001`, `SEC-008`
- Area: 문서-렌더러 정합성, 정찰 모달, 공격 모달
- Severity: **Major**
- Status: **Needs Fix**
- Summary: `spec.md`, `CHANGELOG.md`, `lessons_learned.md`, `audit_roadmap.md`는 정찰 모달에서 `escapeHtml()` 또는 `textContent` 기반 XSS 방어가 적용됐다고 기록한다. 그러나 현재 `app/static/js/game.js`에는 `escapeHtml` 구현이 없고, `innerHTML`에 공원명과 응답 문자열을 직접 삽입한다.
- Evidence:
  - `spec.md:681-684`: Phase 8 완료 항목으로 `XSS 방어 (escapeHtml)`을 선언한다.
  - `spec.md:733-735`: 정찰 모달에 `escapeHtml()` JS 함수를 사용한다고 명시한다.
  - `CHANGELOG.md:151-152`: `innerHTML`에서 `textContent`/`escapeHtml()`로 전환했다고 기록한다.
  - `lessons_learned.md:96`: 사용자 입력을 `innerHTML`에 넣는 패턴을 XSS 원인으로 기록한다.
  - `audit_roadmap.md:37`: 정찰 모달 검증 방법을 `escapeHtml()` 적용 확인으로 둔다.
  - `rg -n "escapeHtml" .`: 코드 구현에는 없고 문서에만 존재한다.
  - `app/static/js/game.js:90-117`: 정찰 HTML 문자열을 조립한 뒤 `contentDiv.innerHTML = html`로 삽입한다.
  - `app/static/js/game.js:119-122`: `data.error` 및 `err.message`를 `innerHTML`에 삽입한다.
  - `app/static/js/game.js:138-139`: `data-target-name`에서 읽은 `targetName`을 공격 모달 제목 `innerHTML`에 삽입한다.
  - `app/templates/dashboard.html:575-578`: `p.name`이 `data-park-name`, `data-target-name` 속성으로 전달된다.
- Expected: 문서 주장대로 정찰/공격 모달은 `escapeHtml()` 또는 DOM node construction/textContent를 사용해 사용자 또는 DB 기원 문자열을 HTML로 해석하지 않아야 한다.
- Actual: 현재 JS는 `innerHTML` 중심으로 렌더링하며 문서에 기록된 `escapeHtml()` 함수가 없다.
- Impact: 현재 회원가입은 `<>&"'/\`를 차단하지만, 기존 DB 데이터, 마이그레이션, 관리자 삽입, NPC/복구 경로, 향후 기능이 해당 전제 밖의 문자열을 넣으면 DOM XSS가 재발할 수 있다. 문서가 이미 이 위험을 과거 회귀로 기록했기 때문에 gate 영향이 크다.
- Suggested Fix: 정찰/공격 모달에서 사용자/DB 기원 문자열은 `textContent` 또는 명시적 escape helper를 통과시키고, 아이콘처럼 고정된 HTML 조각만 안전하게 조립한다. 문서의 `escapeHtml()` 주장과 실제 구현 중 하나를 일치시킨다.
- Re-audit Method: `rg -n "innerHTML|escapeHtml|textContent" app/static app/templates` 재검색 후, 악성 공원명 fixture가 모달에서 텍스트로만 표시되는지 브라우저 또는 DOM 테스트로 확인한다.
- Owner: Coder

## [IMP-F003] 필수 문서 파일명 규약과 실제 파일명이 불일치함

- Pass: Implementation
- Pattern: `SPEC-GAP-001`, `IMP-004`
- Area: D3D Required Files, 문서 authority
- Severity: **Minor**
- Status: **Needs Documentation Recovery**
- Summary: `AGENTS.md`의 Required Files는 `IMPLEMENTATION_SUMMARY.md`, `LESSONS_LEARNED.md`를 요구하지만 현재 루트에는 소문자 `implementation_summary.md`, `lessons_learned.md`만 존재한다.
- Evidence:
  - `AGENTS.md` Required Files: `IMPLEMENTATION_SUMMARY.md`, `LESSONS_LEARNED.md`
  - `ls -1 IMPLEMENTATION_SUMMARY.md LESSONS_LEARNED.md implementation_summary.md lessons_learned.md`: 소문자 파일 2개만 확인됨
  - `wc -l ... IMPLEMENTATION_SUMMARY.md ... LESSONS_LEARNED.md`: 대문자 파일 없음으로 실패
- Expected: Required Files의 실제 파일명과 감사/문서 표준의 authority가 일치해야 한다.
- Actual: 실제 문서는 소문자 파일명이고 AGENTS 규약은 대문자 파일명이다.
- Impact: 자동 감사, 문서 생성, 아카이빙 루틴이 파일을 누락하거나 중복 문서를 만들 수 있다.
- Suggested Fix: 프로젝트 표준을 대문자 또는 소문자 중 하나로 결정하고 `AGENTS.md`, `AI_AUDIT_DOC_STANDARD.md`, 실제 파일명을 동기화한다.
- Re-audit Method: `rg --files`로 Required Files 전체가 정확한 파일명으로 존재하는지 재검증한다.
- Owner: Architect / Coder

## 6. Pass 2: Debug / Engineering Quality Findings

## [DBG-F001] SQLite 기본 구성에서 `with_for_update()`가 no-op이라 v1.8.x 락 기반 수정들이 검증된 보호 경계가 아님

- Pass: Debug / Engineering Quality
- Pattern: `DBG-001`, `ARCH-001`, `BUILD-001`
- Area: DB 락 경계, 배포 구성, 동시성 보증
- Severity: **Critical**
- Status: **Needs Fix**
- Related Previous Findings: `audit_report_47.md`, `audit_report_48.md`, `audit_report_54.md`, `audit_report_56.md`, `audit_report_59.md`, `audit_report_61.md`
- Summary: 현재 기본 DB는 SQLite이고, SQLAlchemy SQLite dialect에서 `with_for_update()`는 `FOR UPDATE` SQL을 생성하지 않는다. 그럼에도 문서와 코드 주석은 다중 프로세스 Gunicorn 환경에서 비관적 행 락이 Lost Update, Stampede, Deadlock을 해결한다고 반복 주장한다.
- Evidence:
  - `app/config.py:17-18`: `SQLALCHEMY_DATABASE_URI = 'sqlite:///game.db'`
  - SQLAlchemy 확인 명령 결과: `select(...).with_for_update()`를 SQLite dialect로 컴파일하면 `SELECT parks.id FROM parks`만 생성되고 `FOR UPDATE`가 없다.
  - `README.md:191-204`: Gunicorn 멀티 워커 환경에서 `with_for_update()`로 완전한 직렬화를 보장한다고 설명한다.
  - `DESIGN_DECISIONS.md:382-386`: Redis 분산 락을 기각하고 SQLite 경량 지향을 유지하면서도 다중 프로세스 직렬화가 100% 보장된다고 기록한다.
  - `DESIGN_DECISIONS.md:484-486`: 분산 다중 워커 프로덕션 환경에서도 2중 정렬 락으로 안전한 격리성을 확보했다고 기록한다.
  - `app/game_engine.py:1516-1520`: `audit_report_59.md` 해결책인 밀사 overcrowding 2차 락도 `with_for_update()`에 의존한다.
- Expected: 기본 배포 DB가 SQLite라면 락 기반 보증은 SQLite의 실제 트랜잭션/쓰기 잠금 모델에 맞춰 설계되어야 한다. 또는 row-lock 지원 DB를 필수 배포 조건으로 명시하고 설정도 그 DB를 사용해야 한다.
- Actual: 기본 실행 구성은 SQLite이고, 핵심 보호 경계는 SQLite에서 작동하지 않는 `with_for_update()`에 의존한다.
- Impact: 기본 구성에서는 `audit_report_59.md`의 overcrowding Lost Update 방지, v1.8.6 NPC 개별 비관적 락, v1.8.8 AP 최종 재락 등 여러 보증이 실제 행 락으로 강제되지 않는다. 반대로 row-lock DB로 옮기면 `IMP-F001`의 호출자 레벨 선점 락 문제가 실제 deadlock으로 재발할 수 있다.
- Suggested Fix: 둘 중 하나를 선택해야 한다. SQLite를 유지한다면 원자적 `UPDATE ... WHERE`와 단일 writer transaction 중심으로 재설계하고 `with_for_update()` 보증 문구를 제거한다. row-lock DB를 목표로 한다면 PostgreSQL/MySQL 설정, migration, 테스트 DB, 배포 문서를 일치시키고 deadlock fixture를 추가한다.
- Re-audit Method: DB dialect별 SQL 컴파일 확인, 실제 배포 DB에서 병렬 regression test 실행, 문서의 "100% 보장" 표현과 실제 isolation level 대조를 수행한다.
- Owner: Architect / Coder

## [DBG-F002] 회귀 테스트 표면이 없어 이전 Critical 동시성 finding을 Verified로 닫을 수 없음

- Pass: Debug / Engineering Quality
- Pattern: `TEST-001`, `DBG-002`
- Area: 테스트, 재현성, 회귀 방지
- Severity: **Major**
- Status: **Needs Fix**
- Summary: `audit_roadmap.md`는 T19-T26 등 동시성, savepoint, AP 환불, 밀사 overcrowding, NPC deadlock 검증이 완료됐다고 기록하지만 현재 저장소에는 테스트 디렉터리, pytest 설정, 동시성 fixture가 없다.
- Evidence:
  - `find . -maxdepth 3 ... tests/pytest...`: 결과 없음
  - `git ls-files ... tests/pytest...`: 결과 없음
  - `requirements.txt`: pytest 또는 테스트 러너 의존성 없음
  - `audit_roadmap.md:174-186`: T14-T26에 복잡한 회귀 케이스가 기록되어 있다.
  - `audit_roadmap.md:126-129`: Savepoint, AP 환불, 밀사 overcrowding, NPC deadlock 해결을 검증 완료로 표시한다.
- Expected: 실제 과거 실패 모드는 이름 붙은 회귀 테스트 또는 최소한 재현 가능한 headless script/fixture로 고정되어야 한다.
- Actual: 현재 감사에서 실행 가능한 테스트 표면이 확인되지 않았다.
- Impact: 동시성/트랜잭션 수정은 정적 리뷰만으로 안전성을 보장하기 어렵다. 이후 수정자가 같은 패턴을 다시 깨뜨려도 자동 감지할 수 없다.
- Suggested Fix: SQLite 기본 모드와 row-lock DB 모드를 분리한 테스트 매트릭스를 만들고, `audit_report_57`, `59`, `61`의 실패 경로를 각각 deterministic regression으로 추가한다.
- Re-audit Method: `pytest` 또는 동등 테스트 러너로 NPC 공격, 밀사 복귀, AP 환불, debug route guard, session config를 자동 실행하고 CI/로컬 명령을 문서와 일치시키는지 확인한다.
- Owner: Coder

## [DBG-F003] `git diff --check`가 trailing whitespace로 실패함

- Pass: Debug / Engineering Quality
- Pattern: `BUILD-001`
- Area: 기본 품질 게이트
- Severity: **Minor**
- Status: **Needs Fix**
- Summary: 현재 수정된 문서와 `app/routes/game_routes.py`에 trailing whitespace가 있어 `git diff --check`가 실패한다.
- Evidence:
  - `git diff --check` 결과:
    - `DESIGN_DECISIONS.md:3`, `DESIGN_DECISIONS.md:4`, `DESIGN_DECISIONS.md:581`
    - `app/routes/game_routes.py:1088`, `1098`, `1134`, `1224`
    - `audit_roadmap.md:3`, `audit_roadmap.md:4`
    - `designs.md:3`, `designs.md:4`
    - `implementation_summary.md:3`, `implementation_summary.md:4`
    - `lessons_learned.md:3`, `lessons_learned.md:4`
    - `spec.md:3`, `spec.md:4`
- Expected: 기본 whitespace gate는 통과해야 한다.
- Actual: `git diff --check` exit code 2.
- Impact: 기능 결함은 아니지만 품질 게이트와 리뷰 노이즈를 만든다.
- Suggested Fix: trailing whitespace를 제거한다.
- Re-audit Method: `git diff --check` 재실행.
- Owner: Coder

## 7. Pass 3: Security Findings

## [SEC-F001] 배포 문서의 환경변수와 실제 설정 키가 달라 기본 시크릿 키와 DEBUG 모드가 프로덕션에 남을 수 있음

- Pass: Security
- Pattern: `SEC-001`, `SEC-002`, `SEC-003`, `BUILD-001`
- Area: Flask secret, debug route, deployment config
- Severity: **Critical**
- Status: **Needs Fix**
- Summary: `BUILD_GUIDE.md`는 `.env`에 `SECRET_KEY`와 `FLASK_ENV=production`을 쓰라고 안내하지만, 실제 `Config`는 `FLASK_SECRET_KEY`와 `DEBUG`만 읽는다. 또한 `requirements.txt`에는 `python-dotenv`가 없고 systemd 서비스에도 `EnvironmentFile`이 없어, 문서대로 만든 `.env`가 Gunicorn 실행에 적용된다는 근거가 없다.
- Evidence:
  - `BUILD_GUIDE.md:68-74`: `.env` 예시는 `FLASK_ENV=production`, `SECRET_KEY=...`, `TURN_INTERVAL=600`을 사용한다.
  - `BUILD_GUIDE.md:77`: `SECRET_KEY` 생성을 안내한다.
  - `BUILD_GUIDE.md:88-100`: systemd 서비스는 `EnvironmentFile` 없이 `PATH`만 지정하고 Gunicorn을 실행한다.
  - `app/config.py:15`: 실제 시크릿은 `FLASK_SECRET_KEY`를 읽고, 없으면 고정 문자열 `jissou-park-secret-desu-2026`을 사용한다.
  - `app/config.py:22`: 실제 DEBUG는 `DEBUG` 환경변수를 읽고 기본값이 `true`다.
  - `app/routes/game_routes.py:415-421`: `/game/debug/next-turn`은 `current_app.config.get('DEBUG')`가 True면 실행된다.
  - `DESIGN_DECISIONS.md:232-236`: 프로덕션에서는 `FLASK_ENV=production`으로 debug route가 차단된다고 설명한다.
  - `run.py:28`: 개발 서버는 `0.0.0.0`, `debug=True`로 실행된다.
- Expected: 프로덕션 문서대로 배포하면 랜덤 시크릿 키가 실제 Flask `SECRET_KEY`로 적용되고 DEBUG가 False가 되어 debug route가 차단되어야 한다. 누락 시 앱이 안전하게 실패해야 한다.
- Actual: 문서대로 `SECRET_KEY`와 `FLASK_ENV`만 설정하면 현재 코드가 읽지 않는다. `.env` 로딩 경로도 명시되어 있지 않다. 그 결과 기본 고정 secret과 DEBUG True가 유지될 수 있다.
- Impact: Flask secure cookie 기반 세션 무결성이 약화되고, debug turn endpoint가 프로덕션에 남을 수 있다. 인증된 사용자는 무한 턴 진행을 악용할 수 있으며, 기본 시크릿이 그대로라면 세션 위조 위험까지 생긴다.
- Suggested Fix: 실제 코드와 문서의 환경변수명을 일치시킨다. `FLASK_SECRET_KEY` 누락 시 시작 실패, `DEBUG` 기본 False, systemd `EnvironmentFile` 또는 명시적 `Environment=` 설정, `.env` 사용 시 `python-dotenv` 의존성 및 로딩 전략을 분명히 해야 한다.
- Re-audit Method: 깨끗한 환경에서 `env -i` 또는 최소 환경으로 app config를 출력해 `SECRET_KEY`와 `DEBUG`가 안전한 값인지 확인한다. systemd 문서 명령만 사용한 smoke에서도 `/game/debug/next-turn`이 차단되는지 확인한다.
- Owner: Coder / Operator

## [SEC-F002] 정찰/공격 모달의 `innerHTML` 렌더링이 문서화된 XSS hard boundary를 위반함

- Pass: Security
- Pattern: `SEC-008`
- Area: DOM injection
- Severity: **Major**
- Status: **Needs Fix**
- Related Finding: `IMP-F002`
- Summary: 문서가 `innerHTML` 제거와 `escapeHtml()` 사용을 보안 경계로 선언했으나, 현재 구현은 정찰 및 공격 모달에서 `innerHTML`을 사용한다.
- Evidence:
  - `app/static/js/game.js:80`, `117`, `119`, `122`, `139`: `innerHTML` 사용
  - `app/static/js/game.js:90-117`: `parkName`, scout JSON 값을 문자열 템플릿으로 조립
  - `app/templates/dashboard.html:575-578`: DB 기원 `p.name`이 data attribute로 들어간 뒤 JS에서 다시 HTML 문자열로 사용됨
  - `spec.md:733-735`, `CHANGELOG.md:151-152`: `escapeHtml()` 적용 주장
- Expected: 사용자/DB 기원 문자열은 HTML이 아닌 텍스트로 삽입되어야 한다.
- Actual: 문자열 템플릿과 `innerHTML`이 결합되어 있다.
- Impact: 현재 가입 검증에 의존하는 단일 방어선이 깨지면 DOM XSS가 재발한다. 감사 표준상 hard boundary 문서와 구현이 충돌하므로 PASS 불가다.
- Suggested Fix: `textContent`, `replaceChildren`, DOM node construction, 또는 검증된 escape helper로 전환한다.
- Re-audit Method: 악성 문자열이 포함된 공원명/오류 메시지를 fixture로 넣고 모달 렌더링 시 스크립트가 실행되지 않는지 브라우저 테스트한다.
- Owner: Coder

## 8. Cross-Pass Conflicts

## [XPF-F001] 문서는 DB 비관적 락으로 완전 해결을 주장하지만 기본 DB에서는 해당 락이 작동하지 않음

- Related Findings: `IMP-F001`, `DBG-F001`
- Conflict: 문서와 changelog는 `with_for_update()` 기반 해결을 완료로 선언한다. 그러나 기본 SQLite 구성에서는 `FOR UPDATE`가 생성되지 않아 보호 경계가 존재하지 않는다.
- Resolution: DB 지원 범위를 먼저 결정해야 한다. SQLite 유지와 row-lock DB 지원은 서로 다른 동시성 설계를 요구한다.
- Gate Impact: **HOLD**
- Required Fix Before PASS: DB dialect별 동시성 설계와 테스트 매트릭스 확정.

## [XPF-F002] 프로덕션 보안 문서는 `FLASK_ENV=production`을 authority로 삼지만 코드의 gate는 `DEBUG` 환경변수임

- Related Findings: `SEC-F001`
- Conflict: 문서상 프로덕션 전환과 실제 debug route 차단 조건이 다르다.
- Resolution: 하나의 canonical config key를 정하고 코드, 문서, systemd, 예제 env를 동기화해야 한다.
- Gate Impact: **HOLD**
- Required Fix Before PASS: 문서대로 배포한 최소 환경에서 `DEBUG=False`가 되는 증거.

## [XPF-F003] 문서는 `escapeHtml()`로 XSS를 닫았다고 하지만 렌더러는 `innerHTML`을 사용함

- Related Findings: `IMP-F002`, `SEC-F002`
- Conflict: 보안 완료 이력과 현재 렌더러 구현이 정면 충돌한다.
- Resolution: 보안 문서의 hard boundary를 구현으로 강제하거나 문서의 완료 주장을 철회해야 한다.
- Gate Impact: **HOLD**
- Required Fix Before PASS: 정찰/공격 모달의 사용자/DB 기원 문자열 텍스트 렌더링 검증.

## 9. Required Fixes Before PASS

1. `_sync_npc_turns()`가 NPC 행을 선점 락한 상태로 `process_npc_turn()`의 공격 경로에 들어가지 않도록 트랜잭션 경계를 재설계한다.
2. SQLite를 공식 기본 DB로 유지할지, row-lock 지원 DB를 프로덕션 필수로 삼을지 결정하고 문서, 설정, 테스트를 일치시킨다.
3. `with_for_update()` 기반 동시성 claim을 DB dialect별로 재검증하고, SQLite 기본 구성에서는 no-op임을 반영한다.
4. 배포 환경변수명을 코드와 문서에서 통일한다. 특히 secret key와 DEBUG 기본값은 안전 실패 방식으로 바꿔야 한다.
5. 정찰/공격 모달의 `innerHTML` 기반 사용자/DB 문자열 삽입을 제거하거나 명시적 escape helper로 감싼다.
6. `audit_report_57`, `59`, `61` 경로를 이름 붙은 회귀 테스트로 고정한다.
7. `git diff --check` 실패 항목의 trailing whitespace를 정리한다.
8. Required Files의 대소문자 규약을 실제 파일명과 동기화한다.

## 10. Accepted Risks

- 없음. 현재 Critical/Major finding은 명시적 owner, 만료 조건, 재검토 조건을 가진 Accepted Risk로 문서화되어 있지 않다.

## 11. Needs Spec Clarification

1. 공식 프로덕션 DB가 SQLite인지 PostgreSQL/MySQL 등 row-lock 지원 DB인지 명확하지 않다. 현재 문서는 SQLite zero-setup과 Gunicorn 다중 워커 완전 직렬화를 동시에 주장한다.
2. `.env` 파일을 런타임에서 누가 어떻게 로드하는지 명확하지 않다. systemd 예시는 `EnvironmentFile`을 사용하지 않는다.
3. Required Files의 canonical filename이 대문자인지 소문자인지 명확하지 않다.

## 12. Re-audit Checklist

- `rg -n "with_for_update|process_npc_turn|execute_battle|_sync_npc_turns" app`로 상위 선점 락이 제거됐는지 확인한다.
- SQLite dialect에서 no-op인 보호 경계가 문서에 남아 있는지 확인한다.
- row-lock DB에서 NPC 공격 병렬 fixture를 실행해 deadlock timeout이 없는지 확인한다.
- `rg -n "SECRET_KEY|FLASK_SECRET_KEY|DEBUG|FLASK_ENV|EnvironmentFile" .`로 설정 키가 동기화됐는지 확인한다.
- 깨끗한 배포 환경에서 `/game/debug/next-turn`이 차단되는지 확인한다.
- `rg -n "innerHTML|escapeHtml|textContent" app/static app/templates`로 XSS 경계가 실제 구현에 반영됐는지 확인한다.
- 테스트 러너로 `audit_report_57`, `59`, `61` 회귀 케이스를 실행한다.
- `git diff --check`를 통과시킨다.

## 13. Final Decision

**HOLD**

이전 감사의 핵심 Critical finding인 NPC 공격 락 순서 역전은 `process_npc_turn()` 내부가 아니라 호출자인 `_sync_npc_turns()`의 선점 락 때문에 여전히 닫히지 않았다. 또한 기본 SQLite 구성에서는 `with_for_update()` 자체가 `FOR UPDATE`를 생성하지 않아, 문서가 주장하는 다수의 비관적 락 기반 동시성 보증을 현재 배포 구성에서 Verified로 볼 수 없다. 배포 secret/debug 설정 불일치와 XSS hard boundary 구현 불일치까지 남아 있어 PASS 또는 PASS WITH KNOWN RISKS로 판정할 수 없다.
