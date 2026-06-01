# JissouParkEmpire 14차 감사 리포트 (Audit Report 14)

**감사 일시**: 2026-05-30
**감사 대상**: 구현 중심 수학적/아키텍처/동시성 로직 재감사 (전투 엔진, 교역 취소, 약탈 로직)
**감사 기준**: `AI_AUDIT_DOC_STANDARD.md`
**감사 방향**: 전투 중 방어자 손실의 무효화(Attacker Immunity), 교역 취소 무한 환불 버그, 약탈(Looting) 시 파이썬 단 비율 산정으로 인한 자원 창조(Double Spend) 결함 분석

---

## 1. 정합성 및 수학적 결함 (Data Integrity & Mathematical Flaws)

### 🔴 [IMP-F035] 전투 중 공격자 피해 무효화 버그 (Attacker Immunity via `refresh`)
* **발생 위치**: `app/battle_engine.py` -> `execute_battle()`
* **결함 내용**:
  전투 시 공격자의 유닛 피해(손실)는 `attacker.guard_count = max(0, attacker.guard_count - atk_losses['guards'])` 형태로 파이썬 메모리에서만 차감됩니다.
  그러나 직후 `_apply_losses(defender, ...)`를 통해 방어자 DB 업데이트만 처리한 뒤, 인구 공간 재계산을 명목으로 **`db.session.refresh(attacker)`가 호출**됩니다.
  `refresh()`는 커밋되지 않은 공격자의 메모리 변경 사항(사상자 반영값)을 모두 덮어쓰고 DB의 원본 데이터를 다시 불러옵니다. 이로 인해 **공격자는 전투에서 패배하거나 막대한 사상자가 발생했어도 유닛이 단 한 마리도 죽지 않는 불사(Immunity) 상태**가 됩니다.
* **수정 방향**: 공격자의 피해 차감 로직도 방어자와 동일하게 `_apply_losses` 내부나 별도의 원자적 `UPDATE` 문을 통해 DB에 직접 반영한 후 `refresh()`를 호출해야 합니다.
* **수정 결과 (Fixed)**:
  - `execute_battle` 내 공격자 피해 적용을 `Park.query.filter(Park.id == attacker.id).update({...})` 원자적 UPDATE + `case()` 음수 방지로 변경.
  - `db.session.refresh(attacker)` 호출 시 이미 DB에 반영된 피해가 메모리에 정상적으로 로드되므로 불사 버그가 제거됨.

### 🔴 [IMP-F036] 교역 취소(`trade_cancel`) 시 조건 미확인으로 인한 무한 중복 환불 (Double Refund)
* **발생 위치**: `app/routes/game_routes.py` -> `trade_cancel()`
* **결함 내용**:
  `trade_reject`에서는 원자적 업데이트 후 `updated == 0`을 체크하여 중복 환불을 막고 있으나, `trade_cancel`에는 해당 방어 로직이 누락되어 있습니다.
  ```python
  TradeOffer.query.filter(id==trade_id, status=='pending').update({'status': 'cancelled'})
  # 업데이트 성공 여부(Row count)를 검사하지 않고 곧바로 무조건 환불 진행!
  Park.query.update({konpeito: konpeito + trade.offer_konpeito, ...})
  ```
  플레이어가 `/trade/cancel/<id>` 요청을 동시에 10번내면, 10개의 스레드가 모두 첫 상태를 `pending`으로 읽고 통과합니다. DB 락에 의해 상태 변경 쿼리는 단 1번만 성공하고 9번은 실패(수정 0건)하지만, 코드 상 예외 처리가 없어 **10개의 스레드 모두 에스크로 자원을 환불하는 원자적 `UPDATE`를 실행**합니다. 결과적으로 취소 1번에 예치금이 10배로 복사되어 들어옵니다.
* **수정 방향**: `trade_cancel`에서도 `TradeOffer.query.update()`의 반환값(영향받은 row 수)을 `updated` 변수로 받아, `updated == 0`일 경우 즉시 `return` 하도록 수정해야 합니다.
* **수정 결과 (Fixed)**:
  - `trade_cancel`에서 `TradeOffer.query.filter(...).update(...)`의 반환값을 `updated` 변수로 캡처.
  - `if updated == 0:` 조건으로 중복 환불 시도를 즉시 차단하여 `flash(get_text('flash.trade_already'), 'error')` 반환.
  - 동시 취소 요청 시 단 1회만 환불이 실행됨.

