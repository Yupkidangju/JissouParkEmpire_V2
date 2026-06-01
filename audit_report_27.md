# JissouParkEmpire Audit Report - 27차 감사

**작성일시**: 2026-05-30
**감사 대상**: 유저 입력값 파싱 무결성, 오버크라우딩(Overcrowding) 강제 퇴거 로직
**감사 초점**: 게임 경제 파괴가 가능한 파라미터 조작(Exploit) 및 인구 제한 우회 우려 사항 집중 점검

---

## 1. 이전 지적 사항 패치 결과 검증

### 1.1. [STATE-F003] `_consume_np`로 인한 AP 유실 (Softlock) - **해결됨 (Fixed)**
- **조치 사항**: `game_engine.py`의 `process_turn()` 내부에서 `_process_food_consumption()` 호출 직전에 `db.session.flush()`가 성공적으로 추가되어 메모리 변경 사항이 트랜잭션에 확정되었습니다.
- **결과**: `_consume_np` 내부의 `refresh()`가 턴 카운터와 AP를 파괴하는 현상이 완전히 해결되어 게임 루프가 정상화되었습니다.

---

## 2. 신규 발견 취약점 상세 (구현 중심 깊은 감사)

### 2.1. [SEC-F001] 도살(Cull) 라우트의 음수(Negative) 파라미터 인젝션 취약점
- **심각도**: **Critical (Game-Breaking, Exploit)**
- **위치**:
  - `app/routes/game_routes.py` (`cull` 함수)
  - `app/game_engine.py` (`action_cull` 함수)
- **문제 발생 메커니즘**:
  1. `/cull` 라우트에서 `request.form.get('count', 1, type=int)`를 통해 도살할 개체 수를 입력받습니다. 이 때 `max(0, ...)` 등 **음수 차단 로직이 누락**되어 있습니다.
  2. 공격자가 `count=-100`과 같은 악의적 페이로드를 전송하면, `action_cull`의 다음 검증문(`park.baby_count < count`)이 `0 < -100` (False)가 되어 손쉽게 통과됩니다.
  3. 이후 데이터베이스 원자적 UPDATE 구문이 실행됩니다:
     ```python
     updated = Park.query.filter(
         Park.id == park.id, getattr(Park, pop_col) >= count
     ).update({
         pop_col: getattr(Park, pop_col) - count
     })
     ```
  4. `pop_col >= -100` 조건은 항상 참이며, 갱신 결과는 `pop_col - (-100)`이 되어 **순식간에 저실장이나 자실장이 100마리 무에서 유로 창조**됩니다.
- **권고 사항**: `game_routes.py`의 `cull` 함수 내 `count` 파싱 시 `max(1, request.form.get('count', 1, type=int))`를 강제하여 0 이하의 값 입력을 원천 차단해야 합니다.

### 2.2. [LOGIC-F001] 과밀도(Overcrowding) 로직의 성체/경호 무적 우회
- **심각도**: **High (Balance-Breaking)**
- **위치**: `app/game_engine.py` (`_process_overcrowding` 함수)
- **문제 발생 메커니즘**:
  1. 인구 상한치(`population_cap`)를 초과했을 때 실행되는 `_process_overcrowding` 함수는 아래와 같이 구현되어 있습니다:
     ```python
     while excess > 0 and park.child_count > 0:
         park.child_count -= 1
         ...
     ```
  2. 폭우(골판지집 파괴) 등으로 `population_cap`이 줄어들어 잉여 인구(`excess`)가 발생했을 때, 공원 내에 **자실장(`child_count`)이 한 마리도 없다면 while 루프가 아예 실행되지 않고 종료**됩니다.
  3. 결과적으로 자실장을 모두 성체로 성장시켰거나 도살한 상태에서는, 성체와 경호실장 수가 상한을 수십, 수백 마리 초과(`excess > 0`)하더라도 아무도 탈주하거나 사망하지 않는 **과밀도 면역(Invulnerability) 상태**가 됩니다.
- **권고 사항**: 자실장이 부족할 경우 성체(`adult_count`)와 경호실장(`guard_count`)도 순차적으로 탈주/사망하도록 `while` 조건과 내부 분기를 보강해야 합니다.

---

## 3. 결론

이번 27차 감사에서는 AP 소모나 게임의 정상적 플레이 없이도 인구를 무한 증식시킬 수 있는 **매우 치명적인 파라미터 조작 취약점(음수 솎아내기)**과 게임 밸런스를 붕괴시키는 **강제 퇴거 로직 구멍**을 적발하였습니다. 두 취약점 모두 악용 난이도가 낮고 파급력이 크므로 신속한 조치를 권고합니다.

---

## 4. 패치 내역 (Fixes Applied)

### [FIXED] SEC-F001 — 도살 라우트 음수 파라미터 인젝션 취약점
- **파일**: `app/routes/game_routes.py`
- **조치**: `cull()` 함수의 `count = request.form.get('count', 1, type=int)` 직후에 `count = max(1, count)`를 추가하여 0 이하 값을 강제로 1로 클램핑.
- **효과**: `count=-100` 등의 악의적 페이로드가 `action_cull`로 전달되지 않음. `pop_col >= count` 조건 우회 및 `pop_col - (-100)` 인구 무한 증식 Exploit 원천 차단.

### [FIXED] LOGIC-F001 — 과밀도 로직의 성체/경호 무적 우회
- **파일**: `app/game_engine.py`
- **조치**: `_process_overcrowding()`의 `while` 루프를 자실장 → 성체실장 → 경호실장 순으로 확장. 자실장이 부족할 경우 성체와 경호도 순차적으로 탈주 처리하도록 로직 보강.
- **효과**: 자실장이 0명이더라도 `excess > 0`인 경우 성체와 경호가 탈주하여, 인구 상한 초과 면역(Invulnerability) 상태가 해소됨.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
