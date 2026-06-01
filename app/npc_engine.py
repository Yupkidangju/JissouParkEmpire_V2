# -*- coding: utf-8 -*-
"""
실장석 공원 제국 - NPC 엔진 (npc_engine.py)
[v0.2.0] NPC 공원의 AI 행동 결정.

5종 성격별로 턴마다 어떤 행동을 우선하는지 결정한다.
- aggressive (야만): 침공 > 채집 > 건설
- defensive (요새): 건설(방벽) > 훈련 > 채집
- peaceful (목장): 채집 > 출산 > 건설
- cunning (교활): 약한 공원만 침공, 평소엔 채집+건설
- berserk (광폭): 무조건 침공! 식량 없으면 솎아내기

각 행동은 game_engine 함수를 그대로 호출한다.
"""
import random

from app.models import db, Park
from app.config import GameConfig as GC
from app import game_engine
from app import dialogues as DLG
from sqlalchemy import case # [v1.8.1] 원자적 UPDATE 캡핑용


def process_npc_turn(park):
    """
    NPC 공원의 턴별 AI 행동.
    AP를 소비하며, 성격에 따라 행동 우선순위가 결정된다.
    [v1.8.1] DB 비관적 락 획득: Lost Update 및 동시 개입 방지 (audit_report_48.md [STATE-F022])
    [v1.8.9] 락 획득 순서 역전 교착 상태 완화 (audit_report_61.md [DEADLOCK-F005])
    - 이전 버전에서 최상단에 일괄 적용되었던 비관적 락(with_for_update)은 NPC가 다른 공원을 공격하여
      execute_battle을 호출할 때 Canonical Locking 정렬(Player -> NPC) 락 획득 과정과 얽혀
      치명적인 상호 교착 상태(Deadlock)를 초래하고 DB 커넥션을 고갈시켰음.
      이에 따라 최상단 비관적 락을 영구 제거하고, 전투 등 각 개별 행동 단위가 안전하게 락을 정렬 순서대로
      자체 획득하도록 통제를 완화하고 위임함.
    """
    if park.is_destroyed or not park.is_npc:
        return

    # [v1.8.9] 교착 상태(DEADLOCK-F005) 완화를 위해 최상단 비관적 락(with_for_update)을 제거함.
    # 동시성 정합성을 해치지 않기 위해 단순 refresh만 수행하여 최신 상태로 새로고침함.
    db.session.refresh(park)

    personality = park.npc_personality or 'peaceful'

    # NPC 자원 소규모 자연 성장 (밸런스용 - 플레이어와의 격차 방지)
    _npc_passive_growth(park)

    # AP가 있는 한 행동 실행
    actions = _get_action_priority(personality, park)

    for action_func in actions:
        if park.action_points <= 0:
            break
        # [v1.8.5] Nested Transaction (Savepoint)을 사용하여 예외 발생 시 락 유실 및 전체 트랜잭션 롤백 차단 (audit_report_54.md [TRANSACTION-F005])
        # [v1.8.9] ResourceClosedError 방지: 행동 내부의 db.session.commit()에 의한 Savepoint 파괴 방지 및 예외 가드 보강 (audit_report_57.md)
        nested = db.session.begin_nested()
        try:
            action_func(park)
            nested.commit()
        except Exception:
            # 해당 행동에서 예외가 발생하더라도 nested 세이브포인트만 롤백하여 비관적 락 유지 및 turn_count 보존
            # [v1.8.9] nested.rollback() 호출 자체가 실패(ResourceClosedError)하더라도 상위 NPC 루프가 폭사하지 않도록 2차 예외 차단 가드 보강 (audit_report_57.md)
            try:
                nested.rollback()
            except Exception:
                db.session.rollback()
            continue  # NPC 행동 실패 시 무시


