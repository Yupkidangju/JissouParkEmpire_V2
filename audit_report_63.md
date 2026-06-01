# D3D Audit Report 63

## 1. Audit Scope

- 감사 일자: 2026-06-01
- 감사 기준: `AI_AUDIT_DOC_STANDARD.md`
- 감사 유형: 재감사, 구현 중심 상세 감사
- 프로젝트 경로: `/mnt/Projects_SSD/python/JissouParkEmpire`
- 프로젝트 유형: Flask + SQLAlchemy 기반 턴제 웹 게임
- 최종 판정: **HOLD**

이번 감사는 코드 수정 없이 현재 워크트리의 문서, 구현, 설정, 테스트를 대조했다. 직전 감사 `audit_report_62.md`와 이전 핵심 감사 `audit_report_57.md`, `audit_report_59.md`, `audit_report_61.md`의 finding이 실제 구현과 테스트에서 닫혔는지 재확인했다.

## 2. Excluded Scope

- 실제 브라우저 수동 플레이와 장시간 서버 구동은 제외했다.
- 실제 다중 프로세스 Gunicorn 부하 테스트와 PostgreSQL/MySQL 실 DB deadlock 테스트는 제외했다.
- `.antigravitycli/`, `.git/`, `__pycache__/` 산출물, `stitch_shitsiseki_empire_ui_refactor/` 참조 트리는 구현 감사 범위에서 제외했다.
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
- `audit_report_59.md`
- `audit_report_61.md`
- `audit_report_62.md`

### 확인한 주요 구현 파일

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

- `venv/bin/python -m pytest -q`: `3 passed, 65 warnings in 0.18s`
- `venv/bin/python -m pytest -q -W error::sqlalchemy.exc.SAWarning`: `3 errors`
- `venv/bin/python -c "... ast.parse ..."`: `AST_OK 15 files`
- `git diff --check`: 통과
- `rg -n "[ \t]+$" ...`: trailing whitespace 5건 발견
- SQLAlchemy dialect 컴파일 확인:
  - SQLite: `SELECT parks.id  FROM parks`
  - PostgreSQL: `SELECT parks.id  FROM parks FOR UPDATE`
- clean env 설정 확인:
  - `DEBUG=False`
  - `SECRET_LEN=48`
  - `DB=sqlite:///game.db`
- 명시 env 설정 확인:
  - `DEBUG=True`
  - `SECRET=stable-secret`
  - `DB=sqlite:///custom.db`

## 4. Previous Audit Mapping

| 이전 보고서 | 이전 finding | 현재 재감사 판정 |
| --- | --- | --- |
| `audit_report_57.md` | NPC 공격 내부 `commit()`이 nested savepoint를 깨뜨려 `ResourceClosedError`와 AP 미소모 루프를 유발 | `_npc_attack`, `_npc_cunning_attack`은 `flush()`로 변경되어 직접 원인은 완화됐다. 단, 새 테스트는 실제 NPC 공격 실패 경로를 호출하지 않아 회귀 방지 증거가 약하다. |
| `audit_report_59.md` | 밀사 처리 후 overcrowding의 무락 `refresh()` + 인메모리 변경으로 Lost Update 가능 | 코드상 `with_for_update()` 재락 시도는 추가됐지만 기본 SQLite에서는 no-op이다. 테스트도 `_process_spy_missions()` 또는 `_process_overcrowding()`을 호출하지 않는다. |
| `audit_report_61.md` | NPC 공격 시 선점 NPC 락과 `execute_battle()` canonical lock의 락 순서 역전 교착 상태 | 직전 `audit_report_62.md`의 지적 이후 `_sync_npc_turns()`가 `process_turn()` 후 commit하고 `process_npc_turn()`을 호출하도록 바뀌어 호출자 락 보유 문제는 완화됐다. 그러나 문서와 테스트가 실제 수정 구조를 따라오지 못했다. |
| `audit_report_62.md` | XSS escape helper 부재 | `app/static/js/game.js`에 `escapeHtml()`이 추가되고 동적 문자열에 적용되어 이전 결함은 대부분 해소됐다. |
| `audit_report_62.md` | 배포 env 불일치와 debug 기본값 위험 | `app/config.py`가 `SECRET_KEY`/`FLASK_SECRET_KEY`를 모두 읽고 `DEBUG=False` 기본값을 갖도록 바뀌었다. 다만 production secret 미지정 시 무작위 secret fallback은 별도 운영 리스크로 남는다. |

## 5. Pass 1: Implementation Compliance Findings

## [IMP-F001] `audit_report_62.md` 이후 실제 NPC deadlock 수정 구조가 문서 authority에 복구되지 않음

