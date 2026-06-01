# D3D Audit Report - 33차 재감사

## 1. Audit Scope
- **Target Files**:
  - `app/game_engine.py` (`_process_starvation`, `check_and_enter_protection`, `_process_overcrowding`)
  - `app/config.py` (`GameConfig` constants)
  - `app/routes/game_routes.py` (`dashboard`)
- **Focus Area**: 게임 내 기아(Starvation) 처리 로직의 NP(Nutritional Point) 부채 상쇄 매커니즘 정합성 검증 및 보호 모드(Protection Mode)와 수용 상한(Population Cap) 시스템 간의 충돌 검증.
- **Reference**: `spec.md` 8.5(기아), 8.8(보호 모드), 9.10(식량 소비).

## 2. Excluded Scope
- 스파이 시스템(Spy Mission)의 데드락 방어 로직 (이미 22차/31차 등에서 검증됨).
- 자동 턴 충전 및 스케줄러 로직.

## 3. Pass 1: Implementation Compliance & Logic Findings

### [LOGIC-F008] 기아 처리 시 과도한 NP 부채 상쇄로 인한 무적 생존 결함
- **Severity**: Critical (Game Balance / Logic Exploit)
- **Status**: Open
- **Evidence**:
  - `config.py`에 정의된 단위 턴당 NP 소비량: `NP_PER_ADULT = 3`, `NP_PER_CHILD = 1`, `NP_PER_BABY = 0.5`.
  - `app/game_engine.py`의 `_process_starvation` 루프:
    ```python
    elif park.adult_count > 0:
        park.adult_count -= 1
        shortage -= 5  # <-- 여기서 5 NP 부채 상쇄
    ```
- **Expected**: 보유 식량이 0인 상태에서 모든 실장석은 각자의 요구 NP만큼 굶주리게 되므로, 1마리가 굶어 죽으면 그 개체가 요구했던 NP만큼만(예: 성체 3) `shortage` 부채가 탕감되어야 하며 식량이 0일 때는 결국 전멸해야 함.
- **Actual**: 성체 1마리가 굶어 죽을 때 `shortage`를 5만큼 탕감시켜줌. 성체 1마리의 요구치는 3이므로, 성체 1마리가 죽으면 자신을 제외한 **다른 성체 1마리의 굶주림(NP 3) 중 2를 무에서 창조하여 채워주는** 효과가 발생함.
  - **시나리오**: 식량 0, 성체 10마리 (필요 NP 30, shortage 30).
  - 성체가 차례대로 죽으며 30 -> 25 -> 20 -> 15 -> 10 -> 5 -> 0 이 됨. 6마리만 죽고 루프가 종료됨.
  - **결과**: 식량이 전혀 없었음에도 불구하고 4마리의 성체가 살아남음. 자실장(-2 탕감, 1 소비), 저실장(-1 탕감, 0.5 소비)도 동일한 비율의 "시체 뜯어먹기" 효과로 비정상적인 생존을 허용함.
- **Suggested Fix**: `shortage` 차감 값을 `GC.NP_PER_ADULT` 등 실제 소비 요구량과 일치시켜야 함.

### [ARCH-F010] 보호 모드 진입 시 수용 상한(Cap) 미복구로 인한 즉각적인 탈주(Immediate Desertion) 모순
- **Severity**: High (UX / Architecture Flaw)
- **Status**: Open
- **Evidence**:
  - `app/game_engine.py`의 `check_and_enter_protection`은 보호 모드 진입 시 즉시 성체 5, 자실장 15, 저실장 8마리로 개체 수를 강제 복구함.
  - 재해(폭우 등)로 인해 골판지집(`cardboard_houses`)이 0이 된 유저의 `population_cap`은 5로 고정되어 있음.
- **Expected**: 시스템이 초보자 보호를 위해 인구를 복구해주었다면, 유저가 이 인구를 활용하여 복구 작업을 할 수 있도록 임시 수용 상한을 주거나 잃어버린 골판지집을 1개 복구해주어야 함.
- **Actual**: `dashboard()` 접근 시 20마리의 인구가 지급되지만(저실장 제외 20마리), `population_cap`은 여전히 5임. 플레이어가 직후 아무 행동(예: 채집)이나 수행하여 `consume_turn -> process_turn -> _process_overcrowding` 사이클이 도는 순간, 초과된 15마리의 자실장이 단 1턴 만에 **전부 탈주(Overcrowding)**함. 보호 모드가 완전히 무의미해지는 구조적 함정에 빠짐.
- **Suggested Fix**: `check_and_enter_protection` 로직 내에서 `cardboard_houses`가 0일 경우 최소 1채의 집을 복구해주고 `population_cap`을 재계산하도록 조치해야 함.

## 4. Pass 2: Security Findings
- 기아 판정 및 인구 보충 로직은 서버 사이드에서 검증되며 유저 입력에 의존하지 않으므로 직접적인 보안(Injection/Privilege Escalation) 위협은 없음. 다만 게임 기획 의도를 무너뜨리는 로직 결함(무적 생존)이 존재함.

## 5. Final Decision
- **Status**: `REJECTED` (Needs Design & Implementation fix)
- 기아 부채 상쇄 로직의 수학적 불일치([LOGIC-F008])와 보호 모드 UX 설계 모순([ARCH-F010])이라는 두 가지 중대한 시스템 결함을 확인.
- 코드를 수정하지 않고 현 상태를 문서화하여 리포트로 남김. 다음 개발 단계에서 상수 동기화 및 보호 모드 스펙 조정 핫픽스가 필요함.

---

## 6. 패치 내역 (Fixes Applied)

### [FIXED] LOGIC-F008 — 기아 처리 시 과도한 NP 부채 상쇄로 인한 무적 생존 결함
- **파일**: `app/game_engine.py`
- **조치**: `_process_starvation()`의 `shortage` 차감 값을 하드코딩된 숫자(`1`, `2`, `5`, `4`)에서 `GC.NP_PER_BABY`, `GC.NP_PER_CHILD`, `GC.NP_PER_ADULT`, `GC.NP_PER_GUARD`로 교체.
- **효과**: 성체 1마리 사망 시 `shortage`가 5에서 3(`NP_PER_ADULT`)로 감소. 식량 0, 성체 10마리 시 10마리 전멸 후 `shortage`가 0이 되어 정상 종료. 더 이상 사망한 개체가 다른 개체의 굶주림을 무에서 창조하여 채워주는 무적 생존 효과가 발생하지 않음.

### [FIXED] ARCH-F010 — 보호 모드 진입 시 수용 상한(Cap) 미복구로 인한 즉각적인 탈주 모순
- **파일**: `app/game_engine.py`
- **조치**: `check_and_enter_protection()` 내 인구 보충 직후에 `cardboard_houses == 0` 여부를 검사하여 0이면 1채를 복구하고 `population_cap`에 `GC.BUILDINGS['cardboard_house']['effect']['population_cap']`(15)를 추가.
- **효과**: 재해 등으로 골판지집이 0인 상태에서 보호 모드 진입 시, 인구(성체 5 + 자실장 15 = 20)가 `population_cap`(5)를 초과하여 즉시 탈주하는 현상 해소. 보호 모드 진입 후 최소 1채의 집이 복구되어 플레이어가 복구 작업을 수행할 시간을 확보함.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
