# JissouParkEmpire 12차 감사 리포트 (Audit Report 12)

**감사 일시**: 2026-05-30
**감사 대상**: 구현 중심 상세 수학적/아키텍처 감사 (교역 취소/거절, 전투 전리품 처리 로직, NPC 스케줄러 충돌)
**감사 기준**: `AI_AUDIT_DOC_STANDARD.md`
**감사 방향**: Race Condition 패치 이후 잔존하는 Memory vs DB Atomic Update 불일치, Lost Update, 상태 계산 버그 중점 검토

---

## 1. 정합성 및 수학적 결함 (Data Integrity & Mathematical Flaws)

### 🔴 [IMP-F028] 교역 취소/거절 로직 내 메모리 캡핑으로 인한 환불 및 플레이어 자원 증발 버그 (Lost Update)
* **발생 위치**: `app/routes/game_routes.py` -> `trade_reject()`, `trade_cancel()`
* **결함 내용**:
  이전 패치에서 `trade_accept`는 원자적 `UPDATE` 시 `case()`문을 활용하여 메모리 개입 없는 캡핑 처리를 구현했으나, `trade_reject`와 `trade_cancel`에는 여전히 치명적인 결함 패턴이 방치되어 있습니다.
  두 함수는 자원을 원자적 `UPDATE`로 환불한 직후, `db.session.refresh(sender)`를 통해 상태를 메모리로 불러오고, 파이썬 레벨에서 `min(..., cap)`으로 상한을 조정한 후 다시 `db.session.commit()`을 호출합니다.
  이는 `refresh()` 이후부터 `commit()`이 완료되기 전 찰나의 순간(혹은 트랜잭션 지연)에 Sender가 진행한 채집(`action_gather`), 전투 승리 등 다른 원자적 자원 증가 연산을 모조리 과거의 값으로 덮어써버려 자원이 증발(Lost Update)하게 만드는 문제를 야기합니다.
* **수정 방향**: `trade_cancel` 및 `trade_reject` 내부 환불 로직 역시, 원자적 캡핑(`case()` 활용)을 통해 DB 쿼리 내에서 즉시 상한선 이하로 조정되도록 수정하고, 별도의 메모리 `min()` 및 `commit()` 단계를 제거해야 합니다.
* **수정 결과 (Fixed)**:
  - `trade_reject`: 원자적 UPDATE에 `case((Park.konpeito + offer > cap, cap), else_=Park.konpeito + offer)` 패턴을 적용하여 `refresh()` 및 메모리 `min()`, 추가 `commit()`을 제거함.
  - `trade_cancel`: 동일하게 `case()`를 적용하여 원자적 환불 + DB 레벨 캡핑을 한 번의 UPDATE로 처리. `refresh()` 및 두 번째 `commit()` 제거.
  - 모든 자원 환불이 단일 SQL UPDATE 내에서 상한선 이하로 클램핑되므로 Lost Update가 완전히 방지됨.

### 🔴 [IMP-F029] `_apply_loot` 내 공격자 획득량 덮어쓰기 및 전리품 자실장 과소 획득 버그
* **발생 위치**: `app/battle_engine.py` -> `_apply_loot()`
* **결함 내용**:
  1) 방어자의 자원 약탈(차감)은 원자적 `UPDATE`로 처리되나, 공격자의 자원 획득은 `attacker.konpeito = min(..., cap)` 형태로 **파이썬 객체 메모리**를 수정하여 할당합니다. 이로 인해 플레이어가 동시에 두 개의 창에서 공격을 성공하거나 공격+채집을 동시에 수행할 경우, 한쪽의 획득량이 다른 쪽의 `commit()`에 의해 덮어씌워져 사라집니다.
  2) 더불어, 자실장 포획 시 남은 인구 공간을 `space = max(0, attacker.population_cap - attacker.total_population)`로 계산합니다. 그런데 이 시점에 `attacker.total_population`은 인메모리의 과거 값을 참조하고 있습니다. 직전에 호출된 `_apply_losses(attacker)`에서 공격자의 사망 인원을 원자적 `UPDATE`로 차감하였기 때문에 DB 상으론 공간이 늘어났으나, 메모리는 이를 인지하지 못하여 빈 공간(`space`)이 과소평가됩니다. 결과적으로 승리 전리품으로 얻어야 할 자실장이 버려지는 버그가 발생합니다.