- Pass: Implementation
- Pattern: `IMP-001`, `IMP-004`, `DOC-001`, 재감사 규칙
- Area: NPC 턴 동기화, 전투 트랜잭션, 문서-구현 정합성
- Severity: **Major**
- Status: **Needs Documentation Recovery**
- Related Previous Finding: `audit_report_61.md` `[DEADLOCK-F005]`, `audit_report_62.md` `[IMP-F001]`
- Summary: 현재 구현은 `_sync_npc_turns()`에서 NPC 기본 턴 처리 후 commit으로 선점 락을 해제하고, 이후 `process_npc_turn()`을 호출하는 2단계 구조를 갖는다. 하지만 핵심 문서들은 여전히 `process_npc_turn()` 최상단 락 제거만으로 데드락이 완치됐다고 설명한다. 특히 `DESIGN_DECISIONS.md`는 "NPC 전투 트랜잭션 분리"를 기각한 대안으로 유지하지만, 실제 코드는 이미 `_sync_npc_turns()`에서 턴 처리와 NPC AI 행동 사이에 commit 경계를 둔다.
- Evidence:
  - `app/game_engine.py:175-204`: `_sync_npc_turns()`가 NPC ID 목록을 순회하고, `process_turn(npc_park)` 후 `db.session.commit()`을 수행한 뒤 `process_npc_turn(npc_park)` 및 최종 commit을 수행한다.
  - `app/game_engine.py:195-201`: 주석은 `audit_report_62.md [DEADLOCK-F005]` 수정으로 "선점 락 해제 후 NPC AI 행동"을 명시한다.
  - `app/npc_engine.py:39-41`: `process_npc_turn()` 최상단의 직접 `with_for_update()`는 제거되어 `refresh()`만 수행한다.
  - `app/battle_engine.py:39-44`: 전투는 여전히 `execute_battle()` 내부에서 두 공원을 ID 오름차순으로 `with_for_update()` 조회한다.
  - `CHANGELOG.md:15`: `audit_report_61.md` 기준의 `process_npc_turn()` 락 제거만 설명하고, `audit_report_62.md`에서 요구된 호출자 레벨 분리 수정은 기록하지 않는다.
  - `README.md:211-212`, `spec.md:109`, `designs.md:451-457`, `implementation_summary.md:338-345`: "최상단 락 제거"만 완치 근거로 제시한다.
  - `DESIGN_DECISIONS.md:647-652`: 실제 코드가 채택한 트랜잭션 분리 성격의 접근을 "기각"된 대안으로 남긴다.
- Expected: D3D `SPEC_IS_LAW` 기준으로 마스터 문서와 의사결정 문서는 실제 구현의 최종 락 경계, commit 경계, 수용한 trade-off를 정확히 설명해야 한다.
- Actual: 소스는 `audit_report_62.md` 이후 구조를 일부 반영했지만, 문서는 이전 해결 설명을 유지해 구현자가 다음 수정 시 어떤 경계를 보존해야 하는지 알 수 없다.
- Impact: 후속 구현자가 `DESIGN_DECISIONS.md`의 기각 사유를 신뢰하면 현재 deadlock 완화 구조를 되돌리거나, 반대로 문서가 말하지 않는 lock-free gap을 Accepted Risk 없이 확대할 수 있다. 이는 문서 기반 복구 가능성도 훼손한다.
- Suggested Fix: `spec.md`, `DESIGN_DECISIONS.md`, `implementation_summary.md`, `designs.md`, `README.md`, `CHANGELOG.md`, `audit_roadmap.md`를 실제 `_sync_npc_turns()` 2단계 commit 구조에 맞춰 동기화한다. 또한 lock-free gap이 의도된 trade-off인지, SQLite와 row-lock DB 각각에서 어떤 보증을 갖는지 명시한다.
- Re-audit Method: 문서에서 `DEADLOCK-F005`, `process_npc_turn`, `NPC 전투 트랜잭션 분리`, `audit_report_62`를 검색하고, 코드의 `_sync_npc_turns()` commit 경계와 같은 설명인지 대조한다.
- Owner: Architect / Coder
- Notes: 코드 자체의 직전 deadlock 원인 완화는 확인되지만, D3D 기준에서는 문서 authority drift 때문에 Verified로 닫을 수 없다.

## [IMP-F002] SQLite WAL 자동 적용 문서 주장이 구현 증거와 맞지 않음

