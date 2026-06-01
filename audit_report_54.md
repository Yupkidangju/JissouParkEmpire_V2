# JissouParkEmpire - Audit Report 54

## 1. 개요
* **감사 대상**: `app/battle_engine.py` (Looting 약탈량 산정 로직), `app/game_engine.py` (`_process_spy_missions`, `_sync_npc_turns`), `app/npc_engine.py` (`process_npc_turn`)
* **감사 목적**: 비동기 상호작용 및 NPC 일괄 처리 시스템에서 발생할 수 있는 데이터 경합(Race Condition), 자원 복제, 그리고 트랜잭션 무결성 결함 심층 점검
* **진행 상태**: **DISCOVERY (진행 중)**

## 2. 주요 발견 사항

### 2.1 [STATE-F028] NPC 일괄 처리루프 내 트랜잭션 해제로 인한 상태 유실 및 덮어쓰기 (Lost Update / Stale Memory Auto-Flush)
* **심각도**: **Critical**
* **위치**: `app/game_engine.py`의 `_sync_npc_turns()` 및 `app/npc_engine.py`의 `process_npc_turn()`
* **발생 원리**:
  1. `_sync_npc_turns` 시작 시 `Park.query.filter_by(is_npc=True).with_for_update().all()`을 호출하여 **모든 NPC의 상태를 한 번에 메모리에 로드하고 DB 쓰기 락을 획득**합니다.
  2. 그러나 `for` 루프 내부의 끝에서 **`db.session.commit()`을 호출하여 현재 트랜잭션을 종료**합니다. 이로 인해 루프의 첫 번째 NPC 처리가 끝나는 순간, **아직 처리되지 않은 나머지 모든 NPC들에 대한 DB 락이 즉시 해제**됩니다.
  3. 이 상태에서 다른 플레이어(B)가 턴을 소모하여 `_sync_npc_turns`를 병렬로 실행하면, B는 락이 풀린 나머지 NPC들을 선점하여 턴 진행 및 행동(`turn_count` 증가 등)을 완료하고 커밋할 수 있습니다.
  4. 이후 원래 플레이어(A)의 루프가 재개되어 다음 NPC를 처리할 때, A는 루프 시작 지점(과거)에 로드했던 **구버전(Stale) 메모리 객체를 기반으로 `process_turn()` 로직(자원 생성 등)을 실행**합니다.
  5. 그 직후 `process_npc_turn()` 내부에서 `Park.query...with_for_update().first()`를 다시 호출할 때, SQLAlchemy의 **`autoflush` 기능이 발동하여 A가 들고 있던 구버전 객체의 변경사항이 DB에 그대로 덮어씌워집니다 (Lost Update).**
  6. 결과적으로 B가 수행한 NPC의 정당한 턴 진행 결과는 소멸되며, NPC는 턴을 두 번 소모한 셈이 되거나 과거 상태로 롤백되는 심각한 상태 무결성 훼손이 발생합니다.

### 2.2 [TRANSACTION-F005] NPC 예외 발생 시 Rollback에 의한 후속 행동 무방비 노출 (Lock Loss via Exception)
* **심각도**: **High**
* **위치**: `app/npc_engine.py`의 `process_npc_turn()` 루프
* **발생 원리**:
  1. NPC AI가 행동(`action_func`)을 순차적으로 시도할 때, 내부에서 `Exception`이 발생하면 `except Exception:` 블록에서 `db.session.rollback()`을 호출합니다.
  2. `rollback()`은 해당 트랜잭션을 완전히 취소할 뿐만 아니라, 함수 진입 시 `with_for_update()`로 획득했던 **NPC 공원 객체의 비관적 락(Row Lock)까지 함께 해제**시킵니다.
  3. 이후 `continue`로 다음 우선순위 행동(ex: `action_scavenge`)을 시도할 때, 해당 로직은 **락이 없는 무방비 상태에서 실행**되므로 다른 트랜잭션(플레이어 침공 등)과의 Race Condition에 노출됩니다.
  4. 또한 이 `rollback`은 앞서 `process_turn()`에서 반영한 NPC의 자원 회복 및 `turn_count` 증가분까지 통째로 날려버리므로, 다음 턴 동기화 시 해당 NPC가 다시 턴을 배정받아 '무한 행동(Stampede)'을 유발할 여지를 남깁니다.

### 2.3 [LOGIC-F021] 사보타주(밀사) TOCTOU에 의한 임의 음수 계산 및 과소 피해 차단 (Minor)
* **심각도**: **Low**
* **위치**: `app/game_engine.py`의 `_process_spy_missions()`
* **발생 원리**:
  - 타겟의 식량(`trash_food`)을 파괴할 때, `db.session.refresh(target)`으로 읽어온 메모리 값을 기반으로 파괴량(`food_destroyed`)을 산정합니다.
  - 이후 데드락 방지를 명목으로 ID를 정렬한 후 원자적 `UPDATE` 문을 실행합니다 (`trash_food - food_destroyed`).
  - 이때 만약 `target`이 다른 유저라면 산정 시점과 적용 시점 사이에 실시간으로 자원을 소비할 수 있는 TOCTOU(Time-of-Check to Time-of-Use) 간격이 존재합니다.
  - 다행히 `case()` 문을 통해 음수로 내려가는 것을 방지하고 있으나(`case(trash_food < food_destroyed, 0)`), 락(`with_for_update`) 없이 연산되므로 로그에 찍히는 파괴량(예: 50개 파괴)과 실제 소실량(실제론 10개만 남아서 10개만 사라짐) 간의 불일치가 발생합니다. (단순 디스플레이 버그 수준)

## 3. 평가 및 권고사항
* **NPC 동시성 제어 붕괴 (Critical)**: `_sync_npc_turns` 내에서의 일괄 조회 후 개별 커밋은 SQLAlchemy 환경에서 대표적인 Anti-Pattern입니다. 이를 방지하려면 루프 내부에서 커밋을 하지 않거나, 루프 외부에서는 ID 목록만 가져온 뒤 루프 내부의 개별 트랜잭션 단위로 단일 NPC를 조회/락킹(Locking)/처리해야 합니다.
* **NPC 트랜잭션 롤백 부작용**: `rollback` 대신 Savepoint(Nested Transaction)를 사용하거나, 에러가 발생한 턴은 아예 스킵하도록 제어 흐름을 정돈하여 락 유실 및 `turn_count` 롤백으로 인한 스탬피드를 막아야 합니다.
* 다음 **55차 감사**에서는 상점/거래(Trade Market)와 랭킹 시스템에서 발생할 수 있는 부동소수점 오차, 오버플로우 악용, 동시 다발적 구매/교환 봇(Bot) 공격 등 인벤토리와 재화 유통 전반에 걸친 경제 무결성을 중점 점검하겠습니다.
