# JissouParkEmpire Audit Report - 21차 감사

**작성일시**: 2026-05-30
**감사 대상**: 멀티플레이어 환경(동시 접속)에서의 상호작용 및 NPC 엔진 트랜잭션 모델
**감사 초점**: 비관적 락(`with_for_update`)과 원자적 `UPDATE`가 도입된 이후 발생하는 **데이터베이스 교착 상태(Deadlock)** 취약점 점검

---

## 1. 발견된 취약점 상세

이전 감사에서 동시성 문제(Lost Update, 자원 복사)를 막기 위해 추가된 락(Lock) 메커니즘들이 서로 충돌하여, **시스템 전체를 마비시키는 치명적인 교착 상태(Deadlock)** 결함 3건이 새롭게 발견되었습니다. 두 개 이상의 트랜잭션이 서로가 점유한 행(Row)의 락이 풀리기를 무한정 대기하는 전형적 구조적 결함입니다.

### 1.1. [DEADLOCK-F001] 유저 간 상호 침공 시 발생하는 교차 Deadlock
- **심각도**: **Critical (DB Lock 무한 대기)** — **Fixed**
- **위치**: `app/routes/game_routes.py` (battle_attack) 및 `app/battle_engine.py` (execute_battle)
- **문제점**:
  - 유저가 침공을 지시하면 `@require_ap`를 통해 `consume_turn()`이 호출되며, 이 시점에 **공격자 자신**의 Row에 비관적 락(`with_for_update`)이 걸립니다.
  - 이후 `execute_battle()`에서 `Park.query.filter(Park.id.in_([attacker.id, defender.id])).with_for_update().all()`를 호출해 **방어자**의 락을 추가로 획득하려 시도합니다.
- **발생 시나리오**:
  1. **Player 1**이 **Player 2**를 공격 $\rightarrow$ Player 1 행 락 획득 $\rightarrow$ Player 2 행 락 대기
  2. 찰나의 순간에 **Player 2**가 **Player 1**을 공격 $\rightarrow$ Player 2 행 락 획득 $\rightarrow$ Player 1 행 락 대기
  3. 두 트랜잭션은 서로가 쥐고 있는 락을 원하므로 DB 타임아웃이 발생할 때까지 완전히 정지하며, 관련된 커넥션 풀을 소진시킵니다.
- **수정 결과 (Fixed)**:
  - `execute_battle()`: `with_for_update()` 호출 시 `sorted([attacker.id, defender.id])`로 id 오름차순 정렬 후 락 획득.
  - 모든 상호 침공 시나리오에서 양측이 동일한 순서로 락을 획득하므로 교차 Deadlock이 원천 차단됨.

### 1.2. [DEADLOCK-F002] 교역 상호 수락에 따른 순차 UPDATE Deadlock
- **심각도**: **Critical** — **Fixed**
- **위치**: `app/routes/game_routes.py` (trade_accept)
- **문제점**:
  - 교역 수락 시, `trade_accept` 라우트는 트랜잭션 내에서 **수락자(park)**의 자원을 먼저 원자적 `UPDATE`로 차감/지급하고, 이후 **발송자(sender)**의 자원을 `UPDATE` 합니다.
  - DB의 `UPDATE` 구문은 실행 즉시 해당 Row의 쓰기 락(Write Lock)을 점유합니다.
- **발생 시나리오**:
  1. **Player 1**이 **Player 2**가 보낸 교역을 수락 $\rightarrow$ Player 1 락 점유 $\rightarrow$ Player 2 락 대기
  2. 동시에 **Player 2**가 **Player 1**이 보낸 다른 교역을 수락 $\rightarrow$ Player 2 락 점유 $\rightarrow$ Player 1 락 대기
  3. 락 획득 순서가 고정되어 있지 않고 "누가 수락 버튼을 눌렀느냐"에 따라 의존하므로, 교차 수락 시 100% Deadlock에 빠집니다.