- Pass: Implementation
- Pattern: `IMP-001`, `BUILD-001`, `DOC-001`
- Area: DB 런타임 설정, 배포 문서, 동시성 설계
- Severity: **Major**
- Status: **Needs Fix**
- Summary: 여러 문서는 SQLite 기본 실행 모드에서 WAL 모드가 자동 적용되어 `with_for_update()` no-op 제약을 보완한다고 설명한다. 그러나 코드와 설정에서 `PRAGMA journal_mode=WAL`, `busy_timeout`, `connect_args`, `SQLALCHEMY_ENGINE_OPTIONS` 등 WAL/locking 관련 설정을 찾을 수 없다.
- Evidence:
  - `spec.md:96`: SQLite 기본 실행 모드에서 DB 파일 단일 writer lock 및 WAL 모드로 동시성 정합성을 보완한다고 설명한다.
  - `spec.md:759`: `SQLite 동시 쓰기 병목` 대응을 `WAL 모드 (자동), 단일 서버`로 기록한다.
  - `DESIGN_DECISIONS.md:383`: SQLite 환경에서 WAL 적용과 DB 파일 write lock으로 정합성을 보완한다고 기록한다.
  - `implementation_summary.md:208`: SQLite 모드에서 WAL 모드와 DB 파일 수준 단일 쓰기 lock이 상호 보완한다고 기록한다.
  - `BUILD_GUIDE.md:222`: `SQLite WAL 모드` 설정을 `자동 적용`으로 표시한다.
  - `rg -n "journal_mode|WAL|PRAGMA|BEGIN IMMEDIATE|busy_timeout|connect_args|SQLALCHEMY_ENGINE_OPTIONS" app run.py requirements.txt spec.md DESIGN_DECISIONS.md implementation_summary.md BUILD_GUIDE.md lessons_learned.md`: 구현 파일에서는 WAL 활성화 코드를 확인하지 못했고 문서 주장만 확인됐다.
  - `app/config.py:36-38`: DB URI와 track modifications만 설정한다.
- Expected: WAL 자동 적용을 문서화하려면 앱 초기화 또는 엔진 설정에서 실제 SQLite PRAGMA 적용 근거가 있어야 한다. 자동 적용이 아니라면 문서는 "운영자가 별도 설정" 또는 "미적용"으로 써야 한다.
- Actual: 문서는 WAL이 자동이라고 주장하지만 구현 증거가 없다.
- Impact: 기본 SQLite 배포에서 동시성 보완책을 실제보다 강하게 믿게 만든다. 특히 `with_for_update()` no-op 문제를 WAL이 보완한다는 설명은 실제 설정 없이는 운영 리스크를 숨긴다.
- Suggested Fix: SQLite 유지가 목표라면 앱 시작 시 WAL/busy timeout 적용 여부를 명확히 구현하고 검증 로그 또는 테스트를 추가한다. 구현하지 않을 경우 문서의 "자동 적용" 표현을 제거하고 row-lock DB 또는 단일 워커 운영 조건을 명시한다.
- Re-audit Method: 앱 생성 후 실제 DB에 `PRAGMA journal_mode`를 질의하고, 코드에서 PRAGMA 적용 위치와 실패 처리 정책을 확인한다.
- Owner: Architect / Coder

## [IMP-F003] `escapeHtml()` 기반 XSS 회귀는 구현상 대부분 해소됐지만 문서의 `innerHTML` 금지 규칙과 잔여 패턴이 충돌함

- Pass: Implementation
- Pattern: `IMP-001`, `SEC-008`
- Area: 프론트엔드 렌더링, 문서-구현 정합성
- Severity: **Minor**
- Status: **Needs Documentation Recovery**
- Related Previous Finding: `audit_report_62.md` `[IMP-F002]`
- Summary: 직전 감사에서 없던 `escapeHtml()` helper가 현재 `app/static/js/game.js`에 추가됐고, 정찰/공격 모달의 동적 문자열에 적용된다. 다만 `lessons_learned.md`는 `innerHTML 사용 금지`를 일반 원칙으로 기록하는 반면, 실제 구현은 고정 HTML scaffold와 escape 처리된 문자열을 `innerHTML`로 계속 사용한다.
- Evidence:
  - `app/static/js/game.js:9-20`: `escapeHtml(str)`가 `&`, `<`, `>`, `"`, `'`, `/`를 escape한다.
  - `app/static/js/game.js:103-133`: 정찰 모달의 `parkName`, `data.error`가 `escapeHtml()`을 통과한다.
  - `app/static/js/game.js:145-153`: 공격 모달 제목의 `targetName`이 `escapeHtml()`을 통과한다.
  - `app/static/js/game.js:94`, `131`, `133`, `136`, `153`: 렌더링 자체는 여전히 `innerHTML`을 사용한다.
  - `lessons_learned.md:148`: `innerHTML 사용 금지`와 `textContent`/`escapeHtml()` 기본 사용을 원칙으로 기록한다.
- Expected: 프로젝트가 `innerHTML` 자체를 금지하는 정책인지, escape된 동적 문자열과 고정 HTML scaffold 조합을 허용하는 정책인지 명확해야 한다.
- Actual: 구현은 escape helper 방식이고 문서는 일부 위치에서 전면 금지처럼 읽힌다.
- Impact: 현재 XSS 직접 재발 증거는 줄었지만, 후속 구현자가 `innerHTML` 사용 자체를 금지로 해석하거나, 반대로 escape 누락 `innerHTML`을 허용하는 혼선을 만들 수 있다.
- Suggested Fix: 문서 원칙을 "동적/외부 기원 문자열은 `textContent` 또는 `escapeHtml()` 필수, 고정 scaffold HTML만 제한적으로 허용"처럼 구체화하거나, 구현을 DOM node construction 중심으로 바꾼다.
- Re-audit Method: `rg -n "innerHTML|escapeHtml|textContent" app/static app/templates` 결과에서 모든 동적 문자열이 escape 또는 text node 경로인지 확인한다.
- Owner: Architect / Coder

