# JissouParkEmpire Audit Report - 28차 감사

**작성일시**: 2026-05-30
**감사 대상**: NPC 인공지능(AI) 타겟팅 로직, 파라미터 조작에 의한 부작용
**감사 초점**: 이전 취약점 패치 확인 및 NPC의 논리적 결함(Logic Flaw) 점검

---

## 1. 이전 지적 사항 패치 결과 검증

### 1.1. [SEC-F001] 도살(Cull) 라우트의 음수 파라미터 취약점 - **해결됨 (Fixed)**
- **조치 사항**: `game_routes.py`의 `cull()` 내부에서 `count = max(1, count)`를 강제하여 0 및 음수 입력을 완벽하게 차단했습니다.
- **결과**: 음수 인구를 이용한 무한 증식 익스플로잇이 원천 차단되었습니다.

### 1.2. [LOGIC-F001] 과밀도 강제 퇴거 로직 우회 (성체 무적) - **해결됨 (Fixed)**
- **조치 사항**: `game_engine.py`의 `_process_overcrowding()` 내부 로직이 보완되어 자실장(`child_count`)뿐만 아니라 성체(`adult_count`)와 경호실장(`guard_count`)까지 순차적으로 인구 상한치 초과분에 대해 사망/탈주 처리를 진행하도록 개선되었습니다.
- **결과**: 더 이상 자실장을 고의로 없애는 방식으로 성체 무적 우회를 할 수 없습니다.

---

## 2. 신규 발견 취약점 상세 (구현 중심 깊은 감사)

### 2.1. [LOGIC-F002] NPC의 동맹(Alliance) 무시 및 강제 백스탭(Backstab) 로직 결함
- **심각도**: **High (Gameplay/Trust-Breaking)**
- **위치**: `app/npc_engine.py` (`_npc_attack` 및 `_npc_cunning_attack` 함수)
- **문제 발생 메커니즘**:
  1. 유저 간 침공(`game_routes.py`의 `/attack`)의 경우 `Diplomacy` 테이블을 조회하여 `is_ally` 상태라면 공격을 명시적으로 차단합니다(`flash.ally_no_attack`).
  2. NPC와 동맹을 맺을 때, 유저가 NPC 대상(`is_npc == True`)으로 동맹을 요청하면 즉시 `status='active'`로 승인 및 성립됩니다.
  3. 하지만 NPC가 행동을 결정할 때 호출되는 `_npc_attack` 및 `_npc_cunning_attack` 함수 내부 타겟 리스트(`targets = Park.query.filter(...)`)에서는, **자신과 동맹인 공원(Ally)을 제외하는 조건이 완전히 누락**되어 있습니다. (보호 모드 제외 로직만 존재)
  4. 그 결과, 유저가 외교(Diplomacy) 시스템을 이용해 전략적으로 NPC와 평화 협정(동맹)을 맺었음에도 불구하고, NPC는 랜덤 픽이나 약자 공격 알고리즘에 의해 동맹인 유저의 공원을 무자비하게 침공(Backstab)할 수 있습니다.
- **권고 사항**:
  - `_npc_attack` 및 `_npc_cunning_attack` 함수 내부에서 `Diplomacy` 테이블을 참조하여 타겟 후보(`targets`)에서 동맹 상태(`active`)인 공원(`park.id`)을 필터링(제외)하도록 쿼리 또는 파이썬 리스트 컴프리헨션을 개선해야 합니다.

---

## 3. 결론

이번 28차 감사에서는 유저의 파라미터 조작뿐만 아니라, **시스템(NPC) 로직이 게임 내 명시적 규칙(동맹 불침)을 스스로 위반하는 치명적인 논리 결함**을 적발하였습니다. NPC와의 동맹 시스템을 무의미하게 만드는 버그이므로 타겟팅 로직의 즉각적인 수정(외교 상태 필터링 추가)을 권고합니다.
