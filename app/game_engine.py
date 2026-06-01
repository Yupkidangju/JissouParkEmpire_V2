# -*- coding: utf-8 -*-
"""
실장석 공원 제국 - 게임 엔진 (game_engine.py)
[v0.1.0] 핵심 게임 로직: 채집, 솎아내기, 출산, 건설, 턴 처리.

모든 행동은 이 엔진을 통해 처리되며,
결과와 함께 랜덤 대사를 반환한다.
"""
import random
import math
import threading
from datetime import datetime, timedelta, timezone

from app.models import db, Park, BuildQueue, TrainQueue, EventLog, SpyMission
from app.config import GameConfig as GC
from app import dialogues as DLG
from sqlalchemy import case  # [v1.7.0] 원자적 UPDATE 캡핑용 (audit_report_11.md~13.md)

# [v1.8.1] [기능 삭제] _npc_turn_lock (threading.Lock) 삭제
# - 삭제 사유: 다중 프로세스(Gunicorn 멀티 워커) 환경에서 프로세스 간 동시성 제어 불가하여 DB 비관적 락 및 turn_count 기반 직렬화로 대체
# - 삭제 버전: v1.8.1 (audit_report_48.md [LOGIC-F019])


# ========================================
# [v1.2.0] 턴 쿼터 시스템
# ========================================

