# Audit Report 61: NPC Engine Lock Order Inversion Deadlock

## 1. 개요 (Overview)
`turn_scheduler.py` 및 `npc_engine.py`에서 발생하는 중첩 트랜잭션과 락(Lock) 관리 메커니즘을 심층 감사한 결과, NPC가 다른 공원을 공격할 때 발생하는 **치명적인 교착 상태(Deadlock) 취약점**을 발견했습니다. 이전 패치에서 `flush()`를 통한 우회나 `_process_spy_missions`의 트랜잭션 분리 등 동시성 문제 해결을 위한 시도가 있었으나, NPC 엔진의 설계적 특성으로 인해 `execute_battle` 호출 시 락 순서 역전(Lock Order Inversion)이 여전히 발생하고 있습니다.

## 2. 취약점 상세 (Vulnerability Details)

### [DEADLOCK-F005] NPC 공격 수행 시 락 획득 순서 역전에 의한 교착 상태
**위치**: `app/npc_engine.py` (`process_npc_turn`, `_npc_attack`) 및 `app/battle_engine.py` (`execute_battle`)
**심각도**: **Critical (서비스 장애 및 DB 커넥션 고갈 가능성)**

**발생 메커니즘**:
1. **락 선점 (Pre-acquisition)**: `process_npc_turn()` 함수는 시작 시점(Line 34)에서 대상 NPC 공원에 대해 비관적 락을 획득합니다 (`with_for_update().first()`). 이 락은 전체 트랜잭션이 종료(`db.session.commit()`)될 때까지 유지됩니다.
2. **공격 실행**: NPC가 공격적인 성향(`aggressive`, `berserk`, `cunning`)일 경우, `_npc_attack()`을 통해 `execute_battle()` 함수를 호출합니다.
3. **교차 락 획득 시도**: `execute_battle()`은 데드락을 방지하기 위해 ID 오름차순(Canonical Ordering)으로 정렬하여 두 공원의 락을 동시에 획득하려 시도합니다 (`Park.query.filter(Park.id.in_(lock_ids)).with_for_update().all()`).
4. **락 순서 역전 (Lock Order Inversion)**:
   - 방어자(Player)의 ID가 공격자(NPC)의 ID보다 작을 경우(`Player.id < NPC.id`), 정렬된 순서는 `[Player.id, NPC.id]`가 됩니다.
   - 하지만 NPC 스레드는 **이미 NPC.id에 대한 락을 보유한 상태**에서 Player.id의 락을 요청하게 됩니다. (실제 획득 순서: `NPC -> Player`)
   - 동시에 Player가 NPC를 공격하거나 교역/외교 등의 트랜잭션으로 Player와 NPC의 락을 정렬하여 획득하려 시도하면, 해당 스레드는 `Player -> NPC` 순서로 락을 요청하게 됩니다.
   - **결과**: NPC 스레드는 Player 락 대기, Player 스레드는 NPC 락 대기 상태에 빠지며 영구적인 교착 상태(Deadlock)가 발생합니다.

### 무효화된 기존 방어 코드 (Ineffective Mitigations):
- **`flush()` 꼼수 실패**: `_npc_attack` 내부(Line 291)에 "락 순서가 역전되는 것을 방지"한다는 주석과 함께 `db.session.flush()`가 적용되어 있습니다. 이는 Auto-flush 시 발생하는 `UPDATE` 락 획득 순서 개입을 막기 위한 의도였으나, **이미 `process_npc_turn` 최상단에서 획득한 명시적 락(`SELECT ... FOR UPDATE`)은 `flush()`로 해제되지 않습니다.** 따라서 본질적인 데드락을 방어할 수 없습니다.

## 3. 부가 확인 사항 (Additional Verifications)
- **Turn Scheduler의 단일 행동 락 안정성**: `turn_scheduler.py`의 `force_process_turn`과 `npc_engine.py`의 `action_build`, `action_gather`, `action_cull`, `action_birth`, `action_train` 등의 호출은 정상적으로 `commit=False` 플래그를 존중하며, Savepoint(`begin_nested()`) 안에서 안전하게 원자적 동작을 수행하고 있음을 확인했습니다.
- **외교 관계 트랜잭션**: `diplomacy_dissolve`, `diplomacy_enemy` 등의 AP 소비와 관련된 비관적 락 해제-재획득 구간을 검증한 결과, 모든 상태 변경이 DB 원자적 연산(`update({'status': 'dissolved'})`)으로 처리되어 TOCTOU나 Race Condition이 발생하지 않는 안전한 구조임을 확인했습니다.

## 4. 권장 수정 방안 (Recommendations)

**옵션 1: NPC 행동 범위 내에서의 락 통제 완화**
- `process_npc_turn()` 최상단에서 무조건적으로 락을 획득하는 코드(`Park.query...with_for_update()`)를 제거합니다.
- 각 행동(`action_gather`, `execute_battle` 등)이 자체적으로 필요한 락을 안전한 순서(Canonical Ordering)에 맞게 획득하도록 역할을 위임합니다.

**옵션 2: NPC 전투 트랜잭션 분리**
- 이전 패치에서 `_process_spy_missions`를 `process_turn` 외부로 빼내어 데드락을 해결했던 것(`audit_report_22.md`)과 동일한 접근법입니다.
- NPC의 공격 의도를 큐나 임시 상태로 저장하고, `process_npc_turn` 트랜잭션이 완전히 커밋되어 NPC 락이 해제된 이후에 독립적인 트랜잭션으로 `execute_battle`을 호출하도록 리팩토링합니다.
