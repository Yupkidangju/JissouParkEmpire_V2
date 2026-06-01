# JissouParkEmpire 8차 감사 리포트 (심층 구현 및 로직 우회)

## 1. 개요
* **감사 일자:** 2026-05-30
* **감사 대상:** `app/models.py`, `app/battle_engine.py`, `app/routes/game_routes.py`, `app/game_engine.py` 등 게임 내 복합 로직 및 상태 변이 시스템
* **감사 목적:** 수학적 오류, 원자성 보장 실패, 입력값 검증 누락, 상태(State) 로직 모순점 발굴
* **감사 결과 요약:** 외교 상태 중첩 버그, 교역 환불 시 상한선 우회, 그리고 이전 7차 감사에서 발견된 방어 인원 음수 버그가 유발하는 '무한 공격력 생성(Phantom Attack Power)' 이라는 치명적인 Exploit을 확인하였습니다.

## 2. 발견된 취약점 상세 (위험도 순)

### [IMP-F017] 방어 병력 음수 설정을 악용한 무한 공격력 생성 (Phantom Attack Power)
* **위치:** `app/battle_engine.py` -> `execute_battle()`, `app/routes/game_routes.py` -> `defend()`
* **위험도:** **Critical (치명적)** — **Fixed**
* **설명:**
  7차 감사에서 발견된 **[IMP-F012] 방어 병력 배치 시 음수 입력 우회 취약점**이 초래하는 실제적인 파괴적 결함입니다.
  `execute_battle` 함수는 공격자가 출정시킬 수 있는 병력을 다음과 같이 계산합니다.
  `avail_guards = max(0, attacker.guard_count - attacker.defending_guards)`
  만약 공격자가 방어 병력(`defending_guards`)을 음수로 설정해두었다면, `avail_guards`가 보유량을 초과하는 값이 됩니다.
* **수정 내용:**
  1. `defend()` 라우트: `num_guards`/`num_adults`에 `max(0, ...)` 적용하여 음수 입력을 강제로 0으로 차단.
  2. `execute_battle()`: `avail_guards`/`avail_adults` 계산 시 `min(보유량, ...)`으로 가용 인원이 실제 보유량을 초과하지 않도록 이중 방어 가드 추가.
* **영향:** 방어 병력 음수 설정을 통한 유령 병력(Phantom Troops) 생성 Exploit이 완전히 차단됨.

### [IMP-F015] 동맹/적대 상태 동시 존재 (State Machine Violation in Diplomacy)
* **위치:** `app/routes/game_routes.py` -> `diplomacy_enemy()` 및 `diplomacy_accept()`
* **위험도:** High (높음) — **Fixed**
* **설명:**
  외교 시스템에서 적대 선언(`diplomacy_enemy`)을 할 때, 기존에 맺어져 있던 동맹을 해제하는 로직이 있습니다. 그러나 이 검사 로직(`existing_ally`)은 오직 `status == 'active'`인 상태만 찾아서 해제(`dissolved`)합니다.
  따라서 A 공원이 B 공원에게 동맹 요청(`pending` 상태)을 보낸 뒤, 즉시 B 공원에게 적대 선언(`active` 상태)을 하면, 기존의 `pending` 동맹 요청은 해제되지 않고 남아있게 됩니다. 이후 B 공원이 교역소에서 그 동맹 요청을 수락(`diplomacy_accept`)하면 두 공원은 **`active` 상태의 적대 관계이면서 동시에 `active` 상태의 동맹 관계**를 가지게 되어 외교 로직이 완전히 꼬이게 됩니다.
* **수정 내용:** `diplomacy_enemy()`의 `existing_ally` 쿼리에서 `Diplomacy.status == 'active'`를 `Diplomacy.status.in_(['active', 'pending'])`로 확장하여, pending 상태의 동맹 요청도 적대 선언 시 자동으로 `dissolved` 처리되도록 수정함.
* **영향:** 동맹 요청 pending 중 적대 선언 시 요청이 자동 취소되어 동맹/적대 동시 존재 상태가 방지됨.

### [IMP-F016] 교역 취소 및 거절 시 저실장 인구 상한선(baby_cap) 우회
* **위치:** `app/routes/game_routes.py` -> `trade_reject()`, `trade_cancel()`
* **위험도:** Medium (중간) — **Fixed**
* **설명:**
  교역 제안을 수락(`trade_accept`)할 때는 에스크로에서 자원을 받을 때 `baby_cap`을 검사하여 초과 인구를 버리는 로직이 존재합니다. 하지만 교역을 등록한 발송자가 제안을 취소(`trade_cancel`)하거나 수신자가 거절(`trade_reject`)하여 자원이 환불될 때는 `baby_count`에 대한 cap 검사 로직이 누락되어 있습니다.
* **수정 내용:**
  - `trade_reject()`: 발송자 환불 후 `sender.baby_count = min(sender.baby_count, sender.baby_cap)` 추가.
  - `trade_cancel()`: 취소자 환불 후 `park.baby_count = min(park.baby_count + trade.offer_babies, park.baby_cap)`로 변경.
* **영향:** 교역 취소/거절을 통한 `baby_cap` 우회 Exploit이 차단됨.

## 3. 결론 및 권고사항
이번 8차 감사에서 발견된 3건의 취약점을 모두 수정 완료하였습니다.
- [IMP-F017] 무한 병력 Exploit: `defend()` 음수 입력 차단 + `execute_battle()` 가용 병력 보유량 캡핑으로 차단 완료.
- [IMP-F015] 외교 상태 중첩: `diplomacy_enemy()`에서 pending 동맹 요청도 자동 해제 처리하도록 수정 완료.
- [IMP-F016] 교역 환불 baby_cap 우회: `trade_reject()` 및 `trade_cancel()`에 `baby_cap` 캡핑 로직 추가 완료.

**Final Decision: PASS WITH KNOWN RISKS** — 8차 감사에서 발견된 모든 Critical/High/Medium 결함이 수정되었습니다.
