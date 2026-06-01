# JissouParkEmpire Audit Report (Turn 6)

## 1. 개요 (Overview)
* **감사 일시**: 2026-05-30
* **감사 대상**: 전체 프로젝트 (구현 중심의 상세 감사 진행 - 결함 및 모순 도출)
* **감사 목적**: AI_AUDIT_DOC_STANDARD.md의 규격에 따른 상세 감사 진행. 이전 감사에서 확인되지 않은 세부 기능(밀사, 전투 피해, 인구 제한, 중독 판정)의 논리적 결함 및 버그 탐색.
* **감사 결과 요약**: 밀사 파견 후 대상 공원 멸망 시 성체 증발 버그, 전투 방어자 피해 계산 시 소수점 절사(Exploit) 방어 누락, 약탈/이벤트/교역을 통한 인구 상한선(Population Cap) 무시 버그, 콘페이토 중독 판정 시 쓰레기 섭취 여부를 누락하는 버그 등 총 4건의 심각한 구현 결함 발견.

---

## 2. 발견된 문제점 (Findings)

### [IMP-F007] 밀사 귀환 시 성체실장 증발 버그 (Spy Adult Evaporation)
* **심각도**: High
* **상태**: Fixed
* **위치**: `app/game_engine.py`의 `_process_spy_missions` 함수
* **증상**: 파견된 밀사가 임무를 마치고 귀환할 때, 대상 공원이 이미 멸망(`is_destroyed`)한 상태라면 성체실장이 공원 인구로 복구되지 않고 그대로 소멸함.
* **원인**: 대상 공원이 멸망한 경우 `mission.status = 'returned'`로 설정되고 `continue`가 호출되나, 이 과정에서 파견 시 차감했던 `park.adult_count += 1` 처리(반환 로직)가 누락되어 있음.
* **수정 내용**: 대상 멸망 분기에 `park.adult_count += 1` 및 귀환 이벤트 로그를 추가하여 성체실장이 무사히 복귀하도록 수정함.
* **영향**: 플레이어 및 NPC의 성체실장이 영구적으로 증발하는 버그가 해소됨.

### [IMP-F008] 방어자 전투 피해 계산 시 확률적 반올림(Stochastic Rounding) 누락
* **심각도**: High
* **상태**: Fixed
* **위치**: `app/battle_engine.py`의 `_calc_losses` 함수
* **증상**: 방어 인원이 적을 경우 패배하거나 승리하더라도 사망자가 단 1명도 발생하지 않는 무적 방어(Exploit)가 가능함.
* **원인**: v1.6.2 업데이트에서 공격자의 소수점 피해 무시를 방지하기 위해 `stochastic_round`를 도입(`_calc_losses_selected`)했으나, 방어자의 피해를 계산하는 `_calc_losses` 함수에는 이를 적용하지 않고 여전히 `int(park.guard_count * loss_rate)`를 사용하여 소수점 이하 피해를 무조건 내림(0) 처리함. (예: 4명 × 20% = 0.8명 → 0명 사망)
* **수정 내용**: `_stochastic_round`를 모듈 레벨 함수로 추출하고, `_calc_losses`에서도 `int()` 대신 `_stochastic_round()`를 사용하도록 수정함.
* **영향**: 방어 유닛을 소수로 유지하더라도 확률적으로 피해가 발생하여 전투 밸런스가 정상화됨.

### [IMP-F009] 약탈/이벤트/교역을 통한 인구 상한선(Population Cap) 우회
* **심각도**: Critical
* **상태**: Fixed
* **위치**:
  - `app/battle_engine.py`의 `_apply_loot` 함수
  - `app/game_engine.py`의 `action_gather` (야생 실장 발견 이벤트)
  - `app/routes/game_routes.py`의 `trade_accept` 함수
* **증상**: 시설물(운치굴 등)에 의한 인구 수용 상한선을 무시하고 자실장과 저실장을 무한대로 늘릴 수 있음.
* **원인**: 출산(`action_birth`) 시에는 `population_cap`과 `baby_cap`을 정상적으로 확인하여 상한을 강제하지만, **전투 약탈**, **채집 이벤트**, **교역 수락**으로 인구를 획득할 때는 해당 Cap 확인 로직이 완전히 누락되어 있음 (`park.baby_count += loot['babies']` 등 단순 덧셈).
* **수정 내용**:
  - `_apply_loot`: 공격자 `baby_count`에 `baby_cap`, `child_count`에 `population_cap` 캡핑 적용
  - `action_gather`: 야생 실장석 발견 시 `baby_cap` 및 `population_cap` 초과 방지
  - `trade_accept`: 수락자/발송자 `baby_count`에 `baby_cap` 캡핑 적용
* **영향**: 인구 상한선을 우회한 무한 인구 증식이 차단됨.

### [IMP-F010] 콘페이토 중독 판정 로직의 쓰레기 섭취 누락 (Addiction Logic Flaw)
* **심각도**: Medium
* **상태**: Fixed
* **위치**: `app/game_engine.py`의 `_process_food_consumption` 및 `_process_addiction` 함수
* **증상**: 쓰레기 식량과 콘페이토를 함께 소비하더라도 100% 콘페이토만 섭취한 것으로 오인되어 중독 수치가 오름.
* **원인**: `_process_food_consumption`에서 식량 소비 후 `_konpeito_consumed_this_turn`과 `_meat_consumed_this_turn` 속성만 플래그로 저장함. 중독 판정 시 `konpeito_consumed and not meat_consumed` 조건으로만 판단하며, **쓰레기(Trash Food) 소비 여부**를 검증하지 않음. 따라서 쓰레기와 콘페이토를 병행 소비해도 고기를 먹지 않으면 중독 스택이 상승함.
* **수정 내용**: `_process_food_consumption`에 `trash_before` 저장 및 `_trash_consumed_this_turn` 플래그 추가. `_process_addiction`에서 중독 판정 조건을 `konpeito_consumed and not meat_consumed and not trash_consumed`로 확장하여 쓰레기 소비 여부도 검증함.
* **영향**: 콘페이토와 쓰레기를 함께 소비하면 중독 스택이 상승하지 않도록 수정되어 중독 회피 전략이 정상 작동함.

---

## 3. 권고 사항 (Recommendations)
* **코드 수정 완료**: 위 발견된 4가지 구현(버그) 결함이 모두 소스 코드 수정을 통해 해결되었습니다.
* **수정 완료 사항**:
  1. `game_engine.py` 내 밀사 귀환 상태 시 `park.adult_count += 1` 복구 로직 추가 완료.
  2. `battle_engine.py` 내 `_calc_losses` 함수에도 `stochastic_round` 적용 완료.
  3. 전투, 채집, 교역의 인구 증가 부분에 `min(기존값 + 추가값, cap)` 캡핑 로직 일괄 적용 완료.
  4. `game_engine.py` 내 `_process_food_consumption`에서 `_trash_consumed_this_turn` 변수를 추가 추적하여 중독 판정 조건 개선 완료.

## 4. 감사 결과 (Final Decision)
- **PASS WITH KNOWN RISKS**: 6차 감사에서 발견된 4건의 구현 결함 `[IMP-F007]`~`[IMP-F010]`을 모두 수정 완료하였음. 밀사 귀환 유닛 증발, 전투 방어자 소수점 피해 Exploit, 인구 상한 우회, 콘페이토 중독 판정 오류가 모두 해소됨.