def _npc_passive_growth(park):
    """NPC 자원 소규모 자연 성장 (플레이어 대비 밸런스) [v1.8.1] case()를 활용한 원자적 UPDATE로 전환하여 autoflush Lost Update 차단 (audit_report_48.md [STATE-F022])"""
    personality = park.npc_personality or 'peaceful'

    # 기본 쓰레기 자연 증가 계산
    base_trash = random.randint(5, 12)
    base_material = random.randint(2, 4)

    # 성격별 추가 성장
    add_baby = 0
    add_guard = 0
    add_adult = 0
    add_material = 0
    add_konpeito = 0

    if personality == 'peaceful':
        if random.random() < 0.3:
            add_baby = random.randint(1, 2)
    elif personality == 'aggressive' or personality == 'berserk':
        if random.random() < 0.1 and park.adult_count > 2:
            add_guard = 1
            add_adult = -1
    elif personality == 'defensive':
        add_material = random.randint(1, 3)
    elif personality == 'cunning':
        if random.random() < 0.03:
            add_konpeito = 1

    # [v1.8.1] case()를 사용해 단 한 번의 원자적 UPDATE로 안전하게 DB에 직접 적용 (autoflush 시 구버전 덮어쓰기 방지)
    Park.query.filter(Park.id == park.id).update({
        'trash_food': case(
            (Park.trash_food + base_trash > Park.trash_food_cap, Park.trash_food_cap),
            else_=Park.trash_food + base_trash
        ),
        'material': case(
            (Park.material + base_material + add_material > Park.material_cap, Park.material_cap),
            else_=Park.material + base_material + add_material
        ),
        'baby_count': case(
            (Park.baby_count + add_baby > Park.baby_cap, Park.baby_cap),
            else_=Park.baby_count + add_baby
        ),
        'guard_count': Park.guard_count + add_guard,
        'adult_count': Park.adult_count + add_adult,
        'defending_adults': case(
            (Park.defending_adults > Park.adult_count + add_adult, Park.adult_count + add_adult),
            else_=Park.defending_adults
        ),
        'konpeito': case(
            (Park.konpeito + add_konpeito > Park.konpeito_cap, Park.konpeito_cap),
            else_=Park.konpeito + add_konpeito
        )
    })
    db.session.flush()
    db.session.refresh(park)


def _get_action_priority(personality, park):
    """성격별 행동 우선순위 결정"""
    if personality == 'aggressive':
        return [_npc_gather, _npc_attack, _npc_train, _npc_build_wall]
    elif personality == 'defensive':
        return [_npc_build_wall, _npc_train, _npc_gather, _npc_defend]
    elif personality == 'peaceful':
        return [_npc_gather, _npc_birth, _npc_build_house, _npc_cull_if_needed]
    elif personality == 'cunning':
        return [_npc_gather, _npc_cunning_attack, _npc_build_wall, _npc_train]
    elif personality == 'berserk':
        return [_npc_attack, _npc_attack, _npc_cull_if_needed, _npc_gather]
    else:
        return [_npc_gather, _npc_build_house]


# === NPC 개별 행동 함수들 ===

