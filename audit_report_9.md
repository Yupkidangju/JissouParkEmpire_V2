# JissouParkEmpire 9차 감사 리포트 (심층 구현 및 로직 우회)

## 1. 개요
* **감사 일자:** 2026-05-30
* **감사 대상:** `app/game_engine.py`, `app/routes/game_routes.py`
* **감사 목적:** 구현 중심으로 수학적 문제나 버그 상세 감사
* **감사 결과 요약:** `v1.6.0`에서 도입된 AP 자동 리필 시스템 리팩토링 과정에서 발생한 이중 차감 버그와 적용 누락, 그리고 이전 감사에서 발견된 음수 방어 인원 버그가 턴이 경과해도 영구적으로 유지되는 2차 상태 모순점을 발견하였습니다.

## 2. 발견된 취약점 상세 (위험도 순)

### [IMP-F018] 밀사 파견 등 일부 행동의 이중 AP 차감 버그 (Double AP Deduction)
* **위치:** `app/game_engine.py` (`consume_turn`, `action_spy`) 및 `app/routes/game_routes.py` (`spy_send`)
* **위험도:** High (높음) — **Fixed**
* **설명:**
  `v1.6.0` 패치로 모든 행동의 AP 차감은 `game_engine.consume_turn()`에서 중앙 집중식으로 처리되도록 변경되었습니다.
  그러나 `action_spy` 함수 내부에 기존의 `park.action_points -= GC.SPY_AP_COST` 코드가 지워지지 않고 남아있었습니다. 그 결과 `spy_send` 라우트에서 `consume_turn`으로 AP를 차감한 뒤, `action_spy`에서 또다시 AP를 차감하여 밀사 파견 비용이 실제로는 **2배(2 AP)** 로 소모되었습니다.
  1 AP 보유 시 `consume_turn`이 1 AP를 차감해 0 AP가 된 후, `action_spy` 내부의 `park.action_points < GC.SPY_AP_COST` 검사(0 < 1)에 걸려 작업이 실패하고 턴만 소비하는 자원 유출(Leak) 버그가 발생했습니다.
* **수정 내용:** `action_spy` 함수 내부의 `park.action_points < GC.SPY_AP_COST` 검사 및 `park.action_points -= GC.SPY_AP_COST` 코드를 제거. AP 소비는 `spy_send` 라우트의 `consume_turn()`에서만 처리되도록 단일화함.
* **영향:** 밀사 파견 시 AP가 1회만 정상적으로 차감되며, 1 AP 보유 시에도 정상적으로 실행됨.

### [IMP-F019] 방어 배치 시 턴 쿼터 자동 소비(AP 리필) 누락
* **위치:** `app/routes/game_routes.py` -> `defend()`
* **위험도:** Medium (중간) — **Fixed**
* **설명:**
  다른 행동 라우트는 모두 `game_engine.consume_turn()`을 사용하여, AP가 0일 경우 자동으로 `turn_quota`를 1 소모하여 다음 턴으로 넘어가고 AP를 가득 채운 뒤 행동을 수행합니다.
  하지만 방어 배치(`defend`) 라우트는 `consume_turn`을 사용하지 않고 기존 방식대로 `park.action_points -= 1`을 직접 수행하고 있었습니다. 이로 인해 0 AP 상태에서 방어 배치 시 턴이 넘어가지 않고 단순히 에러만 발생했습니다.
* **수정 내용:** `defend()` 라우트의 `park.action_points -= 1` 직접 차감을 제거하고, `game_engine.consume_turn(park, ap_cost=1)` 호출로 변경. AP 부족 시 자동으로 턴 쿼터를 소비하여 턴을 진행한 뒤 AP를 리필하고 방어 배치를 수행하도록 수정함.
* **영향:** 방어 배치도 다른 행동과 동일하게 `consume_turn` 기반으로 일관되게 동작함.

### [IMP-F020] 음수 방어 인원의 턴 경과 후 영구화 취약점 (Persistent Phantom Defending Guards)
* **위치:** `app/game_engine.py` -> `process_turn()`
* **위험도:** Critical (치명적) - 8차 감사의 `[IMP-F017]` 심화 발견 — **Fixed**
* **설명:**
  매 턴이 지날 때마다 `process_turn()` 함수는 방어에 투입된 인원이 실제 인원을 초과하지 못하도록 검증하는 로직을 수행합니다.
  `park.defending_guards = min(park.defending_guards, park.guard_count)`
  여기서 하한선(`max(0, ...)`)을 설정하지 않은 것이 치명적입니다. 플레이어가 음수를 방어 인원에 입력하면, `process_turn()`의 `min()` 계산 결과가 여전히 음수가 되어 **유령 병력이 매 턴 정화 로직을 우회하여 영구적으로 유지**됩니다.
* **수정 내용:** `process_turn()`의 방어 인원 조정 로직에 `max(0, min(...))`을 적용하여 하한선을 0으로 강제함.
  - `park.defending_guards = max(0, min(park.defending_guards, park.guard_count))`
  - `park.defending_adults = max(0, min(park.defending_adults, park.adult_count))`
* **영향:** 음수 방어 인원이 턴 경과 시 자동으로 0으로 클램핑되어 유령 병력 영구화가 방지됨.

## 3. 결론 및 권고사항
이번 9차 감사에서 발견된 3건의 취약점을 모두 수정 완료하였습니다.
- [IMP-F018] 밀사 이중 AP 차감: `action_spy` 내부의 중복 AP 코드 제거 완료.
- [IMP-F019] 방어 배치 AP 리필 누락: `defend()`를 `consume_turn` 기반으로 변경 완료.
- [IMP-F020] 음수 방어 인원 영구화: `process_turn()`에 `max(0, min(...))` 하한선 추가 완료.

**Final Decision: PASS WITH KNOWN RISKS** — 9차 감사에서 발견된 모든 High/Critical/Medium 결함이 수정되었습니다.
