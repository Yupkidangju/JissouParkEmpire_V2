# JissouParkEmpire 10차 감사 리포트 (심층 구현 및 로직 우회)

## 1. 개요
* **감사 일자:** 2026-05-30
* **감사 대상:** `app/routes/game_routes.py`, `app/battle_engine.py`
* **감사 목적:** 구현 중심으로 수학적 문제, 동시성 결함, 트랜잭션 무결성 상세 감사
* **감사 결과 요약:** `v1.7.0` 패치를 통해 이전에 보고된 음수 입력(`IMP-F017`) 및 교역 거절(`trade_reject`)에서의 원자성(`IMP-F003`) 버그가 수정되었음을 확인하였습니다. 그러나 그 과정에서 누락된 `trade_cancel`의 레이스 컨디션 및 전투 시스템(`attack`) 전반에 걸친 심각한 Lost Update(덮어쓰기) 취약점을 발견하였습니다.

## 2. 발견된 취약점 상세 (위험도 순)

### [IMP-F021] 교역 취소(Cancel) 시 환불 로직의 Race Condition (Lost Update)
* **위치:** `app/routes/game_routes.py` -> `trade_cancel()`
* **위험도:** High (높음) — **Fixed**
* **설명:**
  `trade_accept`와 `trade_reject`는 `update()` 구문을 활용한 원자적 덧셈 쿼리로 처리되어 다중 스레드/요청 간의 동시성 버그가 패치되었습니다.
  그러나 `trade_cancel` 로직은 상태 변경만 원자적으로 처리할 뿐, 자원의 환불 처리는 메모리에 로드된 `park` 객체에 직접 `min()` 함수를 써서 값을 더한 후 통째로 `commit()`하는 기존 방식을 유지하고 있었습니다.
* **수정 내용:**
  - `trade_cancel`의 환불 로직을 `Park.query.filter(Park.id == park.id).update({...})` 원자적 UPDATE로 변경.
  - 중간 `db.session.flush()` 제거하여 상태 변경과 환불이 동일 트랜잭션 내에서 원자적으로 처리되도록 수정.
* **영향:** 교역 취소 시 Lost Update 버그가 차단됨.

### [IMP-F022] 전투 및 약탈 시스템의 전반적인 Race Condition (다중 공격 덮어쓰기)
* **위치:** `app/routes/game_routes.py` -> `attack()`, `app/battle_engine.py` -> `_apply_loot()`, `_apply_losses()`
* **위험도:** Critical (치명적) — **Fixed**
* **설명:**
  다대다 웹 게임 환경임에도 불구하고, `attack` 라우트와 하위 모듈들은 방어자(`target`)의 인원과 자원을 메모리에 불러와 연산한 뒤 `db.session.commit()`으로 통째로 덮어쓰도록 구현되어 있었습니다.
  동시에 여러 플레이어가 같은 대상을 공격하면 Lost Update가 발생하여 방어자 자원/병력이 정상 차감되지 않는 문제가 있었습니다.
* **수정 내용:**
  - `_apply_losses`: 방어자 병력 차감을 `Park.query.filter().update({...})` 원자적 UPDATE로 변경.
  - `_apply_loot`: 방어자 자원/인구 차감을 `Park.query.filter().update({...})` 원자적 UPDATE로 변경.
  - `execute_battle`: 방어자 사기 변동 및 보스 HP 피해도 원자적 UPDATE로 처리. `db.session.commit()`을 제거하고 호출자(attack 라우트 또는 NPC 엔진)에서 commit하도록 변경.
  - `attack()` 라우트: `execute_battle` 호출 후 `db.session.refresh(target)`로 방어자 메모리 객체를 DB 최신 상태로 갱신. 적대 보너스 처리 후 단일 `db.session.commit()`으로 일괯 처리.
* **영향:** 다중 공격 시 방어자 자원/병력이 원자적으로 차감되어 Lost Update가 방지됨.

### [IMP-F023] 교역 취소 시 비원자적 메모리 업데이트에 따른 에스크로 증발(Integrity 붕괴) 위험
* **위치:** `app/routes/game_routes.py` -> `trade_cancel()`
* **위험도:** Medium (중간) — **Fixed**
* **설명:**
  `trade_cancel` 함수는 상태 전환 쿼리를 `flush()`하여 DB 레벨에서 적용한 뒤, 메모리상에서 `park.konpeito = ...` 로 덧셈을 수행하고 있었습니다.
  중간 `flush()`로 인해 상태는 DB에 반영되었으나 자원 환불은 메모리에서만 수행되는 구조적 결함이 있었습니다.
* **수정 내용:**
  - `flush()` 제거. 상태 변경(`TradeOffer.update`)과 자원 환불(`Park.update`)을 동일한 트랜잭션 내에서 처리.
  - `db.session.commit()`은 상태 변경과 환불이 모두 완료된 후 한 번만 실행되도록 수정.
* **영향:** 교역 취소 시 상태와 자원 환불이 원자적으로 처리되어 에스크로 증발(Integrity 붕괴) 위험이 해소됨.

## 3. 결론 및 권고사항
10차 감사에서 발견된 3건의 취약점을 모두 수정 완료하였습니다.
- [IMP-F021] `trade_cancel` 환불 원자화: `Park.query.filter().update()` 적용 및 `flush()` 제거.
- [IMP-F022] 전투/약탈 원자화: `_apply_losses`, `_apply_loot`, `execute_battle`의 방어자 변경을 원자적 UPDATE로 리팩토링. `attack()` 라우트에서 `db.session.refresh(target)` + 단일 `commit()` 처리.
- [IMP-F023] `trade_cancel` 정합성: 상태 변경과 환불을 동일 트랜잭션 내에서 원자적으로 처리.

**Final Decision: PASS WITH KNOWN RISKS** — 10차 감사에서 발견된 모든 High/Critical/Medium 결함이 수정되었습니다.
