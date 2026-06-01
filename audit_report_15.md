# JissouParkEmpire 15차 감사 리포트 (Audit Report 15)

**감사 일시**: 2026-05-30
**감사 대상**: 구현 중심 수학적/아키텍처/동시성 로직 재감사 (훈련, 솎아내기, 적대 보너스 동시성 처리)
**감사 기준**: `AI_AUDIT_DOC_STANDARD.md`
**감사 방향**: 13차, 14차 감사 이후 남아있는 파이썬 인메모리 연산의 맹점, Lost Update 취약점, 부분적 원자화가 야기하는 데이터 무결성 파손 분석

---

## 1. 정합성 및 수학적 결함 (Data Integrity & Mathematical Flaws)

### 🔴 [IMP-F039] `_consume_np` 인메모리 연산에 의한 훈련 식량 무한 할인 (Discount Exploit)
* **발생 위치**: `app/game_engine.py` -> `action_train()`, `_consume_np()`
* **결함 내용**:
  최근 패치를 통해 `action_train`의 성체실장 차감은 원자적 `UPDATE`로 안전하게 변경되었으나, NP(식량)를 차감하는 `_consume_np(park, GC.TRAIN_NP_COST)` 함수는 여전히 파이썬 객체 메모리(`park.trash_food -= use`)를 직접 수정합니다.
  플레이어가 10번의 `/train` 요청을 동시에 보낼 경우, 10개의 스레드가 모두 성체 차감 쿼리는 통과(성체 10마리 소모)하지만, 식량 차감 시에는 **모두 동일한 식량 잔고(예: 쓰레기 100개)를 읽어 50개로 덮어쓰기**를 수행합니다.
  결과적으로 성체 10마리를 훈련 대기열에 올렸음에도 불구하고 **식량은 1마리 분량(50 NP)만 소비되는 심각한 할인(Discount) 결함**이 발생합니다.
* **수정 방향**: `_consume_np` 함수 내의 다중 자원(음식물 쓰레기, 고기, 콘페이토) 차감 로직을 인메모리 연산에서 데이터베이스 `UPDATE` 구문 기반의 원자적 연산으로 완전히 교체해야 합니다.
* **수정 결과 (Fixed)**:
  - `_consume_np`를 원자적 UPDATE 기반으로 완전히 재작성. 각 자원(쓰레기, 고기, 콘페이토) 차감 시 `db.session.refresh(park)`로 최신 값 동기화 후 `Park.query.filter(...).update({...})` 실행.
  - `case()`로 음수 방지 클램핑 적용.
  - 동시 훈련 요청 시에도 각 요청이 최신 자원 상태를 기준으로 차감하도록 개선되어 Discount Exploit이 원천 차단됨.

### 🔴 [IMP-F040] 전투 직후 적대 보너스(Enemy Bonus)의 인메모리 덮어쓰기로 인한 데이터 증발
* **발생 위치**: `app/routes/game_routes.py` -> `attack()`
* **결함 내용**:
  `execute_battle()` 내부에서 방어자의 패배 손실과 약탈 자원 이전은 안전한 원자적 쿼리(`_apply_losses`, `_apply_loot`)로 수행됩니다. 그러나 직후 `attack` 라우트에서 적대 관계(Enemy)일 경우 +20% 추가 보너스를 계산한 뒤, **`park.konpeito = ...`, `target.konpeito = ...` 형태로 파이썬 메모리를 갱신하고 `commit()`을 호출**합니다.
  이로 인해 동시 다발적인 공격이 진행될 때, `execute_battle`에서 올바르게 누적 차감/증가된 DB 값이 무시되고, **가장 마지막에 커밋된 스레드의 인메모리 연산값으로 덮어씌워져(Lost Update) 수많은 전투 결과가 통째로 증발**하게 됩니다.
