# D3D Audit Report (Turn 50)

## 1. Audit Scope
- **Project Type**: Web Game (Flask + SQLAlchemy)
- **Primary Standard**: `AI_AUDIT_DOC_STANDARD.md`
- **Focus Area**: State Management (Zombie State), TOCTOU (Time-of-Check to Time-of-Use), Trade Logic
- **Inspected Files**:
  - `app/game_engine.py`
  - `app/routes/game_routes.py`
  - `app/battle_engine.py`

## 2. Excluded Scope
- Frontend UI (`templates/`, `static/`)
- Authentication (`auth_routes.py`)
- `tests/` 디렉토리 및 배포 스크립트

## 3. Pass 1: Implementation Compliance Findings
- 특이사항 없음. 문서 상 명시된 게임 오버(공원 멸망) 조건이 존재하며, 멸망한 공원은 더 이상 행동을 취할 수 없어야 한다는 규칙이 구현되어 있음. 그러나 Pass 2에서 심각한 예외 상황이 발견됨.

## 4. Pass 2: Debug / Engineering Quality Findings

### [STATE-F024] Post-Mortem Action Vulnerability (Zombie State TOCTOU)
- **Pass**: Debug / Implementation
- **Area**: State Management / Turn System
- **Severity**: Critical
- **Status**: Needs Fix
- **Summary**: `consume_turn` 및 `trade_accept` 라우트 등에서 `is_destroyed` (공원 멸망 여부)를 검사하는 시점과 실제 락을 획득/적용하는 시점 간에 간극(TOCTOU)이 존재함. 특히 `consume_turn`은 내부에서 `process_turn()`을 호출하여 공원이 멸망할 수 있음에도 이를 재검증하지 않아, 멸망한 공원이 한 번의 액션을 마저 수행할 수 있는 좀비 행동(Zombie Action)이 가능함.
- **Evidence**:
  1. **`consume_turn` (app/game_engine.py:87-162)**:
     - 함수 도입부(Line 103)에서 `if park.is_destroyed:`를 검사함.
     - AP가 부족할 경우 `process_turn(park)`를 호출함 (Line 140).
     - `process_turn` 내부에서 보스실장 굶어죽음(`boss_hp <= 0`) 등으로 인해 `park.is_destroyed = True`가 될 수 있음.
     - 그러나 `consume_turn`은 `process_turn` 이후 멸망 여부를 재검사하지 않고 단순히 `AP`를 차감한 뒤 `return True`를 반환함.
     - 결과적으로 라우트(`game_routes.py`)는 공원이 멸망했음에도 불구하고 `action_build`, `execute_battle` 등을 정상적으로 실행하게 됨 (멸망한 공원의 침공/건설).
  2. **`trade_accept` (app/routes/game_routes.py:792-908)**:
     - Line 832-838에서 `sender = Park.query.get(trade.sender_id)`를 불러와 `sender.is_destroyed`를 검사함.
     - 이후 Line 846-848에서 `lock_ids = sorted([park.id, sender.id])`로 두 공원의 비관적 락(`with_for_update()`)을 획득함.
     - 락 획득 이전에 다른 스레드에 의해 `sender` 공원이 멸망했을 경우, 락 획득 후 `sender.is_destroyed`를 재검사하지 않으므로 멸망한 공원에게 자원을 송금(교환)하는 논리적 오류가 발생함.
- **Expected**: 트랜잭션 도중 상태가 변할 수 있는(특히 `process_turn`처럼 명시적 상태 변이가 일어나는) 함수 호출 이후나 비관적 락 획득 직후에는 반드시 대상 객체의 `is_destroyed` 등 핵심 유효성을 재검증해야 함.
- **Actual**: 초기 진입 시점에만 멸망 상태를 확인하고, 락 획득 및 턴 진행 이후에는 맹목적으로 후속 처리를 진행함.
- **Impact**: 게임 내에서 이미 파괴된 공원이 공격을 가해 자원을 약탈하거나, 죽은 대상과 자원 교역이 성사되는 등 경제 시스템과 랭킹의 무결성이 훼손됨.
- **Suggested Fix**:
  1. `consume_turn`의 `process_turn(park)` 호출 이후에 `if park.is_destroyed: return False, ['...']` 방어 코드를 추가.
  2. `trade_accept` 및 `execute_battle`에서 `with_for_update()`로 락을 획득한 직후, `sender.is_destroyed` 또는 `target.is_destroyed` 상태를 다시 한 번 검사하여 실패 처리(조기 종료 및 롤백)하는 로직 추가.
- **Re-audit Method**: `consume_turn` 직전에 보스 체력을 강제로 0으로 만든 뒤, 해당 턴에서 침공 등의 액션이 무효화되는지 확인.
- **Owner**: Architect / Coder

## 5. Pass 3: Security Findings
- 특이사항 없음.

## 6. Cross-Pass Conflicts
- **Conflict Note**: [STATE-F023]의 Split Transaction 문제와 결부되어, `consume_turn`과 액션 검증 로직이 파편화된 현 상태가 TOCTOU 버그를 더욱 양산하고 있음. 액션 시스템 전반에 대한 트랜잭션 경계 재설정이 시급함.

## 7. Required Fixes Before PASS
- [STATE-F024] 좀비 행동 허용 취약점 수정.

## 8. Final Decision
- **HOLD**: 게임의 규칙 무결성을 훼손하는 심각한 상태 관리 오류가 발견되어 수정이 필수적임.
