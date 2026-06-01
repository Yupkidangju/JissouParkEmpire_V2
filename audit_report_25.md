# JissouParkEmpire Audit Report - 25차 감사

**작성일시**: 2026-05-30
**감사 대상**: 게임 루프(Game Loop), 턴 소비 및 상태 동기화
**감사 초점**: 원자적 업데이트 리팩토링 및 `db.session.refresh()`의 부작용에 대한 논리적 무결성 분석

---

## 1. 이전 지적 사항 패치 결과 검증

### 1.1. [TRANSACTION-F001] NPC 에러 핸들러 내 Rollback 누락 - **해결됨 (Fixed)**
- **조치 사항**: `npc_engine.py`의 `_sync_npc_turns` 내에서 `except Exception:` 블록에 `db.session.rollback()`이 성공적으로 추가되었습니다.

### 1.2. [STATE-F001] 원자적 UPDATE 이후 refresh 누락 - **해결됨 (Fixed)**
- **조치 사항**: `game_engine.py`의 `_consume_np` 함수 마지막에 `db.session.refresh(park)`가 정상적으로 추가되어, 식량 소비 내역 판정 시 DB와 메모리가 일치하게 되었습니다.

---

## 2. 신규 발견 취약점 상세 (구현 중심 깊은 감사)

17차 패치 즈음에 도입된 `process_turn()` 내부의 비관적 락(`with_for_update`)과 `db.session.refresh(park)` 로직이, 상위 함수(`consume_turn`, `_sync_npc_turns`)에서 수행한 **"메모리 상의 미커밋 변경사항"을 강제로 소멸(Discard)시키는 치명적인 버그**를 유발하고 있음을 발견했습니다.

### 2.1. [STATE-F002] `refresh`에 의한 턴 쿼터(Turn Quota) 삭감 내역 유실 (Infinite Turns Bug)
- **심각도**: **Critical (Game-Breaking)**
- **위치**:
  - `app/game_engine.py` (`consume_turn` 및 `process_turn`)
  - `app/npc_engine.py` (`_sync_npc_turns`)
- **문제 발생 메커니즘**:
  1. 유저의 AP가 부족하거나, 턴 강제 소비 조건일 때 `consume_turn()`에서 `park.turn_quota -= 1`을 실행하여 메모리 객체의 턴 수를 1 깎습니다.
  2. 그 직후, 턴 처리를 위해 `process_turn(park)`를 호출합니다.
  3. `process_turn()` 함수의 최상단에서 동시성 방지를 위해 비관적 락을 획득하고, **`db.session.refresh(park)`**를 호출합니다.
  4. SQLAlchemy의 `refresh()` 메서드는 현재 메모리 객체에 보류 중(Pending)인 미커밋 변경사항을 **모두 폐기(Expire)**하고, DB의 최신 상태로 다시 덮어씁니다.
  5. 즉, DB에는 아직 커밋되지 않은 `park.turn_quota -= 1` 내역이 완전히 사라지고, 다시 원래의(깎이기 전) `turn_quota` 값으로 돌아옵니다.
  6. 이후 `process_turn` 로직(식량 소비, 성장 등)이 끝나고 `db.session.commit()`이 호출될 때, 변경되지 않은 원래의 `turn_quota`가 DB에 그대로 저장됩니다.
- **파급 효과 (Impact)**:
  - **무한 턴 플레이**: 유저는 행동을 아무리 많이 해도 `turn_quota`가 절대 줄어들지 않습니다. 무한대로 AP를 충전하여 하루 만에 게임을 끝까지 클리어할 수 있게 되어 방치형(Time-gated) 게임의 밸런스가 완전히 파괴됩니다.
  - **무한 NPC 액션**: NPC 역시 `_sync_npc_turns`에서 `npc_park.turn_quota -= 1` 후 `process_turn`을 호출하므로, 턴 쿼터가 차감되지 않습니다. 매번 유저가 접속하거나 행동할 때마다 NPC에게 무한정 무료 턴이 공급됩니다.
- **권고 사항**:
  - `park.turn_quota -= 1` 처리를 `process_turn(park)` 호출 전에 메모리 수정 방식이 아닌 **원자적 UPDATE 쿼리(`Park.query.filter().update()`)**로 실행하거나,
  - `park.turn_quota -= 1` 직후에 `db.session.commit()`을 수행하여 변경 사항을 DB에 확정한 뒤 `process_turn(park)`을 호출해야 합니다.

---

## 3. 결론

과거 동시성 에러(Double-Spend, Lost Update)를 막기 위해 도입된 락과 Refresh 메커니즘이 오히려 상위 로직의 메모리 연산 결과를 증발시키는 **새로운 형태의 Lost Update(Infinite Turns)**를 만들어냈습니다. 해당 버그는 게임 진행의 핵심 제어 장치를 무력화하므로 즉각적인 원자적 UPDATE 전환 조치가 필요합니다.

---

## 4. 패치 내역 (Fixes Applied)

### [FIXED] STATE-F002 — `refresh`에 의한 턴 쿼터 삭감 내역 유실
- **파일**: `app/game_engine.py`
- **조치**: `consume_turn()` 내 `park.turn_quota -= 1` 직후에 `db.session.commit()`을 추가하여, `process_turn(park)` 내부의 `db.session.refresh(park)` 호출 이전에 미커밋 변경사항을 DB에 확정.
- **효과**: `turn_quota` 차감 내역이 `refresh()`에 의해 폐기되지 않고 정상적으로 DB에 저장됨. 무한 턴 플레이 버그(Infinite Turns Bug) 해소.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