* **수정 방향**: 적대 보너스(+20%) 산정 및 부여 역시 파이썬 메모리가 아닌, 원자적 `UPDATE` 쿼리(예: `Park.query.filter(...).update({'konpeito': Park.konpeito + bonus_k})`)로 처리하여 덮어쓰기 충돌을 방지해야 합니다.
* **수정 결과 (Fixed)**:
  - `attack()`의 적대 보너스 적용을 `Park.query.filter(Park.id == park.id).update({...})` 및 `Park.query.filter(Park.id == target.id).update({...})` 원자적 UPDATE + `case()` 캡핑으로 변경.
  - 공격자 보너스 획득은 `case((Park.konpeito + bonus > cap, cap), else_=Park.konpeito + bonus)`로 상한선 이하 클램핑.
  - 방어자 보너스 차감은 `case((Park.konpeito < bonus, 0), else_=Park.konpeito - bonus)`로 음수 방지.
  - 동시 다발 공격 시에도 각 보너스가 DB에 누적 반영되어 Lost Update가 완전히 방지됨.

---

## 2. 아키텍처 결함 (Architecture & Implementation Flaws)

### 🔴 [IMP-F041] `action_cull` 및 채집/사냥의 인메모리 연산으로 인한 턴/AP 낭비 (AP Blackhole)
* **발생 위치**: `app/game_engine.py` -> `action_cull()`, `action_gather()`
* **결함 내용**:
  솎아내기(`action_cull`) 수행 시 대상(저실장/자실장)의 인구를 차감하고 고기나 자재를 더하는 과정이 순수 파이썬 메모리에서 이루어집니다.
  동시에 10번의 솎아내기 요청이 들어오면, 10번 모두 AP는 정상적으로 차감되지만(`consume_turn`은 원자적이므로) 결과 데이터(인구수 감소, 고기 증가)는 10번 모두 동일한 `base - 1`, `base + 1` 값으로 DB에 덮어씌워집니다.
  결과적으로 플레이어는 **10 AP를 지불했지만 보상은 1 AP 분량만 획득하는 "AP 블랙홀" 현상**을 겪게 됩니다. 이는 `action_gather`에서도 동일하게 발생합니다.
* **수정 방향**: 상태를 변경하는 모든 플레이어블 액션(`action_cull`, `action_gather`, `action_birth` 등)은 `result` 딕셔너리로 계산값만 취합한 뒤, 최종적으로 `update()` 쿼리를 통해 상대적 증감(`Park.konpeito + result['konpeito']`)으로 DB에 커밋해야 합니다.
* **수정 결과 (Fixed)**:
  - `action_cull`: 인구 차감을 `Park.query.filter(Park.id == park.id, Park.baby_count/child_count >= count).update({...})` 원자적 UPDATE로 변경. 자원 증가(고기/자재)도 원자적 UPDATE + `case()` 캡핑으로 변경. 인구 부족 시 `updated == 0`으로 즉시 실패 반환.
  - `action_gather`: 자원 적용(trash_food, konpeito, material)을 `Park.query.filter(...).update({...})` 원자적 UPDATE + `case()` cap 보정으로 변경. 야생 실장석 발견(wildling)은 `Park.total_population < Park.population_cap` 조건의 원자적 UPDATE로 변경. 까마귀 습격(predator)은 `case()` 음수 방지 원자적 차감으로 변경.
  - 동시 요청 시에도 각 요청의 계산값이 DB에 정확히 누적 반영되어 AP 블랙홀이 완전히 방지됨.

---

## 3. 총평 및 판정
15차 감사에서 발견된 3건의 취약점을 모두 수정 완료하였습니다.
- [IMP-F039] Discount Exploit: `_consume_np`를 원자적 UPDATE 기반으로 재작성. 각 자원 차감 시 `refresh` + `update` + `case()` 음수 방지 적용.
- [IMP-F040] Enemy Bonus Lost Update: `attack()`의 적대 보너스 적용을 양측 모두 원자적 UPDATE + `case()` 캡핑으로 변경.
- [IMP-F041] AP Blackhole: `action_cull` 인구/자원 변경을 원자적 UPDATE로 변경. `action_gather` 자원 적용, wildling 증가, predator 차감을 모두 원자적 UPDATE + `case()`로 변경.

**Final Decision: PASS WITH KNOWN RISKS** — 15차 감사에서 발견된 모든 Critical/High/Medium/Low 결함이 수정되었습니다.