## 6. Pass 2: Debug / Engineering Quality Findings

## [DBG-F001] 기본 SQLite 구성에서 `with_for_update()` 기반 동시성 보증은 여전히 실제 행 락으로 검증되지 않음

- Pass: Debug / Engineering Quality
- Pattern: `DBG-001`, `ARCH-001`, `BUILD-001`
- Area: DB 락 경계, 동시성 보증, 배포 구성
- Severity: **Critical**
- Status: **Needs Fix**
- Related Previous Findings: `audit_report_47.md`, `audit_report_48.md`, `audit_report_54.md`, `audit_report_56.md`, `audit_report_59.md`, `audit_report_61.md`, `audit_report_62.md`
- Summary: 현재 기본 DB URI는 SQLite이며, SQLAlchemy SQLite dialect에서 `with_for_update()`는 `FOR UPDATE` SQL을 생성하지 않는다. 그럼에도 보호 모드, NPC 동기화, 밀사 overcrowding, 전투, 외교 등 다수의 안전 주장이 `with_for_update()`에 의존한다.
- Evidence:
  - `app/config.py:36-38`: 기본 `SQLALCHEMY_DATABASE_URI`는 `sqlite:///game.db`다.
  - SQLAlchemy 컴파일 확인:
    - SQLite: `SELECT parks.id  FROM parks`
    - PostgreSQL: `SELECT parks.id  FROM parks FOR UPDATE`
  - `app/game_engine.py:185`: `_sync_npc_turns()`는 각 NPC를 `with_for_update().first()`로 조회한다.
  - `app/game_engine.py:1522-1527`: `_process_spy_missions()` 후 overcrowding 처리 직전 `with_for_update()`와 `refresh()`를 수행한다.
  - `app/battle_engine.py:39-44`: 전투는 두 공원에 대한 `with_for_update()`에 의존한다.
  - `README.md:192`, `README.md:204`, `README.md:210`, `README.md:212`: 다중 워커와 동시 요청에서 완전 해결을 주장한다.
  - `spec.md:96`, `implementation_summary.md:208`, `DESIGN_DECISIONS.md:383`: SQLite no-op을 인정하면서도 WAL/파일 lock으로 보완한다고 설명한다.
- Expected: 기본 배포 DB가 SQLite라면 동시성 보증은 SQLite에서 실제로 강제되는 원자적 UPDATE, explicit transaction, `BEGIN IMMEDIATE`, 단일 writer 정책, 단일 worker 운영 조건 등으로 설명되고 테스트되어야 한다. row-lock DB 보증을 요구한다면 배포 기본값과 테스트 DB도 PostgreSQL/MySQL로 맞춰야 한다.
- Actual: 기본 구성은 SQLite이고, 여러 핵심 경계는 SQLite에서 no-op인 `with_for_update()`를 해결책으로 둔다.
- Impact: 문서상 "완전 차단"된 Lost Update나 Stampede가 기본 실행 구성에서는 실제 행 락으로 차단되지 않을 수 있다. 반대로 row-lock DB로 이전하면 commit 경계와 lock-free gap 설계가 별도 검증 없이 새로운 deadlock 또는 stale overwrite 위험을 만들 수 있다.
- Suggested Fix: 아키텍처를 둘 중 하나로 결정해야 한다. SQLite를 유지한다면 SQLite-native 원자 연산과 명시 트랜잭션으로 재설계하고 `with_for_update()`를 미래 이식성 힌트로만 낮춘다. row-lock DB를 production 기준으로 삼는다면 DB 설정, migration, CI, 부하 테스트, deadlock timeout 테스트를 포함한다.
- Re-audit Method: SQLite와 PostgreSQL/MySQL 두 dialect에서 동일 회귀 테스트를 실행하고, `with_for_update()`가 실제 SQL과 락 대기 동작으로 이어지는지 확인한다.
- Owner: Architect / Coder

## [DBG-F002] 새 회귀 테스트가 실제 실패 경로를 호출하지 않아 이전 Critical finding을 Verified로 닫기 어렵다

