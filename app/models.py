# -*- coding: utf-8 -*-
"""
실장석 공원 제국 - 데이터 모델 (models.py)
[v0.1.0] spec.md 섹션 5.2 기반 SQLAlchemy 모델 정의.

테이블 구조:
- User: 사용자 계정
- Park: 공원 (플레이어 및 NPC)
- BuildQueue: 건설 대기열
- TrainQueue: 훈련 대기열
- BattleLog: 전투 기록
- EventLog: 이벤트 로그
"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import case, event  # [v1.7.0] hybrid_property SQL 표현식용, [v1.8.4] 이벤트 리스너 추가
from sqlalchemy.ext.hybrid import hybrid_property  # [v1.7.0] SQL/Python 양쪽에서 사용 가능한 속성 (audit_report_32.md [STATE-F008])
from sqlalchemy.orm import object_session  # [v1.8.4] before_delete 이벤트 내 세션 탐색용

# SQLAlchemy 인스턴스 (앱 팩토리에서 init_app으로 초기화)
db = SQLAlchemy()


class User(UserMixin, db.Model):
    """사용자 계정 모델"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    last_login = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # 사용자 → 공원 관계 (1:1)
    park = db.relationship('Park', backref='owner', uselist=False,
                           foreign_keys='Park.user_id')

    def set_password(self, password):
        """비밀번호 해시 설정"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """비밀번호 검증"""
        return check_password_hash(self.password_hash, password)


class Park(db.Model):
    """
    공원 모델 - 게임의 핵심 엔티티.
    플레이어와 NPC 모두 이 모델을 사용한다.
    """
    __tablename__ = 'parks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # [v1.7.0] DB 레벨 unique 제약: TOCTOU 레이스 컨디션 방지 (audit_report_41.md [STATE-F014])

    # NPC 설정
    is_npc = db.Column(db.Boolean, default=False)
    npc_personality = db.Column(db.String(20), nullable=True)
    # NPC 성격: aggressive, defensive, peaceful, cunning, berserk

    # === 실장석 인구 ===
    boss_hp = db.Column(db.Integer, default=100)       # 👑 보스실장 HP (0이면 게임오버)
    guard_count = db.Column(db.Integer, default=0)     # ⚔️ 경호실장
    adult_count = db.Column(db.Integer, default=3)     # 🧑 성체실장
    child_count = db.Column(db.Integer, default=10)    # 👶 자실장
    baby_count = db.Column(db.Integer, default=5)      # 🐛 저실장

    # === 자원 (3종 식량 + 자재) ===
    konpeito = db.Column(db.Integer, default=5)        # 🍬 콘페이토
    trash_food = db.Column(db.Integer, default=30)     # 🗑️ 음식물 쓰레기
    meat_stock = db.Column(db.Integer, default=0)      # 🐛→🍖 식용 저실장/자실장 고기
    material = db.Column(db.Integer, default=50)       # 🧱 자재

    # === 저장 상한 ===
    konpeito_cap = db.Column(db.Integer, default=50)
    trash_food_cap = db.Column(db.Integer, default=200)
    material_cap = db.Column(db.Integer, default=100)
    population_cap = db.Column(db.Integer, default=20)

    # === 사기 ===
    morale = db.Column(db.Integer, default=50)         # 사기 (0~100)
    consecutive_trash_turns = db.Column(db.Integer, default=0)
    # 연속 쓰레기만 먹은 턴 수 (3턴 이상이면 사기 패널티)

    # === 시설 수 ===
    cardboard_houses = db.Column(db.Integer, default=1)  # 🏠 골판지집
    unchi_holes = db.Column(db.Integer, default=0)       # 🕳️ 운치굴
    storage_holes = db.Column(db.Integer, default=0)     # 📦 저장굴
    walls = db.Column(db.Integer, default=0)             # 🧱 방벽
    watchtowers = db.Column(db.Integer, default=0)       # 🗼 감시탑

    # === 게임 상태 ===
    action_points = db.Column(db.Integer, default=3)     # 남은 행동 포인트
    turn_count = db.Column(db.Integer, default=0)        # 경과 턴 수
    is_destroyed = db.Column(db.Boolean, default=False)  # 멸망 여부

    # [v1.2.0] 모바일 턴 쿼터 시스템
    turn_quota = db.Column(db.Integer, default=3)          # 현재 보유 턴 (최대 15)
    last_turn_regen_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))  # 마지막 턴 충전 시각

    # 채집에 배치된 인원 (턴 처리용)
    gathering_adults = db.Column(db.Integer, default=0)
    gathering_children = db.Column(db.Integer, default=0)

    # 방어에 배치된 인원
    defending_guards = db.Column(db.Integer, default=0)
    defending_adults = db.Column(db.Integer, default=0)

    # [v1.1.0] Phase 7: 잔혹 컨텐츠 상태 필드
    disease_turns = db.Column(db.Integer, default=0)        # 질병 남은 턴 수 (0=건강)
    konpeito_consecutive = db.Column(db.Integer, default=0)  # 연속 콘페이토 섭취 턴
    is_addicted = db.Column(db.Boolean, default=False)       # 콘페이토 중독 상태
    addiction_clean_turns = db.Column(db.Integer, default=0)  # 해독 중 콘페이토 미섭취 턴
    gather_penalty_turns = db.Column(db.Integer, default=0)  # 채집 패널티 남은 턴 (쓰레기장 철거)
    strike_turns = db.Column(db.Integer, default=0)          # 성체 태업 남은 턴

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # [v1.7.0] 보호 모드 일회성 부조 플래그: 무한 자원 증식 방지 (audit_report_34.md [STATE-F010])
    protection_bailout_done = db.Column(db.Boolean, default=False)

    # [v1.5.0] 인구/자원 음수 방어 — 모델 레벨 자동 클램핑
    # 게임 엔진 내 30+ 곳의 감산에서 음수가 발생해도 DB에 0 미만이 저장되지 않음
    @db.validates('guard_count', 'adult_count', 'child_count', 'baby_count',
                  'konpeito', 'trash_food', 'meat_stock', 'material',
                  'boss_hp', 'morale', 'action_points', 'turn_quota')
    def _clamp_non_negative(self, key, value):
        """음수 값이 설정되면 0으로 클램핑 (DB 무결성 보호)"""
        if value is not None and value < 0:
            return 0
        return value

    # 관계 설정
    build_queue = db.relationship('BuildQueue', backref='park',
                                  cascade='all, delete-orphan')
    train_queue = db.relationship('TrainQueue', backref='park',
                                    cascade='all, delete-orphan')
    event_logs = db.relationship('EventLog', backref='park',
                                 cascade='all, delete-orphan',
                                 order_by='EventLog.created_at.desc()')

    # [v1.7.0] 교역/외교/밀사 cascade — 공원 삭제 시 고아 레코드 방지 (audit_report_5.md [IMP-F006])
    sent_trade_offers = db.relationship(
        'TradeOffer', foreign_keys='TradeOffer.sender_id',
        backref='sender_park', cascade='all, delete-orphan'
    )
    received_trade_offers = db.relationship(
        'TradeOffer', foreign_keys='TradeOffer.receiver_id',
        backref='receiver_park', cascade='all, delete-orphan'
    )
    diplomacy_as_a = db.relationship(
        'Diplomacy', foreign_keys='Diplomacy.park_a_id',
        backref='park_a_ref', cascade='all, delete-orphan'
    )
    diplomacy_as_b = db.relationship(
        'Diplomacy', foreign_keys='Diplomacy.park_b_id',
        backref='park_b_ref', cascade='all, delete-orphan'
    )
    spy_missions_sent = db.relationship(
        'SpyMission', foreign_keys='SpyMission.sender_id',
        backref='sender_park_ref', cascade='all, delete-orphan'
    )
    spy_missions_received = db.relationship(
        'SpyMission', foreign_keys='SpyMission.target_id',
        backref='target_park_ref', cascade='all, delete-orphan'
    )

    @property
    def total_population(self):
        """총 인구 (저실장 제외 - 저실장은 운치굴 별도 관리)"""
        return self.guard_count + self.adult_count + self.child_count

    @hybrid_property
    def baby_cap(self):
        """저실장 수용 한도 (운치굴 수 × 10, 최소 5마리)
        [v1.7.0] hybrid_property로 SQL 쿼리에서도 직접 사용 가능 (audit_report_32.md [STATE-F008])"""
        return max(5, self.unchi_holes * 10)

    @baby_cap.expression
    def baby_cap(cls):
        """SQL 표현식: 운치굴 0개일 때도 최소 5마리 수용 보장 (audit_report_32.md [STATE-F007])"""
        return case((cls.unchi_holes * 10 > 5, cls.unchi_holes * 10), else_=5)

    @property
    def total_combat_power(self):
        """총 전투력 (사기 보정 포함)"""
        from app.config import GameConfig as GC
        base = (GC.POWER_BOSS +
                self.guard_count * GC.POWER_GUARD +
                self.adult_count * GC.POWER_ADULT +
                self.child_count * GC.POWER_CHILD)
        # 사기 보정: 사기/100을 곱함 (사기 50이면 ×1.0, 100이면 ×1.1)
        morale_mult = 1.0 + (self.morale - 50) * GC.MORALE_COMBAT_EFFECT / 50
        return int(base * morale_mult)

    @property
    def defense_power(self):
        """방어 전투력 (방벽 보너스 포함)"""
        from app.config import GameConfig as GC
        base = (self.defending_guards * GC.POWER_GUARD +
                self.defending_adults * GC.POWER_ADULT)
        # 방벽 보너스
        wall_bonus = 1.0 + self.walls * 0.2
        return int(base * wall_bonus)

    @property
    def total_np_per_turn(self):
        """턴 당 총 영양 포인트(NP) 소비량"""
        from app.config import GameConfig as GC
        return (self.guard_count * GC.NP_PER_GUARD +
                self.adult_count * GC.NP_PER_ADULT +
                self.child_count * GC.NP_PER_CHILD +
                self.baby_count * GC.NP_PER_BABY)

    @property
    def total_np_available(self):
        """현재 보유 총 영양 포인트"""
        from app.config import GameConfig as GC
        return (self.konpeito * GC.NP_KONPEITO +
                self.trash_food * GC.NP_TRASH_FOOD +
                self.meat_stock * GC.NP_MEAT)

    def to_dict(self):
        """공원 상태를 딕셔너리로 반환 (API/템플릿용)"""
        return {
            'id': self.id,
            'name': self.name,
            'is_npc': self.is_npc,
            'boss_hp': self.boss_hp,
            'guard_count': self.guard_count,
            'adult_count': self.adult_count,
            'child_count': self.child_count,
            'baby_count': self.baby_count,
            'konpeito': self.konpeito,
            'trash_food': self.trash_food,
            'meat_stock': self.meat_stock,
            'material': self.material,
            'konpeito_cap': self.konpeito_cap,
            'trash_food_cap': self.trash_food_cap,
            'material_cap': self.material_cap,
            'population_cap': self.population_cap,
            'baby_cap': self.baby_cap,
            'morale': self.morale,
            'cardboard_houses': self.cardboard_houses,
            'unchi_holes': self.unchi_holes,
            'storage_holes': self.storage_holes,
            'walls': self.walls,
            'watchtowers': self.watchtowers,
            'action_points': self.action_points,
            'turn_count': self.turn_count,
            'total_population': self.total_population,
            'total_combat_power': self.total_combat_power,
            'total_np_per_turn': self.total_np_per_turn,
            'total_np_available': self.total_np_available,
            'is_destroyed': self.is_destroyed,
        }


class BuildQueue(db.Model):
    """건설 대기열 - 건설 중인 시설 추적"""
    __tablename__ = 'build_queue'

    id = db.Column(db.Integer, primary_key=True)
    park_id = db.Column(db.Integer, db.ForeignKey('parks.id'), nullable=False)
    building_type = db.Column(db.String(50), nullable=False)
    turns_remaining = db.Column(db.Integer, nullable=False)
    workers_assigned = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class TrainQueue(db.Model):
    """훈련 대기열 - 경호실장 훈련 중인 성체실장 추적"""
    __tablename__ = 'train_queue'

    id = db.Column(db.Integer, primary_key=True)
    park_id = db.Column(db.Integer, db.ForeignKey('parks.id'), nullable=False)
    turns_remaining = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class BattleLog(db.Model):
    """전투 기록"""
    __tablename__ = 'battle_logs'

    VALID_RESULTS = ('win', 'lose')

    id = db.Column(db.Integer, primary_key=True)
    attacker_id = db.Column(db.Integer, db.ForeignKey('parks.id'), nullable=False)
    defender_id = db.Column(db.Integer, db.ForeignKey('parks.id'), nullable=False)
    result = db.Column(db.String(20), nullable=False)  # 'win' / 'lose'
    log_text = db.Column(db.Text, nullable=False)      # 전투 로그 텍스트
    loot_konpeito = db.Column(db.Integer, default=0)
    loot_trash = db.Column(db.Integer, default=0)
    loot_material = db.Column(db.Integer, default=0)
    loot_babies = db.Column(db.Integer, default=0)
    loot_children = db.Column(db.Integer, default=0)
    attacker_losses = db.Column(db.Text, default='{}')  # JSON
    defender_losses = db.Column(db.Text, default='{}')  # JSON
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    attacker = db.relationship('Park', foreign_keys=[attacker_id])
    defender = db.relationship('Park', foreign_keys=[defender_id])

    @db.validates('result')
    def _validate_result(self, key, value):
        """전투 결과는 win/lose만 허용 (불일치 데이터 방지) [v1.7.0]"""
        if value not in self.VALID_RESULTS:
            raise ValueError(f"잘못된 battle result: {value}. 허용: {self.VALID_RESULTS}")
        return value


class EventLog(db.Model):
    """이벤트 로그 - 공원에서 발생한 모든 이벤트 기록"""
    __tablename__ = 'event_logs'

    # [v1.7.0] spec.md 10.2 기준 허용 이벤트 타입 목록 (Enum 대신 튜플 + @validates 사용)
    EVENT_TYPES = (
        'gather', 'build', 'birth', 'cull', 'battle', 'starve', 'train', 'npc',
        'trade', 'diplomacy', 'disease', 'cannibalism', 'rebellion', 'addiction',
        'spy', 'sabotage', 'human_evil', 'human_good', 'gameover', 'morale',
        'overcrowd', 'growth', 'breeding', 'protect', 'birth_fail', 'birth_death',
        'disaster'
    )

    id = db.Column(db.Integer, primary_key=True)
    park_id = db.Column(db.Integer, db.ForeignKey('parks.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    turn_number = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    @db.validates('event_type')
    def _validate_event_type(self, key, value):
        """이벤트 타입은 spec.md에 정의된 26개 목록만 허용 (오타 및 잘못된 로그 삽입 방지) [v1.7.0]"""
        if value not in self.EVENT_TYPES:
            raise ValueError(f"잘못된 event_type: {value}. 허용 목록: {self.EVENT_TYPES}")
        return value


# === [v0.4.0] Phase 5: 교역 시스템 모델 ===
class TradeOffer(db.Model):
    """
    교역 제안 - 공원 간 자원 교환.
    제안자가 offer_*를 주고, request_*를 받는 구조.
    상태: pending(대기) → accepted(수락) / rejected(거절) / expired(만료) / cancelled(취소)
    """
    __tablename__ = 'trade_offers'

    VALID_STATUSES = ('pending', 'accepted', 'rejected', 'expired', 'cancelled', 'processing')

    id = db.Column(db.Integer, primary_key=True)
    # 제안 공원 (보내는 쪽)
    sender_id = db.Column(db.Integer, db.ForeignKey('parks.id'), nullable=False)
    # 대상 공원 (받는 쪽, NULL이면 공개 교역 - 아무나 수락 가능)
    receiver_id = db.Column(db.Integer, db.ForeignKey('parks.id'), nullable=True)

    # 제안하는 자원 (이만큼 줄게)
    offer_konpeito = db.Column(db.Integer, default=0)
    offer_trash = db.Column(db.Integer, default=0)
    offer_material = db.Column(db.Integer, default=0)
    offer_babies = db.Column(db.Integer, default=0)

    # 요청하는 자원 (이만큼 달라)
    request_konpeito = db.Column(db.Integer, default=0)
    request_trash = db.Column(db.Integer, default=0)
    request_material = db.Column(db.Integer, default=0)
    request_babies = db.Column(db.Integer, default=0)

    # 상태: pending / accepted / rejected / expired / cancelled
    status = db.Column(db.String(20), default='pending')
    # 메시지 (제안할 때 한 마디)
    message = db.Column(db.String(200), default='')

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    resolved_at = db.Column(db.DateTime, nullable=True)  # 수락/거절 시각

    sender = db.relationship('Park', foreign_keys=[sender_id], overlaps="sender_park,sent_trade_offers")
    receiver = db.relationship('Park', foreign_keys=[receiver_id], overlaps="receiver_park,received_trade_offers")

    @db.validates('status')
    def _validate_status(self, key, value):
        """교역 상태는 spec.md 10.3 기준 목록만 허용 [v1.7.0]"""
        if value not in self.VALID_STATUSES:
            raise ValueError(f"잘못된 trade status: {value}. 허용: {self.VALID_STATUSES}")
        return value


# === [v0.4.0] Phase 5: 외교 시스템 모델 ===
class Diplomacy(db.Model):
    """
    외교 관계 - 공원 간 동맹/적대.
    relation_type: ally(동맹), enemy(적대)
    동맹: 교역 수수료 면제, 침공 불가
    적대: 침공 시 약탈 +20% 보너스
    """
    __tablename__ = 'diplomacies'

    VALID_RELATIONS = ('ally', 'enemy')
    VALID_STATUSES = ('pending', 'active', 'rejected', 'dissolved')

    id = db.Column(db.Integer, primary_key=True)
    # [v1.8.5] Canonical Ordering 보장: 항상 park_a_id < park_b_id 만족
    park_a_id = db.Column(db.Integer, db.ForeignKey('parks.id'), nullable=False)
    park_b_id = db.Column(db.Integer, db.ForeignKey('parks.id'), nullable=False)

    # [v1.8.5] 요청/선언 주체를 명확히 구별하기 위해 initiator_id 추가 (Canonical Ordering용)
    initiator_id = db.Column(db.Integer, db.ForeignKey('parks.id'), nullable=False)

    # 관계 유형: ally(동맹), enemy(적대)
    relation_type = db.Column(db.String(20), nullable=False)
    # 동맹의 경우 상대방 수락 필요
    # 상태: pending(동맹 요청 대기) → active(활성) / rejected(거절) / dissolved(해제)
    # 적대는 즉시 active
    status = db.Column(db.String(20), default='pending')

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    resolved_at = db.Column(db.DateTime, nullable=True)

    # [v1.7.0] DB 레벨 unique 제약: 동일 공원 쌍의 동일 유형+상태 중복 생성 방지
    # (audit_report_42.md [STATE-F015])
    __table_args__ = (
        db.UniqueConstraint('park_a_id', 'park_b_id', 'relation_type', 'status'),
    )

    park_a = db.relationship('Park', foreign_keys=[park_a_id], overlaps="diplomacy_as_a,park_a_ref")
    park_b = db.relationship('Park', foreign_keys=[park_b_id], overlaps="diplomacy_as_b,park_b_ref")
    initiator = db.relationship('Park', foreign_keys=[initiator_id])

    @db.validates('relation_type')
    def _validate_relation_type(self, key, value):
        """외교 관계 유형은 ally/enemy만 허용 (spec.md 10.4) [v1.7.0]"""
        if value not in self.VALID_RELATIONS:
            raise ValueError(f"잘못된 relation_type: {value}. 허용: {self.VALID_RELATIONS}")
        return value

    @db.validates('status')
    def _validate_status(self, key, value):
        """외교 상태는 spec.md 10.4 기준 목록만 허용 [v1.7.0]"""
        if value not in self.VALID_STATUSES:
            raise ValueError(f"잘못된 diplomacy status: {value}. 허용: {self.VALID_STATUSES}")
        return value


# === [v1.1.0] Phase 7: 밀사 시스템 모델 ===
class SpyMission(db.Model):
    """밀사 임무 - 적 공원 침투/사보타주.
    상태: active(진행 중) → success(성공) / detected(발각) / returned(귀환)
    """
    __tablename__ = 'spy_missions'

    VALID_MISSION_TYPES = ('sabotage', 'intel')
    VALID_STATUSES = ('active', 'success', 'detected', 'returned')

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('parks.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('parks.id'), nullable=False)
    mission_type = db.Column(db.String(20), default='sabotage')  # 'sabotage', 'intel'
    turns_remaining = db.Column(db.Integer, default=3)           # 귀환까지 남은 턴
    status = db.Column(db.String(20), default='active')          # active/success/detected/returned
    result_message = db.Column(db.Text, default='')              # 결과 메시지
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    sender = db.relationship('Park', foreign_keys=[sender_id], overlaps="sender_park_ref,spy_missions_sent")
    target = db.relationship('Park', foreign_keys=[target_id], overlaps="spy_missions_received,target_park_ref")

    @db.validates('mission_type')
    def _validate_mission_type(self, key, value):
        """밀사 임무 유형은 sabotage/intel만 허용 (spec.md 10.5) [v1.7.0]"""
        if value not in self.VALID_MISSION_TYPES:
            raise ValueError(f"잘못된 mission_type: {value}. 허용: {self.VALID_MISSION_TYPES}")
        return value

    @db.validates('status')
    def _validate_status(self, key, value):
        """밀사 상태는 spec.md 10.5 기준 목록만 허용 [v1.7.0]"""
        if value not in self.VALID_STATUSES:
            raise ValueError(f"잘못된 spy status: {value}. 허용: {self.VALID_STATUSES}")
        return value


# === [v1.8.4] Cascade Delete로 인한 에스크로 자원 및 유닛 유실(Leakage) 차단용 SQLAlchemy Event Listener ===

@event.listens_for(TradeOffer, 'before_delete')
def before_trade_delete(mapper, connection, target):
    """
    [v1.8.4] 수신자 공원 삭제 등의 Cascade 연쇄 삭제 시, 대기 중(pending)인 교역 제안의
    에스크로 자원을 발신자(sender)에게 안전하게 자동 환불한다. (audit_report_51.md [STATE-F025])
    """
    if target.status == 'pending':
        session = object_session(target)
        if session is not None:
            # 발신자 공원이 세션 내에서 함께 삭제 중인지 확인하고, 생존 공원인 경우에만 환불
            sender = session.query(Park).filter(Park.id == target.sender_id).first()
            if sender and sender not in session.deleted:
                sender.konpeito += target.offer_konpeito
                sender.trash_food += target.offer_trash
                sender.material += target.offer_material
                sender.baby_count += target.offer_babies

                # 자원 한도 초과 방지 클램핑
                if sender.konpeito > sender.konpeito_cap:
                    sender.konpeito = sender.konpeito_cap
                if sender.trash_food > sender.trash_food_cap:
                    sender.trash_food = sender.trash_food_cap
                if sender.material > sender.material_cap:
                    sender.material = sender.material_cap
                if sender.baby_count > sender.baby_cap:
                    sender.baby_count = sender.baby_cap


@event.listens_for(SpyMission, 'before_delete')
def before_spy_delete(mapper, connection, target):
    """
    [v1.8.4] 타겟 공원 삭제 등의 Cascade 연쇄 삭제 시, 진행 중(active)인 밀사 임무의
    에스크로 유닛(성체실장)을 발신자(sender)에게 안전하게 자동 환불한다. (audit_report_51.md [STATE-F025])
    """
    if target.status == 'active':
        session = object_session(target)
        if session is not None:
            # 발신자 공원이 세션 내에서 함께 삭제 중인지 확인하고, 생존 공원인 경우에만 환불
            sender = session.query(Park).filter(Park.id == target.sender_id).first()
            if sender and sender not in session.deleted:
                sender.adult_count += 1


# === [v1.8.9] SQLite 동시성 강화를 위한 WAL 모드 및 busy_timeout pragma 적용 ===
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    [v1.8.9] SQLite 연결 시점에 WAL 모드와 busy_timeout을 자동으로 전개하여,
    with_for_update() no-op 상황에서 발생할 수 있는 동시성 병목 및 DB 잠금(Database Locked)
    상황을 방지하고 동시 쓰기 정합성을 극대화합니다.
    """
    import sqlite3
    # SQLite 커넥션인 경우에만 PRAGMA 적용
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
