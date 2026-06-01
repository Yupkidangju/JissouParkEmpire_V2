# JissouParkEmpire 11차 감사 리포트 (심층 구현 및 로직 우회)

## 1. 개요
* **감사 일자:** 2026-05-30
* **감사 대상:** `app/npc_engine.py`, `app/game_engine.py` (`_process_spy_missions`), `app/battle_engine.py` (`_apply_loot`, `_apply_losses`), `app/routes/game_routes.py` (`trade_accept`)
* **감사 목적:** 구현 중심으로 수학적 문제, 10차 보고서(v1.7.0 패치) 적용 이후의 파생 버그 및 동시성 결함 상세 감사
* **감사 결과 요약:** 이전 10차 감사 보고를 바탕으로 `v1.7.0` 패치에서 많은 부분(`trade_cancel`, `execute_battle` 등)에 원자적(Atomic) 업데이트가 도입되었습니다. 그러나 이 패치가 완전하지 않아 원자적 쿼리의 특성(모델 Validator 우회)을 이용한 **음수 자원 Exploit**이 새롭게 발생하였으며, 메모리 업데이트 혼용에 의한 **Lost Update(덮어쓰기)** 문제도 여전히 남아있습니다.

## 2. 발견된 취약점 상세 (위험도 순)

### [IMP-F027] 전투 원자적 UPDATE에 따른 음수 자원/인구 뚫림 (Negative Exploit)
* **위치:** `app/battle_engine.py` -> `_apply_loot()`, `_apply_losses()`
* **위험도:** Critical (치명적) — **Fixed**
* **설명:**
  `v1.7.0` 패치에서 Race Condition을 방지하고자 방어자의 자원 차감을 원자적 SQL UPDATE로 변경하였으나, `WHERE` 절에 음수 방지 제약이 누락되어 있었습니다. SQLAlchemy의 `update()`는 모델 `@validates`를 거치지 않으므로, 동시 공격 시 방어자의 인구/자원이 음수로 떨어질 수 있었습니다.
* **수정 내용:** `_apply_losses`와 `_apply_loot`의 원자적 UPDATE에 `case((Park.x < 차감량, 0), else_=Park.x - 차감량)`를 적용하여 DB 레벨에서 음수 방지 클램핑을 수행함. SQLAlchemy `case()`를 import하여 사용.
* **영향:** 동시 공격 시에도 방어자 자원/인구가 0 이하로 떨어지지 않음.

### [IMP-F028] `trade_accept` 에스크로 환원 보정 시의 Race Condition (Lost Update)
* **위치:** `app/routes/game_routes.py` -> `trade_accept()`
* **위험도:** High (높음) — **Fixed**
* **설명:**
  `trade_accept`에서 자원 차감은 원자적으로 처리되어 Double-Spend는 막혔으나, 자원을 받는(더하는) 과정은 메모리 객체 수정 후 `commit()`으로 처리되어, 외부 이벤트로 인한 자원 변경이 Lost Update로 증발할 수 있었습니다.
* **수정 내용:** 수락자(park)와 발송자(sender)의 자원 추가 모두를 `Park.query.filter().update({...})` 원자적 UPDATE + `case((... > cap, cap), else_=...)`로 변경. 메모리 `min()` 연산을 제거하고 DB 레벨에서 cap 보정과 동시성 방지를 동시에 수행함.
* **영향:** 교역 수락 시 자원 추가가 원자적으로 처리되어 Lost Update가 방지됨.

### [IMP-F025] 밀사 사보타주(Spy Sabotage) 타겟 업데이트 시 Race Condition (Lost Update)
* **위치:** `app/game_engine.py` -> `_process_spy_missions()`
* **위험도:** Medium (중간) — **Fixed**
* **설명:**
  밀사가 적 공원에 침투해 자원/인구를 파괴할 때, 대상 공원(`target`) 객체를 메모리로 로드하여 뺄셈 연산을 수행했습니다. 이로 인해 동시 요청 시 트랜잭션 충돌 및 덮어쓰기가 발생할 수 있었습니다.
* **수정 내용:** `target.trash_food = max(...)` 메모리 연산을 `Park.query.filter(Park.id == target.id).update({...})` 원자적 UPDATE + `case((Park.x < 차감량, 0), else_=Park.x - 차감량)`으로 변경.
* **영향:** 밀사 사보타주의 자원 파괴가 원자적으로 처리되어 Lost Update가 방지됨.

### [IMP-F024] NPC의 AP 소비 로직 누락에 따른 무한 행동/AP 증발 버그
* **위치:** `app/npc_engine.py` -> `_npc_birth`, `_npc_build_house`, `_npc_train`
* **위험도:** Low (낮음) — **Fixed**
* **설명:**
  NPC의 각종 행동 함수는 `game_engine.action_*(park)` 호출 후 반환값(성공 여부)을 검사하지 않고 무조건 AP를 차감했습니다. 실제 행동이 실패하더라도 AP가 날아가는 구조적 모순이 있었습니다.
* **수정 내용:** `_npc_gather`, `_npc_birth`, `_npc_build_house`, `_npc_build_wall`, `_npc_train`에서 `action_*`의 반환값 `success`를 확인하여 `success`일 때만 `park.action_points -= N`을 실행하도록 수정. `_npc_attack`과 `_npc_cunning_attack`은 전투 시도 자체가 AP 소모 대상이므로 `won` 여부와 무관하게 AP 차감을 유지하되, 반환값을 명시적으로 받도록 수정.
* **영향:** NPC가 실패한 행동에 대해서는 AP를 소모하지 않아 행동 효율이 정상화됨.

## 3. 결론 및 권고사항
11차 감사에서 발견된 4건의 취약점을 모두 수정 완료하였습니다.
- [IMP-F027] 전투 원자적 UPDATE 음수 뚫림: `_apply_losses`, `_apply_loot`에 `case()`로 DB 레벨 음수 방지 클램핑 적용.
- [IMP-F028] `trade_accept` Lost Update: 수락자/발송자 자원 추가를 원자적 UPDATE + `case()` cap 보정으로 변경.
- [IMP-F025] 밀사 사보타주 Lost Update: `_process_spy_missions`의 target 자원 차감을 원자적 UPDATE + `case()`로 변경.
- [IMP-F024] NPC AP 무조건 차감: `_npc_gather`, `_npc_birth`, `_npc_build_*`, `_npc_train`에서 `success` 반환값 확인 후 AP 차감하도록 수정.

**Final Decision: PASS WITH KNOWN RISKS** — 11차 감사에서 발견된 모든 Critical/High/Medium/Low 결함이 수정되었습니다.
