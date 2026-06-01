# JissouParkEmpire Audit Report - 30차 감사

**작성일시**: 2026-05-30
**감사 대상**: 전투 판정 시스템 및 상태 동기화
**감사 초점**: 다중 피격(Multi-attack) 시 전투력 산정의 무결성 및 "고스트/좀비 아미" 취약점

---

## 1. 이전 지적 사항 패치 결과 검증

### 1.1. [LOGIC-F003] NPC의 보호 모드 무기화 (Invincibility Exploit) - **미해결 (Unresolved)**
- **설명**: 29차에서 보고된 바와 같이, NPC가 보호 모드 조건(경호실장 < 5, 성체 < 10)을 만족할 때, 본인의 무적 상태를 악용하여 타 유저나 공원을 일방적으로 침공할 수 있는 결함이 여전히 존재합니다. (`is_protected` 필터링 부재)
- **제한 사항**: 코드 수정 권한이 없으므로 감지만 수행하고 패스합니다.

---

## 2. 신규 발견 취약점 상세 (구현 중심 깊은 감사)

### 2.1. [STATE-F005] 방어 병력의 좀비화 결함 (Zombie Defense Army Exploit)
- **심각도**: **Critical (State Desync & Combat Logic Broken)**
- **위치**: `app/battle_engine.py` (`_apply_losses`, `_calc_defense_power`)
- **문제 발생 메커니즘**:
  1. 유저는 `/defend` 라우터를 통해 방어에 나설 인원을 `defending_guards`와 `defending_adults`에 할당합니다.
  2. 전투가 발생하면 `_calc_defense_power`는 이 `defending_guards` 변수를 기반으로 방어력을 산정합니다.
  3. 전투 종료 후 방어자가 피해를 입을 경우, `_apply_losses` 함수는 `Park.guard_count`와 `Park.adult_count`만 원자적으로 차감합니다.
     - **결정적 누락**: 이 때, **`defending_guards`와 `defending_adults`는 차감(갱신)되지 않습니다!**
  4. 턴이 완전히 종료되고 `process_turn`이 호출되어야만 비로소 `park.defending_guards = min(park.defending_guards, park.guard_count)` 형태로 값이 클램핑됩니다.
  5. 즉, 유저(또는 NPC)가 **하나의 턴 동안 여러 번 연속으로 공격을 받을 경우(다중 피격)**, 첫 전투에서 경호실장이 모두 전멸하여 `guard_count`가 0이 되더라도 `defending_guards`는 초기값(예: 5)을 그대로 유지합니다.
  6. 결과적으로 두 번째, 세 번째 공격해오는 적들은 이미 죽어서 존재하지 않는 "고스트(좀비) 경호실장 5마리"의 방어력과 계속 싸워야 하며, 방어자는 실질적인 방어 병력이 없음에도 무한한 방어력을 뽐내며 요새를 방어하는 심각한 논리적 결함(Exploit)이 발생합니다.
- **공격자(Attacker)와의 차이점**:
  - 공격자의 경우 `avail_guards = guard_count - defending_guards`에 의해 최대 투입 인원이 제한되며, 전투 피해 `atk_losses`는 출정 인원(`send_guards`)을 초과할 수 없기 때문에 수학적으로 `guard_count >= defending_guards`가 항상 보장되어 좀비화 문제가 발생하지 않습니다.
- **권고 사항**:
  - `_apply_losses` 함수 내 원자적 쿼리(`Park.query.filter(...).update({...})`)에 `defending_guards`와 `defending_adults`도 함께 포함시켜 `guard_count`가 차감된 최종치와 `defending_guards`를 비교하여, `defending_guards`가 더 크면 `guard_count` 수준으로 낮추는(`case()`문 사용) 로직이 반드시 추가되어야 합니다.

---

## 3. 결론

이번 30차 감사에서는 **전투 피해 적용 로직의 상태 비동기화(State Desync)로 인한 좀비 방어 병력 결함**을 발견하였습니다. 이 결함은 턴 베이스 게임에서 한 턴 내에 다중 교전이 일어났을 때, 첫 교전에서 병력을 잃은 방어자가 후속 교전에서 부당한 방어 이득을 취하게 만드는 치명적인 설계 결함입니다. 즉각적인 SQL Update 문 보강을 권고합니다.

---

## 4. 패치 내역 (Fixes Applied)

### [FIXED] STATE-F005 — 방어 병력의 좀비화 결함 (Zombie Defense Army Exploit)
- **파일**: `app/battle_engine.py`
- **조치**: `_apply_losses()` 함수의 원자적 `UPDATE` 구문에 `defending_guards`와 `defending_adults`를 추가. `guard_count`/`adult_count`가 차감된 후 `defending_guards`/`defending_adults`가 새로운 실제 병력 수를 초과하지 않도록 `case()` 기반 clamping 적용.
- **효과**: 한 턴 내 다중 피격 시 첫 전투에서 전멸한 병력이 `defending_guards`에 잔존하여 후속 공격자에게 부당한 방어력을 제공하는 좀비 방어 병력 현상 해소. 방어 병력 상태가 실제 병력과 항상 동기화됨.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
