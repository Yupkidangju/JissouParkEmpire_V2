# JissouParkEmpire Audit Report - 22차 감사

**작성일시**: 2026-05-30
**감사 대상**: 멀티플레이어 환경 Lock Ordering 규칙 준수 여부 및 SQLAlchemy Autoflush 부작용
**감사 초점**: 21차 감사 패치(ID 정렬을 통한 락 획득)의 실제 유효성과, 트랜잭션 내 암묵적 락 획득에 의한 순서 역전(Lock Ordering Violation) 집중 분석

---

## 1. 발견된 취약점 상세

이전 패치에서 개발자는 교착 상태(Deadlock)를 방지하기 위해 상호작용하는 두 Park의 ID를 정렬하여 오름차순으로 `with_for_update` 락을 획득하도록(`sorted([id1, id2])`) 수정했습니다.
그러나, **정렬된 락을 요청하기 직전에 원자적 `UPDATE` 쿼리가 먼저 실행되거나, 메모리 수정으로 인해 SQLAlchemy의 Auto-Flush가 개입**하면서, 사실상 정렬 순서가 완전히 무시되고 교착 상태가 재발하는 심각한 논리적 허점 3건이 발견되었습니다.

### 1.1. [DEADLOCK-F001] _process_spy_missions 내 락 획득 순서 고정으로 인한 교차 Deadlock
- **심각도**: **Critical**
- **위치**: `app/game_engine.py` (process_turn -> _process_spy_missions)
- **문제점**:
  - `process_turn(park)`의 최상단에서 `park.id`에 대한 `with_for_update` 비관적 락을 획득합니다.
  - 이후 턴 처리 로직 후반부의 `_process_spy_missions`에서 목표 공원(`target.id`)의 식량과 인구를 파괴하기 위해 `Park.query.filter(Park.id == target.id).update(...)`를 실행합니다.
- **발생 시나리오**:
  - 이 로직은 ID의 대소 관계와 무관하게 **무조건 자신의 락을 먼저 잡은 후 타겟의 락을 요구**합니다.
  - Player 1과 Player 2가 서로에게 보낸 밀사가 동일한 턴에 도착하고, 둘이 동시에 턴을 소비할 경우:
    1. P1: 1번 락 획득 -> 2번 락 `UPDATE` 대기
    2. P2: 2번 락 획득 -> 1번 락 `UPDATE` 대기
  - 서로의 락을 영원히 대기하는 완벽한 데드락이 발생합니다.

### 1.2. [DEADLOCK-F002] trade_accept의 선행 UPDATE에 의한 정렬 무효화 및 Deadlock
- **심각도**: **Critical**
- **위치**: `app/routes/game_routes.py` (trade_accept)
- **문제점**:
  - 814~825 라인에서 수락자(`park.id`)의 자원이 부족하지 않은지 검증하며 차감하기 위해 **원자적 `UPDATE` 쿼리를 먼저 실행**합니다.
  - 관계형 DB에서 `UPDATE` 구문은 즉시 해당 Row에 대해 베타적 쓰기 락(Write Lock)을 획득합니다.
  - 840 라인에서 `lock_ids = sorted([park.id, sender.id])`로 정렬 후 `with_for_update()`를 호출하지만, 이는 아무 소용이 없습니다. 이미 `park.id`의 락을 쥐고 있기 때문입니다.
- **발생 시나리오**:
  - 수락자 ID가 2, 발송자 ID가 1인 경우:
    1. 수락자(ID 2)의 `UPDATE` 실행 $\rightarrow$ **2번 락 선점**
    2. `sorted([2, 1])`에 의해 `with_for_update`가 **1번 락을 요구**
  - 큰 ID(2)를 먼저 쥐고 작은 ID(1)를 요구하게 되며 글로벌 Lock Order를 명백히 위반합니다. 동시 교역 수락 시 데드락이 발생합니다.

### 1.3. [DEADLOCK-F003] NPC 엔진 Auto-Flush 개입에 의한 execute_battle 락 순서 역전
- **심각도**: **High**
- **위치**: `app/npc_engine.py` (_npc_passive_growth, process_npc_turn)
- **문제점**:
  - NPC 턴이 시작되면 `_npc_passive_growth(park)`가 호출되어 메모리 상의 `park.trash_food` 등을 변경합니다.
  - 이후 `_npc_attack`을 통해 `execute_battle(park, target)`이 호출됩니다.
  - `execute_battle`은 ID 정렬 후 `Park.query.filter().with_for_update().all()` 쿼리를 실행하는데, 이 때 SQLAlchemy는 **DB의 상태를 최신화하기 위해 메모리에 보류된 변경사항(trash_food)을 쿼리 실행 직전에 `Auto-Flush`(`UPDATE`) 해버립니다.**