def _npc_gather(park):
    """NPC 채집: 유휴 성체를 보냄 [v1.7.0] AP 소비 추가, 성공 시만 차감 (audit_report_11.md [IMP-F024])"""
    if park.action_points < 1:
        return
    idle_adults = max(1, park.adult_count // 2)
    # [v1.8.1] commit=False 전달: NPC 턴 원자적 트랜잭션 롤백 유지 (audit_report_48.md [STATE-F022])
    success, _, _ = game_engine.action_gather(park, num_adults=idle_adults, num_children=0, commit=False)
    if success:
        park.action_points -= 1


def _npc_birth(park):
    """NPC 출산: 인구 여유가 있고 식량 충분하면 [v1.7.0] AP 소비 추가, 성공 시만 차감"""
    if park.action_points < 2:
        return
    if park.adult_count < 1:
        return
    if park.total_population >= park.population_cap - 3:
        return  # 인구 거의 다 참
    if park.total_np_available < GC.BIRTH_NP_COST * 2:
        return  # 식량 여유 없으면 안 함
    # [v1.8.1] commit=False 전달: NPC 턴 원자적 트랜잭션 롤백 유지 (audit_report_48.md [STATE-F022])
    success, _, _ = game_engine.action_birth(park, commit=False)
    if success:
        park.action_points -= 2


def _npc_build_house(park):
    """NPC 골판지집 건설: 인구 초과 임박 시 [v1.7.0] AP 소비 추가, 성공 시만 차감"""
    if park.action_points < 1:
        return
    if park.total_population < park.population_cap - 5:
        return  # 아직 여유 있으면 안 함
    if park.material < GC.BUILDINGS['cardboard_house']['material_cost']:
        return
    # [v1.8.1] commit=False 전달: NPC 턴 원자적 트랜잭션 롤백 유지 (audit_report_48.md [STATE-F022])
    success, _, _ = game_engine.action_build(park, 'cardboard_house', commit=False)
    if success:
        park.action_points -= 1


def _npc_build_wall(park):
    """NPC 방벽 건설: 방어형/교활형 [v1.7.0] AP 소비 추가, 성공 시만 차감"""
    if park.action_points < 1:
        return
    if park.walls >= 3:
        return  # 방벽 3개 이상이면 충분
    if park.material < GC.BUILDINGS['wall']['material_cost']:
        # 자재 부족하면 골판지집이라도
        if park.material >= GC.BUILDINGS['cardboard_house']['material_cost']:
            if park.total_population >= park.population_cap - 3:
                # [v1.8.1] commit=False 전달
                success, _, _ = game_engine.action_build(park, 'cardboard_house', commit=False)
                if success:
                    park.action_points -= 1
        return
    # [v1.8.1] commit=False 전달
    success, _, _ = game_engine.action_build(park, 'wall', commit=False)
    if success:
        park.action_points -= 1


def _npc_train(park):
    """NPC 훈련: 경호실장 양성 [v1.7.0] AP 소비 추가, 성공 시만 차감"""
    if park.action_points < 1:
        return
    if park.adult_count < 3:
        return  # 성체가 3 미만이면 훈련 안 함 (일손 부족)
    if park.guard_count >= 5:
        return  # 경호 5 이상이면 충분
    if park.total_np_available < GC.TRAIN_NP_COST:
        return
    # [v1.8.1] commit=False 전달
    success, _, _ = game_engine.action_train(park, commit=False)
    if success:
        park.action_points -= 1


def _npc_defend(park):
    """NPC 방어 배치: 경호실장을 방어에 배치 [v1.7.0] AP 소비 추가"""
    if park.action_points < 1:
        return
    if park.guard_count > 0:
        park.defending_guards = park.guard_count
    if park.adult_count > 2:
        park.defending_adults = park.adult_count // 3
    park.action_points -= 1


def _npc_cull_if_needed(park):
    """NPC 솎아내기: 식량 부족 시 저실장 도살 (0AP)"""
    if park.total_np_available > park.total_np_per_turn * 3:
        return  # 3턴분 식량 있으면 안 함

    # 저실장 먼저 도살
    if park.baby_count > 0:
        cull_count = min(park.baby_count, 3)
        # [v1.8.1] commit=False 전달
        game_engine.action_cull(park, 'baby', 'food', cull_count, commit=False)
    # 자실장도 위급하면
    elif park.child_count > 3 and park.total_np_available < park.total_np_per_turn:
        # [v1.8.1] commit=False 전달
        game_engine.action_cull(park, 'child', 'food', 1, commit=False)


def _npc_attack(park):
    """NPC 공격: 다른 공원 침공 [v0.3.0] 유닛 선택 추가"""
    if park.action_points < 2:
        return
    # [v1.7.0] 보호 모드 중인 NPC는 침공 불가: 일방적 무적 상태 방지 (audit_report_29.md [LOGIC-F003])
    if game_engine.is_protected(park):
        return
    if park.guard_count < 1 and park.adult_count < 3:
        return  # 전투 인원 부족

    # 공격 대상 찾기 (자기 제외, 머망 제외)
    targets = Park.query.filter(
        Park.id != park.id,
        Park.is_destroyed == False
    ).all()

    # [v1.3.0] 보호 모드 대상 제외
    from app.game_engine import is_protected
    targets = [t for t in targets if not is_protected(t)]

    # [v1.7.0] 동맹 제외: 동맹 관계인 대상은 침공 불가 (audit_report_31.md [LOGIC-F004])
    from app.models import Diplomacy
    ally_ids = {d.park_b_id if d.park_a_id == park.id else d.park_a_id
                for d in Diplomacy.query.filter(
                    ((Diplomacy.park_a_id == park.id) | (Diplomacy.park_b_id == park.id)),
                    Diplomacy.relation_type == 'ally',
                    Diplomacy.status == 'active'
                ).all()}
    targets = [t for t in targets if t.id not in ally_ids]

    if not targets:
        return

    # 랜덤 타겟 선택
    target = random.choice(targets)

    # [v0.3.0] NPC도 유닛 선택해서 출정 (방어 인원 제외)
    avail_guards = max(0, park.guard_count - park.defending_guards)
    avail_adults = max(0, park.adult_count - park.defending_adults)
    send_g = avail_guards  # NPC는 가용 경호 전원 출정
    send_a = avail_adults // 2  # 성체는 절반만

    from app.battle_engine import execute_battle
    # [v1.7.0] Auto-Flush 방지: _npc_passive_growth 등에서 메모리 수정된 내용을
    # 먼저 커밋하여 execute_battle의 with_for_update() 호출 직전에 예기치 않은
    # NPC 자신 행 UPDATE가 먼저 실행되어 락 순서가 역전되는 것을 방지
    # (audit_report_22.md [DEADLOCK-F003])
    # [v1.8.9] Savepoint 깨짐 방지: db.session.commit() 대신 db.session.flush()를 사용하여 트랜잭션 세이브포인트를 파괴하지 않고 dirty state만 DB에 방출 (audit_report_57.md)
    db.session.flush()
    won, _, _ = execute_battle(park, target,
                                send_guards=send_g,
                                send_adults=send_a,
                                boss_joins=False)
    # 전투는 시도했으므로 AP 소모 (승패와 무관)
    park.action_points -= 2


def _npc_cunning_attack(park):
    """NPC 교활 공격: 자기보다 약한 공원만 공격 [v0.3.0] 유닛 선택 추가"""
    if park.action_points < 2:
        return
    # [v1.7.0] 보호 모드 중인 NPC는 침공 불가: 일방적 무적 상태 방지 (audit_report_29.md [LOGIC-F003])
    if game_engine.is_protected(park):
        return
    if park.guard_count < 1:
        return

    targets = Park.query.filter(
        Park.id != park.id,
        Park.is_destroyed == False
    ).all()

    # 자기보다 약한 공원만 필터링 + [v1.3.0] 보호 모드 제외
    from app.game_engine import is_protected
    weak_targets = [t for t in targets
                    if t.total_combat_power < park.total_combat_power * 0.7
                    and not is_protected(t)]

    # [v1.7.0] 동맹 제외: 동맹 관계인 대상은 침공 불가 (audit_report_31.md [LOGIC-F004])
    from app.models import Diplomacy
    ally_ids = {d.park_b_id if d.park_a_id == park.id else d.park_a_id
                for d in Diplomacy.query.filter(
                    ((Diplomacy.park_a_id == park.id) | (Diplomacy.park_b_id == park.id)),
                    Diplomacy.relation_type == 'ally',
                    Diplomacy.status == 'active'
                ).all()}
    weak_targets = [t for t in weak_targets if t.id not in ally_ids]

    if not weak_targets:
        return  # 약한 상대 없으면 안 싸움 (교활!)

    target = random.choice(weak_targets)

    # [v0.3.0] 교활형은 켄수를 써서 반만만 보냄 (피해 최소화)
    avail_guards = max(0, park.guard_count - park.defending_guards)
    send_g = max(1, avail_guards // 2)
    send_a = 0  # 성체는 되도록 안 보냄

    from app.battle_engine import execute_battle
    # [v1.7.0] Auto-Flush 방지: _npc_passive_growth 등에서 메모리 수정된 내용을
    # 먼저 커밋하여 execute_battle의 with_for_update() 호출 직전에 예기치 않은
    # NPC 자신 행 UPDATE가 먼저 실행되어 락 순서가 역전되는 것을 방지
    # (audit_report_22.md [DEADLOCK-F003])
    # [v1.8.9] Savepoint 깨짐 방지: db.session.commit() 대신 db.session.flush()를 사용하여 트랜잭션 세이브포인트를 파괴하지 않고 dirty state만 DB에 방출 (audit_report_57.md)
    db.session.flush()
    won, _, _ = execute_battle(park, target,
                                send_guards=send_g,
                                send_adults=send_a,
                                boss_joins=False)
    # 전투는 시도했으므로 AP 소모 (승패와 무관)
    park.action_points -= 2