- **수정 결과 (Fixed)**:
  - `trade_accept()`: 자원 교환 UPDATE 이전에 `sorted([park.id, sender.id])`로 id 오름차순 정렬 후 `Park.query.filter(Park.id.in_(lock_ids)).with_for_update().all()`로 락을 먼저 획득.
  - 이후 UPDATE는 수락자/발송자 순서로 그대로 진행되나, 락 획득은 항상 id 오름차순으로 이루어져 교차 Deadlock이 원천 차단됨.

### 1.3. [DEADLOCK-F003] consume_turn의 단일 대형 트랜잭션과 NPC 연쇄 Deadlock
- **심각도**: **Fatal (단일 유저 행동이 전체 시스템을 정지시킬 위험)** — **Fixed**
- **위치**: `app/game_engine.py` (consume_turn, _sync_npc_turns)
- **문제점**:
  - `consume_turn()`은 플레이어의 턴 쿼터가 소모될 때 `process_turn()`과 `_sync_npc_turns()`를 모두 실행한 **이후에 단 한 번의 `commit()`**으로 트랜잭션을 종료합니다.
  - 이 하나의 트랜잭션은 플레이어 자신은 물론이고, 모든 NPC(`npc_parks`), 그리고 NPC가 공격이나 사보타주 대상으로 삼는 **무고한 제3의 유저들**의 락까지 무자비하게 끌어모아 점유합니다.
- **발생 시나리오**:
  1. **Player 1** 턴 소모 $\rightarrow$ Player 1 락 $\rightarrow$ **NPC 1** 락 $\rightarrow$ NPC 1이 우연히 **Player 2**를 침공 $\rightarrow$ Player 2 락 대기
  2. 동시에 **Player 2** 턴 소모 $\rightarrow$ Player 2 락 $\rightarrow$ **NPC 1** 락 대기 (Player 1이 점유 중)
  3. Player 1은 Player 2의 락을, Player 2는 Player 1이 물고 있는 NPC 1의 락을 대기하는 복합적인 Deadlock 사슬이 형성됩니다.
  4. 다대다 멀티플레이어 환경에서 접속자가 늘어날수록, 턴을 넘길 때마다 DB 전체가 얽히면서 서버가 마비되는 최악의 결과를 초래합니다.
- **수정 결과 (Fixed)**:
  - `consume_turn()`: `process_turn()` 실행 후 `db.session.commit()`으로 플레이어 트랜잭션을 즉시 종료. 이후 `_sync_npc_turns()`를 별도로 호출.
  - `_sync_npc_turns()`는 `threading.Lock()`으로 동시 실행을 방지하고 있으며, 각 NPC의 `process_turn()`은 별도 트랜잭션으로 처리됨.
  - Player 1의 턴 트랜잭션과 NPC 1의 공격 트랜잭션이 분리되어 연쇄 Deadlock이 원천 차단됨.

---

## 2. 총평 및 판정

21차 감사에서 발견된 3건의 취약점을 모두 수정 완료하였습니다.
- [DEADLOCK-F001] Cross-attack Deadlock: `execute_battle()`의 `with_for_update()` 호출 시 `sorted([attacker.id, defender.id])`로 id 오름차순 정렬하여 락 획득 순서 강제.
- [DEADLOCK-F002] Cross-trade Deadlock: `trade_accept()` 시작 시 `sorted([park.id, sender.id])`로 id 오름차순 정렬하여 `with_for_update()`로 락을 먼저 획득한 후 UPDATE 진행.
- [DEADLOCK-F003] consume_turn-NPC Chain Deadlock: `consume_turn()`에서 `process_turn()` 후 `db.session.commit()`으로 플레이어 트랜잭션 즉시 종료. `_sync_npc_turns()`를 commit 이후 별도 호출로 분리.

**Final Decision: PASS WITH KNOWN RISKS** — 21차 감사에서 발견된 모든 Critical/Fatal 결함이 수정되었습니다.
