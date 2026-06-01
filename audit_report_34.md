# JissouParkEmpire Audit Report - 34차 감사

## 1. 개요 (Overview)
* **감사 목적**: `AI_AUDIT_DOC_STANDARD.md` 기준에 따라 `game_engine.py` 및 `battle_engine.py`의 핵심 상태 동기화 및 턴 처리 로직에 대한 상세 재감사. (코드 수정 없음)
* **발견된 주요 취약점**: 전투 피해로 인한 파괴 검증 누락(Zombie Boss) 및 보호 모드의 무한 자원 증식(Infinite Well) 결함을 발견했습니다.

## 2. 발견된 취약점 (Vulnerabilities)

### 2.1 [STATE-F009] Zombie Boss Exploit (지연 파괴 검증 누락)
* **심각도**: Critical
* **위치**: `app/battle_engine.py` (`execute_battle`), `app/game_engine.py` (`process_turn`)
* **설명**:
  `execute_battle()`에서 공격자가 승리하여 방어자(Target)의 보스실장 HP(`boss_hp`)가 0 이하로 떨어질 때, 코드 작성자는 `process_turn`에서 멸망 처리가 이루어진다고 가정하고 의도적으로 `attacker.is_destroyed = True` 처리를 생략했습니다.
  ```python
  # (boss_hp <= 0 시 다음 턴 process_turn에서 처리)
  ```
  그러나 정작 `game_engine.py`의 `process_turn()` 내부에는 `boss_hp <= 0`을 전역적으로 검사하는 로직이 **존재하지 않습니다.** (오직 굶주림이나 반란 이벤트 발생 시에만 부분적으로 검사함). 이로 인해 HP가 음수로 떨어진 공원이 멸망하지 않고 정상적으로 게임을 계속 진행할 수 있는 '좀비' 상태가 됩니다. 또한, 보호 모드 진입 시 `boss_hp`를 무조건 50으로 리셋해주기 때문에 플레이어는 멸망을 영구적으로 회피할 수 있습니다.
* **재현 시나리오**:
  1. 공격자가 다른 플레이어의 공원을 공격하여 방어자의 `boss_hp`를 -10으로 만듦.
  2. 방어자는 멸망(`gameover`) 화면을 보지 않고 계속 턴 진행 및 조작 가능.
  3. 방어자가 대시보드에 접근 시 보호 모드 로직이 발동하여 `boss_hp`가 50으로 부활함.

### 2.2 [STATE-F010] Protection Mode Infinite Well Exploit (보호 모드 무한 자원 증식)
* **심각도**: Critical
* **위치**: `app/game_engine.py` (`check_and_enter_protection`, `is_protected`)
* **설명**:
  보호 모드는 `guard_count < 1` 또는 `adult_count < 3`일 때 활성화되며, 대시보드(`/dashboard`) 접속 시마다 `check_and_enter_protection()`이 호출되어 부족한 자원과 인구를 최소치(예: `adult_count = 3`, `trash_food = 50`)로 채워줍니다.
  문제는 이 리셋이 **보호 모드 조건이 유지되는 한 대시보드 로드 시마다 무한 반복**된다는 점입니다. 플레이어가 경호실장을 보유하지 않은 상태(`guard_count == 0`)라면 항상 보호 모드로 판정됩니다.
  따라서 성체를 소모하는 행동(훈련)이나 자원을 소모하는 행동(건설, 솎아내기 등)을 한 뒤 대시보드를 리로드하기만 하면, 소비된 성체와 자원이 즉시 100% 무료 리필됩니다.
* **재현 시나리오**:
  1. 플레이어의 상태: `guard_count = 0`, `adult_count = 3` (보호 모드 활성화).
  2. 플레이어가 '훈련' 실행: `action_train()`이 호출되어 1AP와 1성체 소모 (`adult_count = 2` 됨).
  3. 라우트가 완료되어 `/dashboard`로 리다이렉트됨.
  4. 대시보드 접속 시 `is_protected()`가 True이므로 `check_and_enter_protection()` 실행.
  5. `adult_count`가 다시 3으로 채워짐.
  6. 플레이어는 이를 반복하여 무한정 훈련(Guard 양산 대기열 추가) 및 무료 자원 소모 가능.

## 3. 구조적 평가 (Architecture Assessment)
* **데이터 정합성**: 보호 모드의 멱등성(Idempotency) 결여. 보호 모드가 "일회성 부조(Bailout)"가 아니라 "조건부 패시브(Passive)"로 동작하도록 구현되어 경제 시스템 붕괴를 초래합니다.
* **상태 관리**: 파괴 상태 검증의 파편화. 엔티티 파괴와 같은 핵심 생명주기(Lifecycle) 체크가 단일 진실 공급원(Single Source of Truth) 없이 여러 곳(전투, 굶주림, 반란)에 흩어져 있고, 정작 공통 루프(`process_turn`)에는 누락된 점이 치명적인 아키텍처적 결함입니다.

## 4. 향후 감사 방향 (Next Steps)
* 보호 모드의 남용을 막기 위한 상태 전이 쿨타임(Cooldown) 또는 단방향 트리거 설계 여부 점검.
* 모든 `boss_hp` 변동 작업 직후 또는 `process_turn()`의 최상단에서 범용적 파괴 검증(`global death check`)을 수행하도록 설계 검토.
* 추가적인 상태 누수/TOCTOU 결함 조사 (특히 무한 반복 가능한 행동 위주).

---

## 5. 패치 내역 (Fixes Applied)

### [FIXED] STATE-F009 — Zombie Boss Exploit (지연 파괴 검증 누락)
- **파일**: `app/battle_engine.py`, `app/game_engine.py`
- **조치**:
  1. `execute_battle()`의 방어자 보스 피해(대승 시) 블록에 `db.session.refresh(defender)` 후 `defender.boss_hp <= 0`이면 `defender.is_destroyed = True`를 즉시 설정.
  2. `process_turn()`의 최상단, `db.session.refresh(park)` 직후에 전역 파괴 검증을 추가: `park.boss_hp <= 0`이면 `park.is_destroyed = True`로 설정하고 즉시 `return`.
- **효과**: 방어자의 `boss_hp`가 음수로 떨어져도 `process_turn` 호출을 기다리지 않고 즉시 멸망 처리됨. 좀비 공원 상태 해소.

### [FIXED] STATE-F010 — Protection Mode Infinite Well Exploit (보호 모드 무한 자원 증식)
- **파일**: `app/models.py`, `app/game_engine.py`
- **조치**:
  1. `Park` 모델에 `protection_bailout_done` (Boolean, default=False) 컬럼 추가.
  2. `check_and_enter_protection()`에 보호 모드 에피소드당 1회만 리셋 적용하는 로직 추가:
     - 보호 모드 탈출 시(`not is_protected()`) `protection_bailout_done`을 `False`로 초기화.
     - 보호 모드 진입 시(`is_protected()`) 이미 `protection_bailout_done == True`이면 리셋 스킵.
     - 리셋 적용 시 `protection_bailout_done = True`로 설정.
- **효과**: 보호 모드 진입 후 대시보드 재접속으로 무한 자원/인구 리필이 불가능해짐. 에피소드당 1회의 일회성 부조(Bailout)로 변경되어 경제 시스템 붕괴 방지.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