- Pass: Debug / Engineering Quality
- Pattern: `TEST-001`, `DBG-002`, 재감사 규칙
- Area: 회귀 테스트, 동시성 테스트, 실패 경로 재현성
- Severity: **Major**
- Status: **Needs Fix**
- Summary: `tests/test_regression.py`가 추가되어 `pytest`는 통과한다. 그러나 세 테스트는 핵심 실패 경로를 대부분 직접 실행하지 않거나, SQLite no-op 락을 확인하는 수준이다. 따라서 `audit_report_57`, `audit_report_59`, `audit_report_61/62`의 실제 회귀 방지 증거로는 부족하다.
- Evidence:
  - `requirements.txt:7-8`: `python-dotenv`, `pytest`가 추가됐다.
  - `tests/conftest.py:7-23`: 테스트 DB를 `sqlite:///:memory:`로 설정한다.
  - `tests/test_regression.py:12-52`: savepoint 테스트는 수동 `begin_nested()`, 수동 `flush()`, 수동 예외만 검증한다. 실제 `_npc_attack()`, `_npc_cunning_attack()`, `process_npc_turn()` 예외 처리 경로를 강제로 실행하지 않는다.
  - `tests/test_regression.py:55-79`: 밀사 overcrowding 테스트는 `Park.query...with_for_update().first()`와 `refresh()` 후 `adult_count > population_cap`만 검증한다. `_process_spy_missions()` 또는 `_process_overcrowding()` 호출, 병렬 writer, lost update 검증이 없다.
  - `tests/test_regression.py:82-119`: NPC deadlock 테스트는 `_sync_npc_turns()`를 import하지만 호출하지 않는다. `process_turn()`과 `process_npc_turn()`를 수동 순서로 호출하며, 공격 대상/전투 실행/row-lock DB deadlock 조건을 만들지 않는다.
  - `venv/bin/python -m pytest -q`: `3 passed, 65 warnings`.
- Expected: 회귀 테스트는 과거 실패를 일으킨 실제 public/internal path를 최소 한 번 호출하고, 실패 조건이 재도입되면 실패해야 한다.
- Actual: 테스트는 변경 의도를 시뮬레이션하지만 실제 위험 경로를 충분히 고정하지 않는다.
- Impact: 구현이 다시 `commit()`을 NPC 공격 내부에 넣거나, `_sync_npc_turns()` 호출 경계를 깨거나, overcrowding lock을 제거해도 현재 테스트가 잡지 못할 가능성이 높다.
- Suggested Fix: 각 감사 finding마다 deterministic fixture를 만든다. `audit_report_57`은 NPC 공격 함수가 nested savepoint 안에서 실제 `execute_battle()`까지 들어가도록 강제한다. `audit_report_59`는 concurrent update 또는 두 세션 기반 stale overwrite를 재현한다. `audit_report_61/62`는 `_sync_npc_turns()` 자체를 호출하고 공격 행동을 강제하며 row-lock DB 매트릭스를 추가한다.
- Re-audit Method: 위험 코드를 되돌린 mutant patch가 테스트에서 실패하는지 확인한다. 최소한 monkeypatch/random seed로 NPC 공격 경로와 밀사 복귀 경로를 결정적으로 실행한다.
- Owner: Coder

## [DBG-F003] SQLAlchemy relationship 경고가 warning-clean 테스트 게이트를 차단함

- Pass: Debug / Engineering Quality
- Pattern: `DBG-001`, `TEST-001`, `MAINT-001`
- Area: ORM 모델, mapper configuration, 테스트 품질
- Severity: **Major**
- Status: **Needs Fix**
- Summary: 일반 `pytest`는 통과하지만 65개 warning을 낸다. 특히 SQLAlchemy `SAWarning`을 에러로 승격하면 모든 테스트가 setup 단계에서 실패한다. 경고 내용은 `TradeOffer`, `Diplomacy`, `SpyMission`의 관계가 동일 FK 컬럼을 중복으로 copy할 수 있다는 mapper conflict다.
- Evidence:
  - `venv/bin/python -m pytest -q`: `3 passed, 65 warnings`.
  - `venv/bin/python -m pytest -q -W error::sqlalchemy.exc.SAWarning`: `3 errors`.
  - 첫 에러: `relationship 'TradeOffer.sender' will copy column parks.id to column trade_offers.sender_id, which conflicts with relationship(s): 'Park.sent_trade_offers', 'TradeOffer.sender_park'`.
  - `app/models.py:147-169`: `Park`에 `TradeOffer`, `Diplomacy`, `SpyMission` 관련 backref 관계가 정의되어 있다.
  - `app/models.py:380`, `428-429`, `466-467`: 동일 FK에 대해 `TradeOffer.sender`, `Diplomacy.park_a/park_b`, `SpyMission.sender/target` 관계가 별도로 정의되어 있다.
- Expected: ORM 관계는 `back_populates`, `overlaps`, `viewonly=True` 등으로 의도를 명시해 mapper warning 없이 초기화되어야 한다.
- Actual: SQLAlchemy가 쓰기 대상 FK 충돌 가능성을 경고하고, warning-as-error 품질 게이트가 실패한다.
- Impact: 단순 노이즈로 볼 수도 있지만, 이 프로젝트는 교역/외교/밀사처럼 상태 전이가 복잡하다. ORM 관계 충돌 경고를 방치하면 실제 write path에서 예기치 않은 relationship sync 또는 리뷰 누락으로 이어질 수 있다.
- Suggested Fix: 각 관계의 단일 authoritative relationship을 정하고 `back_populates`로 양방향 관계를 명시한다. 읽기 편의 alias라면 `viewonly=True` 또는 정확한 `overlaps`를 추가한다.
- Re-audit Method: `venv/bin/python -m pytest -q -W error::sqlalchemy.exc.SAWarning`이 통과해야 한다.
- Owner: Coder

