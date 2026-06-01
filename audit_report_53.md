# Audit Report 53

## 1. Audit Target
- **Target File**: `app/models.py`, `app/routes/game_routes.py`
- **Focus**: 외교 시스템(`Diplomacy`)의 동시성 제어 및 다중 관계 생성(Race Condition)으로 인한 논리적 모순 분석

## 2. Findings

### [STATE-F027] 교차 동맹/적대 요청에 의한 중복 외교 관계 생성 (Race Condition)
- **Severity**: High (심각)
- **Location**: `app/models.py` (`Diplomacy`), `app/routes/game_routes.py` (`diplomacy_ally`, `diplomacy_enemy`)
- **Description**:
  두 공원(Park A와 Park B)이 동시에 서로에게 동맹(`diplomacy_ally`) 또는 적대(`diplomacy_enemy`)를 선언할 경우, `Diplomacy` 모델의 UniqueConstraint(`park_a_id`, `park_b_id`, `relation_type`, `status`)가 **ID의 위치 순서를 구별**하기 때문에, DB 레벨에서 `(A, B)` 레코드와 `(B, A)` 레코드가 별개의 고유한 레코드로 취급되어 무결성 충돌(IntegrityError) 없이 동시에 삽입(Commit)됩니다.
  각 요청 라우트는 `with_for_update()`로 '자신의 공원(sender)' 레코드에만 락을 걸기 때문에, 교차 요청 시 두 트랜잭션이 서로를 블로킹하지 않고 독립적으로 `existing = ...first()`가 `None`임을 확인한 뒤 각각 중복 레코드를 생성하게 됩니다.
- **Impact**:
  A와 B 사이에 '동맹 대기(pending)' 상태의 레코드가 2개(또는 적대의 경우 'active' 2개) 생성됩니다. UI 상에서 동맹/적대 목록에 동일한 공원이 중복으로 노출되며, 두 동맹 요청을 각각 수락할 경우 한 쌍의 공원 간에 '활성(active)' 동맹 관계가 2개나 중복 존재하게 됩니다.

### [LOGIC-F020] 중복 외교 관계로 인한 상태 해제 누락 및 '동맹이자 적대' 모순 상태 (Compounded State Corruption)
- **Severity**: Critical (치명적)
- **Location**: `app/routes/game_routes.py` (`diplomacy_enemy`, `diplomacy_dissolve`)
- **Description**:
  [STATE-F027] 레이스 컨디션으로 인해 한 쌍의 공원 간에 여러 개의 중복 동맹 레코드(pending 또는 active)가 존재할 때, A 공원이 B 공원을 상대로 '적대 선언(`diplomacy_enemy`)'을 하면, 라우트 내에서 기존 동맹을 해제하는 로직(`existing_ally.first()`)이 **첫 번째로 검색된 단 한 개의 레코드만 `dissolved` 상태로 변경**합니다.
  결과적으로 나머지 중복 동맹 레코드는 여전히 `active` 또는 `pending`으로 남아 있게 됩니다. 상대방이 남아있는 `pending` 요청을 수락하거나, 이미 `active`인 중복 레코드가 존재한다면, A와 B는 **'활성화된 동맹'이면서 동시에 '활성화된 적대'**라는 게임 논리상 불가능한 모순 상태(State Corruption)에 빠집니다.
- **Impact**:
  1. **전투 불가 (AP Blackhole)**: 적대를 선언하고 1AP를 소비했음에도 불구하고, 여전히 존재하는 중복 동맹 레코드 때문에 `is_ally` 체크에 걸려 상대를 침공할 수 없습니다.
  2. **관계 해제 불가 (Zombie Relations)**: 유저가 수동으로 '동맹 해제'나 '적대 취소(`diplomacy_dissolve`)'를 시도해도, UI를 통해 전달된 단일 `diplo_id` 하나만 해제될 뿐, 숨어있는 중복 관계가 유지되어 게임의 외교/전투 진행을 심각하게 방해합니다.

## 3. Recommendation (권고사항)
1. **DB 레벨 식별자 순서 강제 (Canonical Ordering)**: `Diplomacy` 모델을 생성할 때 항상 `park_a_id < park_b_id`를 만족하도록 코드를 강제하여 중복 생성을 DB 레벨에서 완벽히 차단해야 합니다. (이 경우 요청 주체를 구분하기 위해 `initiator_id` 등의 컬럼 추가가 권장됩니다).
2. **동시성 락(Lock) 대상 확대 및 정렬**: 외교 관계를 맺거나 끊을 때 단일 공원이 아닌 두 공원(`park`, `target`) 모두에 대해 ID 오름차순으로 `with_for_update()` 락을 획득하여 교차 레이스 컨디션을 원천 차단해야 합니다.
3. **일괄 상태 변경(Bulk Update)**: 관계를 변경할 때 `.first()`로 가져와서 하나만 변경하는 대신 `.update()`를 사용하여 존재하는 모든 연관 관계(동일 공원 쌍의 해당 상태)를 일괄로 `dissolved` 처리하여 기존에 발생한 데이터 오염을 자동 복구해야 합니다.

## 4. Next Step
- 외교 모델의 심각한 상태 오염 취약점 분석을 완료하였으므로, 다음 54차 감사에서는 비동기적 상호작용이 발생하는 '전투 약탈(Looting) 자원 분배' 및 '밀사 시스템(`SpyMission`)'에 대해 추가적인 레이스 컨디션(자원 복제/증발 여부)을 집중 감사할 예정입니다.
