# D3D Audit Report - 31차 재감사

## 1. Audit Scope
- **Target Files**:
  - `app/npc_engine.py` (`_npc_attack`, `_npc_cunning_attack`)
  - `app/routes/game_routes.py` (`attack`, `spy_send`)
  - `app/battle_engine.py` (`execute_battle`)
  - `app/game_engine.py` (`_process_spy_missions`, `action_spy`)
- **Focus Area**: 외교(Diplomacy) 시스템과 NPC AI, 스파이(Spy) 로직 간의 통합 정합성 검증.
- **Reference**: `spec.md` Section 9.12 (밀사 시스템), 9.14 (외교 시스템), 10.4 (Diplomacy 타입).

## 2. Excluded Scope
- 전투 로그 출력부, 랭킹 조회 성능(N+1 문제) 등 렌더링 영역 (기 감사 완료).

## 3. Pass 1: Implementation Compliance Findings

### [LOGIC-F004] NPC AI가 동맹(Ally) 조약을 무시하고 플레이어를 침공할 수 있는 결함
- **Severity**: High (게임 규칙 위반)
- **Status**: Open
- **Evidence**:
  - `spec.md` 9.14: "동맹: ... 침공 불가."
  - `app/npc_engine.py`의 `_npc_attack()` 및 `_npc_cunning_attack()` 내부를 보면, 타겟 필터링 로직이 자기 자신과 보호 모드(`is_protected`) 대상만 제외할 뿐, `Diplomacy` 모델을 조회하여 `relation_type == 'ally'`인 대상을 제외하는 로직이 전무함.
- **Expected**: NPC가 타겟을 선정할 때, 자신과 동맹 상태(`active` ally)인 공원은 타겟 리스트(`targets`)에서 반드시 제외되어야 함.
- **Actual**: 타겟 선정 쿼리 시 외교 관계를 확인하지 않으므로, 랜덤 픽에 의해 자신의 동맹을 찌르는 하극상/규칙 위반 상황이 발생함.
- **Suggested Fix**: `targets` 리스트 필터링 시 `Diplomacy` 테이블을 조인하거나 필터링하여 동맹 공원을 제외하도록 NPC 타겟팅 로직을 수정.

### [LOGIC-F005] NPC가 적대(Enemy) 상태인 플레이어 공격 시 승리 20% 약탈 보너스 누락
- **Severity**: Medium (로직 비대칭)
- **Status**: Open
- **Evidence**:
  - `spec.md` 9.14: "적대: ... 약탈 +20% 보너스."
  - `app/routes/game_routes.py`의 `attack()` 라우트에서는 플레이어가 공격하여 승리(`won == True`)한 후 `is_enemy` 여부를 조회하여 `loot`에 20%를 직접 곱하여 적용함.
  - 하지만 정작 전투 핵심 함수인 `app/battle_engine.py`의 `execute_battle()` 내부에는 해당 로직이 없음.
  - `app/npc_engine.py`의 NPC 공격 로직은 `execute_battle()`만 호출하고 `attack()` 라우트를 타지 않으므로, NPC가 적대 상태인 플레이어를 공격해 이겨도 20% 약탈 보너스를 전혀 받지 못함.
- **Expected**: 전투 보너스 등 코어 룰은 `execute_battle()` 내부 또는 공용 헬퍼 함수에서 처리되어 플레이어와 NPC에게 공평하게 적용되어야 함.
- **Actual**: 플레이어의 웹 요청(route)에만 적대 보너스 20%가 하드코딩되어 있어, NPC AI 로직은 룰의 혜택을 받지 못함.
- **Suggested Fix**: 적대 보너스(+20%) 계산 로직을 라우트(`game_routes.py`)에서 분리하여 `execute_battle()` 내부 또는 `_apply_loot()` 내부로 이관하여 일관성을 확보.

### [LOGIC-F006] 밀사 사보타주 파견 시 동맹(Ally) 불가 검증 누락
- **Severity**: Medium
- **Status**: Open
- **Evidence**:
  - `spec.md` 9.14: "동맹: ... 침공 불가." (사보타주도 적대적 행위)
  - `app/game_engine.py`의 `action_spy()` 로직을 보면, 타겟 검증 시 `is_destroyed`나 자기 자신인지만 확인할 뿐 `Diplomacy` 동맹 여부를 확인하지 않음.
- **Expected**: 일반 침공(`attack` 라우트)과 마찬가지로, 동맹을 상대로는 밀사를 보내지 못하도록 차단하거나, 파견 시 동맹이 즉시 파기되는 등의 기조가 있어야 함 (최소한 차단).
- **Actual**: 시스템상 완벽한 동맹 관계라도 밀사를 보내서 상대방의 식량을 파괴하고 저실장을 암살(사보타주)할 수 있으며, 발각되어도 동맹이 깨지지 않음.
- **Suggested Fix**: `action_spy` 내에서 타겟과의 외교 관계를 조회하여 동맹 상태일 경우 파견을 거부하는 검증 로직 추가.

## 4. Pass 2: Debug / Engineering Quality Findings