## [DBG-F004] `git diff --check`는 통과하지만 전체 현재 파일 기준 trailing whitespace가 남아 있음

- Pass: Debug / Engineering Quality
- Pattern: `BUILD-001`, `MAINT-001`
- Area: whitespace, 리뷰 품질, untracked test files
- Severity: **Minor**
- Status: **Needs Fix**
- Summary: tracked diff 기준 `git diff --check`는 통과한다. 그러나 새로 추가된 untracked 테스트 파일과 JS 파일까지 포함해 검색하면 trailing whitespace가 남아 있다.
- Evidence:
  - `git diff --check`: 통과.
  - `rg -n "[ \t]+$" tests app/static/js/game.js ...` 결과:
    - `app/static/js/game.js:202`
    - `tests/test_regression.py:15`
    - `tests/test_regression.py:39`
    - `tests/test_regression.py:49`
    - `tests/test_regression.py:58`
- Expected: 저장소에 추가될 파일은 tracked/untracked 여부와 무관하게 기본 whitespace gate를 통과해야 한다.
- Actual: untracked 테스트 파일과 현재 JS 파일에 trailing whitespace가 있다.
- Impact: 기능 결함은 아니지만, 새 테스트 도입 시 리뷰 노이즈와 품질 게이트 실패 가능성을 만든다.
- Suggested Fix: trailing whitespace를 제거하고, untracked 파일 포함 lint 또는 pre-commit 범위를 정한다.
- Re-audit Method: 동일 `rg` 명령과 `git diff --check`를 모두 재실행한다.
- Owner: Coder

## 7. Pass 3: Security Findings

## [SEC-F001] Production secret 미지정 시 무작위 fallback이 보안 기본값은 개선하지만 다중 워커/재시작 세션 안정성을 깨뜨릴 수 있음

- Pass: Security
- Pattern: `SEC-001`, `SEC-002`, `BUILD-001`
- Area: Flask `SECRET_KEY`, deployment config, session stability
- Severity: **Major**
- Status: **Needs Spec Clarification**
- Related Previous Finding: `audit_report_62.md` `[SEC-F001]`
- Summary: 직전 감사의 env 불일치와 debug 기본값 문제는 대부분 개선됐다. `Config`는 `SECRET_KEY`와 `FLASK_SECRET_KEY`를 모두 읽고, `DEBUG` 기본값은 false다. 하지만 secret이 없을 때 `os.urandom(24).hex()`로 매 프로세스마다 secret을 생성한다. 이는 하드코딩 secret보다 안전하지만, production에서 secret 누락을 조용히 통과시키면 Gunicorn 다중 worker 또는 재시작 시 사용자 session이 worker마다 불일치하거나 전체 로그아웃될 수 있다.
- Evidence:
  - `app/config.py:25-34`: `SECRET_KEY` 또는 `FLASK_SECRET_KEY`가 없으면 `os.urandom(24).hex()`로 생성한다.
  - `app/config.py:40-43`: `DEBUG`는 명시 `true`, `1`, `yes`가 아니면 false다.
  - `requirements.txt:7`: `python-dotenv`가 추가됐다.
  - `BUILD_GUIDE.md:68-74`: `.env` 예시는 `SECRET_KEY`를 안내한다.
  - `BUILD_GUIDE.md:88-95`: systemd 서비스에 `EnvironmentFile=/opt/jissou-park/.env`가 추가됐다.
  - clean env 확인: `DEBUG=False`, `SECRET_LEN=48`, `DB=sqlite:///game.db`.
  - 명시 env 확인: `DEBUG=True`, `SECRET=stable-secret`, `DB=sqlite:///custom.db`.
- Expected: production 기준 secret 누락은 fail-closed로 서버 시작을 중단하거나, dev/test 전용 fallback임을 config/env로 명확히 제한해야 한다.
- Actual: 환경변수 누락 시에도 서버가 무작위 secret으로 시작한다.
- Impact: 다중 worker 환경에서 각 프로세스가 서로 다른 secret을 가지면 signed cookie/session 검증이 worker별로 달라질 수 있다. 재시작 때도 전체 session이 무효화된다. 공격자가 곧바로 secret을 아는 상태는 아니지만, 운영 안정성과 인증 경계 예측 가능성 측면에서 production에는 부적합하다.
- Suggested Fix: `ENV_TYPE`, `FLASK_ENV`, `DEBUG`, 별도 `ALLOW_RANDOM_SECRET_FOR_DEV` 등 명시 조건으로 dev fallback을 제한한다. production 문서에는 `SECRET_KEY` 누락 시 시작 실패가 기대 동작이라고 기록한다.
- Re-audit Method: production env에서 `SECRET_KEY` 없이 app import/create 시 실패하는지, dev/test env에서만 random fallback이 허용되는지 확인한다.
- Owner: Architect / Human / Coder

## [SEC-F002] DOM XSS 직전 finding은 직접 취약점에서 문서 정책 정리 문제로 낮아졌지만 테스트가 없음