### 🔴 [IMP-F037] 약탈(`_apply_loot`) 시 비율 산정 오차로 인한 무한 자원 창조 (Out-of-Thin-Air Resource Generation)
* **발생 위치**: `app/battle_engine.py` -> `_calculate_loot()` 및 `_apply_loot()`
* **결함 내용**:
  약탈량(`loot`)을 산정할 때 파이썬 메모리에 로드된 방어자의 초기 자원량(`defender.konpeito`)에 랜덤 비율(예: 10%)을 곱해 산출합니다.
  다중 스레드로 20번의 동시 침공을 시도할 경우, 20개의 공격 모두 **수정되기 전의 방어자 자원(예: 10,000)**을 읽고 1,000이라는 동일한 훔칠 양을 산정합니다.
  방어자의 자원을 깎는 쿼리는 `case`문에 의해 0 이하로 내려가지 않지만(최대 10,000 소진), **공격자의 자원을 늘려주는 쿼리는 `+ 1000`을 20번 강제 실행**합니다.
  결과적으로 방어자에게서 10,000을 빼앗고, 공격자는 총 20,000을 획득하게 되어 **10,000의 자원이 허공에서 복사 생성**되는 심각한 경제 파괴 결함입니다.
* **수정 방향**: `_apply_loot`에서 약탈 비율을 파이썬에서 고정 숫자로 전달하지 말고, SQL 쿼리 내부(`konpeito = konpeito + (defender.konpeito * 0.1)`)에서 처리하여 실시간 잔액을 기반으로 이동되게 하거나, 트랜잭션 락(Pessimistic Lock - `FOR UPDATE`)을 통해 동시 약탈을 직렬화해야 합니다.
* **수정 결과 (Fixed)**:
  - `execute_battle` 시작 시 `Park.query.filter(Park.id.in_([attacker.id, defender.id])).with_for_update().all()`로 비관적 락을 획득하여 동일 방어자에 대한 동시 전투를 직렬화.
  - 락 획득 후 `db.session.refresh(attacker)` 및 `db.session.refresh(defender)`로 최신 DB 상태를 메모리에 동기화.
  - 이로써 다중 동시 침공 시에도 약탈량 산정이 최신 자원 기준으로 이루어지며, 방어자 자원보다 많은 전리품이 허공에서 창조되지 않음.

---

## 2. 아키텍처 결함 (Architecture & Implementation Flaws)

### 🔴 [IMP-F038] `consume_turn` 및 턴 강제 실행이 야기하는 다중 사보타주 증폭 (Turn Race Multiplication)
* **발생 위치**: `app/game_engine.py` -> `_process_spy_missions()`
* **결함 내용**:
  AP가 고갈된 상태에서 다중 요청이 유입되면 `consume_turn`이 `process_turn()`을 여러 번 동시에 호출합니다.
  만약 완료가 1턴 남은 밀사 사보타주 임무가 있을 때 `process_turn()`이 10회 동시 실행되면, 각 스레드가 `mission.turns_remaining -= 1`을 수행하며 모두 `turns_remaining <= 0` 블록에 진입합니다.
  결과적으로 사보타주(방어자 자원 및 인구 원자적 차감 쿼리)가 10번 중복으로 폭격되어 **적 공원 하나를 순식간에 초토화시킬 수 있는 타겟 파괴 결함**이 발생합니다.
* **수정 방향**: 턴 경과 처리를 파이썬 메모리가 아닌 `UPDATE SpyMission SET turns_remaining = turns_remaining - 1 ...` 로 원자화하여 남은 턴 수가 중복으로 0을 통과하지 못하게 방어해야 합니다.
* **수정 결과 (Fixed)**:
  - `_process_spy_missions`에서 `mission.turns_remaining -= 1` 메모리 연산을 `SpyMission.query.filter(SpyMission.id == mission.id, SpyMission.turns_remaining > 0).update({'turns_remaining': SpyMission.turns_remaining - 1})` 원자적 UPDATE로 변경.
  - `updated == 0`이면 `continue`로 중복 처리 방지. `db.session.refresh(mission)`로 갱신된 값 동기화 후 `turns_remaining <= 0` 체크.
  - 동시 `process_turn` 실행 시에도 각 미션의 턴이 정확히 1씩만 차감되고, 중복 사보타주가 발생하지 않음.

---

## 3. 총평 및 판정
14차 감사에서 발견된 4건의 취약점을 모두 수정 완료하였습니다.
- [IMP-F035] Attacker Immunity: 공격자 피해를 원자적 UPDATE로 처리하여 `refresh()` 시 불사 버그 제거.
- [IMP-F036] trade_cancel Double Refund: `TradeOffer.update()` 반환값을 검증하여 중복 환불 방지.
- [IMP-F037] Loot Out-of-Thin-Air: `execute_battle` 시작 시 `with_for_update()` 비관적 락으로 동시 약탈 직렬화, `refresh` 후 최신 자원 기준으로 약탈량 산정.
- [IMP-F038] Turn Race Multiplication: `_process_spy_missions`에서 `turns_remaining` 원자적 차감으로 중복 사보타주 방지.

**Final Decision: PASS WITH KNOWN RISKS** — 14차 감사에서 발견된 모든 Critical/High/Medium/Low 결함이 수정되었습니다.