### [STATE-F006] 밀사 귀환 시 인구 상한(population_cap) 우회 현상
- **Severity**: Low (일시적 Exploit)
- **Status**: Open
- **Evidence**:
  - `app/game_engine.py`의 `_process_spy_missions()`에서, 밀사가 무사 귀환하거나 대상 공원이 멸망한 경우 `Park.adult_count + 1`을 원자적(UPDATE)으로 복귀시킴.
  - 이 턴 처리는 `consume_turn()` 내에서 `process_turn(park)` 실행(여기서 초과 인원 솎아내기인 `_process_overcrowding`이 이미 실행됨) 직후에 후행(Post-turn) 실행됨.
- **Expected**: 귀환 시에도 공원의 `population_cap`을 검증하여 초과 시 즉시 도살/탈주 처리하거나, 다음 행동 시 솎아내지도록 해야 하지만, 현재 구조상 다음 번 AP 소진 시점(즉, 다음번 `consume_turn`에서 `turn_quota`를 깎을 때까지)까지는 인구 캡을 뚫고 초과 생존함.
- **Actual**: 1마리가 `population_cap`을 초과하여 돌아와도 방치됨 (만약 10마리의 밀사가 동시 귀환하면 10마리가 인구 상한을 초과하여 존재함).
- **Suggested Fix**: `adult_count`를 돌려주는 UPDATE 실행 시, `_process_overcrowding`을 재호출하거나, UPDATE 자체에 cap case 로직을 반영해야 함.

## 5. Pass 3: Security Findings
- 본 감사에서 발견된 보안 이슈(권한 우회/인젝션 등)는 없음. 동시성 원자적 업데이트는 `_process_spy_missions`와 교역에서 잘 지켜지고 있음 (기존 감사 결과 반영 확인).

## 6. Needs Spec Clarification
- **사보타주와 외교 관계**: `spec.md`에는 '침공(Attack)'에 대해서만 동맹 시 불가라고 명시되어 있음. 사보타주(Spy)에 대해서는 동맹 시 파견 가능 여부가 명확히 적혀 있지 않아, [LOGIC-F006]을 버그로 확정하기 위해서는 기획(Spec)의 의도 확인이 필요함.

## 7. Final Decision
- **Status**: `REJECTED` (Needs Implementation fix)
- NPC가 동맹 시스템을 무시하는 하극상 버그와 20% 약탈 보너스의 비대칭 적용 등 치명적인 전투/외교 연동 결함이 남아있음.
- 코드를 수정하지 않고 보고서를 제출함. 다음 단계에서 해당 로직 수정 필요.

---

## 8. 패치 내역 (Fixes Applied)

### [FIXED] LOGIC-F004 — NPC AI가 동맹(Ally) 조약을 무시하고 플레이어를 침공할 수 있는 결함
- **파일**: `app/npc_engine.py`
- **조치**: `_npc_attack()` 및 `_npc_cunning_attack()`의 타겟 필터링 로직에 `Diplomacy` 테이블을 조회하여 `relation_type == 'ally'`이고 `status == 'active'`인 대상을 `ally_ids` 집합으로 수집한 뒤, `targets`/`weak_targets` 리스트에서 제외.
- **효과**: NPC가 동맹 관계인 공원을 침공하지 않음. 게임 규칙(spec.md 9.14) 준수.

### [FIXED] LOGIC-F005 — NPC가 적대(Enemy) 상태인 플레이어 공격 시 승리 20% 약탈 보너스 누락
- **파일**: `app/battle_engine.py`, `app/routes/game_routes.py`
- **조치**:
  1. `execute_battle()` 내부, `_calculate_loot(defender)` 직후 `_apply_loot()` 호출 이전에 `Diplomacy` 적대 관계를 조회하여 `loot['konpeito']`, `loot['trash']`, `loot['material']`에 1.2배(+20%) 보너스를 적용.
  2. `game_routes.py`의 `attack()` 라우트에서 동일한 적대 보너스 하드코딩 로직(원자적 UPDATE 포함)을 제거.
- **효과**: 플레이어와 NPC 모두 동일한 전투 핵심 함수(`execute_battle`)를 통해 적대 보너스를 공평하게 받음. 로직 비대칭 해소.

### [FIXED] LOGIC-F006 — 밀사 사보타주 파견 시 동맹(Ally) 불가 검증 누락
- **파일**: `app/game_engine.py`
- **조치**: `action_spy()` 내 타겟 검증 직후 `Diplomacy` 동맹 여부를 조회하는 로직을 추가. `relation_type == 'ally'`이고 `status == 'active'`인 경우 파견을 거부하고 메시지를 반환.
- **효과**: 동맹 관계인 공원에게 밀사 사보타주를 파견할 수 없음. 침공(Attack)과 동일한 외교 규칙이 밀사(Spy)에도 적용됨.

### [FIXED] STATE-F006 — 밀사 귀환 시 인구 상한(population_cap) 우회 현상
- **파일**: `app/game_engine.py`
- **조치**: `_process_spy_missions()`의 `for mission in active_missions:` 루프 종료 후, `db.session.refresh(park)`로 최신 DB 상태를 메모리에 동기화한 뒤 `_process_overcrowding(park)`를 재호출하고 다시 `db.session.commit()`.
- **효과**: 귀환한 밀사로 인해 `adult_count`가 `population_cap`을 초과하더라도, 임무 처리 트랜잭션 종료 직전에 과밀도 처리가 실행되어 초과 인구가 탈주/도살 처리됨.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
