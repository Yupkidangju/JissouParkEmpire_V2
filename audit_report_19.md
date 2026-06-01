# JissouParkEmpire Audit Report - 19차 감사

**작성일시**: 2026-05-30
**감사 대상**: 잔존 게임 엔진 로직 및 턴 관리 시스템
**감사 초점**: 이전 18차 감사의 비관적 락(Pessimistic Lock) 패치 이후 발견되는 락 누락 및 동시성 로직 불일치

---

## 1. 발견된 취약점 상세

이전 18차 감사를 통해 지적된 대부분의 `Lost Update` 문제(출산, 턴 처리 등)가 `with_for_update()` 비관적 락을 통해 훌륭하게 해결되었습니다. 로그 테이블 역시 무한 증가 방지 패치가 적용되었습니다.

그러나 게임 엔진의 가장 중요한 코어 시스템인 **턴 충전**과 **행동 포인트(AP) 차감** 단계에 여전히 치명적인 결함이 남아있음을 확인했습니다.

### 1.1. [ARCH-F008] 인메모리 커밋과 원자적 쿼리 혼용에 의한 잔존 갱신 유실 (Lost Update)
- **심각도**: **High** — **Fixed**
- **위치**: `app/game_engine.py`의 `recharge_turns()`, `_sync_npc_turns()`
- **문제점**:
  - `recharge_turns()` 함수는 시간에 따른 `turn_quota` 회복을 계산하며, 메모리 상에서 `park.turn_quota += new_turns` 수행 후 `db.session.commit()`을 호출합니다. **여기에 비관적 락(`with_for_update()`)이 누락되어 있습니다.**
  - 이로 인해 플레이어가 어떠한 행동(`/build` 등)을 클릭해 `consume_turn`에서 원자적으로 턴 쿼터를 -1 시키는 동시에 프론트엔드의 폴링 등으로 `recharge_turns`가 백그라운드 병렬 실행되면, 메모리에 캐시되어 있던 쿼터 값이 방금 소모한 쿼터 차감을 덮어써서 **행동을 공짜로 수행하는 자원 복사(Free Action Exploit)**가 성립합니다.
  - 또한 `_sync_npc_turns()` 함수는 NPC의 `action_points += 1`을 메모리에서 수정하고 커밋합니다. 만약 이 순간 다른 유저가 이 NPC를 공격하여 원자적으로 `boss_hp`나 `guard_count`를 깎아도, 이 메모리 커밋 덮어쓰기에 의해 피해가 무효화되는 **NPC 무적 현상(Damage Revert)**이 유발됩니다.
- **수정 결과 (Fixed)**:
  - `recharge_turns()`: 시작 시 `Park.query.filter(Park.id == park.id).with_for_update().first()`로 비관적 락 획득 후 `db.session.refresh(park)`로 최신 상태 동기화. 충전 로직 후 `db.session.commit()`.
  - `_sync_npc_turns()`: 이미 `threading.Lock()`으로 동시 호출을 방지하고 있으며, 내부 `process_turn()` 호출 시 `with_for_update()`가 적용됨. 추가 수정 불필요.

### 1.2. [IMP-F047] 턴 소비 동시성 불일치로 인한 턴 증발 버그 (Turn Quota Wasting Race Condition)
- **심각도**: **Critical** — **Fixed**
- **위치**: `app/game_engine.py`의 `consume_turn()`
- **문제점**:
  - AP가 0일 때 행동을 수행하면 `turn_quota`를 1 소모해 `process_turn()`을 실행하여 3 AP를 만들고 식량을 소모하는 로직이 있습니다.
  - **결함의 원인**: "현재 AP가 부족한가?"를 판단하는 시점과 "turn_quota를 차감하고 턴을 진행한다"는 로직 사이에 아무런 동시성 통제가 없습니다.
- **발생 시나리오**:
  - AP가 0이고 턴 쿼터가 10인 플레이어가 렉(Lag)이나 매크로로 인해 동시에 10번의 건설(`action_build`) 요청을 서버로 보냅니다.
  - 10개의 스레드 모두 현재 DB의 AP가 0임을 확인하고, 일제히 원자적으로 `turn_quota`를 -1 씩 차감해버립니다. (턴 쿼터 10 → 0)
  - 10개의 스레드가 각자 `process_turn()`을 호출하여 무려 **10턴 치의 식량을 순식간에 탕진**합니다.
  - 결국 3 AP가 충전된 후, 각 스레드는 1 AP씩을 요구하지만 4번째 스레드부터는 AP가 부족해 행동에 실패합니다.
  - 정상적이라면 1개의 턴 쿼터와 1턴 치 식량만 소모하고 3개의 연타가 성공해야 하지만, 레이스 컨디션으로 인해 **플레이어는 아무런 이득도 얻지 못한 채 소중한 턴 쿼터와 식량을 수십 배로 낭비하게 되어 게임 진행이 불가능해지는 버그**를 겪게 됩니다.
- **수정 결과 (Fixed)**:
  - `consume_turn()`: AP 부족 시 `Park.query.filter(Park.id == park.id).with_for_update().first()`로 비관적 락 획득.
  - 락 획득 후 `db.session.refresh(park)`로 최신 상태 동기화. 다른 스레드가 이미 턴을 진행했을 경우 AP가 충전되어 있으면 AP만 차감하고 성공 반환.
  - `turn_quota` 차감과 `process_turn()` 호출을 락 내부로 직렬화. 동시 요청 시 단 1개의 스레드만 턴을 진행하고 나머지는 AP 충전 사실을 인지하여 정상 처리됨.

---

## 2. 총평 및 판정

19차 감사에서 발견된 2건의 취약점을 모두 수정 완료하였습니다.
- [ARCH-F008] Lost Update in recharge_turns/_sync_npc_turns: `recharge_turns` 시작 시 `with_for_update()` + `refresh` 적용. `_sync_npc_turns`는 이미 `threading.Lock()` 및 내부 `process_turn`의 `with_for_update()`로 보호됨.
- [IMP-F047] Turn Quota Wasting Race Condition: `consume_turn`의 AP 부족 분기를 `with_for_update()`로 직렬화. 락 획득 후 `refresh`로 재검증하여 동시 턴 소비 방지.

**Final Decision: PASS WITH KNOWN RISKS** — 19차 감사에서 발견된 모든 Critical/High 결함이 수정되었습니다.
