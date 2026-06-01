# JissouParkEmpire Audit Report - 24차 감사

**작성일시**: 2026-05-30
**감사 대상**: 전체 게임 엔진 및 NPC 엔진 구동 로직, 23차 패치 검증
**감사 초점**: 트랜잭션 에러 핸들링, 메모리-DB 동기화 결함에 따른 논리적 버그(State Synchronization) 집중 분석

---

## 1. 이전 지적 사항 패치 결과 검증

### 1.1. `[DEADLOCK-F004]` NPC 엔진 턴 동기화 락 누수 - **해결됨 (Fixed)**
- **조치 사항**: `_sync_npc_turns()` 함수의 반복문 내에서 `process_npc_turn(npc_park)` 실행이 끝날 때마다 `db.session.commit()`을 호출하도록 추가됨.
- **결과**: `execute_battle` 과정에서 획득된 타겟 객체의 Write Lock이 매 NPC 턴 종료 시 즉시 반환되므로, 다음 루프에서 발생하는 교차 데드락이 완전히 해소되었습니다.

---

## 2. 신규 발견 취약점 상세 (구현 중심 깊은 감사)

23차까지의 감사로 데드락(Deadlock)과 관련된 심각한 병발성 이슈들은 대부분 정리되었습니다. 이번 24차 감사에서는 **데이터 불일치 및 예외 처리 누락**으로 인한 심각한 로직 파괴 현상을 식별했습니다.

### 2.1. [TRANSACTION-F001] NPC 에러 핸들러 내 `Session Rollback` 누락에 의한 트랜잭션 오염 및 유저 자원 증발
- **심각도**: **High**
- **위치**: `app/npc_engine.py` (`process_npc_turn` 내부 루프)
- **문제점**:
  - NPC 행동을 순차 실행하는 로직이 `try: action_func(park) except Exception: continue` 형태로 감싸져 있습니다.
  - SQLAlchemy에서는 데이터베이스 쿼리 중 예외(예: `IntegrityError`, `OperationalError`)가 발생하면 해당 세션(Transaction)이 FAILED 상태로 고정됩니다.
  - 이를 해결하기 위해서는 `except` 블록 내에서 반드시 **`db.session.rollback()`**을 명시적으로 호출해야 하지만 이 부분이 누락되어 있습니다.
- **파급 효과 (Impact)**:
  - NPC 턴 처리 중 사소한 DB 경합 예외가 발생하면 해당 세션이 오염됩니다.
  - 이후 `_sync_npc_turns()` 루프 끝에 도달하여 `db.session.commit()`을 호출할 때 `PendingRollbackError`가 발생하며 애플리케이션에 500 내부 서버 오류를 일으킵니다.
  - 가장 심각한 점은, 유저가 AP를 소모하기 위해 호출한 `consume_turn()`은 **이미 `turn_quota`와 `AP`를 차감한 직후에 NPC 엔진을 호출한다는 것**입니다. 따라서 에러 발생 시 유저는 아무런 행동을 하지 못한 채 자원만 잃게 됩니다.
- **권고 사항**: `except Exception:` 하위에 `db.session.rollback()` 코드를 추가하여 트랜잭션을 정상 상태로 복구한 뒤 `continue` 하도록 수정해야 합니다.

### 2.2. [STATE-F001] 원자적 `UPDATE` 이후 `refresh` 누락으로 인한 식량 소비 이력 파괴
- **심각도**: **High (Critical Gameplay Bug)**
- **위치**: `app/game_engine.py` (`_process_food_consumption`, `_consume_np`)
- **문제점**:
  - 17차 패치에서 `_consume_np` 함수 내의 자원 소비 로직을 메모리 갱신 방식에서 원자적 쿼리(`Park.query.filter().update()`)로 변경했습니다.
  - 하지만 **`UPDATE` 쿼리 실행 직후 메모리의 `park` 객체를 동기화(`db.session.refresh(park)`)하는 코드가 누락**되었습니다. (예: 콘페이토 소비 로직)
  - `_process_food_consumption`에서는 소비 여부를 판별하기 위해 `konpeito_before > park.konpeito` 와 같은 비교식을 사용합니다.
  - DB의 값은 깎였으나 메모리 상의 `park.konpeito`는 여전히 `UPDATE` 이전의 과거 값을 들고 있으므로, `konpeito_before > park.konpeito`는 **항상 False**가 됩니다.
- **파급 효과 (Impact)**:
  - `konpeito_consumed`와 `meat_consumed`가 영구적으로 `False`로 판정됩니다.
  - 유저가 아무리 고급 식량을 제공해도, 엔진은 **"이번 턴에 쓰레기만 먹었다"**고 오판하여 `consecutive_trash_turns`가 영구적으로 매 턴마다 증가하게 됩니다.
  - 결과적으로 공원의 사기가 무한히 하락하며, 정상적인 게임 플레이(사기 관리)가 불가능해지는 치명적인 버그입니다.
- **권고 사항**: `_consume_np` 함수의 반환 직전에 `db.session.refresh(park)`를 호출하거나, 각 `UPDATE` 블록 직후에 갱신 처리를 넣어 메모리와 DB 간의 상태를 일치시켜야 합니다.

---

## 3. 결론

데드락 관련 문제는 해소되었으나, 부분적인 원자적 연산 전환 패치가 오히려 **ORM 메모리 동기화 불일치**라는 심각한 사이드 이펙트를 낳았습니다. 또한 NPC 엔진의 **안전장치(Rollback) 부재**로 인한 자원 증발 위험이 식별되었습니다. 위 두 가지 취약점을 최우선으로 패치할 것을 권고합니다.

---

## 4. 패치 내역 (Fixes Applied)

### [FIXED] TRANSACTION-F001 — NPC 에러 핸들러 내 Session Rollback 누락
- **파일**: `app/npc_engine.py`
- **조치**: `process_npc_turn()` 내부 `except Exception:` 블록에 `db.session.rollback()`을 추가.
- **효과**: NPC 행동 중 DB 예외 발생 시 세션이 FAILED 상태로 고정되는 것을 방지. 후속 `db.session.commit()`이 정상적으로 수행되며, 유저의 `turn_quota` 및 `AP`가 무상으로 증발하는 현상 방지.

### [FIXED] STATE-F001 — 원자적 UPDATE 이후 refresh 누락으로 인한 식량 소비 이력 파괴
- **파일**: `app/game_engine.py`
- **조치**: `_consume_np()` 함수의 반환 직전에 `db.session.refresh(park)`를 추가.
- **효과**: 원자적 `UPDATE`로 DB에서 차감된 `konpeito`, `meat_stock`, `trash_food` 값이 메모리 `park` 객체에 동기화됨. `_process_food_consumption()`의 `konpeito_before > park.konpeito` 등 비교식이 정확히 작동하여 `consecutive_trash_turns`가 고급 식량 소비 시 정상적으로 초기화됨.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
