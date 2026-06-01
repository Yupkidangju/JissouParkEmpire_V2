# 🔍 실장석 공원 제국 (JissouParkEmpire) - 감사 리포트 (Audit 7)

## 📌 개요
- **감사 일시**: 2026년 5월 30일
- **감사 대상**: `app/game_engine.py`, `app/routes/game_routes.py`, `app/battle_engine.py` 등
- **감사 포커스**: 세부 구현상의 논리 오류, 입력값 검증 누락, 예외 상황 처리 미비 등 세부 심화 감사 진행.
- **감사 원칙**: `AI_AUDIT_DOC_STANDARD.md` 기반 정합성 및 구현 분석

---

## 🛑 주요 발견 사항 (Critical Findings)

### 1. [IMP-F011] 멸망한 공원의 밀사 임무 영구 고립 (Zombie Spy Missions)
- **위치**: `app/game_engine.py` 내 `_process_spy_missions()` 함수
- **설명**:
  - `_process_spy_missions()` 시작 부분에서 `if park.is_destroyed: return`을 수행합니다.
  - 밀사 임무(`SpyMission`)는 발송 공원(`sender_id`) 턴 진행 시 남은 턴 수를 차감하여 완료 여부를 판정합니다.
  - 하지만 발송 공원이 멸망하면 해당 공원의 턴 처리가 완전히 중단되므로, 해당 공원이 발송했던 진행 중인(`active`) 모든 밀사 임무는 영원히 `turns_remaining`이 줄어들지 않고 데이터베이스에 고아 레코드(Zombie)로 남게 됩니다.
- **위험도**: 높음 (DB Bloat, 데이터 무결성 훼손)
- **개선안**: 공원 멸망 처리 시점(`park.is_destroyed = True`)에 해당 공원이 발송한 모든 밀사 임무를 `failed` 또는 `cancelled`로 일괄 처리해야 합니다.

### 2. [IMP-F012] 방어 병력 배치 시 음수 입력 우회 취약점
- **위치**: `app/routes/game_routes.py` 내 `defend()` 라우트
- **설명**:
  - 방어 병력을 배치할 때 `num_guards > park.guard_count` 및 `num_adults > park.adult_count`로만 검증하고 있습니다.
  - 사용자가 폼 조작 등을 통해 `num_guards`에 `-10`과 같은 음수를 전달하면, `-10 > park.guard_count`는 `False`가 되므로 검증을 무사히 통과합니다.
  - 그 결과 `park.defending_guards = -10`과 같이 방어 병력이 음수로 설정되어, 최종적으로 전투력 계산(`total_combat_power`, `defense_power`) 시 음수 방어력이 적용되는 상태 변조가 일어납니다.
- **위험도**: 중간 (상태 변조 및 잠재적 버그 유발)
- **개선안**: `request.form.get()` 값에 대하여 `max(0, ...)` 처리를 통해 음수 입력을 강제 차단해야 합니다.

### 3. [IMP-F013] 밀사 파견 시스템의 초보자 보호 모드 우회 (Protection Bypass)
- **위치**: `app/routes/game_routes.py` 내 `spy_send()` 및 `app/game_engine.py` 내 `action_spy()`
- **설명**:
  - `attack` 라우트의 경우, 타겟이 보호 모드일 때(`game_engine.is_protected(target)`) 공격을 명시적으로 차단하고 있습니다.
  - 그러나 밀사(`spy_send`) 파견 로직에는 대상이 보호 모드인지 확인하는 로직이 전혀 누락되어 있습니다.
  - 이로 인해 공격을 받을 수 없는 보호 모드의 뉴비 공원을 상대로 밀사를 보내 식량을 파기하고 저실장을 학살할 수 있는 심각한 꼼수가 존재합니다.
- **위험도**: 높음 (뉴비 보호 시스템 무력화 및 기획 의도 훼손)
- **개선안**: `action_spy()` 함수 내에 타겟이 보호 상태인지 확인하고, 보호 중일 경우 밀사 파견을 차단하는 코드를 추가해야 합니다.

### 4. [IMP-F014] 불완전한 과밀화 처리 (성체/경호실장 과밀화 면역)
- **위치**: `app/game_engine.py` 내 `_process_overcrowding()` 함수
- **설명**:
  - 공원의 `total_population`이 `population_cap`을 초과했을 때, `excess` 수치만큼 인구를 감소시킵니다.
  - 하지만 인구 감소 루프가 `while excess > 0 and park.child_count > 0:`으로 작성되어 있습니다.
  - 즉, 자실장(`child_count`)만 희생되며, 자실장이 0마리가 되면 `excess`가 여전히 남아있더라도 과밀화 감소 루프가 종료됩니다.
  - 성체실장과 경호실장은 과밀화 페널티를 전혀 받지 않으므로, 이들 위주의 공원은 수용 인원 캡을 아무리 초과해도 페널티 없이 계속해서 병력을 쌓아둘 수 있는 문제가 있습니다.
- **위험도**: 높음 (인구 상한(Cap) 시스템 무력화, 밸런스 붕괴)
- **개선안**: `child_count`가 바닥나면 `adult_count`, 그 이후엔 `guard_count` 순서대로 개체 수를 감소시켜 `excess`를 끝까지 해소하도록 로직을 수정해야 합니다.

---

## 🛡️ 향후 감사 방향
- **제7차 감사 결론**: 밀사 임무의 고립(Zombie), 음수 검증 누락, 보호 모드 우회, 과밀화 시스템 우회 등 구현의 허점들을 발견했습니다.
- **권장 조치**: 감사된 사항들에 대한 `app/game_engine.py` 및 `game_routes.py` 의 실질적인 코드 수정(Remediation) 권고.
