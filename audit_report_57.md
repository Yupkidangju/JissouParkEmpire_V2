# Audit Report 57: NPC Turn Transaction Crash & Infinite AP Exploit

## 1. 개요 (Overview)
- **발견 일시**: 2026-05-31
- **심각도**: **High (고위험 - 치명적 트랜잭션 오류 및 무한 액션 버그)**
- **컴포넌트**: `app/npc_engine.py`, `app/game_engine.py`
- **핵심 문제**: `v1.8.5`에서 도입된 NPC 턴 네스티드 트랜잭션(`db.session.begin_nested()`)과 `v1.7.0`에서 추가된 각종 `db.session.commit()` 로직이 심각하게 충돌하여 `ResourceClosedError`를 유발하고, 그 결과 NPC의 모든 전투가 롤백되며 AP 소모 없이 1회 액션을 성공하는 심각한 버그 발견.

## 2. 세부 분석 (Detailed Analysis)

### 2.1. 문제의 발단 (Root Cause Context)
`app/npc_engine.py`의 `process_npc_turn` 함수는 `v1.8.5` 패치에서 트랜잭션 모순을 방어하기 위해 개별 행동을 Savepoint(`begin_nested()`)로 감싸도록 변경되었습니다.
```python
    # _sync_npc_turns 호출 흐름
    for action_func in actions:
        if park.action_points <= 0:
            break
        nested = db.session.begin_nested()  # Savepoint 생성
        try:
            action_func(park)               # NPC 액션 실행
            nested.commit()
        except Exception:
            nested.rollback()
            continue
```
그러나 NPC가 호출하는 대부분의 액션 함수(`_npc_aggressive_attack`, `action_scavenge`, `action_build` 등)는 내부적으로 **글로벌 커밋(`db.session.commit()`)을 명시적으로 호출**하고 있습니다.

### 2.2. 메커니즘 (Exploit / Bug Mechanism)
1. **Savepoint 소멸 및 연결 끊김**: SQLAlchemy에서 `begin_nested()`가 활성화된 상태에서 `db.session.commit()`을 호출하면, 트랜잭션 전체가 즉시 커밋되고 기존 Savepoint는 유효성을 상실합니다.
2. **ResourceClosedError 발생**: `action_func` 내에서 `db.session.commit()`이 실행된 직후 반환되어 `nested.commit()`이 호출될 때, 트랜잭션 및 Savepoint 상태가 이미 소멸되었기 때문에 **`ResourceClosedError: This transaction is closed`** 예외가 발생합니다.
3. **Rollback 중복 실패 (Double Fault)**: 예외 처리 블록(`except Exception:`)에서 `nested.rollback()`을 시도하지만 이 또한 유효하지 않은 Savepoint에 접근하므로 **또 다시 `ResourceClosedError` 예외가 발생**하여 에러가 상위로 전파됩니다.
4. **NPC 행동 강제 종료 (AP 미소모 Exploit)**: 상위 루프(`_sync_npc_turns`)에서 이 예외를 잡아서 `db.session.rollback()`을 실행합니다. 그 결과, 다음과 같은 치명적인 상태가 발생합니다:
   - **자원 획득 및 턴 강제 종료**: `action_scavenge` 같은 함수는 종료 전 커밋을 하므로 자원은 이미 DB에 반영됩니다. 하지만 그 직후 예외로 인해 턴 처리가 중단되며, 메모리 상에서 차감한 `park.action_points -= 1`은 DB에 최종 커밋되지 않고 소멸됩니다. (결과: NPC는 매 턴마다 AP 소모 없이 1회의 행동에 대한 보상을 영구적으로 얻음).
   - **NPC 전투 불가 버그**: `_npc_aggressive_attack`는 교착 상태(Deadlock) 방지를 위해 `execute_battle` 직전에 커밋을 수행하고, 전투 후에는 커밋하지 않습니다. 따라서 전투 후 예외가 터지고 전체 롤백(`db.session.rollback()`)이 실행되어 **전투 결과(손실, 노획, 로그 등)가 모조리 롤백**됩니다. (결과: NPC는 절대로 공격을 성공시킬 수 없습니다).

## 3. 재현 경로 (Reproduction Steps)
1. NPC가 `process_npc_turn`에 진입합니다.
2. NPC가 자원 채집(`action_scavenge`)을 시도합니다. `begin_nested()`가 활성화됩니다.
3. `action_scavenge` 함수가 끝날 때 `db.session.commit()`이 실행되며 자원 획득 내역이 저장됩니다.
4. `nested.commit()`이 실패하고, 이어서 `nested.rollback()`도 실패합니다.
5. 상위 코드에서 예외를 캐치하고 세션을 롤백하지만 이미 커밋된 자원 획득은 취소되지 않으며, 인메모리 상에서 차감될 예정이었던 AP(`park.action_points -= 1`) 차감 로직은 소멸합니다.
6. 결과적으로 NPC는 영구적으로 1행동 분량의 자원을 공짜로 얻고 턴이 종료됩니다.

## 4. 해결 방안 (Recommended Fixes)
1. **중첩 트랜잭션 커밋 분리**: NPC용으로 `action_*` 헬퍼 함수를 호출할 때 `commit=False` 인자를 명시하여 중복 커밋을 방지해야 합니다. (예: `action_scavenge(park, commit=False)`).
2. **전투 로직 커밋 일관성**: `_npc_aggressive_attack` 및 `_npc_cunning_attack`에서 무리하게 호출하는 `db.session.commit()`을 제거하거나, 아키텍처 수준에서 트랜잭션 경계를 명확히 재설정해야 합니다. (비관적 락의 순서를 맞추는 방식으로 Deadlock을 회피해야 함).
3. **예외 처리 안전성 강화**: `nested.rollback()` 호출 시 `except Exception`을 한 겹 더 감싸 상위 루프로 에러가 치명적으로 전파되는 것을 막아야 합니다.