def recharge_turns(park):
    """
    [v1.2.0] 접속 시 턴 충전 계산 (온디맨드 방식).
    마지막 충전 시각부터 경과한 시간에 따라 턴을 자동 충전한다.
    [v1.7.0] 비관적 락: 원자적 UPDATE와의 혼용으로 인한 Lost Update 방지 (audit_report_19.md [ARCH-F008])
    반환: 충전된 턴 수
    """
    if park.is_destroyed:
        return 0

    # [v1.7.0] 비관적 락 획득 (audit_report_19.md [ARCH-F008])
    Park.query.filter(Park.id == park.id).with_for_update().first()
    db.session.refresh(park)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # 마지막 충전 시각이 없으면 현재로 설정
    if park.last_turn_regen_at is None:
        park.last_turn_regen_at = now
        db.session.commit()
        return 0

    elapsed = (now - park.last_turn_regen_at).total_seconds()
    new_turns = int(elapsed // GC.TURN_REGEN_SECONDS)

    if new_turns <= 0:
        return 0

    # 충전 (최대값 제한)
    old_quota = park.turn_quota
    park.turn_quota = min(GC.TURN_QUOTA_MAX, park.turn_quota + new_turns)
    charged = park.turn_quota - old_quota

    # 충전된 만큼의 시간만 소비 (나머지는 보존)
    park.last_turn_regen_at += timedelta(seconds=new_turns * GC.TURN_REGEN_SECONDS)

    db.session.commit()
    return charged


def get_turn_info(park):
    """
    [v1.2.0] 프론트엔드 표시용 턴 정보 반환.
    반환: dict {quota, max, next_regen_seconds, is_full}
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if park.last_turn_regen_at is None:
        park.last_turn_regen_at = now

    elapsed = (now - park.last_turn_regen_at).total_seconds()
    next_secs = max(0, int(GC.TURN_REGEN_SECONDS - elapsed))

    return {
        'quota': park.turn_quota,
        'max': GC.TURN_QUOTA_MAX,
        'next_regen_seconds': next_secs if park.turn_quota < GC.TURN_QUOTA_MAX else 0,
        'is_full': park.turn_quota >= GC.TURN_QUOTA_MAX,
    }


def consume_turn(park, ap_cost=1):
    """
    [v1.6.0] 행동 실행 시 호출하는 AP 소비 + 자동 턴 진행 래퍼.

    설계 원칙 (v1.5.1 → v1.6.0 리팩토링):
    - 이전 버전에서는 매 행동마다 턴이 진행되어 AP 시스템이 무력화(Ghost AP)되었음.
    - 수정 후: AP가 충분하면 AP만 감소시키고 턴은 진행하지 않음.
    - AP가 부족할 때 턴쿼터를 소비하여 턴을 진행하고 AP를 리셋함.

    흐름:
    1. AP가 부족하면 → 턴쿼터 1 소비 → process_turn() 실행 (AP=3 리셋)
    2. AP 소비 (ap_cost만큼)
    3. 행동 라우트에서 실제 행동 수행

    반환: (성공여부, 이벤트 메시지 리스트)
    """
    if park.is_destroyed:
        return False, ['공원이 멸망한 데스...']

    # [v1.7.0] 원자적 AP 차감 시도 (audit_report_13.md [IMP-F031])
    updated = Park.query.filter(
        Park.id == park.id,
        Park.action_points >= ap_cost
    ).update({
        'action_points': Park.action_points - ap_cost
    })

    if updated > 0:
        db.session.refresh(park)
        return True, []

    # AP 부족 → 비관적 락 획득 후 턴 소비 (audit_report_19.md [IMP-F047])
    Park.query.filter(Park.id == park.id).with_for_update().first()
    db.session.refresh(park)

    # 락 획득 후 재검증: 다른 스레드가 이미 턴을 진행했을 수 있음
    if park.action_points >= ap_cost:
        # 다른 스레드가 턴을 진행해서 AP가 충전되었으면 AP만 차감
        park.action_points -= ap_cost
        db.session.commit()
        db.session.refresh(park)
        return True, []

    if park.turn_quota <= 0:
        db.session.commit()
        return False, ['⚡ 턴이 없는 데스! 충전될 때까지 기다리라 데스!']

    # 턴 소비 및 처리
    park.turn_quota -= 1
    # [v1.7.0] 선행 커밋: process_turn 내부의 db.session.refresh(park)가
    # 미커밋된 메모리 변경사항(turn_quota 차감)을 DB로부터 덮어쓰며 유실시키는 것을 방지
    # (audit_report_25.md [STATE-F002])
    db.session.commit()
    process_turn(park)

    db.session.commit()
    db.session.refresh(park)

    # [v1.8.3] 턴 처리 도중 보스 HP가 0이 되는 등 공원이 멸망한 경우 차단 (Zombie Action TOCTOU 방지)
    if park.is_destroyed:
        return False, ['공원이 멸망한 데스...']

    # [v1.7.0] 밀사 임무는 process_turn 외부의 별도 트랜잭션에서 처리하여
    # 자신의 Park 락을 선점한 채 타겟의 락을 요청하는 교차 데드락 방지
    # (audit_report_22.md [DEADLOCK-F001])
    _process_spy_missions(park)

    # [v1.7.0] NPC 동기 처리는 별도 트랜잭션으로 분리 (audit_report_21.md [DEADLOCK-F003])
    # [v1.8.1] player_park 인자 전달: 동기화 비교용
    if GC.TURN_NPC_SYNC:
        _sync_npc_turns(park)

    # [v1.8.8] AP 복제(Lost Update) 방지: 락이 해제된 틈새(Gap) 동안 실행된 concurrent HTTP requests(패스트 패스)로
    # 변경된 AP 값을 반영하기 위해 다시 비관적 락을 획득하고 최신 상태로 새로고침 (audit_report_56.md [STATE-F029])
    Park.query.filter(Park.id == park.id).with_for_update().first()
    db.session.refresh(park)

    # 턴 리셋 후 AP 재검증
    if park.action_points < ap_cost:
        db.session.commit()
        return False, [f'행동 포인트가 부족한 데스! {ap_cost}AP 필요한 데스!']

    park.action_points -= ap_cost
    db.session.commit()
    db.session.refresh(park)
    return True, []


def _sync_npc_turns(player_park):
    """
    [v1.2.0] NPC 공원 동기 턴 처리 (플레이어 턴 소비 시 호출)
    [v1.8.5] 개별 트랜잭션 단위 락 획득으로 Lost Update 및 Auto-Flush 데이터 유실 완화 (audit_report_54.md [STATE-F028])
    """
    from app.npc_engine import process_npc_turn
    # [v1.8.5] 루프 외부에서는 ID 목록만 추출하여 개별 루프 트랜잭션 격리 유지 (데드락 방지 오름차순 정렬)
    npc_ids = [p.id for p in Park.query.filter_by(is_npc=True, is_destroyed=False).order_by(Park.id.asc()).all()]
    for npc_id in npc_ids:
        # 개별 트랜잭션 단위로 비관적 락 획득 및 조회
        npc_park = Park.query.filter_by(id=npc_id, is_destroyed=False).with_for_update().first()
        if not npc_park:
            continue
        db.session.refresh(npc_park)
        db.session.refresh(player_park)

        # [v1.8.1] 중복 진행(NPC Stampede) 방지: 이미 동기화된 NPC는 스킵
        if npc_park.turn_count >= player_park.turn_count:
            continue

        # [v1.8.9] 락 순서 역전 교착 상태 완화 (audit_report_62.md [DEADLOCK-F005])
        # - 1단계: NPC 기본 턴 처리 (식량 소비, 기아, 질병 등) 수행 후 커밋하여 선점 락을 해제함
        process_turn(npc_park)
        db.session.commit()

        # - 2단계: 선점 락이 해제된 상태에서 NPC AI 행동 의사결정 및 연산을 구동함
        # 이 시점에는 락이 풀려 있으므로 execute_battle 진입 시 Canonical Ordering 정렬 락 획득이 데드락 가능성을 낮춘다.
        process_npc_turn(npc_park)
        # NPC의 AI 행동 완료 후 변경된 AP 차감 및 자원 상태를 최종 커밋하여 반영함
        db.session.commit()


# ========================================
# [v1.3.0] 보호 모드 시스템
# ========================================

def is_protected(park):
    """
    [v1.3.0] 보호 모드 여부 판정.
    경호실장 < PROTECT_GUARD_MIN 또는 성체실장 < PROTECT_ADULT_MIN이면 보호 상태.
    반환: bool (True = 보호 중)
    """
    if park.is_destroyed:
        return False
    return (park.guard_count < GC.PROTECT_GUARD_MIN or
            park.adult_count < GC.PROTECT_ADULT_MIN)


def check_and_enter_protection(park):
    """
    [v1.3.0] 보호 모드 진입 체크 + 자원 리셋.
    현재 자원이 보호 리셋 기준보다 낮으면 보호 리셋 수준까지 보충한다.
    (실장석은 재배치, 자원은 최소 유지)
    [v1.7.0] 일회성 부조: 보호 모드 에피소드당 1회만 리셋 적용 (audit_report_34.md [STATE-F010])
    [v1.8.0] 비관적 락 및 리프레시 추가: TOCTOU 동시성 이슈 및 Lost Update 방지 (audit_report_47.md [STATE-F020])
    반환: bool (True = 보호 모드에 진입해서 자원이 보충됨)
    """
    if park.is_destroyed:
        return False

    # [v1.8.0] 비관적 락 획득 및 리프레시: Lost Update 방지 (audit_report_47.md [STATE-F020])
    Park.query.filter(Park.id == park.id).with_for_update().first()
    db.session.refresh(park)

    # [v1.7.0] 보호 모드 탈출 시 플래그 초기화: 다음 보호 진입 시 부조 가능 (audit_report_34.md [STATE-F010])
    if not is_protected(park) and park.protection_bailout_done:
        park.protection_bailout_done = False
        db.session.commit()
        return False

    if not is_protected(park):
        return False

    # [v1.7.0] 이미 부조를 받은 에피소드는 중복 리셋 차단 (audit_report_34.md [STATE-F010])
    if park.protection_bailout_done:
        return False

    reset_applied = False

    # 인구 보충 (현재보다 리셋값이 높을 때만 적용)
    if park.adult_count < GC.PROTECT_RESET_ADULTS:
        park.adult_count = GC.PROTECT_RESET_ADULTS
        reset_applied = True
    if park.child_count < GC.PROTECT_RESET_CHILDREN:
        park.child_count = GC.PROTECT_RESET_CHILDREN
        reset_applied = True
    if park.baby_count < GC.PROTECT_RESET_BABIES:
        park.baby_count = GC.PROTECT_RESET_BABIES
        reset_applied = True

    # [v1.7.0] 골판지집 복구: 보호 모드 진입 시 집이 0이면 1채 복구 + population_cap 증가
    # 재해 등으로 집이 파괴된 상태에서 인구만 복구하면 즉시 과밀도 탈주 발생함 (audit_report_33.md [ARCH-F010])
    if park.cardboard_houses == 0:
        park.cardboard_houses = 1
        park.population_cap += GC.BUILDINGS['cardboard_house']['effect'].get('population_cap', 15)
        reset_applied = True

    # 자원 보충 (현재보다 리셋값이 높을 때만 적용)
    if park.trash_food < GC.PROTECT_RESET_TRASH:
        park.trash_food = GC.PROTECT_RESET_TRASH
        reset_applied = True
    if park.konpeito < GC.PROTECT_RESET_KONPEITO:
        park.konpeito = GC.PROTECT_RESET_KONPEITO
        reset_applied = True
    if park.material < GC.PROTECT_RESET_MATERIAL:
        park.material = GC.PROTECT_RESET_MATERIAL
        reset_applied = True

    # 사기 최소 유지
    if park.morale < 30:
        park.morale = 30
        reset_applied = True

    # 보스 HP 최소 유지
    if park.boss_hp < 50:
        park.boss_hp = 50
        reset_applied = True

    if reset_applied:
        park.protection_bailout_done = True  # [v1.7.0] 부조 완료 표시 (audit_report_34.md [STATE-F010])
        add_event(park, 'protect',
                  f'🛡️ 보호 모드 발동! 자원과 실장석이 재배치되었는 데스! '
                  f'(경호 {GC.PROTECT_GUARD_MIN}↑ \u0026 성체 {GC.PROTECT_ADULT_MIN}↑ 시 해제)')
        db.session.commit()

    return reset_applied


def get_protection_info(park):
    """
    [v1.3.0] 보호 모드 UI 표시용 정보.
    반환: dict {is_protected, guard_progress, adult_progress,
                guard_need, adult_need}
    """
    protected = is_protected(park)
    return {
        'is_protected': protected,
        'guard_current': park.guard_count,
        'guard_min': GC.PROTECT_GUARD_MIN,
        'guard_need': max(0, GC.PROTECT_GUARD_MIN - park.guard_count),
        'adult_current': park.adult_count,
        'adult_min': GC.PROTECT_ADULT_MIN,
        'adult_need': max(0, GC.PROTECT_ADULT_MIN - park.adult_count),
    }



def add_event(park, event_type, message, turn=None):
    """이벤트 로그를 공원에 추가"""
    log = EventLog(
        park_id=park.id,
        event_type=event_type,
        message=message,
        turn_number=turn or park.turn_count,
    )
    db.session.add(log)


# ========================================
# 채집 행동 (1 AP)
# ========================================
def action_gather(park, num_adults=0, num_children=0, commit=True):
    """
    채집 실행. 성체/자실장을 채집에 보내 쓰레기·콘페이토·자재를 획득.
    반환: (성공여부, 결과 딕셔너리, 대사 리스트)
    """
    messages = []

    # [v1.6.0] AP 체크/소비는 consume_turn(ap_cost=1)에서 처리됨

    # [v1.1.0] 태업 중이면 채집 불가
    if park.strike_turns > 0:
        return False, {}, ["✊ 성체들이 태업 중인 데스!! 채집을 거부하는 데스!!"]

    # 인원 검증 (보유 수 초과 불가)
    num_adults = min(num_adults, park.adult_count)
    num_children = min(num_children, park.child_count)

    if num_adults + num_children == 0:
        return False, {}, ["아무도 안 보내면 안 되는 데스!"]

    # 채집 인원 기억 (다음 턴 기본값으로 사용)
    park.gathering_adults = num_adults
    park.gathering_children = num_children

    # 출발 대사
    if num_adults > 0:
        messages.append(DLG.get_random_dialogue(DLG.GATHER_DEPART['adult']))
    if num_children > 0:
        messages.append(DLG.get_random_dialogue(DLG.GATHER_DEPART['child']))

    # === 수확 계산 ===
    result = {'trash': 0, 'konpeito': 0, 'material': 0, 'events': []}

    # 성체실장 채집
    for _ in range(num_adults):
        result['trash'] += random.randint(*GC.GATHER_TRASH_ADULT)
        result['material'] += random.randint(*GC.GATHER_MAT_ADULT)
        # 콘페이토 발견 확률
        if random.random() < GC.GATHER_KONPEITO_ADULT_CHANCE:
            result['konpeito'] += 1

    # 자실장 채집
    for _ in range(num_children):
        result['trash'] += random.randint(*GC.GATHER_TRASH_CHILD)
        result['material'] += random.randint(*GC.GATHER_MAT_CHILD)
        if random.random() < GC.GATHER_KONPEITO_CHILD_CHANCE:
            result['konpeito'] += 1

    # [v1.1.0] 쓰레기장 철거 패널티 (수확 50% 감소)
    if park.gather_penalty_turns > 0:
        result['trash'] = int(result['trash'] * 0.5)
        result['material'] = int(result['material'] * 0.5)
        messages.append('🚛 쓰레기장 철거로 수확량이 반토막인 데스...')

    # [v1.1.0] 콘페이토 중독 패널티 (채집 효율 50% 감소)
    if park.is_addicted:
        result['trash'] = int(result['trash'] * GC.ADDICTION_GATHER_PENALTY)
        result['material'] = int(result['material'] * GC.ADDICTION_GATHER_PENALTY)
        messages.append('🍬😵 중독된 실장석들이 의욕 없이 채집하는 데스...')

    # === 랜덤 이벤트 ===
    total_gatherers = num_adults + num_children

    # 이벤트 1: 쓰레기통 대박 (쓰레기 ×3)
    if random.random() < GC.GATHER_EVT_JACKPOT_CHANCE:
        result['trash'] *= 3
        result['events'].append('jackpot')
        messages.extend(DLG.get_random_dialogues(DLG.GATHER_EVT_JACKPOT, 2))

    # 이벤트 2: 야생 실장석 발견 [v1.7.0] 원자적 인구 증가 (audit_report_15.md [IMP-F041])
    if random.random() < GC.GATHER_EVT_WILDLING_CHANCE:
        if random.random() < 0.5:
            # 자실장 원자적 증가 (population_cap 체크)
            updated = Park.query.filter(
                Park.id == park.id,
                (Park.guard_count + Park.adult_count + Park.child_count) < Park.population_cap
            ).update({
                'child_count': Park.child_count + 1
            })
            if updated > 0:
                result['events'].append('wildling_child')
                messages.extend(DLG.get_random_dialogues(DLG.GATHER_EVT_WILDLING, 2))
        else:
            # 저실장 원자적 증가 (baby_cap 체크) [v1.7.0] hybrid_property 사용 (audit_report_32.md [LOGIC-F007])
            updated = Park.query.filter(
                Park.id == park.id,
                Park.baby_count < Park.baby_cap
            ).update({
                'baby_count': Park.baby_count + 1
            })
            if updated > 0:
                result['events'].append('wildling_baby')
                messages.extend(DLG.get_random_dialogues(DLG.GATHER_EVT_WILDLING, 2))

    # 이벤트 3: 까마귀 습격 (자실장 사망 위험) [v1.7.0] 원자적 차감 (audit_report_15.md [IMP-F041])
    if num_children > 0 and random.random() < GC.GATHER_EVT_PREDATOR_CHANCE:
        Park.query.filter(Park.id == park.id).update({
            'child_count': case((Park.child_count < 1, 0), else_=Park.child_count - 1)
        })
        result['events'].append('predator')
        messages.extend(DLG.get_random_dialogues(DLG.GATHER_EVT_PREDATOR, 2))

    # === 자원 적용 (상한 제한) [v1.7.0] 원자적 UPDATE (audit_report_15.md [IMP-F041])
    Park.query.filter(Park.id == park.id).update({
        'trash_food': case((Park.trash_food + result['trash'] > Park.trash_food_cap, Park.trash_food_cap), else_=Park.trash_food + result['trash']),
        'konpeito': case((Park.konpeito + result['konpeito'] > Park.konpeito_cap, Park.konpeito_cap), else_=Park.konpeito + result['konpeito']),
        'material': case((Park.material + result['material'] > Park.material_cap, Park.material_cap), else_=Park.material + result['material']),
    })

    # 성공 대사
    if result['konpeito'] > 0:
        messages.append(DLG.get_random_dialogue(DLG.GATHER_KONPEITO_FOUND))

    if result['trash'] >= total_gatherers * 8:
        messages.extend(DLG.get_random_dialogues(DLG.GATHER_SUCCESS_BIG, 1))
    else:
        messages.append(DLG.get_random_dialogue(DLG.GATHER_SUCCESS_SMALL))

    # 이벤트 로그 저장
    summary = (f"🌿 채집 완료! 🗑️음쓰 +{result['trash']} "
               f"🍬콘페이토 +{result['konpeito']} 🧱자재 +{result['material']}")
    add_event(park, 'gather', summary)

    if commit:
        db.session.commit()
    return True, result, messages


# ========================================
# 솎아내기 (도살) 행동 (0 AP)
# ========================================
def action_cull(park, target_type, convert_to, count=1, commit=True):
    """
    솎아내기 (도살) 실행.
    target_type: 'baby' (저실장) 또는 'child' (자실장)
    convert_to: 'food' (식량) 또는 'material' (자재)
    count: 도살할 마리 수
    반환: (성공여부, 결과, 대사 리스트)
    """
    messages = []

    # 대상 확인
    if target_type == 'baby':
        if park.baby_count < count:
            return False, {}, ["저실장이 부족한 데스!"]
    elif target_type == 'child':
        if park.child_count < count:
            return False, {}, ["자실장이 부족한 데스!"]
    else:
        return False, {}, ["뭘 솎아내라는 건지 모르겠는 데스!"]

    result = {'food': 0, 'material': 0}

    # [v1.7.0] 원자적 인구 차감: 동시 솎아내기 AP Blackhole 방지 (audit_report_15.md [IMP-F041])
    pop_col = 'baby_count' if target_type == 'baby' else 'child_count'
    updated = Park.query.filter(
        Park.id == park.id,
        getattr(Park, pop_col) >= count
    ).update({
        pop_col: getattr(Park, pop_col) - count
    })
    if updated == 0:
        return False, {}, [f"{ '저실장' if target_type == 'baby' else '자실장' }이 부족한 데스!"]
    db.session.refresh(park)

    # 자원 증가량 계산
    if target_type == 'baby':
        for _ in range(count):
            messages.append(DLG.get_random_dialogue(DLG.CULL_BABY_VICTIM))
            if convert_to == 'food':
                result['food'] += GC.CULL_BABY_FOOD
                messages.append(DLG.get_random_dialogue(DLG.CULL_BABY_EXECUTOR))
            else:
                result['material'] += GC.CULL_BABY_MAT
                messages.append(DLG.get_random_dialogue(DLG.CULL_BABY_TO_MAT))
    else:
        for _ in range(count):
            messages.append(DLG.get_random_dialogue(DLG.CULL_CHILD_VICTIM))
            if convert_to == 'food':
                result['food'] += GC.CULL_CHILD_FOOD
                messages.append(DLG.get_random_dialogue(DLG.CULL_CHILD_EXECUTOR))
            else:
                result['material'] += GC.CULL_CHILD_MAT
                messages.append(DLG.get_random_dialogue(DLG.CULL_CHILD_TO_MAT))

    # [v1.7.0] 원자적 자원 증가: 동시 솎아내기 Lost Update 방지 (audit_report_15.md [IMP-F041])
    if convert_to == 'food':
        meat_add = count if target_type == 'baby' else count * 2
        Park.query.filter(Park.id == park.id).update({
            'meat_stock': Park.meat_stock + meat_add
        })
    else:
        mat_add = count * (GC.CULL_BABY_MAT if target_type == 'baby' else GC.CULL_CHILD_MAT)
        Park.query.filter(Park.id == park.id).update({
            'material': case((Park.material + mat_add > Park.material_cap, Park.material_cap), else_=Park.material + mat_add)
        })

    # 이벤트 로그
    emoji = '🐛' if target_type == 'baby' else '👶'
    name = '저실장' if target_type == 'baby' else '자실장'
    what = f"식량 {result['food']}NP" if convert_to == 'food' else f"자재 {result['material']}"
    add_event(park, 'cull', f"🔪 {emoji}{name} {count}마리 솎아내기 → {what}")

    if commit:
        db.session.commit()
    return True, result, messages


# ========================================
# 출산 행동 (2 AP)
# ========================================
def action_birth(park, commit=True):
    """
    출산 실행. 성체실장 1마리가 자실장/저실장을 낳는다.
    비용: 2 AP + 30 NP
    [v1.1.0] 출산 잔혹 이벤트 추가: 사산, 기형, 대량출산, 모체 사망, 포식
    반환: (성공여부, 결과, 대사 리스트)
    """
    messages = []

    # [v1.6.0] AP 체크/소비는 consume_turn(ap_cost=2)에서 처리됨

    if park.adult_count < 1:
        return False, {}, ["출산할 성체실장이 없는 데스!"]

    # 영양 비용 확인 (30 NP)
    if park.total_np_available < GC.BIRTH_NP_COST:
        return False, {}, ["식량이 부족해서 출산할 수 없는 데스! 30NP 필요한 데스!"]

    # [v1.7.0] 비관적 락: _consume_np 이전에 획득 (audit_report_20.md [IMP-F048])
    Park.query.filter(Park.id == park.id).with_for_update().first()
    db.session.refresh(park)

    # NP 소비 (쓰레기부터 소비) [v1.7.0] shortage 반환값 확인 (audit_report_17.md [IMP-F044])
    shortage = _consume_np(park, GC.BIRTH_NP_COST)
    if shortage > 0:
        add_event(park, 'birth_fail', f'💀 식량 부족으로 출산 실패! {shortage}NP 모자람!')
        if commit:
            db.session.commit()
        return False, {}, ["식량이 부족해서 출산할 수 없는 데스! 30NP 필요한 데스!"]

    # [v1.1.0] 사산 판정 (5%)
    if random.random() < GC.BIRTH_STILLBORN_CHANCE:
        messages.append(DLG.get_random_dialogue(DLG.BIRTH_STILLBORN))
        add_event(park, 'birth_fail', '🐣💀 사산... 식량만 소비되었는 데스...')
        park.morale = max(0, park.morale - 5)
        if commit:
            db.session.commit()
        return True, {'children': 0, 'babies': 0, 'event': 'stillborn'}, messages

    # 출산 결과
    new_children = random.randint(*GC.BIRTH_CHILDREN)
    new_babies = random.randint(*GC.BIRTH_BABIES)

    # [v1.1.0] 대량 출산 (8%)
    if random.random() < GC.BIRTH_MASSIVE_CHANCE:
        new_children = random.randint(8, 12)
        messages.append(DLG.get_random_dialogue(DLG.BIRTH_MASSIVE))

    # [v1.1.0] 기형 출산 (10%) - 저실장 1마리가 사용 불가
    deform_count = 0
    if random.random() < GC.BIRTH_DEFORM_CHANCE and new_babies > 0:
        deform_count = 1
        new_babies = max(0, new_babies - 1)  # 기형 1마리는 바로 사망 처리
        messages.append(DLG.get_random_dialogue(DLG.BIRTH_DEFORM))
        park.morale = max(0, park.morale - 3)

    # 인구 상한 확인 (자실장 — population_cap 기준)
    space = park.population_cap - park.total_population
    new_children = min(new_children, max(0, space))

    # [v1.5.0] 저실장 수용 상한 확인 (baby_cap 기준) — Exploit 차단
    # [v1.7.0] baby_cap hybrid_property가 max(5, unchi_holes*10)를 내장 (audit_report_32.md [STATE-F008])
    baby_space = max(0, park.baby_cap - park.baby_count)
    new_babies = min(new_babies, baby_space)

    park.child_count += new_children
    park.baby_count += new_babies

    result = {'children': new_children, 'babies': new_babies}

    # 대사
    messages.extend(DLG.get_random_dialogues(DLG.BIRTH_NORMAL, 2))
    if new_babies > 0:
        messages.append(DLG.get_random_dialogue(DLG.BIRTH_WITH_BABY))
    if new_children >= 5:
        messages.append(DLG.get_random_dialogue(DLG.BIRTH_MANY))

    # [v1.1.0] 모체 사망 (2%)
    if random.random() < GC.BIRTH_MOTHER_DEATH_CHANCE and park.adult_count > 1:
        park.adult_count -= 1
        # [v1.7.0] 방어 배치 동기화: 성체 감소 시 defending_adults도 clamping
        # (audit_report_35.md [STATE-F011])
        park.defending_adults = min(park.defending_adults, park.adult_count)
        messages.append(DLG.get_random_dialogue(DLG.BIRTH_MOTHER_DEATH))
        add_event(park, 'birth_death', '🐣💀 출산 중 성체 1마리 사망...')
        park.morale = max(0, park.morale - 10)
        result['mother_died'] = True

    # [v1.1.0] 기아 상태 출산 시 포식 (3%)
    if (park.total_np_available <= 0 and
            random.random() < GC.BIRTH_CANNIBALISM_CHANCE and
            new_children > 0 and park.adult_count > 1):
        eaten = min(2, new_children)
        park.child_count -= eaten
        park.meat_stock += eaten  # 고기로 전환
        new_children -= eaten
        messages.append(DLG.get_random_dialogue(DLG.BIRTH_CANNIBALISM_EVENT))
        add_event(park, 'cannibalism', f'🐣🩸 배고픈 성체가 갓난 자실장 {eaten}마리를 포식!')
        park.morale = max(0, park.morale + GC.CANNIBALISM_MORALE_PENALTY)
        result['eaten'] = eaten

    # 이벤트 로그
    event_msg = f"🐣 출산! 👶자실장 +{new_children}, 🐛저실장 +{new_babies}"
    if deform_count > 0:
        event_msg += f" (기형 {deform_count})"
    add_event(park, 'birth', event_msg)

    if commit:
        db.session.commit()
    return True, result, messages


# ========================================
# 건설 행동 (1 AP)
# ========================================
def action_build(park, building_type, commit=True):
    """
    건설 시작. 자재를 소비하고 건설 대기열에 추가.
    반환: (성공여부, 결과, 대사 리스트)
    """
    messages = []

    # [v1.6.0] AP 체크/소비는 consume_turn(ap_cost=1)에서 처리됨

    # [v1.1.0] 태업 중이면 건설 불가
    if park.strike_turns > 0:
        return False, {}, ["✊ 성체들이 태업 중인 데스!! 건설을 거부하는 데스!!"]

    if building_type not in GC.BUILDINGS:
        return False, {}, ["그런 건물은 모르는 데스!"]

    bldg = GC.BUILDINGS[building_type]

    # [v1.7.0] 원자적 자재 차감: 동시 건설 Double Spend 방지 (audit_report_13.md [IMP-F032])
    updated = Park.query.filter(
        Park.id == park.id,
        Park.material >= bldg['material_cost']
    ).update({
        'material': Park.material - bldg['material_cost']
    })

    if updated == 0:
        return False, {}, [f"자재가 부족한 데스! {bldg['material_cost']}🧱 필요한 데스!"]

    db.session.refresh(park)

    # 건설 대기열에 추가
    build = BuildQueue(
        park_id=park.id,
        building_type=building_type,
        turns_remaining=bldg['turns'],
    )
    db.session.add(build)

    # 대사
    build_dialogues = DLG.BUILD_START.get(building_type, DLG.BUILD_START['default'])
    messages.extend(DLG.get_random_dialogues(build_dialogues, 2))

    # 이벤트 로그
    add_event(park, 'build',
              f"🔨 {bldg['emoji']}{bldg['name']} 건설 시작! ({bldg['turns']}턴 소요)")

    if commit:
        db.session.commit()
    return True, {'building': building_type, 'turns': bldg['turns']}, messages


# ========================================
# 훈련 행동 (1 AP)
# ========================================
def action_train(park, commit=True):
    """
    경호실장 훈련 시작. 성체실장 1마리를 훈련에 투입.
    반환: (성공여부, 결과, 대사 리스트)
    """
    messages = []

    # [v1.6.0] AP 체크/소비는 consume_turn(ap_cost=1)에서 처리됨

    if park.adult_count < 1:
        return False, {}, ["훈련할 성체실장이 없는 데스!"]

    if park.total_np_available < GC.TRAIN_NP_COST:
        return False, {}, [f"식량이 부족한 데스! 훈련에 {GC.TRAIN_NP_COST}NP 필요한 데스!"]

    # [v1.7.0] 비관적 락: _consume_np 이전에 획득 (audit_report_20.md [IMP-F048])
    Park.query.filter(Park.id == park.id).with_for_update().first()
    db.session.refresh(park)

    # [v1.7.0] 원자적 성체 차감 + 방어 배치 동기화: 동시 훈련 Double Spend 및
    # Phantom Defense Exploit 방지 (audit_report_13.md [IMP-F032], audit_report_35.md [STATE-F011])
    updated = Park.query.filter(
        Park.id == park.id,
        Park.adult_count >= 1
    ).update({
        'adult_count': Park.adult_count - 1,
        'defending_adults': case(
            (Park.defending_adults > Park.adult_count - 1, Park.adult_count - 1),
            else_=Park.defending_adults
        )
    })

    if updated == 0:
        return False, {}, ["훈련할 성체실장이 없는 데스!"]

    db.session.refresh(park)

    # NP 소비 [v1.7.0] shortage 반환값 확인 (audit_report_17.md [IMP-F044])
    shortage = _consume_np(park, GC.TRAIN_NP_COST)
    if shortage > 0:
        # NP 부족 시 성체 원자적 복구
        Park.query.filter(Park.id == park.id).update({
            'adult_count': Park.adult_count + 1
        })
        if commit:
            db.session.commit()
        return False, {}, [f"식량이 부족한 데스! 훈련에 {GC.TRAIN_NP_COST}NP 필요한 데스!"]

    # 훈련 대기열 추가
    train = TrainQueue(
        park_id=park.id,
        turns_remaining=GC.TRAIN_TURNS,
    )
    db.session.add(train)

    messages.extend(DLG.get_random_dialogues(DLG.TRAIN_START, 2))
    add_event(park, 'train', f"📖 경호실장 훈련 시작! ({GC.TRAIN_TURNS}턴 소요)")

    if commit:
        db.session.commit()
    return True, {'turns': GC.TRAIN_TURNS}, messages


# ========================================
# 턴 처리 (스케줄러에서 호출)
# ========================================
def process_turn(park):
    """
    1턴 처리. 매 턴 자동으로 실행되는 로직.
    [v1.1.0] 순서: AP → 식량 → 카니발리즘 → 건설 → 훈련 → 성장 → 운치굴 →
                   재해 → 질병 → NPC악행 → 반란 → 중독 → 밀사 → 수용초과
    [v1.7.0] 비관적 락: ORM 커밋과 원자적 UPDATE 혼용으로 인한 Lost Update 방지 (audit_report_18.md [ARCH-F006])
    """
    # [v1.7.0] 비관적 락: 턴 처리 중 다른 원자적 UPDATE가 개입하지 못하게 함
    Park.query.filter(Park.id == park.id).with_for_update().first()
    db.session.refresh(park)

    # [v1.7.0] 전역 파괴 검증: boss_hp <= 0인 공원은 즉시 멸망 처리
    # 전투 등에서 boss_hp가 음수로 떨어졌을 때 process_turn이 없으면 좀비 상태가 되는 결함 방지
    # (audit_report_34.md [STATE-F009])
    if park.boss_hp <= 0:
        park.is_destroyed = True
        add_event(park, 'gameover',
                  "👑 보스실장이... 굶어서... 죽었는 데스... 공원은 끝난 데스...")
        db.session.commit()
        return

    park.turn_count += 1
    park.action_points = GC.ACTION_POINTS_PER_TURN

    # 배치 인원 조정 (죽었거나 줄어든 경우 기억값을 보유 수에 맞춤) [v1.7.0] 음수 하한선 추가 (audit_report_9.md [IMP-F020])
    park.gathering_adults = min(park.gathering_adults, park.adult_count)
    park.gathering_children = min(park.gathering_children, park.child_count)
    park.defending_guards = max(0, min(park.defending_guards, park.guard_count))
    park.defending_adults = max(0, min(park.defending_adults, park.adult_count))

    # [v1.7.0] 메모리 수정분 보존: _consume_np 등 하위 함수의 refresh()가
    # 미커밋 변경사항(turn_count, action_points, 배치 인원 등)을 폐기하지 않도록
    # 트랜잭션 내에 먼저 확정(flush) (audit_report_26.md [STATE-F003])
    db.session.flush()

    # 1. 식량 소비
    _process_food_consumption(park)

    # 2. [v1.1.0] 자동 카니발리즘 (기아 시 경호 포식)
    _process_cannibalism(park)

    # 3. 건설 진행
    _process_building(park)

    # 4. 훈련 진행
    _process_training(park)

    # 5. 성장 판정 (자실장 → 성체실장)
    _process_growth(park)

    # 6. 운치굴 저실장 증가
    _process_unchi_breeding(park)

    # 7. [v1.1.0] 재해 & 환경 이벤트
    _process_disasters(park)

    # 8. [v1.1.0] 질병 시스템
    _process_disease(park)

    # 9. [v1.1.0] NPC 악행 이벤트
    _process_human_events(park)

    # 10. [v1.1.0] 반란 & 태업
    _process_rebellion(park)

    # 11. [v1.1.0] 콘페이토 중독 판정
    _process_addiction(park)

    # 12. [v1.1.0] 밀사 임무 진행
    # [v1.7.0] process_turn 내부에서 타겟 Park를 UPDATE하면 자신의 락을 선점한 상태에서
    # 타겟의 락을 요청하게 되어 교차 데드락이 발생함. consume_turn에서 별도 트랜잭션으로 분리
    # (audit_report_22.md [DEADLOCK-F001])
    # _process_spy_missions(park)  <- consume_turn()으로 이동

    # 13. 수용 인원 초과 판정
    _process_overcrowding(park)

    # 채집 패널티 턴 감소
    if park.gather_penalty_turns > 0:
        park.gather_penalty_turns -= 1

    # 태업 턴 감소
    if park.strike_turns > 0:
        park.strike_turns -= 1

    db.session.commit()

    # [v1.7.0] 로그 테이블 주기적 청소: 무한 증가 방지 (audit_report_18.md [ARCH-F007])
    _prune_old_logs(park)


def _prune_old_logs(park):
    """오래된 로그 레코드를 주기적으로 삭제하여 테이블 무한 증가 방지 [v1.7.0] (audit_report_18.md [ARCH-F007])"""
    # 100턴당 1회 정도의 확률로 청소 실행 (과도한 I/O 방지)
    if park.turn_count % 100 != 0:
        return
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
    EventLog.query.filter(EventLog.created_at < cutoff).delete(synchronize_session=False)
    BattleLog.query.filter(BattleLog.created_at < cutoff).delete(synchronize_session=False)
    SpyMission.query.filter(
        SpyMission.status.in_(['returned', 'detected', 'success']),
        SpyMission.turns_remaining <= 0
    ).delete(synchronize_session=False)
    db.session.commit()


def _consume_np(park, np_needed):
    """
    영양 포인트(NP)를 소비. 우선순위: 쓰레기 → 고기 → 콘페이토.
    [v1.7.0] 원자적 UPDATE로 변경하여 Discount Exploit 방지 (audit_report_15.md [IMP-F039])
    """
    remaining = np_needed

    # 1순위: 음식물 쓰레기
    if remaining > 0:
        db.session.refresh(park)
        use = min(park.trash_food, remaining)
        if use > 0:
            Park.query.filter(Park.id == park.id).update({
                'trash_food': case((Park.trash_food < use, 0), else_=Park.trash_food - use)
            })
            remaining -= use

    # 2순위: 식용 고기
    if remaining > 0:
        db.session.refresh(park)
        use_meat = min(park.meat_stock, math.ceil(remaining / GC.NP_MEAT))
        if use_meat > 0:
            Park.query.filter(Park.id == park.id).update({
                'meat_stock': case((Park.meat_stock < use_meat, 0), else_=Park.meat_stock - use_meat)
            })
            remaining -= use_meat * GC.NP_MEAT

    # 3순위: 콘페이토
    if remaining > 0:
        db.session.refresh(park)
        use_kon = min(park.konpeito, math.ceil(remaining / GC.NP_KONPEITO))
        if use_kon > 0:
            Park.query.filter(Park.id == park.id).update({
                'konpeito': case((Park.konpeito < use_kon, 0), else_=Park.konpeito - use_kon)
            })
            remaining -= use_kon * GC.NP_KONPEITO

    # [v1.7.0] 원자적 UPDATE 후 메모리 동기화: _process_food_consumption의
    # 소비 여부 판정(konpeito_before > park.konpeito 등)이 정확히 작동하려면
    # DB의 최신 값을 메모리 객체에 반영해야 함 (audit_report_24.md [STATE-F001])
    db.session.refresh(park)
    return max(0, remaining)  # [v1.7.0] 음수 반환 방지 (audit_report_17.md [MATH-F004])


def _process_food_consumption(park):
    """턴 당 식량 소비 처리 [v1.7.0] 콘페이토/고기/쓰레기 소비 여부 정확히 추적"""
    np_needed = park.total_np_per_turn

    # [v1.7.0] _consume_np 호출 전 자원량 저장 (audit_report_4.md [MATH-F003], audit_report_6.md [IMP-F010])
    konpeito_before = park.konpeito
    meat_before = park.meat_stock
    trash_before = park.trash_food

    shortage = _consume_np(park, np_needed)

    # [v1.7.0] 실제 소비 여부 판별: _consume_np 이후 감소분 비교
    konpeito_consumed = konpeito_before > park.konpeito
    meat_consumed = meat_before > park.meat_stock
    trash_consumed = trash_before > park.trash_food

    # [v1.7.0] _process_addiction에서도 동일한 판정 기준을 사용할 수 있도록 임시 플래그 저장
    park._konpeito_consumed_this_turn = konpeito_consumed
    park._meat_consumed_this_turn = meat_consumed
    park._trash_consumed_this_turn = trash_consumed

    # 연속 쓰레기 턴 판정: 콘페이토나 고기를 소비하지 않았으면 증가
    if not konpeito_consumed and not meat_consumed:
        park.consecutive_trash_turns += 1
    else:
        park.consecutive_trash_turns = 0

    # 사기 조정
    if park.consecutive_trash_turns >= 3:
        park.morale = max(0, park.morale + GC.MORALE_TRASH_PENALTY)
        add_event(park, 'morale',
                  DLG.get_random_dialogue(DLG.FOOD_TRASH_ONLY))

    # 기아 판정 (식량 부족 시)
    if shortage > 0:
        _process_starvation(park, shortage)


def _process_starvation(park, shortage):
    """기아 처리: 식량 부족 시 약한 개체부터 사망 [v1.7.0] 경호실장 사망 추가
    [v1.7.0] shortage 탕감량을 config 상수와 동기화하여 무적 생존 Exploit 방지
    (audit_report_33.md [LOGIC-F008])"""
    add_event(park, 'starve', DLG.get_random_dialogue(DLG.FOOD_STARVING))

    # 부족한 NP만큼 개체 사망 (약한 순서: 저실장 → 자실장 → 성체 → 경호실장)
    while shortage > 0:
        if park.baby_count > 0:
            park.baby_count -= 1
            shortage -= GC.NP_PER_BABY
        elif park.child_count > 0:
            park.child_count -= 1
            shortage -= GC.NP_PER_CHILD
            add_event(park, 'starve', DLG.get_random_dialogue(DLG.FOOD_DEATH))
        elif park.adult_count > 0:
            park.adult_count -= 1
            # [v1.7.0] 방어 배치 동기화: 성체 감소 시 defending_adults도 clamping
            # (audit_report_35.md [STATE-F011])
            park.defending_adults = min(park.defending_adults, park.adult_count)
            shortage -= GC.NP_PER_ADULT
            add_event(park, 'starve', DLG.get_random_dialogue(DLG.FOOD_DEATH))
        elif park.guard_count > 0:
            # [v1.7.0] 경호실장 사망 로직 추가 (audit_report_4.md [MATH-F001])
            park.guard_count -= 1
            # [v1.7.0] 방어 배치 동기화: 경호 감소 시 defending_guards도 clamping
            # (audit_report_35.md [STATE-F011])
            park.defending_guards = min(park.defending_guards, park.guard_count)
            shortage -= GC.NP_PER_GUARD  # [v1.7.0] config 상수 동기화 (audit_report_33.md [LOGIC-F008])
            add_event(park, 'starve', DLG.get_random_dialogue(DLG.FOOD_DEATH))
        else:
            # 모든 실장석이 죽으면 보스에게 피해
            park.boss_hp -= 10
            shortage = 0
            if park.boss_hp <= 0:
                park.is_destroyed = True
                add_event(park, 'gameover',
                          "👑 보스실장이... 굶어서... 죽었는 데스... 공원은 끝난 데스...")


def _process_building(park):
    """건설 대기열 처리"""
    for build in park.build_queue:
        build.turns_remaining -= 1
        if build.turns_remaining <= 0:
            # 건설 완료!
            btype = build.building_type
            bldg = GC.BUILDINGS.get(btype, {})

            # 시설 수 증가
            if btype == 'cardboard_house':
                park.cardboard_houses += 1
                park.population_cap += bldg['effect'].get('population_cap', 0)
            elif btype == 'unchi_hole':
                park.unchi_holes += 1
            elif btype == 'storage_hole':
                park.storage_holes += 1
                park.konpeito_cap += bldg['effect'].get('konpeito_cap', 0)
                park.trash_food_cap += bldg['effect'].get('trash_food_cap', 0)
                park.material_cap += bldg['effect'].get('material_cap', 0)
            elif btype == 'wall':
                park.walls += 1
            elif btype == 'watchtower':
                park.watchtowers += 1

            add_event(park, 'build',
                      f"🔨 {bldg.get('emoji', '🏗️')}{bldg.get('name', btype)} 완성! "
                      + DLG.get_random_dialogue(DLG.BUILD_COMPLETE))
            db.session.delete(build)


def _process_training(park):
    """훈련 대기열 처리"""
    for train in park.train_queue:
        train.turns_remaining -= 1
        if train.turns_remaining <= 0:
            # 훈련 완료 - 성공/실패 판정
            if random.random() < GC.TRAIN_SUCCESS_RATE:
                park.guard_count += 1
                add_event(park, 'train',
                          f"⚔️ 훈련 성공! " + DLG.get_random_dialogue(DLG.TRAIN_SUCCESS))
            else:
                # 실패 시 성체실장으로 복귀
                park.adult_count += 1
                add_event(park, 'train',
                          f"📖 훈련 실패... " + DLG.get_random_dialogue(DLG.TRAIN_FAIL))
            db.session.delete(train)


def _process_growth(park):
    """자실장 → 성체실장 성장 판정 [v1.7.0] 인구 상한 제거 (Zero-Sum)"""
    new_adults = 0
    remaining_children = park.child_count

    for _ in range(park.child_count):
        if random.random() < GC.CHILD_TO_ADULT_CHANCE:
            # [v1.7.0] 성장은 총 인구 변화가 없는 Zero-Sum 연산이므로
            # population_cap의 영향을 받지 않아야 함 (audit_report_4.md [MATH-F002])
            new_adults += 1
            remaining_children -= 1

    if new_adults > 0:
        park.child_count = remaining_children
        park.adult_count += new_adults
        add_event(park, 'growth',
                  f"🐣 자실장 {new_adults}마리가 성체실장으로 성장한 데스!")


def _process_unchi_breeding(park):
    """운치굴에서 저실장 자동 증가"""
    if park.unchi_holes <= 0:
        return

    new_babies = 0
    for _ in range(park.unchi_holes):
        new_babies += random.randint(1, 2)

    # 운치굴 수용 한도 확인
    baby_cap = park.baby_cap
    space = max(0, baby_cap - park.baby_count)
    actual_new = min(new_babies, space)

    if actual_new > 0:
        park.baby_count += actual_new
        add_event(park, 'breeding',
                  f"🕳️ 운치굴에서 저실장 {actual_new}마리가 자란 데스!")


def _process_overcrowding(park):
    """수용 인원 초과 판정 [v1.7.0] 성체/경호실장도 탈주 대상에 포함 (audit_report_27.md [LOGIC-F001])"""
    excess = park.total_population - park.population_cap
    if excess <= 0:
        return

    fled_children = 0
    fled_adults = 0
    fled_guards = 0

    # 자실장부터 탈주
    while excess > 0 and park.child_count > 0:
        park.child_count -= 1
        excess -= 1
        fled_children += 1

    # 자실장이 부족하면 성체실장 탈주
    while excess > 0 and park.adult_count > 0:
        park.adult_count -= 1
        # [v1.7.0] 방어 배치 동기화: 성체 감소 시 defending_adults도 clamping
        # (audit_report_35.md [STATE-F011])
        park.defending_adults = min(park.defending_adults, park.adult_count)
        excess -= 1
        fled_adults += 1

    # 성체도 부족하면 경호실장 탈주
    while excess > 0 and park.guard_count > 0:
        park.guard_count -= 1
        # [v1.7.0] 방어 배치 동기화: 경호 감소 시 defending_guards도 clamping
        # (audit_report_35.md [STATE-F011])
        park.defending_guards = min(park.defending_guards, park.guard_count)
        excess -= 1
        fled_guards += 1

    total_fled = fled_children + fled_adults + fled_guards
    if total_fled > 0:
        msg_parts = []
        if fled_children > 0:
            msg_parts.append(f"👶자실장 {fled_children}마리")
        if fled_adults > 0:
            msg_parts.append(f"🧑성체 {fled_adults}마리")
        if fled_guards > 0:
            msg_parts.append(f"⚔️경호 {fled_guards}마리")
        add_event(park, 'overcrowd',
                  f"🏠 수용 초과! {', '.join(msg_parts)}가 탈주! "
                  + DLG.get_random_dialogue(DLG.OVERCROWDED))


# ============================================================
# [v1.1.0] Phase 7: 잔혹 컨텐츠 턴 처리 함수
# ============================================================

def _process_disasters(park):
    """[v1.1.0] 재해 & 환경 이벤트 (턴마다 확률 판정)"""
    if park.is_destroyed:
        return

    # 1. 폭우 - 골판지집 1동 파괴
    if random.random() < GC.DISASTER_RAIN_CHANCE and park.cardboard_houses > 0:
        park.cardboard_houses -= 1
        park.population_cap = max(5, park.population_cap - 15)
        add_event(park, 'disaster',
                  f"🌧️ 폭우! 골판지집 1동 파괴! (수용 -15) "
                  + DLG.get_random_dialogue(DLG.DISASTER_RAIN))

    # 2. 한파 - 저실장/자실장 동사
    if random.random() < GC.DISASTER_COLD_CHANCE:
        baby_dead = int(park.baby_count * 0.3)
        child_dead = int(park.child_count * 0.1)
        # 방벽이 있으면 피해 50% 감소
        if park.walls > 0:
            baby_dead = baby_dead // 2
            child_dead = child_dead // 2
        park.baby_count = max(0, park.baby_count - baby_dead)
        park.child_count = max(0, park.child_count - child_dead)
        if baby_dead + child_dead > 0:
            add_event(park, 'disaster',
                      f"❄️ 한파! 🐛저실장 -{baby_dead}, 👶자실장 -{child_dead} 동사! "
                      + DLG.get_random_dialogue(DLG.DISASTER_COLD))

    # 3. 살충제 - 운치굴 저실장 50% 사망
    if random.random() < GC.DISASTER_PESTICIDE_CHANCE and park.unchi_holes > 0:
        baby_dead = int(park.baby_count * 0.5)
        park.baby_count = max(0, park.baby_count - baby_dead)
        if baby_dead > 0:
            add_event(park, 'disaster',
                      f"☠️ 살충제! 🐛저실장 -{baby_dead} 사망! "
                      + DLG.get_random_dialogue(DLG.DISASTER_PESTICIDE))

    # 4. 쥐떼 - 식량30% + 저실장20%
    if random.random() < GC.DISASTER_RATS_CHANCE:
        food_lost = int(park.trash_food * 0.3)
        baby_dead = int(park.baby_count * 0.2)
        park.trash_food = max(0, park.trash_food - food_lost)
        park.baby_count = max(0, park.baby_count - baby_dead)
        if food_lost + baby_dead > 0:
            add_event(park, 'disaster',
                      f"🐀 쥐떼! 🗑️음쓰 -{food_lost}, 🐛저실장 -{baby_dead}! "
                      + DLG.get_random_dialogue(DLG.DISASTER_RATS))

    # 5. 고양이 - 자실장 1~3마리 사망
    if random.random() < GC.DISASTER_CAT_CHANCE and park.child_count > 0:
        killed = min(random.randint(1, 3), park.child_count)
        park.child_count -= killed
        add_event(park, 'disaster',
                  f"🐱 고양이 습격! 👶자실장 -{killed} 사망! "
                  + DLG.get_random_dialogue(DLG.DISASTER_CAT))

    # 6. 쓰레기장 철거 - 3턴 동안 채집 -50%
    if random.random() < GC.DISASTER_DUMP_REMOVAL_CHANCE and park.gather_penalty_turns <= 0:
        park.gather_penalty_turns = 3
        add_event(park, 'disaster',
                  "🚛 쓰레기장 철거! 3턴간 채집 수확 50% 감소! "
                  + DLG.get_random_dialogue(DLG.DISASTER_DUMP_REMOVAL))


def _process_cannibalism(park):
    """[v1.1.0] 자동 카니발리즘 - 기아 상태에서 경호가 자실장을 강제 포식"""
    if not GC.CANNIBALISM_AUTO_ENABLED or park.is_destroyed:
        return

    # 식량이 바닥났을 때만 발동
    if park.trash_food > 0 or park.meat_stock > 0 or park.konpeito > 0:
        return

    # 경호실장의 자실장 강제 포식 (경호 1마리당 20% 확률)
    eaten = 0
    for _ in range(park.guard_count):
        if random.random() < GC.CANNIBALISM_GUARD_FEED_CHANCE and park.child_count > 0:
            park.child_count -= 1
            park.meat_stock += 1  # 고기로 전환
            eaten += 1

    if eaten > 0:
        add_event(park, 'cannibalism',
                  f"🩸 경호실장이 자실장 {eaten}마리를 강제 포식! "
                  + DLG.get_random_dialogue(DLG.CANNIBALISM_GUARD_PREDATION))
        # 목격 사기 감소
        park.morale = max(0, park.morale + GC.CANNIBALISM_MORALE_PENALTY)
        add_event(park, 'morale', DLG.get_random_dialogue(DLG.CANNIBALISM_WITNESS))


def _process_disease(park):
    """[v1.1.0] 질병 시스템 - 과밀 시 전염병 발생/진행"""
    if park.is_destroyed:
        return

    # 이미 질병 중이면 진행
    if park.disease_turns > 0:
        park.disease_turns -= 1
        # 매 턴 피해
        baby_dead = max(1, int(park.baby_count * GC.DISEASE_BABY_DEATH_RATE))
        child_dead = max(0, int(park.child_count * GC.DISEASE_CHILD_DEATH_RATE))
        park.baby_count = max(0, park.baby_count - baby_dead)
        park.child_count = max(0, park.child_count - child_dead)
        if park.disease_turns > 0:
            add_event(park, 'disease',
                      f"🤢 전염병 진행 중! 🐛-{baby_dead} 👶-{child_dead} (남은 {park.disease_turns}턴) "
                      + DLG.get_random_dialogue(DLG.DISEASE_PROGRESS))
        else:
            add_event(park, 'disease',
                      "🤢 전염병이 자연 소멸... 많은 피해를 입은 데스...")
        return

    # 새 질병 발생 판정: 수용 90% 초과 + 운치굴 3개 이상
    if park.total_population <= 0:
        return
    occupancy = park.total_population / max(1, park.population_cap)
    if occupancy >= GC.DISEASE_OVERCROWD_THRESHOLD and park.unchi_holes >= 3:
        if random.random() < GC.DISEASE_CHANCE_PER_TURN:
            park.disease_turns = random.randint(*GC.DISEASE_DURATION)
            add_event(park, 'disease',
                      f"🤢 전염병 발생! {park.disease_turns}턴 동안 지속! "
                      + DLG.get_random_dialogue(DLG.DISEASE_OUTBREAK))


def _process_human_events(park):
    """[v1.1.0] NPC 악행 이벤트 (인간과의 상호작용)"""
    if park.is_destroyed:
        return

    # 1. 학대자 인간 (2%) - 자실장 3~5 납치
    if random.random() < GC.NPC_EVENT_ABUSER_CHANCE and park.child_count > 0:
        taken = min(random.randint(3, 5), park.child_count)
        park.child_count -= taken
        park.morale = max(0, park.morale - 8)
        add_event(park, 'human_evil',
                  f"😈 학대자 출현! 👶자실장 {taken}마리 납치! "
                  + DLG.get_random_dialogue(DLG.HUMAN_ABUSER))
        return  # 한 턴에 인간 이벤트 1회만

    # 2. 실험체 포획 (1%) - 성체 1마리
    if random.random() < GC.NPC_EVENT_EXPERIMENT_CHANCE and park.adult_count > 1:
        park.adult_count -= 1
        # [v1.7.0] 방어 배치 동기화: 성체 감소 시 defending_adults도 clamping
        # (audit_report_35.md [STATE-F011])
        park.defending_adults = min(park.defending_adults, park.adult_count)
        park.morale = max(0, park.morale - 10)
        add_event(park, 'human_evil',
                  "🔬 실험체 포획! 🧑성체 1마리 사라짐! "
                  + DLG.get_random_dialogue(DLG.HUMAN_EXPERIMENT))
        return

    # 3. 어린이 장난 (4%) - 골판지집 피해
    if random.random() < GC.NPC_EVENT_KIDS_CHANCE and park.cardboard_houses > 0:
        # 50% 확률로 골판지집 파괴, 50%는 피해만
        if random.random() < 0.5:
            park.cardboard_houses -= 1
            park.population_cap = max(5, park.population_cap - 15)
            add_event(park, 'human_evil',
                      "👦💦 어린이 장난! 골판지집 1동 파괴! "
                      + DLG.get_random_dialogue(DLG.HUMAN_KIDS))
        else:
            park.morale = max(0, park.morale - 5)
            add_event(park, 'human_evil',
                      "👦💦 어린이 장난! 물벼락으로 사기 하락! "
                      + DLG.get_random_dialogue(DLG.HUMAN_KIDS))
        return

    # 4. 착한 인간 (5%) - 선물!
    if random.random() < GC.NPC_EVENT_KINDNESS_CHANCE:
        gift_konpeito = random.randint(3, 5)
        gift_trash = random.randint(10, 20)
        park.konpeito = min(park.konpeito_cap, park.konpeito + gift_konpeito)
        park.trash_food = min(park.trash_food_cap, park.trash_food + gift_trash)
        park.morale = min(100, park.morale + 10)
        add_event(park, 'human_good',
                  f"😇 착한 인간! 🍬+{gift_konpeito} 🗑️+{gift_trash}! "
                  + DLG.get_random_dialogue(DLG.HUMAN_KINDNESS))
        return

    # 5. 펫샵 포획 (1%) - 자실장 2마리
    if random.random() < GC.NPC_EVENT_PETSHOP_CHANCE and park.child_count >= 2:
        park.child_count -= 2
        add_event(park, 'human_evil',
                  "🏪 펫샵 포획! 👶자실장 2마리 납치! "
                  + DLG.get_random_dialogue(DLG.HUMAN_PETSHOP))


def _process_rebellion(park):
    """[v1.1.0] 반란 & 태업 시스템"""
    if park.is_destroyed:
        return

    # 1. 자실장 탈주 (사기 20 이하)
    if park.morale <= GC.REBELLION_MORALE_THRESHOLD:
        if random.random() < GC.REBELLION_CHANCE:
            fled = max(1, int(park.child_count * GC.REBELLION_DESERTION_RATE))
            fled = min(fled, park.child_count)
            if fled > 0:
                park.child_count -= fled
                add_event(park, 'rebellion',
                          f"🏃 자실장 {fled}마리 탈주! "
                          + DLG.get_random_dialogue(DLG.REBELLION_DESERTION))

    # 2. 성체 태업 (사기 30 이하)
    if park.morale <= 30 and park.strike_turns <= 0:
        if random.random() < GC.REBELLION_ADULT_STRIKE_CHANCE:
            park.strike_turns = 2  # 2턴 동안 채집/건설 불가
            add_event(park, 'rebellion',
                      "✊ 성체 태업 발생! 2턴간 행동 제한! "
                      + DLG.get_random_dialogue(DLG.REBELLION_STRIKE))

    # 3. 경호 쿠데타 (사기 20 이하 + 보스 HP 30 이하)
    if (park.morale <= GC.REBELLION_MORALE_THRESHOLD and
            park.boss_hp <= GC.REBELLION_BOSS_HP_THRESHOLD and
            park.guard_count > 0):
        if random.random() < GC.REBELLION_GUARD_COUP_CHANCE:
            park.boss_hp = max(0, park.boss_hp - GC.REBELLION_GUARD_COUP_DAMAGE)
            # 쿠데타 참여 경호 50% 이탈
            coup_guards = max(1, park.guard_count // 2)
            park.guard_count -= coup_guards
            # [v1.7.0] 방어 배치 동기화: 경호 감소 시 defending_guards도 clamping
            # (audit_report_35.md [STATE-F011])
            park.defending_guards = min(park.defending_guards, park.guard_count)
            add_event(park, 'rebellion',
                      f"⚔️💀 쿠데타! 보스HP -{GC.REBELLION_GUARD_COUP_DAMAGE}, "
                      f"경호 {coup_guards}마리 이탈! "
                      + DLG.get_random_dialogue(DLG.REBELLION_GUARD_COUP))
            if park.boss_hp <= 0:
                park.is_destroyed = True
                add_event(park, 'gameover',
                          '👑💀 쿠데타로 보스실장 사망! 공원 멸망!')


def _process_addiction(park):
    """[v1.1.0] 콘페이토 중독 판정 [v1.7.0] 소비 여부 정확히 추적"""
    if park.is_destroyed:
        return

    # [v1.7.0] _process_food_consumption에서 설정한 실제 소비 플래그를 읽음
    # audit_report_4.md [MATH-F003], audit_report_6.md [IMP-F010]
    konpeito_consumed = getattr(park, '_konpeito_consumed_this_turn', False)
    meat_consumed = getattr(park, '_meat_consumed_this_turn', False)
    trash_consumed = getattr(park, '_trash_consumed_this_turn', False)

    # 콘페이토만 섭취했는지 판정: 콘페이토는 소비했으나 고기/쓰레기는 소비하지 않음
    # [v1.7.0] 쓰레기 소비 여부도 검증 (IMP-F010)
    if konpeito_consumed and not meat_consumed and not trash_consumed:
        park.konpeito_consecutive += 1
    else:
        # 다른 식량도 먹은 턴 또는 콘페이토 미소비
        if park.is_addicted:
            park.addiction_clean_turns += 1
        park.konpeito_consecutive = 0

    # 중독 발생 (3턴 연속 콘페이토만 섭취)
    if park.konpeito_consecutive >= GC.ADDICTION_TRIGGER_TURNS and not park.is_addicted:
        park.is_addicted = True
        park.addiction_clean_turns = 0
        add_event(park, 'addiction',
                  DLG.get_random_dialogue(DLG.ADDICTION_ONSET))

    # 중독 상태에서 콘페이토 없으면 사기 대폭 하락
    if park.is_addicted and park.konpeito <= 0:
        park.morale = max(0, park.morale + GC.ADDICTION_MORALE_PENALTY)
        add_event(park, 'addiction',
                  DLG.get_random_dialogue(DLG.ADDICTION_WITHDRAWAL))

    # 해독 (3턴 연속 콘페이토 미섭취)
    if park.is_addicted and park.addiction_clean_turns >= GC.ADDICTION_CURE_TURNS:
        park.is_addicted = False
        park.addiction_clean_turns = 0
        park.konpeito_consecutive = 0
        add_event(park, 'addiction',
                  DLG.get_random_dialogue(DLG.ADDICTION_CURED))


def _process_spy_missions(park):
    """[v1.1.0] 밀사 임무 진행 (해당 공원이 보낸 밀사 처리)
    [v1.7.0] process_turn 외부에서 별도 트랜잭션으로 실행하며,
    Park UPDATE는 ID 오름차순으로 정렬하여 교차 데드락 방지 (audit_report_22.md [DEADLOCK-F001])"""
    if park.is_destroyed:
        return

    active_missions = SpyMission.query.filter_by(
        sender_id=park.id, status='active'
    ).all()

    for mission in active_missions:
        # [v1.7.0] 원자적 턴 차감: 동시 process_turn 호출 시 중복 사보타주 방지 (audit_report_14.md [IMP-F038])
        updated = SpyMission.query.filter(
            SpyMission.id == mission.id,
            SpyMission.turns_remaining > 0
        ).update({'turns_remaining': SpyMission.turns_remaining - 1})

        if updated == 0:
            continue  # 이미 처리되었거나 turns_remaining <= 0

        db.session.refresh(mission)

        if mission.turns_remaining <= 0:
            target = db.session.get(Park, mission.target_id)
            if not target:
                continue

            # [v1.8.5] 사보타주 연산 및 TOCTOU 방지를 위해 두 공원(park, target)에 대해 ID 정렬 2중 비관적 락 획득 (audit_report_54.md [LOGIC-F021])
            lock_ids = sorted([park.id, target.id])
            Park.query.filter(Park.id.in_(lock_ids)).with_for_update().all()
            db.session.refresh(park)
            db.session.refresh(target)

            # 락 획득 후 대상 멸망 상태 재확인 (TOCTOU 방지)
            if target.is_destroyed:
                # [v1.7.0] 대상 멸망 시에도 원자적 성체 복귀 (audit_report_13.md [IMP-F033])
                Park.query.filter(Park.id == park.id).update({
                    'adult_count': Park.adult_count + 1
                })
                mission.status = 'returned'
                mission.result_message = '대상 공원이 멸망한 데스... 성체 1마리는 무사 귀환!'
                add_event(park, 'spy',
                          f"🕵️ {mission.target_id}번 공원 멸망... 밀사가 성체 1마리와 함께 귀환했는 데스!")
                db.session.commit()  # [v1.7.0] 임무 단위로 커밋하여 락 즉시 해제 (audit_report_22.md [DEADLOCK-F001])
                continue

            # 발각 판정
            detect_chance = GC.SPY_DETECTION_CHANCE
            if target.watchtowers > 0:
                detect_chance += GC.SPY_WATCHTOWER_DETECT_BONUS

            if random.random() < detect_chance:
                # 밀사 발각 → 성체 1마리 손실 (이미 파견 시 차감했으므로 추가 손실 없음)
                mission.status = 'detected'
                mission.result_message = '밀사가 발각되어 처형당했는 데스...'
                add_event(park, 'spy',
                          f"🕵️❌ {target.name}에 보낸 밀사 발각! "
                          + DLG.get_random_dialogue(DLG.SPY_DETECTED))
                # 적 공원에도 알림
                add_event(target, 'spy',
                          DLG.get_random_dialogue(DLG.SPY_ENEMY_DETECTED))
                db.session.commit()  # [v1.7.0] 임무 단위로 커밋하여 락 즉시 해제 (audit_report_22.md [DEADLOCK-F001])
            else:
                # 사보타주 성공 [v1.8.5] 비관적 락 확보 상태이므로 TOCTOU 격차를 낮출 수 있음 (audit_report_54.md [LOGIC-F021])
                food_ratio = random.uniform(*GC.SPY_SABOTAGE_FOOD_RATIO)
                food_destroyed = int(target.trash_food * food_ratio)
                baby_killed = min(GC.SPY_SABOTAGE_BABY_KILL, target.baby_count)

                # [v1.7.0] Deadlock 방지: Park UPDATE를 ID 오름차순으로 실행 (audit_report_22.md [DEADLOCK-F001])
                ids = sorted([park.id, target.id])
                for pid in ids:
                    if pid == target.id:
                        Park.query.filter(Park.id == target.id).update({
                            'trash_food': case((Park.trash_food < food_destroyed, 0), else_=Park.trash_food - food_destroyed),
                            'baby_count': case((Park.baby_count < baby_killed, 0), else_=Park.baby_count - baby_killed),
                        })
                    else:
                        # [v1.7.0] 원자적 성체 복귀 (audit_report_13.md [IMP-F033])
                        Park.query.filter(Park.id == park.id).update({
                            'adult_count': Park.adult_count + 1
                        })

                mission.status = 'success'
                mission.result_message = (
                    f'{target.name}: 🗑️-{food_destroyed}, 🐛-{baby_killed} 파괴!'
                )
                add_event(park, 'spy',
                          f"🕵️✅ {target.name} 사보타주 성공! "
                          f"🗑️-{food_destroyed} 🐛-{baby_killed}! "
                          + DLG.get_random_dialogue(DLG.SPY_SUCCESS))
                add_event(target, 'sabotage',
                          f"🕵️ 밀사 사보타주 피해! 🗑️-{food_destroyed} 🐛-{baby_killed}!")
                db.session.commit()  # [v1.7.0] 임무 단위로 커밋하여 락 즉시 해제 (audit_report_22.md [DEADLOCK-F001])

    # [v1.7.0] 귀환한 밀사로 인한 인구 초과 방지: 모든 임무 처리 후
    # [v1.8.9] Lost Update 경쟁 상태 차단: 단순 refresh 대신 with_for_update() 비관적 락을 획득 후 refresh 및 과밀도 처리 (audit_report_59.md)
    Park.query.filter(Park.id == park.id).with_for_update().first()
    db.session.refresh(park)
    _process_overcrowding(park)
    db.session.commit()


def action_cure_disease(park):
    """[v1.1.0] 질병 치료 행동 (콘페이토 5개 소비) [v1.7.0] 원자적 UPDATE (audit_report_18.md [IMP-F046])"""
    if park.disease_turns <= 0:
        return False, {}, ['질병이 없는 데스!']

    # [v1.7.0] 원자적 콘페이토 차감 + 질병 턴 초기화 (audit_report_18.md [IMP-F046])
    updated = Park.query.filter(
        Park.id == park.id,
        Park.konpeito >= GC.DISEASE_CURE_KONPEITO
    ).update({
        'konpeito': Park.konpeito - GC.DISEASE_CURE_KONPEITO,
        'disease_turns': 0,
    })

    if updated == 0:
        return False, {}, [f'콘페이토가 부족한 데스! {GC.DISEASE_CURE_KONPEITO}개 필요한 데스!']

    db.session.refresh(park)
    messages = DLG.get_random_dialogues(DLG.DISEASE_CURED, 1)
    add_event(park, 'disease', '💊 콘페이토 치료! 전염병 종료!')
    db.session.commit()
    return True, {'cured': True}, messages


def action_spy(park, target_id):
    """[v1.1.0] 밀사 파견 행동 (1AP + 성체 1마리) [v1.7.0] AP 소비는 consume_turn에서 처리 (audit_report_9.md [IMP-F018])"""
    # [v1.7.0] AP 체크/소비는 spy_send 라우트의 consume_turn()에서 처리됨

    if park.adult_count < 2:  # 최소 1마리는 남겨야 함
        return False, {}, ['성체가 부족한 데스! 최소 2마리 이상 필요한 데스!']

    target = db.session.get(Park, target_id)
    if not target or target.is_destroyed or target.id == park.id:
        return False, {}, ['유효하지 않은 대상인 데스!']

    # [v1.7.0] 동맹 차단: 동맹 관계인 대상에게는 밀사 파견 불가 (audit_report_31.md [LOGIC-F006])
    from app.models import Diplomacy
    is_ally = Diplomacy.query.filter(
        ((Diplomacy.park_a_id == park.id) & (Diplomacy.park_b_id == target.id)) |
        ((Diplomacy.park_a_id == target.id) & (Diplomacy.park_b_id == park.id)),
        Diplomacy.relation_type == 'ally',
        Diplomacy.status == 'active'
    ).first()
    if is_ally:
        return False, {}, [f'동맹인 {target.name}에게는 밀사를 보낼 수 없는 데스!']

    # [v1.7.0] 원자적 성체 차감 + 방어 배치 동기화: 동시 밀사 Double Spend 및
    # Phantom Defense Exploit 방지 (audit_report_13.md [IMP-F033], audit_report_35.md [STATE-F011])
    updated = Park.query.filter(
        Park.id == park.id,
        Park.adult_count >= 2
    ).update({
        'adult_count': Park.adult_count - 1,
        'defending_adults': case(
            (Park.defending_adults > Park.adult_count - 1, Park.adult_count - 1),
            else_=Park.defending_adults
        )
    })

    if updated == 0:
        return False, {}, ['성체가 부족한 데스! 최소 2마리 이상 필요한 데스!']

    db.session.refresh(park)

    mission = SpyMission(
        sender_id=park.id,
        target_id=target_id,
        mission_type='sabotage',
        turns_remaining=GC.SPY_RETURN_TURNS,
    )
    db.session.add(mission)

    messages = DLG.get_random_dialogues(DLG.SPY_DEPART, 1)
    add_event(park, 'spy',
              f'🕵️ {target.name}에 밀사 파견! ({GC.SPY_RETURN_TURNS}턴 후 귀환)')

    db.session.commit()
    return True, {'target': target.name, 'turns': GC.SPY_RETURN_TURNS}, messages


def create_default_park(user, name=None):
    """
    [v1.8.0] 기본 공원을 생성해주는 통합 헬퍼 함수 (audit_report_47.md [STATE-F021]).
    사용자의 공원이 유실되었을 때 복구하거나 회원가입 시 공원을 생성할 때 공통으로 호출된다.
    """
    if name is None:
        name = f"{user.username}의 공원"

    park = Park(
        user_id=user.id,
        name=name,
        is_npc=False,
        boss_hp=GC.INITIAL_BOSS_HP,
        guard_count=GC.INITIAL_GUARDS,
        adult_count=GC.INITIAL_ADULTS,
        child_count=GC.INITIAL_CHILDREN,
        baby_count=GC.INITIAL_BABIES,
        konpeito=GC.INITIAL_KONPEITO,
        trash_food=GC.INITIAL_TRASH_FOOD,
        meat_stock=GC.INITIAL_MEAT_STOCK,
        material=GC.INITIAL_MATERIAL,
        konpeito_cap=GC.INITIAL_KONPEITO_CAP,
        trash_food_cap=GC.INITIAL_TRASH_FOOD_CAP,
        material_cap=GC.INITIAL_MATERIAL_CAP,
        population_cap=GC.INITIAL_POP_CAP,
        morale=GC.INITIAL_MORALE,
        action_points=GC.ACTION_POINTS_PER_TURN,
    )
    db.session.add(park)
    db.session.commit()
    db.session.refresh(user)
    return park


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
    db.session.commit()
    db.session.refresh(park)
