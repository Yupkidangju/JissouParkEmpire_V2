# JissouParkEmpire Audit Report 35

## 1. 개요 (Overview)
- **감사 일시**: 35차 감사
- **감사 대상**: `game_engine.py` (인구 증감, 훈련, 밀사 파견, 턴 처리 로직), `battle_engine.py` (전투 피해 적용 로직)
- **발견된 취약점 수**: 1개 (기능/로직/상태 불일치)

## 2. 발견된 취약점 상세 (Vulnerability Details)

### [STATE-F011] Phantom Defense Exploit (방어 병력 동기화 누락 및 좀비 방어선)
- **심각도**: **High**
- **유형**: State Divergence / Logic Flaw
- **위치**:
  - `app/game_engine.py`: `action_train()`, `action_spy()`, `action_birth()`, `_process_starvation()`, `_process_overcrowding()`
  - `app/routes/game_routes.py`: `defend()`
- **설명**:
  게임 시스템에서 공원의 전투 방어력은 `defending_guards`와 `defending_adults`에 의해 결정됩니다. 사용자는 `/defend` 라우트를 통해 현재 보유 중인 `guard_count`와 `adult_count` 한도 내에서 방어 인원을 배치할 수 있습니다.
  전투 엔진(`battle_engine.py`의 `_apply_losses`)에서는 전투로 인해 병력이 사망할 경우, 감소한 인구 수에 맞추어 `defending_guards`와 `defending_adults`를 올바르게 clamping(상한선 조정)하여 감소시킵니다.
  그러나 **전투 이외의 원인으로 병력이 감소하는 모든 로직(훈련, 밀사 파견, 출산 중 모체 사망, 기아, 과밀도 탈주 등)**에서는 `adult_count`와 `guard_count`를 차감하면서 **방어 배치 인원(`defending_*`)을 함께 감소시키지 않는 치명적인 누락**이 존재합니다.
- **Exploit 시나리오**:
  1. 사용자가 10마리의 성체실장을 보유하고 있습니다.
  2. 1 AP를 소모하여 10마리 모두 방어 병력으로 배치합니다 (`defending_adults` = 10).
  3. 남은 AP를 사용하여 `action_train`이나 `action_spy`를 반복 실행하여 성체실장 10마리를 전부 소모합니다 (`adult_count` = 0).
  4. 이 상태에서 다른 플레이어나 NPC가 공격을 오면, 실제 성체실장이 0마리임에도 불구하고 방어 전투력 계산 시 `defending_adults`가 10으로 적용되어 방어력 보너스를 그대로 얻게 됩니다.
  5. `game_engine.py`의 `process_turn()` 함수 시작 부분에서 배치 인원을 clamping하는 로직이 추가되었으나, **턴(AP)이 완전히 소모되기 전(AP > 0)**에 `action_train` 등을 수행한 직후에는 `process_turn()`이 호출되지 않으므로, 다음 턴 리셋 전까지 "유령 방어선"이 유지되는 악용이 가능합니다.
- **영향**:
  플레이어는 방어 병력을 미리 최대로 배치해 두고 훈련(경호실장 전환)이나 밀사 파견으로 성체실장을 소모하여 **이중 이득(Double Benefit)**을 취할 수 있으며, 방어 밸런스를 붕괴시킵니다.
- **수정 권고안**:
  `action_train`, `action_spy`, `action_birth` 등 인구수(특히 성체와 경호실장)를 차감하는 모든 원자적 `UPDATE` 로직과 ORM 메모리 수정 로직에 `defending_adults` 및 `defending_guards`를 동기화(clamping)하는 로직을 추가해야 합니다.
  *예시 (`action_train` 내부 UPDATE):*
  ```python
  updated = Park.query.filter(Park.id == park.id, Park.adult_count >= 1).update({
      'adult_count': Park.adult_count - 1,
      'defending_adults': case(
          (Park.defending_adults > Park.adult_count - 1, Park.adult_count - 1),
          else_=Park.defending_adults
      )
  })
  ```
  이와 같이 인구가 줄어드는 모든 곳에서 `defending_adults`가 `adult_count`를 초과하지 못하도록 즉각 보정해야 합니다.

## 3. 총평 및 권고사항 (Conclusion & Recommendations)
이전 감사(`audit_report_30.md [STATE-F005]`)에서 전투 피해 적용 시의 방어 인원 동기화 누락과 `process_turn` 진입 시의 초기화 로직은 추가되었으나, **턴 도중(Intra-turn) 발생하는 인구 소모 및 상태 변화(훈련, 밀사 파견 등)에 대한 방어 병력 clamping은 누락되어 있습니다.** 이는 게임의 자원 소모 모델(성체를 희생하여 다른 이득을 취함)을 회피할 수 있는 심각한 경제/전투 밸런스 버그입니다. 인구가 직접 차감되는 모든 도메인 이벤트에 대해 방어선 보정 로직을 원자적으로 결합할 것을 권고합니다.

---

## 4. 패치 내역 (Fixes Applied)

### [FIXED] STATE-F011 — Phantom Defense Exploit (방어 병력 동기화 누락 및 좀비 방어선)
- **파일**: `app/game_engine.py`
- **조치**: 성체실장/경호실장이 전투 이외 원인으로 감소하는 모든 로직에 `defending_adults`/`defending_guards` clamping을 추가:
  1. `action_train()`: 원자적 `UPDATE`에 `defending_adults` case() clamping 추가 (`Park.defending_adults > Park.adult_count - 1`이면 `Park.adult_count - 1`로).
  2. `action_spy()`: 원자적 `UPDATE`에 `defending_adults` case() clamping 추가.
  3. `action_birth()`: 모체 사망 시 `park.defending_adults = min(park.defending_adults, park.adult_count)` 추가.
  4. `_process_starvation()`: 성체/경호 사망 시 `defending_adults`/`defending_guards`를 `min()`으로 clamping.
  5. `_process_overcrowding()`: 성체/경호 탈주 시 `defending_adults`/`defending_guards`를 `min()`으로 clamping.
  6. `_process_human_events()`: 실험체 포획(성체 1마리 감소) 시 `defending_adults` clamping.
  7. `_process_rebellion()`: 경호 쿠데타(경호 감소) 시 `defending_guards` clamping.
- **효과**: 방어 병력을 최대로 배치한 뒤 훈련/밀사로 성체를 소모해도 `defending_adults`가 실제 `adult_count`를 초과하지 않음. Phantom Defense Exploit 및 좀비 방어선 현상 해소.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
