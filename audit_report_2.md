# D3D Audit Report

## 1. Audit Scope
- 프로젝트 경로: `/home/eunho1/Projects/python/JissouParkEmpire`
- 감사 중점: 문서(`spec.md`, `audit_roadmap.md`)와 실제 구현 코드(`app/models.py`, `app/game_engine.py`, `app/battle_engine.py`, `app/routes/game_routes.py`) 간의 정합성 불일치(Discrepancy) 심층 점검
- 턴(Turn): 2차 감사

## 2. Excluded Scope
- UI 렌더링 세부 구현 (HTML/CSS)
- 가상 환경(`venv/`) 및 캐시

## 3. Pass 1: Implementation Compliance Findings

### [IMP-F001] 밀사(Spy) 시스템 API 누락 (Orphan Code)
- Pass: Implementation
- Pattern: IMP-002
- Area: `game_routes.py` 및 `game_engine.py`
- Severity: Critical
- Status: Fixed
- Summary: `game_routes.py`에 `/spy/<int:target_id>` POST 엔드포인트를 추가하여 `game_engine.action_spy()`를 호출하도록 연결함. `consume_turn()`으로 AP 소비 및 턴 자동 진행을 함께 처리.
- Evidence: `game_routes.py` 1047~1066라인
- Expected: `/spy` 엔드포인트가 라우터에 존재하여 `action_spy()`를 호출
- Actual: `/spy/<int:target_id>` 라우트 추가 완료. 플래시 메시지 및 리다이렉트 처리 포함.
- Impact: 밀사 파견 기능이 대시보드 및 API를 통해 정상 접근 가능.
- Suggested Fix: 적용 완료 (`game_routes.py`에 라우트 추가)
- Re-audit Method: `grep -n "def spy_send" app/routes/game_routes.py`로 엔드포인트 존재 확인
- Owner: Coder

### [IMP-F002] 전투 방어력 계산 로직 심각한 불일치
- Pass: Implementation
- Pattern: IMP-001 (명세 불일치)
- Area: `app/battle_engine.py` (`_calc_defense_power`)
- Severity: Critical
- Status: Fixed
- Summary: `_calc_defense_power`의 `base` 계산을 `park.defending_guards` / `park.defending_adults` 기준으로 변경하고, `park.child_count`를 제거하여 방어 배치 전략이 실제 전투에 반영되도록 수정함.
- Evidence: `battle_engine.py` 203~215라인 (수정 후)
- Expected: `(defending_guards * GC.POWER_GUARD + defending_adults * GC.POWER_ADULT)` 기반 연산
- Actual: `park.defending_guards`, `park.defending_adults` 사용으로 변경 완료. `park.guard_count`, `park.adult_count`, `park.child_count` 제거 완료.
- Impact: 방어 배치 기능이 실제 방어력에 정상 반영되어 AP 소모 병력 분산 전략이 유효해짐.
- Suggested Fix: 적용 완료
- Re-audit Method: `grep -A5 "def _calc_defense_power" app/battle_engine.py`로 defending 변수 사용 확인
- Owner: Coder

### [IMP-F003] EventLog.event_type 타입 선언 불일치 (재확인)
- Pass: Implementation
- Pattern: IMP-001
- Area: `app/models.py`
- Severity: Minor
- Status: Fixed (1차 감사에서 처리 완료 — `audit_report_1.md` [IMP-F001] 참조)
- Summary: `EVENT_TYPES` 튜플(26개)과 `@validates('event_type')`가 `models.py`에 추가되어 오타 및 잘못된 로그 삽입이 방지됨.
- Owner: Coder

## 4. Pass 2: Debug / Engineering Quality Findings

### [DBG-F001] spec.md 내부 문서 간 설정 불일치 (Internal Inconsistency)
- Pass: Debug
- Pattern: DOC-001
- Area: `spec.md`
- Severity: Moderate
- Status: Fixed
- Summary: `spec.md` 12.1항 방어력 수식에 감시탑 보너스 `(1.0 + (watchtowers>0)*0.1)` 및 사기 보정 `(1.0 + (morale-50)*0.1/50)`을 추가하여 9.9항 본문 설명과 코드 구현과 일치시킴.
- Evidence: `spec.md` 12.1항 (수정 후)
- Expected: 스펙 문서 내의 공식이 일관성 있게 유지되어야 함.
- Actual: 12.1항 수식이 9.9항 및 `battle_engine.py`와 동기화됨.
- Impact: 유지보수 시 문서-코드 불일치 혼란 해소.
- Suggested Fix: 적용 완료
- Re-audit Method: `spec.md` 12.1항 리뷰
- Owner: Architect

## 5. Pass 3: Security Findings

### [SEC-F001] 불필요한 고아(Orphan) 로직으로 인한 보안 홀 가능성
- Pass: Security
- Pattern: SEC-005
- Area: `SpyMission`
- Severity: Minor
- Status: Verified (Accepted for now)
- Summary: 라우트 없이 게임 엔진 내부에만 존재하는 스파이 로직이 추후 실수로 노출될 때 권한 검증 누락 등이 발생할 수 있음.
- Owner: Architect

## 6. Cross-Pass Conflicts
- **IMP-F001(API 부재) vs DBG(엔진 내 잔존 코드)**: 코드는 작성되었으나 인터페이스가 없는 상태. 문서가 틀린 것인지, 개발이 덜 된 것인지 방향성 결정(Spec Clarification)이 선행되어야 함.

## 7. Required Fixes Before PASS
- 없음. `[IMP-F001]` 밀사 라우트 추가 완료, `[IMP-F002]` 방어력 계산 수정 완료, `[DBG-F001]` spec.md 동기화 완료.

## 8. Accepted Risks
- `[DBG-F001]` 문서 내 미세한 수식 누락은 런타임 버그를 유발하지 않으므로 단기 수용.

## 9. Needs Spec Clarification
- 스파이 기능: `audit_roadmap.md`의 "API는 존재"라는 문구를 "엔진 로직만 존재, 라우터 부재"로 명확히 수정하거나 개발 마무리를 지을 것인지 명확히 할 것.

## 10. Re-audit Checklist
- [x] 방어력 산출식(`battle_engine.py` 203라인) 변경 확인 — `defending_guards`/`defending_adults` 사용
- [x] 스파이 라우터(`game_routes.py` 1047라인) 반영 확인 — `/spy/<int:target_id>` POST 추가
- [x] spec.md 12.1항 방어력 수식 감시탑/사기 보정 추가 확인

## 11. Final Decision
- **PASS WITH KNOWN RISKS**: 2차 감사에서 발견된 Critical 결함 `[IMP-F001]`(밀사 라우트 누락), `[IMP-F002]`(방어력 계산 오류)를 모두 수정 완료하였으며, `[DBG-F001]`(spec.md 문서 불일치)도 동기화 완료함. `[IMP-F003]`은 1차 감사에서 이미 조치됨. 남은 구조적 리스크는 `audit_roadmap.md`에 명시된 Accepted Risk 항목들과 동일함.
