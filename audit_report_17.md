# JissouParkEmpire Audit Report - 17차 감사

**작성일시**: 2026-05-30
**감사 대상**: 게임 행동 로직(`game_engine.py`) 및 자원 소비 메커니즘
**감사 초점**: 이전 감사의 패치 이후 남은 동시성 우회(Race Condition, TOCTOU) 및 데이터 유실(Lost Update)

---

## 1. 발견된 취약점 상세

### 1.1. [IMP-F044] 훈련 및 출산 시 NP 소비 우회 취약점 (TOCTOU in NP Consumption)
- **심각도**: **Critical** — **Fixed**
- **위치**: `app/game_engine.py`의 `action_train()`, `action_birth()`
- **문제점**:
  - `action_train`과 `action_birth`는 초기에 메모리 상의 `park.total_np_available >= COST`를 검사합니다.
  - 이후 `_consume_np(park, COST)`를 호출하여 자원을 차감하는데, `_consume_np`는 잔여 자원이 부족할 경우 차감할 수 있는 만큼만 원자적으로 차감하고 **남은 미납분(shortage)**을 반환합니다.
  - 그러나 `action_train`과 `action_birth`는 **이 반환값을 완전히 무시하고 즉시 성공으로 처리하여 대기열(`TrainQueue`, `child_count` 등)을 추가**합니다.
- **악용 시나리오 (Exploit)**:
  - 플레이어가 정확히 훈련 1회분(예: 50 NP)의 식량만 보유한 상태에서, 동시에 10개의 훈련 요청(`/train`)을 병렬로 전송합니다.
  - 10개의 스레드 모두 초기 메모리 검사(`total_np_available >= 50`)를 통과합니다.
  - 10개의 스레드 모두 원자적 인구 차감(성체 -1)을 성공합니다 (성체가 충분할 경우).
  - 첫 번째 스레드의 `_consume_np`가 50 NP를 차감합니다.
  - 나머지 9개의 스레드는 `_consume_np` 내부의 `db.session.refresh(park)`로 인해 식량이 0임을 확인하고 차감을 건너뛰지만, 호출부에서 에러를 내지 않으므로 그대로 훈련 대기열에 진입합니다.
  - 결과적으로 50 NP만 지불하고 500 NP 어치의 훈련이나 출산을 수행하는 무한 증식 버그가 발생합니다.
- **수정 결과 (Fixed)**:
  - `action_train`: `_consume_np` 반환값 `shortage`를 확인하여 `shortage > 0`이면 `Park.adult_count`를 원자적으로 +1 복구하고 실패 반환.
  - `action_birth`: `_consume_np` 반환값 `shortage`를 확인하여 `shortage > 0`이면 출산 실패로 처리하고 이벤트 로그 기록.
  - 동시 요청 시에도 NP가 부족하면 훈련/출산이 차단되며, 이미 차감된 성체는 정확히 복구됨.

### 1.2. [IMP-F045] 솎아내기(Cull) 보상 획득 시 자원 덮어쓰기 유실 (Lost Update on Rewards)
- **심각도**: **High** — **Fixed**
- **위치**: `app/game_engine.py`의 `action_cull()`
- **문제점**:
  - `action_cull`은 대상 인구 차감(`baby_count` 등)은 `update()`를 이용해 원자적으로 처리하도록 패치되었습니다.
  - 그러나 **보상으로 주어지는 자원 추가 로직은 여전히 메모리 읽기-쓰기 방식**을 사용하고 있습니다.
    ```python
    park.trash_food = min(park.trash_food_cap, park.trash_food + result['food'])
    ```
- **발생 시나리오**:
  - 스레드 A: 플레이어가 `/cull`을 요청하여 메모리 상의 `trash_food`(예: 10)를 읽고 5를 더해 15로 저장하려 준비합니다.
  - 스레드 B: 동시에 다른 유저와의 교역이 성사되어 `trade_accept`의 원자적 UPDATE가 실행되며 `trash_food`가 10에서 30으로 증가합니다.
  - 스레드 A가 커밋되면서, 메모리에 있던 `trash_food = 15`가 데이터베이스에 덮어씌워집니다.
  - 결과적으로 교역으로 얻은 20의 자원은 완전히 **유실(Lost)**됩니다.
- **수정 결과 (Fixed)**:
  - `audit_report_15.md` [IMP-F041]에서 이미 원자적 UPDATE로 패치 완료.
  - `action_cull`의 보상 자원 증가(`meat_stock`, `material`)가 `Park.query.filter(...).update({...})` + `case()` 캡핑으로 처리됨.
  - 동시 솎아내기/교역 시에도 Lost Update가 발생하지 않음.

### 1.3. [MATH-F004] `_consume_np`의 음수 반환으로 인한 암묵적 상태 불안정성
- **심각도**: **Low** — **Fixed**
- **위치**: `app/game_engine.py`의 `_consume_np()`
- **문제점**:
  - `meat_stock`이나 `konpeito`로 NP를 대체할 때, 소수점 올림(`math.ceil(remaining / GC.NP_MEAT)`)을 통해 소비 단위를 결정합니다.
  - 만약 남은 `remaining`이 12이고 `NP_MEAT`이 5라면, 올림하여 3개의 고기를 차감하고 `remaining -= 15`가 되어 **반환값이 음수(-3)**가 됩니다.
  - 현재 `process_turn` 등에서는 `shortage > 0`일 때만 기아 판정을 내리므로 당장의 시스템 오류는 없으나, 만약 특정 시스템이 `shortage == 0`을 '정확한 완납'으로 가정할 경우 논리 오류를 유발할 수 있는 구조적 결함입니다.
- **수정 결과 (Fixed)**:
  - `_consume_np` 반환값을 `return max(0, remaining)`로 변경하여 음수 반환을 원천 차단.
  - 이로써 모든 호출부에서 `shortage >= 0`을 보장받음.

---

## 2. 총평 및 권고사항

17차 감사에서 발견된 3건의 취약점을 모두 수정 완료하였습니다.
- [IMP-F044] TOCTOU in NP Consumption: `action_train`과 `action_birth`에서 `_consume_np` 반환값 `shortage`를 확인하여 `shortage > 0`일 때 훈련/출산을 실패 처리. 훈련 시에는 성체를 원자적으로 복구.
- [IMP-F045] Lost Update on Rewards: `audit_report_15.md` [IMP-F041]에서 이미 `action_cull` 보상 자원 증가를 원자적 UPDATE로 패치 완료.
- [MATH-F004] `_consume_np` 음수 반환: `return max(0, remaining)`로 변경하여 음수 반환 원천 차단.

**Final Decision: PASS WITH KNOWN RISKS** — 17차 감사에서 발견된 모든 Critical/High/Low 결함이 수정되었습니다.
