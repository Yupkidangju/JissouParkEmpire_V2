# 51차 재감사 보고서: 교역 및 밀사 시스템 종속 삭제로 인한 상태 유실 결함 (Cascade Deletion Vulnerabilities)

## 개요
- **감사 기준**: `AI_AUDIT_DOC_STANDARD.md`
- **감사 대상**: `/app/models.py`, `/app/game_engine.py`, `/app/routes/game_routes.py`
- **목적**: 게임 내 크로스-파크(Cross-Park) 상호작용인 교역(`TradeOffer`)과 밀사(`SpyMission`) 모델에서 상대방(수신자/타겟)이 공원을 삭제할 때 발동되는 Cascade 제약으로 인한 자원/유닛 유실(Leakage) 점검

## 상세 발견 사항 (구현 중심 분석)

### [STATE-F025] 수신자/타겟 공원 재시작(Cascade Delete)으로 인한 발신자 자원 및 유닛 영구 유실 (High)

#### 1) 문제 위치
- **`/app/models.py` (Line 145-169)**:
```python
    sent_trade_offers = db.relationship(
        'TradeOffer', foreign_keys='TradeOffer.sender_id',
        backref='sender_park', cascade='all, delete-orphan'
    )
    received_trade_offers = db.relationship(
        'TradeOffer', foreign_keys='TradeOffer.receiver_id',
        backref='receiver_park', cascade='all, delete-orphan'
    )
    # ...
    spy_missions_received = db.relationship(
        'SpyMission', foreign_keys='SpyMission.target_id',
        backref='target_park_ref', cascade='all, delete-orphan'
    )
```
- **`/app/routes/game_routes.py` (Line 432)**:
```python
    @game_bp.route('/restart', methods=['POST'])
    ...
    db.session.delete(park)
```

#### 2) 구현 결함 설명
현재 `TradeOffer` 모델과 `SpyMission` 모델은 `sender`와 `receiver`(혹은 `target`) 양쪽 `Park` 레코드에 대해 `cascade='all, delete-orphan'` 옵션을 가지고 있습니다. 이는 어느 한 쪽의 공원(`Park`) 레코드가 삭제되면(예: 유저가 게임오버 후 `/restart`를 실행하여 DB에서 `db.session.delete(park)`가 호출될 때) 해당 상호작용 레코드들도 연쇄적으로 삭제(Cascade Delete)됨을 의미합니다.

하지만, 교역과 밀사는 **발신자(Sender)가 미리 자원이나 유닛을 "에스크로(Escrow)" 형태로 선차감하여 보류해 둔 상태**로 진행됩니다:
- `action_spy`: 밀사 파견 시 즉각적으로 `adult_count - 1` (발신자의 성체 1마리 차감)
- `trade_create`: 교역 제안 시 즉각적으로 자원(`konpeito`, `trash_food` 등) 차감

만약 **수신자(Receiver/Target) 유저가 `/restart`를 클릭**하여 공원을 폭파하면:
1. `Park` 테이블에서 수신자 공원 레코드가 삭제됩니다.
2. 수신자가 참조된 모든 `TradeOffer`, `SpyMission`이 `delete-orphan` 제약에 의해 **DB에서 강제 삭제**됩니다.
3. 하지만, 삭제(Delete) 이벤트 발생 시 발신자의 에스크로(자원 및 파견된 성체)를 **반환해주는 SQLAlchemy Event Listener나 애플리케이션 레벨의 후속 처리 로직이 존재하지 않습니다.**
4. 결국 억울한 발신자는 자신의 에스크로 자원과 파견된 성체실장을 영구적으로 잃어버리게 됩니다. (Resource Leak)

#### 3) 공격 또는 발생 시나리오
- **악의적 트롤링**: A 유저가 부계정(B 유저)에게 고가의 자원(콘페이토 100개)을 묶어두는 1:1 교역을 걸어둡니다. (혹은 여러 명에게 걸어둠)
- B 유저가 `/restart`를 통해 공원을 리셋합니다.
- A 유저가 제안한 `TradeOffer`는 B 유저의 `Park` 레코드 삭제와 함께 DB 상에서 흔적도 없이 사라집니다.
- A 유저는 콘페이토 100개를 영원히 돌려받지 못하게 됩니다.

## 결론 및 권고사항
- **TradeOffer, SpyMission Cascade 제한**: 상대방(`receiver`, `target`)의 삭제가 트랜잭션 기록의 소멸로 이어지지 않도록, 수신자에 대한 외래 키(Foreign Key)는 `ondelete='SET NULL'`로 변경하거나, Cascade 설정을 제거하고 애플리케이션 레벨에서 명시적으로 자원 반환 후 삭제하는 논리적 처리(`cancel_trade`, `return_spy`)가 선행되어야 합니다.
- **SQLAlchemy `before_delete` 이벤트 리스너 도입**: 특정 엔티티(`TradeOffer`, `SpyMission`)가 삭제될 때 `status == 'pending'` 혹은 `status == 'active'`라면, 발신자(`sender_id`)에게 자원/성체를 원자적으로 환불해주는 보상 로직을 이벤트 리스너에 내장하여 데이터 무결성을 강제해야 합니다.
