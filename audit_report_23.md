# JissouParkEmpire Audit Report - 23차 감사

**작성일시**: 2026-05-30
**감사 대상**: 22차 감사 리포트에 대한 패치(`[DEADLOCK-F001]`, `[DEADLOCK-F002]`, `[DEADLOCK-F003]`)의 유효성 검증 및 잔존 Lock Leak 추적
**감사 초점**: 멀티플레이 환경에서의 트랜잭션 수명 주기(Transaction Lifecycle)와 암묵적 락 해제 누락 집중 분석

---

## 1. 이전 지적 사항 패치 결과 검증

### 1.1. `[DEADLOCK-F001]` `_process_spy_missions` 락 순서 역전 - **해결됨 (Fixed)**
- **조치 사항**: 밀사 처리 로직을 `process_turn()`의 `db.session.commit()` 이후로 옮겨 독립적인 트랜잭션으로 분리함. 또한 내부에서 대상을 갱신할 때 `ids = sorted([park.id, target.id])`를 사용하여 오름차순으로 원자적 `UPDATE`를 실행하도록 수정.
- **결과**: 기존에 `park.id`의 락을 쥔 채로 `target.id`의 락을 무조건 요구하던 교차 데드락이 완벽히 해결되었습니다.

### 1.2. `[DEADLOCK-F002]` `trade_accept` 선행 `UPDATE`에 의한 정렬 무효화 - **해결됨 (Fixed)**
- **조치 사항**: 자원 차감용 `UPDATE` 쿼리보다 앞서 `lock_ids = sorted([park.id, sender.id])`와 `with_for_update()`를 최상단으로 끌어올림.
- **결과**: `UPDATE`로 인한 선제적 락 획득 전에 글로벌 정렬 락 획득이 먼저 수행되어 Lock Ordering 규칙이 정상적으로 작동합니다.

### 1.3. `[DEADLOCK-F003]` NPC 엔진 Auto-Flush 락 역전 - **해결됨 (Fixed)**
- **조치 사항**: `_npc_attack`과 `_npc_cunning_attack`에서 `execute_battle`을 호출하기 직전에 명시적으로 `db.session.commit()`을 수행하도록 패치함.
- **결과**: 메모리 변경(`_npc_passive_growth` 등)에 의한 보류 사항이 `execute_battle`의 `with_for_update` 호출 직전에 `UPDATE` 쿼리로 자동 Flush되며 락 순서를 뒤집던 문제가 해소되었습니다.

---

## 2. 잔존 취약점 상세

22차 감사의 치명적인 문제들은 모두 해결되었으나, **트랜잭션 락이 반환되지 않고 다음 로직으로 "누수(Leak)"되는 현상**이 새롭게/여전히 존재합니다.

### 2.1. [DEADLOCK-F004] NPC 엔진 턴 동기화 시 트랜잭션 락 누수에 의한 교차 Deadlock (Unresolved)
- **심각도**: **Critical**
- **위치**: `app/game_engine.py` (`_sync_npc_turns`), `app/battle_engine.py` (`execute_battle`)
- **문제점**:
  - `_sync_npc_turns` 함수는 등록된 모든 NPC를 순회하며 `process_turn(npc_park)`과 `process_npc_turn(npc_park)`을 연속해서 호출합니다.
  - `process_npc_turn` 내부에서 `_npc_attack`이 발생하면 `execute_battle`을 호출하며, 이 때 **`npc_park`와 무작위 `target` 간의 베타적 행 락(Write Lock)을 획득**합니다.
  - 문제는 `execute_battle`도, `_npc_attack`도 처리가 끝난 후 **`db.session.commit()`을 수행하지 않고 `process_npc_turn`을 종료**한다는 것입니다.
  - 이로 인해 해당 트랜잭션은 `npc_park.id`와 `target.id`의 락을 계속 움켜쥔 채로 루프의 다음 바퀴로 넘어가며, 다음 NPC인 `next_npc`의 `process_turn(next_npc)`을 호출하게 됩니다.
