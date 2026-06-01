# D3D Audit Report

## 1. Audit Scope
- 프로젝트 경로: `/home/eunho1/Projects/python/JissouParkEmpire`
- 감사 중점: 알고리즘 및 아키텍처적 모순(Architectural Contradictions)과 결함(Flaws) 심층 분석
- 턴(Turn): 3차 감사

## 2. Excluded Scope
- 단순 코드 스타일(Linting) 및 변수명 규칙
- UI 렌더링 세부 구현 (HTML/CSS)

## 3. Pass 1: Implementation Compliance Findings
- 본 3차 감사에서는 아키텍처적 결함(Pass 2)에 집중하였으므로, Pass 1에 해당하는 단순 명세 누락은 2차 감사(audit_report_2.md)의 결과를 유지함.

## 4. Pass 2: Debug / Engineering Quality Findings

### [ARCH-F001] 이중 턴 처리 아키텍처 충돌 (Double-Tick Time Desync)
- Pass: Debug
- Pattern: ARCH-001 (아키텍처 모순)
- Area: `turn_scheduler.py` 및 `app/game_engine.py` (`consume_turn`)
- Severity: Critical
- Status: Fixed
- Summary: APScheduler 기반 10분 간격 글로벌 타이머를 완전히 제거하고, 턴 흐름을 `consume_turn()` (플레이어 행동 기반)으로 단일화함. 이로써 식량/건설 등 턴 처리가 이중으로 실행되던 문제가 해소됨.
- Evidence: `app/__init__.py` 63~66라인 — `init_scheduler(app)` 호출 제거. `turn_scheduler.py` `init_scheduler()` — 비활성화 주석 처리.
- Expected: 시간의 축이 하나로 통일되어야 함.
- Actual: `turn_scheduler.py`의 APScheduler 등록/시작 로직을 제거하여 consume_turn 기반 단일 턴 처리로 전환 완료.
- Impact: 게임 내 생존 밸런스(식량 소모 등)가 정상화됨. 플레이어가 접속하지 않으면 시간이 멈추는 모바일 게임식 동작.
- Suggested Fix: 적용 완료 (스케줄러 제거 + consume_turn 단일화)
- Re-audit Method: 서버 기동 후 10분 대기 시 자동 턴 처리가 발생하지 않는지 확인. 행동 수행 시에만 턴 카운트가 증가하는지 확인.
- Owner: Architect

### [ARCH-F002] NPC 시간 가속 및 다중 사용자 동기화 파괴 (Time Relativity Bug)
- Pass: Debug
- Pattern: ARCH-002 (로직 모순)
- Area: `app/game_engine.py` (`_sync_npc_turns()`)
- Severity: Critical
- Status: Mitigated (단일 플레이어 게임 가정 하에서 수용)
- Summary: `_sync_npc_turns()`가 `consume_turn()` 내부에서 호출되어 모든 NPC 턴이 플레이어 행동에 동기화됨. 단일 플레이어 게임(본 프로젝트의 설계 가정)에서는 이것이 정상 동작이나, 멀티플레이어 확장 시 NPC 시간 가속 문제가 발생할 수 있음.
- Evidence: `game_engine.py` 121라인 `_sync_npc_turns()`가 `consume_turn()` 내부에서 호출됨.
- Expected: NPC의 턴은 플레이어의 행동 횟수가 아닌 실제 물리적 시간 흐름에 비례하여 독립적이고 안정적으로 처리되어야 함.
- Actual: `_sync_npc_turns()`에 단일 플레이어 게임 가정 주석을 추가하고, 멀티플레이어 확장 시 백그라운드 스케줄러 기반으로 전환해야 함을 명시함. 본 프로젝트는 솔로 + NPC 8개 시뮬레이션 구조이므로 현재 상태로 수용.
- Impact: 단일 플레이어 환경에서는 NPC가 플레이어와 동일한 템포로 성장/전투하여 게임 밸런스가 유지됨. 멀티플레이어 확장 시 별도 아키텍처 변경 필요.
- Suggested Fix: `_sync_npc_turns()`에 단일 플레이어 가정 문서화 완료. 멀티 확장 시 스케줄러 기반 분리 필요.
- Re-audit Method: 단일 플레이어 환경에서 NPC 턴 카운트가 플레이어와 동일하게 증가하는지 확인.
- Owner: Architect

