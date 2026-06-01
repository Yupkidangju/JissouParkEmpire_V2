# Audit Report 55: Trade Market IDOR & Zombie Trades Vulnerability

## 1. 개요 (Overview)
본 감사는 `AI_AUDIT_DOC_STANDARD.md`의 구현(Implementation) 및 보안(Security) 기준을 적용하여, `app/routes/game_routes.py`의 교역 시스템(Trade Market)을 집중적으로 분석한 결과입니다. 교역 수락/취소 로직의 원자성은 우수하게 구현되어 있으나, **교역 거절(Reject) 라우트의 인가(Authorization) 결함** 및 **공개 교역 만료 표기 누락** 등의 문제를 발견하였습니다.

## 2. 발견된 문제점 (Findings)

### [AUTH-F001] IDOR in Trade Reject: 교역 거절 권한 검증 누락 (High)
*   **분류**: Broken Access Control (Insecure Direct Object Reference)
*   **위치**: `app/routes/game_routes.py`의 `trade_reject(trade_id)`
*   **설명**:
    `trade_reject` 함수는 인자로 받은 `trade_id`의 교역 상태를 원자적 쿼리를 통해 `rejected`로 변경하고 발송자에게 자원을 환불합니다.
    ```python
    updated = TradeOffer.query.filter(
        TradeOffer.id == trade_id,
        TradeOffer.status == 'pending'
    ).update({'status': 'rejected', 'resolved_at': datetime.utcnow()})
    ```
    그러나, 해당 라우트 어디에도 **현재 로그인한 유저(`current_user.park.id`)가 해당 교역의 정당한 수신자(`receiver_id`)인지 확인하는 인가(Authorization) 검증 로직이 없습니다.**
    *결과적으로, 악의적인 유저는 임의의 `trade_id`를 삽입하여 POST 요청을 전송함으로써, 타인 간의 프라이빗 교역이나 공개 교역을 마음대로 거절(삭제)하고 시장을 훼손(DoS)할 수 있습니다.*
*   **영향**: 누구나 타인의 교역을 임의로 거절하여 시장 기능을 마비시킬 수 있음.
*   **권장 수정 방안**:
    원자적 UPDATE 쿼리에 `TradeOffer.receiver_id == park.id` 조건을 추가하여 본인에게 온 교역만 거절할 수 있도록 제한해야 합니다. (공개 교역은 거절 불가하거나, 발송자가 `trade_cancel`을 사용하도록 해야 함)

### [LOGIC-F022] Zombie Trades in Public Market (Low)
*   **분류**: Logic Error (Display/State Validation)
*   **위치**: `app/routes/game_routes.py`의 `trade_market()`
*   **설명**:
    교역 시장에서 공개 교역 목록을 불러올 때, 발송자(Sender)가 멸망(is_destroyed)했는지 여부를 검사하지 않습니다.
    ```python
    public_trades = TradeOffer.query.filter(
        TradeOffer.status == 'pending',
        TradeOffer.sender_id != park.id,
        TradeOffer.receiver_id == None
    ).order_by(TradeOffer.created_at.desc()).limit(20).all()
    ```
    발송자가 멸망하더라도 해당 교역은 `pending` 상태로 시장에 계속 노출됩니다. 다른 유저가 이를 수락(`trade_accept`)하려고 시도할 때서야 비로소 비관적 락 이후 `sender.is_destroyed`를 확인하고 `expired`로 처리(소멸)됩니다.
*   **영향**: 멸망한 유저의 교역(Zombie Trades)이 시장에 지속 노출되어 쿼터 낭비 및 사용자 경험 저하를 유발합니다.
*   **권장 수정 방안**: `trade_market()` 쿼리 단계에서 `Park` 모델과 JOIN 하거나 추가 필터링을 통해 멸망한 유저의 교역은 표시하지 않도록 개선이 필요합니다.

## 3. 우수 구현 사항 (Positive Findings)
*   **원자적 교역 캡핑 연산**: `trade_accept` 및 `trade_cancel` 시 환불/수령 자원에 대해 `case()` 문을 사용한 캡핑은 매우 안전하며 Over-capacity 버그를 원천 차단합니다.
*   **음수 입력 방지**: `trade_create` 라우트에서 `max(0, value)`를 통해 음수 교역 제안을 통한 자원 증식 Exploit을 잘 방어하고 있습니다.
*   **Race Condition 완화**: 교역 수락 시, ID 순(Canonical Order)으로 두 Park의 비관적 락(`with_for_update`)을 획득함으로써 상호 수락/수정으로 인한 교착 상태(Deadlock) 및 Lost Update를 매우 효과적으로 방지하고 있습니다.

## 4. 향후 감사 계획
- **다음 단계 (Turn 56)**: NPC 전투 및 침략(Invasion) 로직에서의 유닛 손실 계산식 정밀 분석. `_stochastic_round` 및 `random.uniform`을 활용하는 과정에서 극단적인 입력값에 대한 수학적 Overflow / 부동소수점 오차가 발생하는지 검증할 예정입니다.