- **발생 시나리오**:
  - `Auto-Flush`가 발생하면 NPC 자신(`npc_park.id`)에 대한 `UPDATE` 쿼리가 먼저 DB로 전송되어 **NPC 자신의 행 락이 먼저 획득**됩니다.
  - 즉, NPC ID가 10, 타겟 ID가 5일 경우, 정렬 순서 상 5번 락부터 획득해야 하지만 Auto-Flush 때문에 10번 락을 먼저 쥐게 됩니다.
  - 타겟(ID 5) 유저가 게임을 플레이(락 획득)하는 타이밍과 겹치면 즉시 데드락이 터집니다. (ORM 프레임워크의 동작을 완벽히 이해하지 못해 발생한 숨겨진 버그입니다.)

---

## 2. 총평 및 권고사항

이전 감사에서 지적된 데드락 문제는 "ID 정렬"이라는 이론적으로 완벽한 해법을 도입했음에도 불구하고, **프레임워크(SQLAlchemy)의 암묵적 동작(Auto-Flush)과 SQL `UPDATE`의 특성을 고려하지 않고 배치된 순서** 때문에 처참하게 실패했습니다.

1. **지연 업데이트 (Lock-First Policy)**:
   - 교역, 전투, 밀사 등 2개 이상의 객체(Row)가 개입되는 트랜잭션에서는 **그 어떠한 상태 변경(메모리 변경, 원자적 UPDATE 등)보다도 `sorted([id1, id2])` 기반의 `with_for_update().all()` 락 획득 코드가 "최우선적"으로 실행되어야 합니다.**
   - 락을 확보하기 전에 수행하는 모든 `UPDATE`나 메모리 수정(`Auto-Flush` 유발)은 Lock Ordering을 완전히 박살 냅니다.
2. **`_process_spy_missions` 구조 개편**:
    - `process_turn` 트랜잭션 내부에서 타겟 유저를 직접 `UPDATE` 하는 현재 방식은 태생적으로 데드락을 유발합니다. 타겟 유저에 대한 처리는 별도의 독립 트랜잭션으로 분리하거나 비동기 이벤트 큐(Event Queue) 모델로 해결해야 합니다.

---

## 3. 패치 내역 (Fixes Applied)

### [FIXED] DEADLOCK-F001 — `_process_spy_missions` 교차 데드락
- **파일**: `app/game_engine.py`
- **조치**:
  1. `process_turn()` 내부의 `_process_spy_missions(park)` 호출을 제거하고, `consume_turn()`에서 `db.session.commit()` 이후、`_sync_npc_turns()` 이전에 별도로 호출하도록 이동.
  2. `_process_spy_missions()` 내 사보타주 성공 시 `Park UPDATE`를 `sorted([park.id, target.id])` 오름차순으로 재배열하여 항상 낮은 ID부터 락을 획득하도록 수정.
  3. 각 밀사 임무 처리 후 `db.session.commit()`을 추가하여 띅을 즉시 해제하고, 연속 임무 간 락 축적을 방지.

### [FIXED] DEADLOCK-F002 — `trade_accept` 선행 UPDATE에 의한 정렬 무효화
- **파일**: `app/routes/game_routes.py`
- **조치**:
  1. `trade_accept()` 내 `sorted([park.id, sender.id])` 기반 `with_for_update()` 띅 획득 코드를, **어떠한 `Park` 원자적 `UPDATE`보다도 가장 먼저 실행**되도록 이동.
  2. 수락자의 request 자원 차감 `UPDATE`는 띅 획득 이후에 수행되도록 순서를 재배열.

### [FIXED] DEADLOCK-F003 — NPC 엔진 Auto-Flush 락 순서 역전
- **파일**: `app/npc_engine.py`
- **조치**:
  1. `_npc_attack()` 및 `_npc_cunning_attack()`에서 `execute_battle()` 호출 직전에 `db.session.commit()`을 추가.
  2. 이를 통해 `_npc_passive_growth()` 등에서 메모리상 변경된 `park.trash_food` 등의 상태가 `execute_battle`의 `with_for_update()` 쿼리 실행 전에 DB로 플러시되도록 하여, SQLAlchemy Auto-Flush에 의한 예기치 않은 띅 순서 역전을 방지.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
