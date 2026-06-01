# D3D Audit Report (Turn 49)

## 1. Audit Scope
- **Project Type**: Web Game (Flask + SQLAlchemy)
- **Primary Standard**: `AI_AUDIT_DOC_STANDARD.md`
- **Focus Area**: AP Consumption Logic, Game Action Boundaries, Transaction Atomicity
- **Inspected Files**:
  - `app/routes/game_routes.py`
  - `app/game_engine.py`
  - `app/battle_engine.py`

## 2. Excluded Scope
- Frontend UI (`templates/`, `static/`)
- Authentication (`auth_routes.py`)
- `tests/` 디렉토리 및 배포 스크립트

## 3. Pass 1: Implementation Compliance Findings
- 특이사항 없음. 문서 상 명시된 AP 시스템의 의도(Ghost AP 방지)에 맞게 `consume_turn` 래퍼가 구현되어 있으나, 이로 인해 Pass 2/3에서 심각한 트랜잭션 분리 문제가 발견됨.

## 4. Pass 2: Debug / Engineering Quality Findings

### [STATE-F023] Non-Atomic Action Execution Causes AP Leakage (Lost AP on Validation Failure)
- **Pass**: Debug / Implementation
- **Area**: Game Action Execution / Transaction Management / AP System
- **Severity**: Major
- **Status**: Needs Fix
- **Summary**: `game_routes.py`에서 행동(건설, 훈련, 침공 등)을 실행할 때 `game_engine.consume_turn`과 실제 Action 함수(`action_build`, `execute_battle` 등)를 분리된 트랜잭션으로 호출함. 이로 인해 내부 검증 실패나 동시성 경합으로 Action이 중단될 경우 이미 커밋된 AP 소비량이 환불되지 않는 영구적인 AP 누수(AP Leakage)가 발생함.
- **Evidence**:
  1. `game_routes.py` 내부의 `/build`, `/train`, `/attack`, `/gather`, `/birth` 등 AP를 소비하는 행동 라우트 공통 패턴:
     ```python
     turn_ok, turn_msgs = game_engine.consume_turn(park, ap_cost=1)
     # consume_turn은 내부적으로 AP를 차감한 후 db.session.commit()을 수행하여 트랜잭션을 닫음.
     # ...
     success, result, messages = game_engine.action_build(park, building_type)
     ```
  2. `game_engine.py`의 `action_build`, `action_gather` 등은 유효성 검사 실패 시 단순히 `return False, {}, [...]`로 응답함. (예: `park.strike_turns > 0` 이거나 원자적 자재 차감 시 `updated == 0` 인 경우)
  3. Action 실패 시 Route 핸들러는 에러 메시지를 플래시(flash)로 출력하지만, 앞서 `consume_turn` 트랜잭션에서 선행 소비/커밋된 AP는 롤백되거나 환불되지 않고 그대로 증발함.
- **Expected**: 행동에 필요한 모든 검증(자원, 인력, 파업 상태 등)과 AP 소비가 원자적(Atomic) 단일 트랜잭션 안에서 묶여 처리되거나, 행동 실패 시 AP를 명시적으로 복구(Compensating Transaction)해야 함.
- **Actual**: `consume_turn`이 선행 커밋을 수행하여 트랜잭션이 끊어지며, 이후 Action 검증 로직이 실패할 때 AP를 환불(Refund)하는 복구 로직이 부재함.
- **Impact**: 동시 요청으로 자원이 부족해지는 경합(Race Condition)이 발생하거나, 성체가 파업(Strike) 중인 상태에서 사용자가 UI 상으로 채집/건설을 시도할 때마다 행동은 실행되지 않지만 플레이어의 AP 자원이 허공으로 소멸(Ghost Deduction)됨.
- **Suggested Fix**: AP 차감 로직과 Action 본문을 단일 트랜잭션 및 비관적 락 블록으로 통합하거나, `game_routes.py`에서 Action이 `False`를 반환할 때 명시적으로 AP를 환불(Refund)하고 커밋하는 보상 트랜잭션(Compensation)을 추가.
- **Re-audit Method**: Action 내부 검증에서 고의적 실패를 유발(예: `park.strike_turns = 1` 상태에서 `/gather` 호출)한 뒤 행동은 무시되더라도 AP가 보존되는지 확인.
- **Owner**: Architect / Coder

## 5. Pass 3: Security Findings
- 특이사항 없음.

## 6. Cross-Pass Conflicts
- **Conflict Note**: 과거 [IMP-F047] 조치 및 Ghost AP 현상을 해결하기 위해 `consume_turn`을 독립 함수로 분리하고 조기 커밋(Early Commit)을 적용한 결정이 결국 본 트랜잭션 분할(Split Transaction) 취약점을 파생시킴. 조기 커밋에 의한 `turn_quota` 보존 이점과, Action과 AP 소비의 트랜잭션 원자성(Atomicity) 간 균형을 다시 맞춰야 함.

## 7. Required Fixes Before PASS
- [STATE-F023]의 Split Transaction에 의한 AP 누수 취약점 수정.

## 8. Final Decision
- **HOLD**: 플레이어의 핵심 재화(AP) 누수를 유발하는 아키텍처/상태 취약점이 발견되어 픽스 필요.