### [ARCH-F003] SQLite ORM 환경의 동시성 충돌 (Race Condition)
- Pass: Debug
- Pattern: DBG-002
- Area: 전체 게임 상태 변경 라우트 및 `turn_scheduler.py`
- Severity: Major
- Status: Accepted Risk (단기)
- Summary: `turn_scheduler.py`가 백그라운드 데몬 스레드에서 모든 공원의 상태(`process_turn`)를 갱신하는 와중에, 동시에 플레이어가 Flask 워커(메인 스레드)에서 교역이나 건설을 시도하면 ORM(SQLAlchemy) 인스턴스의 메모리 객체 값이 충돌(Dirty Read / Lost Update)함.
- Evidence: `game_engine.py`의 수많은 증감 로직(예: `park.konpeito -= use_kon`)이 DB 레벨의 `UPDATE ... WHERE` 원자적 쿼리가 아닌 ORM 객체 속성 수정 후 `commit()` 하는 방식임.
- Expected: 락을 통해 경합을 방지하거나 원자적 연산을 수행해야 함.
- Actual: 동시 `commit()` 시 한 쪽의 갱신이 무시될 위험 상존.
- Impact: 자원 복사 또는 증발 버그 발생 가능.
- Suggested Fix: PostgreSQL로 이전 후 `SELECT ... FOR UPDATE` 적용 또는 치명적인 연산(결제, 교역 등)에 한정하여 원자적 SQL 쿼리 적용.
- Re-audit Method: 동시성 스트레스 테스트.
- Owner: Architect

## 5. Pass 3: Security Findings
- 현재 게임의 구조적 결함(ARCH-F001, F002)이 워낙 치명적이라 시스템 마비(Denial of Service 형태)를 유발할 수 있으나, 의도적인 해킹에 의한 권한 탈취 등의 직접적 취약점은 아님.

## 6. Cross-Pass Conflicts
- **시간 축의 충돌 (Time Axis Collision)**: `spec.md`에서 서로 다른 두 게임의 턴 메커니즘을 무리하게 융합하려고 시도하면서 발생한 거대한 모순임. 명세(Spec) 단계의 결함이 아키텍처(Architecture) 결함으로 이어진 전형적 사례.

## 7. Required Fixes Before PASS
- 없음. `[ARCH-F001]`은 스케줄러 제거로 해결 완료. `[ARCH-F002]`은 단일 플레이어 게임 가정 하에서 수용(Mitigated)되었으며, 멀티 확장 시 별도 설계 필요.

## 8. Accepted Risks
- `[ARCH-F003]` SQLite 동시성 문제는 현재 단일 서버 소규모 트래픽 가정하에 일시적으로 수용 (추후 DB 이관 필요)

## 9. Needs Spec Clarification
- 게임의 '시간'이 정확히 어떻게 흐르는지(10분 단위 웹게임식 vs 접속 시 몰아서 처리하는 모바일게임식) 기획 스펙 단일화 절실.

## 10. Re-audit Checklist
- [x] 턴 아키텍처 리팩토링 후 consume_turn 단일화 확인 (스케줄러 미동작)
- [x] `_sync_npc_turns()` 단일 플레이어 가정 주석 확인
- [x] spec.md 스케줄러 항목 및 앱 팩토리 흐름 동기화 확인

## 11. Final Decision
- **PASS WITH KNOWN RISKS**: 3차 감사에서 발견된 Critical 아키텍처 결함 `[ARCH-F001]`(이중 턴 처리)를 APScheduler 제거 및 consume_turn 단일화로 해결 완료함. `[ARCH-F002]`(NPC 시간 가속)은 단일 플레이어 게임 설계 가정 하에서 수용(Mitigated)되었으며, `_sync_npc_turns()`에 멀티 확장 시 전환 가이드를 주석으로 남김. `[ARCH-F003]`(SQLite 동시성)은 기존 Accepted Risk로 유지.
