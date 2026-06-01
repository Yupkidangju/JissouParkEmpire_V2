# Audit Report 58: Missing Commit in AP Refund (Retracted - False Positive)

## 1. 개요 (Overview)
- **발견 일시**: 2026-05-31
- **상태**: **Retracted (철회됨)**
- **컴포넌트**: `app/routes/game_routes.py`, `app/game_engine.py` (`refund_ap`)

## 2. 세부 분석 (Detailed Analysis)
초기 감사에서 `game_routes.py`의 예외 처리 분기들(예: 대상 멸망 시)에서 `game_engine.refund_ap()` 호출 이후 `db.session.commit()`이 누락되었다고 판단하여 자원 유실 버그(AP Blackhole)로 식별했습니다.

그러나 `app/game_engine.py`의 `refund_ap` 함수 구현부(`line 1636-1648`)를 정밀 재분석한 결과, 다음과 같이 헬퍼 함수 내부에서 **안전하게 `db.session.commit()`을 수행**하고 있음이 확인되었습니다.

```python
def refund_ap(park, ap_cost):
    """
    [v1.8.2] 보상 트랜잭션: 행동 검증 실패 시 이미 consume_turn()에서 선행 차감 및 커밋된 AP를 안전하게 복구하고 커밋한다.
    (audit_report_49.md [STATE-F023])
    """
    if park.is_destroyed:
        return
    Park.query.filter(Park.id == park.id).update({
        'action_points': Park.action_points + ap_cost
    })
    db.session.commit()  # <-- 여기서 커밋이 정상적으로 수행됨
    db.session.refresh(park)
```

따라서 `refund_ap`를 호출한 직후 `redirect`를 반환하더라도 AP 복구 내역은 정상적으로 DB에 반영되므로 **이 보고서는 False Positive로 판정되어 철회(Retracted) 처리**합니다.
