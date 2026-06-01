# JissouParkEmpire Audit Report - 29차 감사

**작성일시**: 2026-05-30
**감사 대상**: 전투 및 NPC 타겟팅 관련 시스템 로직
**감사 초점**: NPC 특권 남용 및 보호 모드(Protection Mode) 무력화 논리 결함 점검

---

## 1. 이전 지적 사항 패치 결과 검증

### 1.1. [LOGIC-F002] NPC의 동맹(Alliance) 무시 및 강제 백스탭 결함 - **미해결 (Unresolved)**
- **설명**: 28차에서 보고된 바와 같이, `_npc_attack` 및 `_npc_cunning_attack` 내부에서 타겟을 선정할 때 동맹(`Diplomacy` 상태가 'active')인 대상을 배제하는 쿼리 필터링이 누락되어 있습니다.
- **제한 사항**: 본 감사는 코드 수정 권한이 없으므로, 해당 이슈는 지속적인 경고 상태로 남겨둡니다.

---

## 2. 신규 발견 취약점 상세 (구현 중심 깊은 감사)

### 2.1. [LOGIC-F003] NPC의 보호 모드 무기화 (Invincibility Exploit)
- **심각도**: **High (Gameplay/Balance Breaking)**
- **위치**: `app/npc_engine.py` (`_npc_attack` 및 `_npc_cunning_attack`), `app/routes/game_routes.py` (`attack` 라우터)
- **문제 발생 메커니즘**:
  1. 시스템 상 "보호 모드(Protection Mode)"는 공원이 극도로 취약해졌을 때 발동하며(`guard_count < 5` 또는 `adult_count < 10`), 보호 모드 중인 대상은 침공할 수 없는 무적 상태가 됩니다.
  2. 공정성을 위해 유저(Human)가 침공을 시도할 경우, `/attack` 라우터에서 본인이 보호 모드인지 검사하여 침공을 원천 차단합니다. (보호 방벽 뒤에서 일방적으로 공격하는 것을 막음)
  3. 하지만 NPC가 공격을 결정하는 `_npc_attack` 및 `_npc_cunning_attack`에서는 **본인(NPC 자신)이 보호 모드인지 검사하는 로직이 완전히 누락**되어 있습니다.
  4. NPC의 최소 공격 조건은 `guard_count >= 1` 또는 `adult_count >= 3`입니다. 따라서 NPC가 4마리의 경호실장과 9마리의 성체를 보유한 경우, 해당 NPC는 시스템적으로 **보호 모드** 판정을 받아 타인의 공격을 전혀 받지 않지만, 자신은 유저나 타 NPC를 일방적으로 짓밟고 자원을 약탈(Attack)할 수 있는 악의적인 무적 상태(Invincibility Exploit)를 누리게 됩니다.
- **권고 사항**:
  - `_npc_attack` 및 `_npc_cunning_attack` 함수의 도입부에 유저와 동일하게 `if game_engine.is_protected(park): return` 조건을 추가하여 보호 모드 상태에서는 출정을 제한해야 합니다.

### 2.2. [DEADCODE-M001] 방어 배치 라우터(`/defend`) 내 도달 불가능한 데드 코드 존재
- **심각도**: **Low (Clean Code / Maintenance Issue)**
- **위치**: `app/routes/game_routes.py` (336~343 라인 부근)
- **설명**: `defend` 함수 내부에서 `return redirect(url_for('game.dashboard'))`가 호출된 직후, 들여쓰기가 잘못되거나 중복 병합된 데드 코드가 남아있습니다.
  ```python
  flash(get_text('flash.defend_deploy', guards=num_guards, adults=num_adults), 'success')
  return redirect(url_for('game.dashboard'))

  park.action_points -= 1 # 도달 불가 영역 (Dead Code)
  park.defending_guards = num_guards
  # ...
  ```
  이 코드는 논리적인 결함을 일으키지는 않지만, 유지보수 측면에서 혼동을 유발하므로 정리가 필요합니다.

---

## 3. 결론

이번 29차 감사에서는 NPC가 보호 모드(안전지대)의 맹점을 악용해 **피해를 받지 않으면서 일방적으로 침공이 가능한 밸런스 붕괴 논리 결함**을 적발하였습니다. 또한 병합 중 실수로 남겨진 데드 코드를 발견하였습니다.
NPC의 침공 로직에 `is_protected(park)` 검사를 즉시 도입하여 불공정한 일방적 약탈을 차단할 것을 권고합니다.

---

## 4. 패치 내역 (Fixes Applied)

### [FIXED] LOGIC-F003 — NPC의 보호 모드 무기화 (Invincibility Exploit)
- **파일**: `app/npc_engine.py`
- **조치**: `_npc_attack()` 및 `_npc_cunning_attack()` 함수 도입부에 `if game_engine.is_protected(park): return` 조건을 추가.
- **효과**: 보호 모드 상태의 NPC는 자신이 보호받으면서도 타인을 침공하는 일방적 무적 상태가 해소됨. 유저와 동일한 보호 모드 행동 제한이 NPC에게도 적용됨.

### [FIXED] DEADCODE-M001 — 방어 배치 라우터 내 도달 불가능한 데드 코드
- **파일**: `app/routes/game_routes.py`
- **조치**: `defend()` 함수의 `return redirect(...)` 이후에 남아있던 도달 불가능한 중복 코드(`park.action_points -= 1` 등)를 제거.
- **효과**: 유지보수 혼란 제거 및 코드 가독성 향상.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