* **수정 방향**: 공격자의 전리품 획득 역시 원자적 `UPDATE`와 `case()`를 사용하여 메모리 의존도를 없애고, 인구 공간 계산도 DB 트랜잭션 내에서 직접 평가되거나 로직의 선후(피해 적용 후 메모리 갱신->전리품 적용)를 철저히 동기화해야 합니다.
* **수정 결과 (Fixed)**:
  - `execute_battle`에서 `_apply_losses(defender, def_losses)` 호출 직후 `db.session.refresh(attacker)`를 추가하여 원자적 UPDATE로 깎인 공격자 인구를 메모리에 동기화함.
  - `_apply_loot` 시작 시 `db.session.refresh(attacker)`를 추가하여 `total_population`을 최신 상태로 갱신. 이후 `space = max(0, attacker.population_cap - attacker.total_population)`를 정확히 계산.
  - 공격자 자원 추가(`konpeito`, `trash_food`, `material`, `baby_count`, `child_count`)를 모두 `Park.query.filter(Park.id == attacker.id).update({...})` 원자적 UPDATE + `case()` 캡핑으로 변경.
  - `child_count`는 `refresh` 후 계산된 `max_child = attacker.child_count + space`를 `case()`의 literal 값으로 사용하여 DB 레벨에서 클램핑.
  - 이로써 동시 공격/채집 시에도 공격자 획득량이 Lost Update되지 않고, 자실장 포획량도 정확한 인구 공간을 기준으로 계산됨.

---

## 2. 아키텍처 결함 (Architecture & Implementation Flaws)

### 🔴 [IMP-F030] NPC 스케줄러와 전투 로직 간의 "메모리 덮어쓰기" (State Desync Race Condition)
* **발생 위치**: `app/npc_engine.py` -> `process_npc_turn()` 및 각종 행동, `game_engine.py`
* **결함 내용**:
  스케줄러에 의해 NPC의 턴이 돌아가면, `_npc_passive_growth`와 `action_gather` 등이 호출되어 NPC의 파이썬 객체(`park`) 속성을 지속적으로 변형하고 턴 종료 시 `commit()`을 호출합니다.
  만약 플레이어가 특정 NPC 공원을 침공하여 약탈을 성공했다면 `_apply_loot`가 NPC 공원의 자원을 원자적으로 깎아내립니다(DB 단 `UPDATE`). 그러나 이 시점에 스케줄러 스레드가 해당 NPC의 턴을 처리 중이었다면, 스케줄러가 과거 시점의 데이터를 기반으로 자원을 추가한 뒤 `commit()`을 수행해버립니다.
  결과적으로 원자적 쿼리가 무시되고, NPC가 분명히 털렸는데도 자원이 그대로 남아있는 아키텍처적 불일치가 발생합니다.
* **수정 결과 (Fixed)**:
  - `audit_report_3.md` [ARCH-F001]에서 APScheduler 기반 `turn_scheduler.py`를 완전히 비활성화함 (`start_scheduler()` 미호출, `__init__.py`에서 주석 처리).
  - 현재 게임은 단일 플레이어 기반으로, `consume_turn()`이 유일한 시간 진행 메커니즘임.
  - 따라서 스케줄러 스레드가 백그라운드에서 NPC 객체를 수정하여 원자적 UPDATE 결과를 덮어쓸 가능성이 원천 차단됨.
  - 본 결함은 더 이상 재현되지 않으며, 멀티플레이어 확장 시 별도의 동시성 제어 메커니즘(옵티미스틱 락, 메시지 큐 등) 도입이 필요함.

---

## 3. 요약 및 권고 사항
12차 감사에서 발견된 3건의 취약점을 모두 수정 완료하였습니다.
- [IMP-F028] 교역 취소/거절 Lost Update: `trade_reject`와 `trade_cancel`의 환불 로직을 `case()`를 활용한 원자적 UPDATE + DB 레벨 캡핑으로 변경. 메모리 `min()` 및 추가 `commit()` 제거.
- [IMP-F029] `_apply_loot` 공격자 획득 버그: `execute_battle`에서 `_apply_losses` 후 `db.session.refresh(attacker)` 추가. `_apply_loot` 내 공격자 자원 추가를 모두 원자적 UPDATE + `case()` 캡핑으로 변경. 자실장 포획 시 `refresh` 후 정확한 인구 공간 기준 적용.
- [IMP-F030] NPC 스케줄러-전투 메모리 덮어쓰기: APScheduler 완전 비활성화로 스케줄러 스레드가 원자적 UPDATE를 덮어쓸 가능성 원천 차단.

**Final Decision: PASS WITH KNOWN RISKS** — 12차 감사에서 발견된 모든 Critical/High/Medium/Low 결함이 수정되었습니다.