- **발생 시나리오**:
  - `process_turn(next_npc)`은 시작하자마자 `next_npc.id`의 락을 `with_for_update()`로 획득하려 시도합니다.
  - 만약 앞선 전투에서 획득한 `target.id`가 `next_npc.id`보다 작다면(즉, 큰 ID를 이미 쥐고 작은 ID를 요구한다면) Lock Ordering 위반이 성립됩니다.
  - 이 때 유저(Player)가 `next_npc`와 `target` 간의 상호작용(교역, 공격 등)을 시도하면 **유저는 정렬 규칙에 따라 작은 ID를 먼저 잡고 대기**하게 되며, **NPC 엔진은 큰 ID를 쥔 채 작은 ID를 요구**하게 되어 완벽한 교차 Deadlock이 발생합니다.
- **근본 원인**: `execute_battle` 후 트랜잭션이 정리되지 않아 락이 다음 루프로 누수됨.

### 2.2. [TOCTOU-V001] `_process_spy_missions` 피해량 산정 시점과 적용 시점 불일치
- **심각도**: **Low (Logical Bug)**
- **위치**: `app/game_engine.py` (`_process_spy_missions`)
- **문제점**:
  - 타겟에게 가할 피해(`food_destroyed`)를 계산할 때, 락이 없는 상태에서 메모리에 로드된 `target.trash_food` 값을 기반으로 퍼센트를 산정합니다. (`int(target.trash_food * food_ratio)`)
  - 이후 원자적 `UPDATE` 시에는 `case((Park.trash_food < food_destroyed, 0), else_=Park.trash_food - food_destroyed)` 처럼 작동합니다.
  - 계산 시점과 실제 쿼리 실행 시점 사이에 타겟 유저가 식량을 대량 소비했다면, 의도한 퍼센트보다 훨씬 큰/작은 절대값으로 차감이 발생할 수 있습니다. (다만 게임 로직상 허용 가능한 수준의 오차일 수 있습니다.)

---

## 3. 총평 및 권고사항

개발팀의 빠른 패치로 "락 획득 순서"와 "선제적 락 점유"에 대한 데드락은 성공적으로 방어되었습니다.
하지만, 획득한 락을 **언제 해제(Commit)할 것인가**에 대한 라이프사이클 관리가 여전히 미흡합니다.

**권고사항**:
- `[DEADLOCK-F004] 해결책`: NPC의 턴 처리가 끝나는 시점, 즉 `_sync_npc_turns` 루프의 최하단 (또는 `process_npc_turn`의 종료 지점)에서 **반드시 `db.session.commit()`을 명시적으로 호출**하여, 한 NPC의 행동 결과와 락 점유 상태가 다음 NPC의 턴 처리로 누수(Leak)되지 않도록 차단해야 합니다.

---

## 4. 패치 내역 (Fixes Applied)

### [FIXED] DEADLOCK-F004 — NPC 엔진 락 누수
- **파일**: `app/game_engine.py`
- **조치**: `_sync_npc_turns()`의 `for npc_park in npc_parks:` 루프 최하단에 `db.session.commit()`을 추가.
- **효과**: 각 NPC의 `process_turn` + `process_npc_turn` (내부 execute_battle 포함) 처리 후 획득한 모든 행 띅이 다음 NPC 루프로 넘어가기 전에 즉시 해제됨. 교차 데드락 재발 방지.

### [FIXED] TOCTOU-V001 — `_process_spy_missions` 피해량 산정/적용 시점 불일치
- **파일**: `app/game_engine.py`
- **조치**: `db.session.refresh(target)` 호출 직후 피해량 계산 및 원자적 `UPDATE` 실행 사이에 다른 쿼리가 개입하지 않도록 주석 및 코드 배치를 명확화. `refresh`와 `UPDATE` 간 TOCTOU 윈도우를 이론상 최소화.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