- Pass: Security
- Pattern: `SEC-008`, `TEST-001`
- Area: 프론트엔드 XSS, 정찰 모달, 공격 모달
- Severity: **Minor**
- Status: **Needs Fix**
- Related Previous Finding: `audit_report_62.md` `[IMP/SEC-F002]`
- Summary: `escapeHtml()` 도입으로 이전의 명시적 helper 부재는 해소됐다. 그러나 악성 공원명 fixture가 정찰/공격 모달에서 HTML로 실행되지 않는다는 자동 테스트 또는 브라우저 검증은 없다.
- Evidence:
  - `app/static/js/game.js:9-20`: escape helper 존재.
  - `app/static/js/game.js:105`, `133`, `136`, `153`: 동적 문자열에 helper 적용.
  - `tests/test_regression.py`: 프론트엔드 DOM/XSS 테스트 없음.
- Expected: 과거 XSS 회귀는 최소한 악성 이름 fixture와 렌더링 결과 검증으로 고정해야 한다.
- Actual: 구현은 개선됐지만 회귀 테스트는 없다.
- Impact: 향후 정찰 모달 필드가 추가되거나 다른 DOM 삽입 경로가 생길 때 escape 누락을 자동 감지하지 못한다.
- Suggested Fix: JS unit test, Playwright/Selenium, 또는 최소 DOM fixture 테스트로 `<img onerror=...>` 형태의 이름이 텍스트로만 표시되는지 검증한다.
- Re-audit Method: `rg -n "innerHTML" app/static`와 악성 fixture 렌더링 테스트를 함께 실행한다.
- Owner: Coder

## 8. Cross-Pass Conflicts

## [XPF-F001] "SQLite zero-setup"과 "다중 워커 완전 직렬화"가 동시에 문서 authority로 남아 있음

- Pass: Cross-Pass
- Pattern: `ARCH-001`, `DOC-001`, `SEC-002`
- Area: DB 선택, 배포 모델, 동시성 보안 경계
- Severity: **Critical**
- Status: **Hold**
- Summary: 프로젝트는 SQLite zero-setup을 장점으로 유지하면서도 Gunicorn 다중 워커에서 `with_for_update()` 기반 완전 직렬화를 반복 주장한다. SQLite dialect 확인상 `with_for_update()`는 no-op이고, WAL 자동 적용 구현도 확인되지 않는다.
- Evidence:
  - `app/config.py:36-38`: 기본 DB는 SQLite.
  - SQLite 컴파일 결과: `FOR UPDATE` 없음.
  - `BUILD_GUIDE.md:95-97`: Gunicorn `--workers 2` 구동을 안내한다.
  - `README.md:192`, `spec.md:98`, `implementation_summary.md:208`: 프로세스 안전 직렬화를 주장한다.
- Expected: 배포 모델은 "SQLite 단일 worker/제한적 동시성" 또는 "row-lock DB 기반 다중 worker" 중 하나로 hard boundary를 명확히 해야 한다.
- Actual: 문서는 두 목표를 모두 만족한다고 주장하지만 구현 증거가 부족하다.
- Impact: 운영자가 문서대로 `workers 2` + SQLite를 사용할 때, 동시성 결함이 재현되어도 문서상 원인을 찾기 어렵다.
- Suggested Fix: production support matrix를 작성한다. SQLite는 단일 worker/명시 transaction만 지원한다고 제한하거나, PostgreSQL/MySQL을 production 기준으로 승격한다.
- Re-audit Method: support matrix, config default, BUILD_GUIDE, 테스트 DB 매트릭스가 같은 결론을 말하는지 확인한다.
- Owner: Architect / Human

## [XPF-F002] 테스트 통과와 품질 검증 통과가 같은 의미로 기록될 위험이 있음

- Pass: Cross-Pass
- Pattern: `TEST-001`, `DBG-002`, `DOC-001`
- Area: 테스트 신뢰도, 감사 기록
- Severity: **Major**
- Status: **Needs Fix**
- Summary: `pytest`는 3개 테스트를 통과하지만, 테스트는 핵심 실패 경로와 실제 DB 락 동작을 충분히 검증하지 않는다. 또한 warning-clean 게이트는 실패한다. 따라서 "테스트 통과"를 "이전 Critical finding Verified"로 기록하면 감사 기록이 과장된다.
- Evidence:
  - `venv/bin/python -m pytest -q`: `3 passed, 65 warnings`.
  - `venv/bin/python -m pytest -q -W error::sqlalchemy.exc.SAWarning`: `3 errors`.
  - `tests/test_regression.py:55-79`: lost update 방지가 아니라 단순 비교 assertion.
  - `tests/test_regression.py:82-119`: `_sync_npc_turns()` 자체 미호출.
