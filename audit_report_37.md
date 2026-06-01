# JissouParkEmpire Audit Report - 37차

## 1. 개요 (Overview)
- **감사 일시**: 37차 감사
- **감사 대상**:
  - `app/game_engine.py` (Protection 로직 검증 및 기아, 재해 이벤트 추적)
  - `app/npc_engine.py` (NPC 패시브 성장 및 상태 동기화)
- **감사 목적**:
  - `check_and_enter_protection`이 유발할 수 있는 보호 모드 무한 리셋 익스플로잇 가능성 검증.
  - NPC 공원의 턴/성장 처리 시 원자성과 상태 무결성 확인.
  - 재해/질병/이벤트에서 `defending_adults`와 `adult_count` 간의 불일치 여부 확인.

## 2. 발견된 문제점 (Findings)

### [STATE-F012] NPC 자연 성장 시 방어 배치 동기화 누락 (Phantom Defense on NPCs)
- **위험도**: Low
- **분류**: State Inconsistency
- **위치**: `app/npc_engine.py` -> `_npc_passive_growth(park)`
- **증상**:
  - 'aggressive' 또는 'berserk' 성격을 가진 NPC 공원이 자연 성장을 할 때, 10% 확률로 성체실장(`adult_count`)이 1마리 감소하고 경호실장(`guard_count`)이 1마리 증가함.
  - 이 때 `park.adult_count -= 1`을 수행하지만, `park.defending_adults`의 값을 Clamping(제한)하지 않음.
  - 만약 해당 NPC 공원의 `defending_adults`가 기존 `adult_count`와 동일했다면, 성장 직후 `defending_adults > adult_count` 상태가 되어 실제 존재하는 성체보다 많은 수의 성체가 방어에 참여하는 유령 방어(Phantom Defense)가 발생함.
- **원인**: 플레이어의 행동(`action_train`, `action_spy`, `_process_starvation`)에는 성체 감소 시 `defending_adults`를 동기화하는 로직이 패치(STATE-F011)로 적용되었으나, NPC 엔진의 백그라운드 성장 로직에는 해당 검증이 누락됨.

## 3. 검증된 안전 로직 (Verified Safe Logic)

### [SAFE-V015] 보호 모드(Protection Bailout) 무한 악용 차단 완료
- **분석**: `game_engine.py`의 `check_and_enter_protection(park)`은 보호 모드 진입 시 부족한 인구(`adult_count`)를 `GC.PROTECT_RESET_ADULTS` (5마리)로 복원함. 플레이어가 고의로 훈련(`action_train`)이나 밀사(`action_spy`)를 통해 성체를 감소시켜 보호 리셋을 유발하고 공짜 인구를 얻는 익스플로잇이 의심되었음.
- **결과**: `park.protection_bailout_done` 플래그를 통해 보호 에피소드당 단 1회만 자원 및 인구 복구가 이루어지도록 제한됨(STATE-F010). 보호 모드를 완전히 탈출(경호 5 이상, 성체 15 이상)해야만 플래그가 초기화되므로, 무한 리셋을 통한 자원 복구 어뷰징은 불가능한 것으로 판명됨.

### [SAFE-V016] 재해 및 질병 시스템에서의 방어 무결성
- **분석**: `_process_disasters`, `_process_disease`, `_process_rebellion`, `_process_human_events` 등의 이벤트가 인구에 미치는 영향을 검증.
- **결과**:
  - 재해 및 질병은 주로 '자실장'과 '저실장'에만 피해를 주어 방어 인력(성체/경호)에는 영향을 주지 않음.
  - 인간 이벤트(실험체 포획)나 굶주림(`_process_starvation`) 등으로 성체나 경호가 죽는 경우, 모두 `min(defending_*, *_count)` 로직이 정상적으로 호출되어 방어력 누수나 오버플로우가 발생하지 않음을 재확인함.

## 4. 개선 제안 (Recommendations)

1. **NPC 자연 성장 동기화 (npc_engine.py)**
   - `_npc_passive_growth` 내 'aggressive'/'berserk' 로직에 `defending_adults = min(defending_adults, adult_count)` 코드를 추가하여 NPC 공원의 방어력 일관성을 유지할 것.
   ```python
   elif personality == 'aggressive' or personality == 'berserk':
       if random.random() < 0.1 and park.adult_count > 2:
           park.guard_count += 1
           park.adult_count -= 1
           park.defending_adults = min(park.defending_adults, park.adult_count)
   ```

2. **NPC 솎아내기 자원 상한 로직 검토**
   - NPC가 솎아내기(`_npc_cull_if_needed`)를 진행할 때, 플레이어용 `action_cull` 함수를 그대로 호출함.
   - 솎아낸 고기나 식량이 `meat_stock` 또는 `trash_food` 상한을 넘어가는지 NPC 한정으로도 엄격히 제한될 수 있도록 `action_cull` 내 UPDATE 문이 잘 커버하고 있으나 지속적 모니터링 필요.

## 5. 결론 (Conclusion)
보호 모드 및 시스템 이벤트에서 발생할 수 있는 주요 익스플로잇은 이전 패치들을 통해 매우 견고하게 방어되고 있습니다. `npc_engine.py`에서 발견된 NPC의 방어 병력 불일치 버그(`[STATE-F012]`)만 수정한다면, 백그라운드 성장 로직도 완전한 무결성을 갖추게 될 것입니다. 다음 턴에서는 해당 문제에 대한 패치 진행 또는 추가 모듈 감사를 건의합니다.

---

## 6. 패치 내역 (Fixes Applied)

### [FIXED] STATE-F012 — NPC 자연 성장 시 방어 배치 동기화 누락 (Phantom Defense on NPCs)
- **파일**: `app/npc_engine.py`
- **조치**: `_npc_passive_growth()`의 'aggressive'/'berserk' 성격 분기에서 `park.adult_count -= 1` 직후에 `park.defending_adults = min(park.defending_adults, park.adult_count)`를 추가.
- **효과**: NPC 공원의 성체가 자연 성장으로 경호로 전환될 때도 `defending_adults`가 실제 `adult_count`를 초과하지 않음. NPC의 유령 방어(Phantom Defense) 현상 해소.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
