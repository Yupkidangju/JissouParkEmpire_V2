# Audit Report 52

## 1. Audit Target
- **Target File**: `app/npc_engine.py`, `app/turn_scheduler.py`
- **Focus**: NPC 턴 프로세싱(`process_npc_turn`) 시 트랜잭션 관리와 상태 누수(Transaction Bleed) 분석

## 2. Findings

### [TRANSACTION-F002] NPC 턴 결과의 트랜잭션 누수 및 타 공원 에러로 인한 롤백 (Transaction Bleed)
- **Severity**: High (심각)
- **Location**: `app/npc_engine.py` (`process_npc_turn`), `app/turn_scheduler.py` (`process_all_turns`)
- **Description**:
  `turn_scheduler.py`의 `active_parks` 루프에서 NPC 공원을 처리할 때 심각한 트랜잭션 누수가 발생합니다.
  1. 루프 내에서 `process_turn(park)`는 내부적으로 `db.session.commit()`을 수행하여 자신의 변경사항을 커밋합니다.
  2. 그 직후 `process_npc_turn(park)`이 호출되어 NPC 행동(예: 훈련, 건설 등 `commit=False`로 실행되는 행동들)이 수행되지만, 함수 종료 시 커밋(`db.session.commit()`)을 명시적으로 호출하지 않고 반환합니다.
  3. 이로 인해 NPC의 행동 결과가 `db.session`에 **미커밋 상태(Pending)** 로 남게 됩니다.
  4. 루프가 다음 공원(`park2`)으로 넘어가 `process_turn(park2)`를 실행하다가 예외(Exception)가 발생하면, `turn_scheduler.py`의 `except Exception` 블록에서 `db.session.rollback()`이 호출됩니다.
  5. 이때 `park2`의 변경사항뿐만 아니라, **이전 루프에서 커밋되지 않고 남아있던 `park1`의 NPC 행동 결과까지 전부 롤백**되어 버립니다. (State Leakage / Transaction Bleed)
  6. 반대로 `process_turn(park2)`가 정상적으로 끝나서 내부적으로 `commit()`을 호출하면, 그때서야 `park1`의 NPC 행동 결과가 `park2`의 트랜잭션과 함께 엉뚱하게 커밋됩니다.

- **Impact**:
  NPC들의 행동이 독립적인 원자적 트랜잭션으로 보장되지 않으며, 한 공원의 데이터 에러가 다른 정상적인 NPC 공원의 행동을 소급해서 취소시켜버리는 치명적인 상태 유실이 발생합니다.

### [TRANSACTION-F003] 동일 NPC 턴 내 Exception 발생 시 이전 행동 강제 롤백
- **Severity**: Medium (보통)
- **Location**: `app/npc_engine.py` (`process_npc_turn`)
- **Description**:
  `process_npc_turn` 내부의 `for action_func in actions:` 루프에서 다음과 같이 예외 처리를 하고 있습니다.
  ```python
  try:
      action_func(park)
  except Exception:
      db.session.rollback()
      continue
  ```
  이러한 롤백 로직은 해당 `action_func`에서 발생한 예외만 취소하는 것이 아니라, **같은 턴 내에서 성공적으로 완료된 이전 행동(`commit=False`로 실행된 채집, 출산 등)과 자연 성장(`_npc_passive_growth`의 flush 결과)까지 모두 롤백**해버립니다. 특정 행동 하나가 실패했다고 해서 해당 NPC의 턴 행동 전체(성공한 앞선 행동들)가 취소되는 것은 의도치 않은 동작(All-or-Nothing Bleed)입니다.

## 3. Recommendation (권고사항)
1. **`turn_scheduler.py` 턴 루프 커밋 보장**: `for park in active_parks:` 루프의 `try` 블록 마지막에 명시적으로 `db.session.commit()`을 추가하여, 각 공원의 턴 처리가 완전히 독립적인 트랜잭션으로 커밋되도록 격리해야 합니다.
2. **`process_npc_turn`의 원자성 강화**: NPC의 다중 행동이 서로 간섭하지 않도록, `process_npc_turn`의 `actions` 루프 내부의 `except` 블록에서 롤백을 수행하기 전에, 개별 행동마다 성공 시 커밋(`db.session.commit()`)을 하거나, 트랜잭션 세이브포인트(Savepoint)를 사용하여 실패한 행동만 롤백되도록 개선해야 합니다.

## 4. Next Step
- NPC 행동 엔진과 트랜잭션의 취약점을 문서화하였으므로, 이어서 다른 NPC 행동 분기 및 동맹/외교 시스템(`Diplomacy`)과 관련된 잠재적 Race Condition이나 참조 무결성 이슈를 추가로 감사할 예정입니다.
