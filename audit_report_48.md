# 48차 코드 감사 보고서 (audit_report_48.md)

## 1. 감사 개요
*   **감사 대상**: `game_engine.py`, `game_routes.py`, `npc_engine.py`
*   **감사 기준**: `AI_AUDIT_DOC_STANDARD.md`의 [STATE] 및 [LOGIC] 파트
*   **감사 목적**: 교역 생성(Trade) 및 NPC 턴 동기화 로직에서의 프로세스 간 동시성 제어 유효성 검증 및 NPC 턴 처리 과정의 트랜잭션 무결성 검증

## 2. 주요 발견 사항

### [LOGIC-F019] Cross-Process Concurrency Failure with Threading Locks
*   **위험도**: High (Rate Limit 우회 및 NPC Stampede 발생)
*   **위치**: `game_routes.py` (Line 19: `_trade_create_lock`), `game_engine.py` (Line 20: `_npc_turn_lock`)
*   **내용 및 원인**:
    *   현재 교역 생성(`/trade/create`) 스팸 방지와 NPC 동시 턴 처리 방지를 위해 파이썬 내장 `threading.Lock()`을 사용하고 있습니다.
    *   그러나 Gunicorn 등 다중 워커 프로세스(Multi-Process) 기반의 프로덕션 환경에서는 `threading.Lock()`이 단일 프로세스 내의 스레드 간 동기화만 보장할 뿐, **프로세스 간 동기화는 전혀 불가능**합니다.
    *   이로 인해 유저가 동시에 여러 요청을 보내 서로 다른 워커에 할당되면 교역 생성 제한(`pending_count >= 10`)을 손쉽게 우회할 수 있습니다.
    *   더 치명적으로, 유저들의 동시다발적인 행동으로 인해 `_sync_npc_turns()`가 여러 워커에서 동시 호출되면, 락을 우회하고 여러 프로세스에서 **동일한 NPC의 턴을 중복해서 처리(NPC Stampede/Hyper-acceleration)**하게 되어 게임 밸런스가 완전히 붕괴됩니다.

### [STATE-F022] Lost Update in NPC Turn Processing due to Mixing In-Memory and Atomic Updates
*   **위험도**: High (플레이어 공격/약탈 결과 덮어쓰기 및 자원 복사)
*   **위치**: `npc_engine.py` -> `process_npc_turn()`, `_npc_passive_growth()`, `_npc_gather()` 등
*   **내용 및 원인**:
    *   NPC 턴 루프 내에서 `_npc_passive_growth()`는 `npc_park`의 `trash_food`, `material`, `guard_count` 등을 락이나 원자적 쿼리 없이 **메모리 상에서 직접 수정**합니다.
    *   이후 `_npc_gather()` 등에서 `game_engine.action_gather()`를 호출하면 내부적으로 원자적 `UPDATE` 쿼리를 실행하는데, 이 쿼리 실행 직전에 SQLAlchemy의 `autoflush`가 작동하여 앞선 **메모리 수정본을 DB로 강제 UPDATE(덮어쓰기)** 해버립니다.
    *   만약 이 시점 찰나에 플레이어가 NPC를 성공적으로 공격(전투)하여 자원을 뺏거나 경호실장을 죽였더라도, autoflush에 의해 플레이어의 공격 결과가 묵살되고 **NPC의 구버전 상태로 덮어씌워져 죽은 병력이 부활하고 약탈당한 자원이 복구되는(Lost Update)** 현상이 발생합니다.
    *   또한 `action_gather()`가 내부에서 `db.session.commit()`을 수행해버려 트랜잭션 단위가 쪼개지므로, 이후 `process_npc_turn`에서 예외가 발생해 `db.session.rollback()`이 호출될 경우, 후속 메모리 연산이었던 `park.action_points -= 1`만 롤백되어 **AP는 보존되고 채집한 자원은 획득되는 상태 불일치(무한 자원 버그)**가 발생할 위험이 있습니다.

## 3. 권고 사항
1.  **[LOGIC-F019] 수정 방향**:
    *   `threading.Lock()`에 의존하는 설계를 폐기하고, 데이터베이스 레벨의 비관적 락(`with_for_update()`)이나 Redis 같은 분산 락(Distributed Lock) 시스템을 도입하여 프로세스 간 동시성 제어를 보장해야 합니다.
2.  **[STATE-F022] 수정 방향**:
    *   NPC 턴 처리(`process_npc_turn`) 시 가장 먼저 NPC의 `Park` 레코드에 비관적 락(`with_for_update()`)을 걸어 다른 플레이어의 동시 개입을 막아야 합니다.
    *   `_npc_passive_growth()` 내의 상태 변경 역시 `case()`를 활용한 원자적 `UPDATE`로 변경하여 autoflush로 인한 덮어쓰기 부작용을 방지해야 합니다.
    *   `action_gather` 등의 범용 엔진 함수 내부에 하드코딩된 `db.session.commit()`을 제거하거나 NPC 모드와 트랜잭션을 분리하여, 단일 NPC 턴 전체가 원자적(Atomic) 트랜잭션 안에서 수행/롤백될 수 있도록 구조를 리팩토링해야 합니다.
