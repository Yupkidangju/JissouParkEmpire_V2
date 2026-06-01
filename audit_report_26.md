# JissouParkEmpire Audit Report - 26차 감사

**작성일시**: 2026-05-30
**감사 대상**: 게임 루프(`process_turn`), 상태 동기화 누수
**감사 초점**: 메모리 수정분과 `db.session.refresh()` 간의 충돌 및 25차 패치 회귀 테스트

---

## 1. 이전 지적 사항 패치 결과 검증

### 1.1. [STATE-F002] 무한 턴(Infinite Turns) 버그 - **해결됨 (Fixed)**
- **조치 사항**: `game_engine.py`의 `consume_turn()` 내에서 `park.turn_quota -= 1` 수행 직후 `db.session.commit()`을 호출하도록 추가되었습니다.
- **결과**: `process_turn` 진입 전 턴 삭감이 DB에 확정되므로 `refresh`에 의한 소멸 현상이 해결되었습니다. NPC 턴 처리 로직에서도 해당 구조가 분리/삭제되어 동일 문제가 해소되었습니다.

---

## 2. 신규 발견 취약점 상세 (구현 중심 깊은 감사)

24차 감사에서 `[STATE-F001]`(원자적 `UPDATE` 후 상태 불일치)을 해결하기 위해 `_consume_np` 함수 내부에 `db.session.refresh(park)`를 도입한 패치로 인해, **또 다른 치명적인 메모리 유실 현상**이 연쇄적으로 발생하고 있습니다.

### 2.1. [STATE-F003] `_consume_np`의 `refresh`로 인한 AP 리필 및 턴 카운트 유실 (AP Softlock)
- **심각도**: **Critical (Game-Breaking)**
- **위치**: `app/game_engine.py` (`process_turn` 및 `_consume_np`)
- **문제 발생 메커니즘**:
  1. 턴이 진행될 때 `process_turn(park)`의 가장 첫 부분에서 다음 로직이 실행됩니다:
     ```python
     park.turn_count += 1
     park.action_points = GC.ACTION_POINTS_PER_TURN
     park.gathering_adults = min(park.gathering_adults, park.adult_count)
     ...
     ```
     이는 메모리에만 반영된(Pending) 상태이며, 아직 `flush`되거나 `commit`되지 않았습니다.
  2. 그 직후 `_process_food_consumption(park)`이 호출되며 내부적으로 `_consume_np(park)`가 실행됩니다.
  3. `_consume_np`는 원자적 식량 소비 처리를 하기 위해(또는 그 직후 상태 일치를 위해) 내부에 **`db.session.refresh(park)`**를 호출합니다.
  4. SQLAlchemy의 `refresh()`는 **현재 메모리에 보류된 미커밋 변경사항을 모두 폐기(Expire)**하고 데이터베이스의 이전 상태를 다시 불러옵니다.
  5. 결과적으로 1번에서 증가시킨 `turn_count`, `action_points`(AP 재충전), `gathering_adults` 등의 보정 값이 모두 원상복구(0 또는 이전 턴의 값)되어 날아갑니다.
- **파급 효과 (Impact)**:
  - **AP 재충전 불가 (Softlock)**: 턴 쿼터는 정상적으로 소모되지만, 유저의 AP는 영구적으로 충전되지 않습니다. 한 번 AP를 다 쓴 유저는 더 이상 아무런 행동도 할 수 없는 소프트락(Softlock) 상태에 빠집니다.
  - **턴 카운트 정지**: 게임의 진행도를 나타내는 `turn_count`가 영구적으로 멈춥니다.
  - **인구 배치 패널티**: 인구가 줄어들었을 때 채집/방어 인원을 하향 조정하는 방어 기제가 삭제되어 유효하지 않은 인구 배치가 잔류할 수 있습니다.
- **권고 사항**:
  - `process_turn(park)` 내부에서 `park.turn_count`, `park.action_points` 등을 메모리에 수정한 직후, `_process_food_consumption(park)`를 호출하기 전에 **`db.session.flush()`**를 호출하여 변경 사항을 트랜잭션 내에 확정(Pending -> DB)지어야 합니다.
  - 이를 통해 `_consume_np` 내부의 `refresh`가 기존에 수행한 메모리 변경분을 덮어쓰며 삭제하는 현상을 막을 수 있습니다.

---

## 3. 결론

턴 쿼터 무한 증식 버그는 해결되었으나, 게임의 핵심인 **AP 충전과 턴 카운터 증가 로직이 원자적 쿼리 동기화 로직과 충돌하며 완전히 파괴**되었습니다. 방치형 게임에서 AP 충전이 막히면 게임 진행 자체가 불가능하므로, `process_turn` 초입의 메모리 갱신분에 대한 명시적인 `flush()` 또는 `commit()` 처리가 가장 시급합니다.

---

## 4. 패치 내역 (Fixes Applied)

### [FIXED] STATE-F003 — `_consume_np`의 `refresh`로 인한 AP 리필 및 턴 카운트 유실
- **파일**: `app/game_engine.py`
- **조치**: `process_turn()` 내 메모리 수정분(`turn_count += 1`, `action_points = ...`, 배치 인원 조정 등) 직후, `_process_food_consumption(park)` 호출 이전에 `db.session.flush()`를 추가.
- **효과**: 메모리에만 존재하던 미커밋 변경사항이 트랜잭션 내 DB에 확정되어, 후속 `_consume_np()` 내부의 `db.session.refresh(park)`가 DB의 최신 값(=방금 flush된 값)을 다시 로드함. `turn_count`와 `action_points` 유실 방지, AP 소프트락 해소.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