- Expected: 감사 문서는 "테스트 명령 통과"와 "회귀 finding 검증 완료"를 구분해야 한다.
- Actual: 현재 테스트 이름과 주석은 `완치 검증`을 강하게 주장하지만 실제 검증 범위는 좁다.
- Impact: 다음 감사자 또는 구현자가 false confidence를 갖고 동시성 문제를 종결 처리할 수 있다.
- Suggested Fix: 테스트 이름, 주석, 문서 판정을 실제 검증 범위에 맞게 낮추고, 누락된 결정적 회귀 테스트를 추가한다.
- Re-audit Method: 테스트가 실제 위험 경로를 호출하는지 coverage 또는 call spy로 확인한다.
- Owner: Auditor / Coder

## 9. Required Fixes Before PASS

- `spec.md`, `DESIGN_DECISIONS.md`, `implementation_summary.md`, `designs.md`, `README.md`, `CHANGELOG.md`, `audit_roadmap.md`를 `_sync_npc_turns()`의 실제 2단계 commit 구조와 일치시킨다.
- SQLite 기본 구성에서 `with_for_update()` no-op을 보완할 실제 동시성 설계를 확정한다.
- WAL 자동 적용 주장을 구현하거나 문서에서 제거한다.
- `audit_report_57`, `audit_report_59`, `audit_report_61/62`의 실제 실패 경로를 호출하는 결정적 회귀 테스트를 추가한다.
- SQLAlchemy relationship warning을 제거하고 warning-as-error 테스트를 통과시킨다.
- production secret 누락 정책을 fail-closed 또는 dev-only fallback으로 명확히 한다.
- XSS escape 경로를 자동 테스트로 고정한다.

## 10. Accepted Risks

- 현재 감사에서는 새 Accepted Risk를 인정하지 않았다.
- SQLite `with_for_update()` no-op과 WAL 미구현은 문서에 일부 언급되어 있으나, owner, 만료 조건, production support matrix, 재검토 조건이 부족하므로 `Accepted Risk`가 아니라 `Hold`로 판정한다.
- `innerHTML` 사용은 모든 동적 문자열에 escape가 적용된 범위에서는 낮은 위험으로 보지만, 정책과 테스트가 부족해 완전 Accepted Risk로 처리하지 않는다.

## 11. Needs Spec Clarification

- production 공식 DB가 SQLite인지 PostgreSQL/MySQL 등 row-lock DB인지 결정해야 한다.
- SQLite를 유지한다면 Gunicorn 다중 worker를 공식 지원하는지, 단일 worker로 제한하는지 결정해야 한다.
- `with_for_update()`는 현재 기능 보증 수단인지, 미래 DB 이식성을 위한 코드 형태인지 명확히 해야 한다.
- production에서 `SECRET_KEY` 누락 시 서버 시작 실패가 맞는지, 무작위 fallback으로 시작하는 것이 허용되는지 결정해야 한다.
- `innerHTML` 정책은 전면 금지인지, escape된 동적 문자열 + 고정 scaffold 조합을 허용하는지 결정해야 한다.

## 12. Re-audit Checklist

- `venv/bin/python -m pytest -q`
- `venv/bin/python -m pytest -q -W error::sqlalchemy.exc.SAWarning`
- `git diff --check`
- `rg -n "[ \t]+$" tests app/static/js/game.js app/*.py app/routes/*.py spec.md README.md CHANGELOG.md BUILD_GUIDE.md DESIGN_DECISIONS.md designs.md implementation_summary.md lessons_learned.md audit_roadmap.md`
- `rg -n "journal_mode|WAL|PRAGMA|BEGIN IMMEDIATE|busy_timeout|connect_args|SQLALCHEMY_ENGINE_OPTIONS" app run.py requirements.txt`
- SQLAlchemy SQLite/PostgreSQL dialect별 `with_for_update()` 컴파일 비교
- `_sync_npc_turns()`가 실제로 호출되는 NPC 공격 회귀 테스트
- `_process_spy_missions()`와 `_process_overcrowding()`이 실제로 호출되는 lost update 회귀 테스트
- 악성 공원명 DOM 렌더링 XSS 회귀 테스트
- production env에서 `SECRET_KEY` 누락 동작 확인

## 13. Final Decision

**HOLD**

구현은 직전 `audit_report_62.md` 이후 일부 핵심 문제를 개선했다. 특히 `escapeHtml()` 부재, debug 기본값, env key 불일치, `_sync_npc_turns()`의 호출자 레벨 선점 락 문제는 완화됐다.

그러나 PASS로 올릴 수 없다. 이유는 다음 세 가지다.

1. 문서 authority가 실제 동시성 수정 구조를 따라오지 못했다.
2. 기본 SQLite 구성에서 `with_for_update()` 기반 보증과 WAL 자동 적용 주장이 구현 증거로 뒷받침되지 않는다.
3. 새 회귀 테스트는 존재하지만 실제 실패 경로와 warning-clean 품질 게이트를 충분히 검증하지 못한다.

다음 재감사는 DB support matrix 확정, 문서 복구, 결정적 회귀 테스트 추가, SQLAlchemy warning 제거 이후 수행해야 한다.
