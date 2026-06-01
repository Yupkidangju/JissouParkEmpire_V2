# -*- coding: utf-8 -*-
"""
실장석 공원 제국 - 게임 라우트 (game_routes.py)
[v0.1.0] 대시보드, 채집, 건설, 출산, 솎아내기, 훈련 등 게임 행동 처리.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
import threading
from datetime import datetime, timezone

from app.models import db, Park, EventLog
from app.config import GameConfig as GC
from app import game_engine
from app import dialogues as DLG
from app.i18n import get_text

game_bp = Blueprint('game', __name__, url_prefix='/game')

# [v1.8.1] [기능 삭제] _trade_create_lock (threading.Lock) 삭제
# - 삭제 사유: 다중 프로세스(Gunicorn 멀티 워커) 환경에서 프로세스 간 동시성 제어 불가하여 DB 비관적 락 및 pending_count 동시성 직렬화로 대체
# - 삭제 버전: v1.8.1 (audit_report_48.md [LOGIC-F019])


@game_bp.route('/dashboard')
@login_required
def dashboard():
    """메인 대시보드 - 공원 현황 표시"""
    park = current_user.park
    if not park:
        # [v1.8.0] 공원 부재 감지 시 자동 생성 및 복구 (audit_report_47.md [STATE-F021])
        park = game_engine.create_default_park(current_user)

    if park.is_destroyed:
        return render_template('gameover.html', park=park)

    # [v1.2.0] 접속 시 턴 자동 충전
    charged = game_engine.recharge_turns(park)
    if charged > 0:
        flash(f'⚡ {charged}턴 충전 완료! (현재 {park.turn_quota}/{GC.TURN_QUOTA_MAX})', 'info')

    # [v1.3.0] 보호 모드 체크 + 자원 리셋
    protection_reset = game_engine.check_and_enter_protection(park)
    if protection_reset:
        flash(get_text('flash.protect_activated'), 'info')

    # [v1.2.0] 턴 정보
    turn_info = game_engine.get_turn_info(park)

    # [v1.3.0] 보호 모드 정보
    protect_info = game_engine.get_protection_info(park)

    # 최근 이벤트 로그 (최신 10개)
    recent_logs = EventLog.query.filter_by(park_id=park.id) \
        .order_by(EventLog.created_at.desc()).limit(10).all()

    # 건설/훈련 대기열
    building_queue = park.build_queue
    training_queue = park.train_queue

    # 인사말
    greeting = DLG.get_random_dialogue(DLG.DASHBOARD_GREETING)

    # NPC 공원 목록 (전투/정찰용)
    other_parks = Park.query.filter(
        Park.id != park.id,
        Park.is_destroyed == False
    ).all()

    return render_template('dashboard.html',
                           park=park,
                           turn_info=turn_info,
                           protect_info=protect_info,
                           recent_logs=recent_logs,
                           building_queue=building_queue,
                           training_queue=training_queue,
                           greeting=greeting,
                           other_parks=other_parks,
                           buildings=GC.BUILDINGS,
                           GC=GC)


@game_bp.route('/gather', methods=['POST'])
@login_required
def gather():
    """채집 행동 실행 [v1.2.0] 턴 1개 소비"""
    park = current_user.park

    # [v1.5.1] int() 직접 캐스팅 → 안전 파싱 (ValueError 방지)
    num_adults = request.form.get('num_adults', 0, type=int)
    num_children = request.form.get('num_children', 0, type=int)

    # [v1.7.0] 채집 가능 여부 사전 검증: AP Blackhole 방지
    # (audit_report_43.md [LOGIC-F016])
    if num_adults < 0 or num_children < 0:
        flash(get_text('flash.gather_negative'), 'error')
        return redirect(url_for('game.dashboard'))
    if num_adults + num_children == 0:
        flash(get_text('flash.gather_no_units'), 'error')
        return redirect(url_for('game.dashboard'))

    # [v1.6.0] AP 소비 + 필요 시 턴 자동 진행 (1AP) — 검증 후 호출
    turn_ok, turn_msgs = game_engine.consume_turn(park, ap_cost=1)
    if not turn_ok:
        for msg in turn_msgs:
            flash(msg, 'error')
        return redirect(url_for('game.dashboard'))

    success, result, messages = game_engine.action_gather(
        park, num_adults, num_children
    )

    # [v1.8.2] 행동 실패 시 선행 커밋된 AP를 안전하게 복구 (보상 트랜잭션)
    # [v1.8.9] AP 블랙홀 방지: 환불 후 라우터 단에서 명시적으로 트랜잭션을 최종 커밋하여 환불 수치 영구 저장 (audit_report_58.md)
    if not success:
        game_engine.refund_ap(park, 1)
        db.session.commit()

    for msg in messages:
        flash(msg, 'success' if success else 'error')

    if success:
        flash(f"🌿 수확: 🗑️음쓰 +{result['trash']} "
              f"🍬콘페이토 +{result['konpeito']} "
              f"🧱자재 +{result['material']}", 'info')

    return redirect(url_for('game.dashboard'))


@game_bp.route('/cull', methods=['POST'])
@login_required
def cull():
    """솎아내기 (도살) 행동"""
    park = current_user.park
    target = request.form.get('target_type', '')  # 'baby' 또는 'child'
    convert = request.form.get('convert_to', '')  # 'food' 또는 'material'
    count = request.form.get('count', 1, type=int)  # [v1.5.1] 안전 파싱
    # [v1.7.0] 음수 입력 차단: 음수 count로 인구 무한 증식 Exploit 방지 (audit_report_27.md [SEC-F001])
    count = max(1, count)

    success, result, messages = game_engine.action_cull(
        park, target, convert, count
    )

    for msg in messages:
        flash(msg, 'warning' if success else 'error')

    return redirect(url_for('game.dashboard'))


@game_bp.route('/birth', methods=['POST'])
@login_required
def birth():
    """출산 행동 [v1.2.0] 턴 1개 소비"""
    park = current_user.park

    # [v1.7.0] 출산 가능 여부 사전 검증: AP Blackhole 방지
    # (audit_report_43.md [LOGIC-F016])
    if park.adult_count < 1:
        flash(get_text('flash.birth_no_adults'), 'error')
        return redirect(url_for('game.dashboard'))

    # [v1.7.0] 식량 사전 검증: AP Blackhole 방지 (audit_report_44.md [LOGIC-F017])
    if park.total_np_available < GC.BIRTH_NP_COST:
        flash(get_text('flash.birth_no_np', cost=GC.BIRTH_NP_COST), 'error')
        return redirect(url_for('game.dashboard'))

    # [v1.2.0] 턴 소비
    # [v1.6.0] AP 소비 + 필요 시 턴 자동 진행 (출산=2AP) — 검증 후 호출
    turn_ok, turn_msgs = game_engine.consume_turn(park, ap_cost=2)
    if not turn_ok:
        for msg in turn_msgs:
            flash(msg, 'error')
        return redirect(url_for('game.dashboard'))

    success, result, messages = game_engine.action_birth(park)

    # [v1.8.2] 행동 실패 시 선행 커밋된 AP를 안전하게 복구 (보상 트랜잭션)
    # [v1.8.9] AP 블랙홀 방지: 환불 후 라우터 단에서 명시적으로 트랜잭션을 최종 커밋하여 환불 수치 영구 저장 (audit_report_58.md)
    if not success:
        game_engine.refund_ap(park, 2)
        db.session.commit()

    for msg in messages:
        flash(msg, 'success' if success else 'error')

    if success:
        flash(f"🐣 태어남: 👶자실장 +{result['children']}, "
              f"🐛저실장 +{result['babies']}", 'info')

    return redirect(url_for('game.dashboard'))


@game_bp.route('/build', methods=['POST'])
@login_required
def build():
    """건설 행동 [v1.2.0] 턴 1개 소비"""
    park = current_user.park
    building_type = request.form.get('building_type', '')

    # [v1.7.0] 건설 타입 유효성 사전 검증: AP Blackhole 방지
    # (audit_report_43.md [LOGIC-F016])
    if building_type not in GC.BUILDINGS:
        flash(get_text('flash.invalid_building'), 'error')
        return redirect(url_for('game.dashboard'))

    # [v1.7.0] 자재 사전 검증: AP Blackhole 방지 (audit_report_44.md [LOGIC-F017])
    bldg = GC.BUILDINGS[building_type]
    if park.material < bldg['material_cost']:
        flash(get_text('flash.build_no_material', cost=bldg['material_cost']), 'error')
        return redirect(url_for('game.dashboard'))

    # [v1.6.0] AP 소비 + 필요 시 턴 자동 진행 (1AP) — 검증 후 호출
    turn_ok, turn_msgs = game_engine.consume_turn(park, ap_cost=1)
    if not turn_ok:
        for msg in turn_msgs:
            flash(msg, 'error')
        return redirect(url_for('game.dashboard'))

    success, result, messages = game_engine.action_build(park, building_type)

    # [v1.8.2] 행동 실패 시 선행 커밋된 AP를 안전하게 복구 (보상 트랜잭션)
    # [v1.8.9] AP 블랙홀 방지: 환불 후 라우터 단에서 명시적으로 트랜잭션을 최종 커밋하여 환불 수치 영구 저장 (audit_report_58.md)
    if not success:
        game_engine.refund_ap(park, 1)
        db.session.commit()

    for msg in messages:
        flash(msg, 'success' if success else 'error')

    return redirect(url_for('game.dashboard'))


@game_bp.route('/train', methods=['POST'])
@login_required
def train():
    """훈련 행동 [v1.2.0] 턴 1개 소비"""
    park = current_user.park

    # [v1.7.0] 훈련 가능 여부 사전 검증: AP Blackhole 방지
    # (audit_report_43.md [LOGIC-F016])
    if park.adult_count < 1:
        flash(get_text('flash.train_no_adults'), 'error')
        return redirect(url_for('game.dashboard'))

    # [v1.7.0] 식량 사전 검증: AP Blackhole 방지 (audit_report_44.md [LOGIC-F017])
    if park.total_np_available < GC.TRAIN_NP_COST:
        flash(get_text('flash.train_no_np', cost=GC.TRAIN_NP_COST), 'error')
        return redirect(url_for('game.dashboard'))

    # [v1.6.0] AP 소비 + 필요 시 턴 자동 진행 (1AP) — 검증 후 호출
    turn_ok, turn_msgs = game_engine.consume_turn(park, ap_cost=1)
    if not turn_ok:
        for msg in turn_msgs:
            flash(msg, 'error')
        return redirect(url_for('game.dashboard'))

    success, result, messages = game_engine.action_train(park)

    # [v1.8.2] 행동 실패 시 선행 커밋된 AP를 안전하게 복구 (보상 트랜잭션)
    # [v1.8.9] AP 블랙홀 방지: 환불 후 라우터 단에서 명시적으로 트랜잭션을 최종 커밋하여 환불 수치 영구 저장 (audit_report_58.md)
    if not success:
        game_engine.refund_ap(park, 1)
        db.session.commit()

    for msg in messages:
        flash(msg, 'success' if success else 'error')

    return redirect(url_for('game.dashboard'))


@game_bp.route('/attack', methods=['POST'])
@login_required
def attack():
    """침공 행동 [v1.2.0] 턴 1개 소비 [v0.4.0] 동맹 차단 + 적대 약탈 보너스"""
    park = current_user.park

    # [v1.5.1] 안전 파싱
    target_id = request.form.get('target_id', 0, type=int)
    send_guards = request.form.get('send_guards', 0, type=int)
    send_adults = request.form.get('send_adults', 0, type=int)
    boss_joins = request.form.get('boss_joins') == 'on'

    target = db.session.get(Park, target_id)
    if not target or target.is_destroyed or target.id == park.id:
        flash(get_text('flash.invalid_target'), 'error')
        return redirect(url_for('game.dashboard'))

    # [v1.3.0] 보호 모드 - 자기가 보호 중이면 침공 불가
    if game_engine.is_protected(park):
        flash(f'🛡️ 보호 모드 중에는 침공할 수 없는 데스! '
              f'(경호 {GC.PROTECT_GUARD_MIN}↑ & 성체 {GC.PROTECT_ADULT_MIN}↑ 필요)', 'error')
        return redirect(url_for('game.dashboard'))

    # [v1.3.0] 보호 모드 - 보호 대상 침공 불가
    if game_engine.is_protected(target):
        flash(get_text('flash.protect_target', name=target.name), 'error')
        return redirect(url_for('game.dashboard'))

    # [v0.4.0] 동맹 차단: 동맹인 상대는 침공 불가
    from app.models import Diplomacy
    is_ally = Diplomacy.query.filter(
        ((Diplomacy.park_a_id == park.id) & (Diplomacy.park_b_id == target.id)) |
        ((Diplomacy.park_a_id == target.id) & (Diplomacy.park_b_id == park.id)),
        Diplomacy.relation_type == 'ally',
        Diplomacy.status == 'active'
    ).first()
    if is_ally:
        flash(get_text('flash.ally_no_attack', name=target.name), 'error')
        return redirect(url_for('game.dashboard'))

    # 출정 인원 검증
    if send_guards + send_adults == 0 and not boss_joins:
        flash(get_text('flash.attack_min_unit'), 'error')
        return redirect(url_for('game.dashboard'))

    # [v1.7.0] AP 소비는 모든 검증 통과 후에 수행: AP Blackhole 방지
    # (audit_report_43.md [LOGIC-F016])
    turn_ok, turn_msgs = game_engine.consume_turn(park, ap_cost=2)
    if not turn_ok:
        for msg in turn_msgs:
            flash(msg, 'error')
        return redirect(url_for('game.dashboard'))

    from app.battle_engine import execute_battle
    won, loot, messages = execute_battle(park, target,
                                          send_guards=send_guards,
                                          send_adults=send_adults,
                                          boss_joins=boss_joins)

    # [v1.8.2] 가용 유닛 부족 등으로 전투 무산 시 이미 차감된 2AP 환불 (보상 트랜잭션)
    if not won and len(messages) == 1 and messages[0] == "아무도 안 보내면 침공할 수 없는 데스!":
        game_engine.refund_ap(park, 2)

    # [v1.7.0] execute_battle 내 원자적 UPDATE로 인해 방어자 메모리 객체가 stale됨 — 갱신 필요 (audit_report_10.md [IMP-F022])
    db.session.refresh(target)

    # [v1.7.0] 전투 결과 commit (audit_report_10.md [IMP-F022])
    db.session.commit()

    for msg in messages:
        if won:
            flash(msg, 'success')
        else:
            # [v1.8.2] 전투 무산 실패인 경우 'error'로 분류하고, 정상적인 전투 패배는 'warning'으로 표시
            if len(messages) == 1 and messages[0] == "아무도 안 보내면 침공할 수 없는 데스!":
                flash(msg, 'error')
            else:
                flash(msg, 'warning')

    if won:
        flash(get_text('flash.attack_win', konpeito=loot['konpeito'], trash=loot['trash'],
              material=loot['material'], babies=loot['babies'], children=loot['children']), 'info')

    return redirect(url_for('game.dashboard'))


@game_bp.route('/defend', methods=['POST'])
@login_required
def defend():
    """방어 배치 행동 (1 AP) [v1.7.0] consume_turn 기반 AP 관리 (audit_report_9.md [IMP-F019])"""
    park = current_user.park
    # [v1.5.1] 안전 파싱 [v1.7.0] 음수 입력 차단 (audit_report_7.md [IMP-F012], audit_report_8.md [IMP-F017])
    num_guards = max(0, request.form.get('num_guards', 0, type=int))
    num_adults = max(0, request.form.get('num_adults', 0, type=int))

    # [v1.7.0] 모든 검증 통과 후에 AP 소비: AP Blackhole 방지
    # (audit_report_43.md [LOGIC-F016])
    if num_guards > park.guard_count or num_adults > park.adult_count:
        flash(get_text('flash.defend_insufficient'), 'error')
        return redirect(url_for('game.dashboard'))

    turn_ok, turn_msgs = game_engine.consume_turn(park, ap_cost=1)
    if not turn_ok:
        for msg in turn_msgs:
            flash(msg, 'error')
        return redirect(url_for('game.dashboard'))

    # [v1.7.0] 원자적 방어 배치 + DB 클램핑: consume_turn() 커밋 후 락 해제로
    # 인해 발생하는 TOCTOU 레이스 컨디션 방지 (audit_report_40.md [STATE-F013])
    # DB의 실제 guard_count/adult_count를 기준으로 defending_*를 클램핑
    Park.query.filter(Park.id == park.id).update({
        'defending_guards': case(
            (Park.guard_count < num_guards, Park.guard_count), else_=num_guards
        ),
        'defending_adults': case(
            (Park.adult_count < num_adults, Park.adult_count), else_=num_adults
        )
    })
    db.session.commit()

    flash(get_text('flash.defend_deploy', guards=num_guards, adults=num_adults), 'success')
    return redirect(url_for('game.dashboard'))


@game_bp.route('/battle-logs')
@login_required
def battle_logs():
    """전투 기록 조회"""
    park = current_user.park
    from app.models import BattleLog

    logs = BattleLog.query.filter(
        db.or_(BattleLog.attacker_id == park.id, BattleLog.defender_id == park.id)
    ).order_by(BattleLog.created_at.desc()).limit(20).all()

    return render_template('battle_logs.html', park=park, logs=logs)


@game_bp.route('/debug/next-turn', methods=['POST'])
@login_required
def debug_next_turn():
    """디버그: 턴 강제 실행 (개발 편의용)"""
    from flask import current_app
    from app.turn_scheduler import force_process_turn

    # [v1.5.1] 보안: DEBUG 모드 전용 가드 — 프로덕션에서 백도어 차단
    if not current_app.config.get('DEBUG', False):
        flash('디버그 모드가 아닌 데스! 이 기능은 사용할 수 없는 데스!', 'error')
        return redirect(url_for('game.dashboard'))

    park = current_user.park
    force_process_turn(current_app._get_current_object(), park.id)
    flash(get_text('flash.debug_turn', turn=park.turn_count), 'info')
    return redirect(url_for('game.dashboard'))


@game_bp.route('/restart', methods=['POST'])
@login_required
def restart():
    """게임오버 후 재시작 - 멸망한 공원을 삭제하고 새 공원 생성"""
    park = current_user.park

    if not park or not park.is_destroyed:
        flash(get_text('flash.restart_not_destroyed'), 'warning')
        return redirect(url_for('game.dashboard'))

    # 기존 공원의 정보 보존
    old_name = park.name

    # [v1.8.0] 단일 트랜잭션(Atomic)으로 묶어 기존 삭제와 새 생성의 정합성 보장 (audit_report_47.md [STATE-F021])
    db.session.delete(park)
    game_engine.create_default_park(current_user)

    flash(get_text('flash.restart_success', name=old_name), 'success')
    return redirect(url_for('game.dashboard'))


@game_bp.route('/api/park-status')
@login_required
def park_status():
    """AJAX 공원 상태 조회 API"""
    park = current_user.park
    if not park:
        return jsonify({'error': get_text('flash.no_park')}), 404
    return jsonify(park.to_dict())


# ============================================================
# [v0.4.0] Phase 5: 실시간 알림 API
# ============================================================

@game_bp.route('/api/notifications')
@login_required
def notifications():
    """
    알림 API - 최근 이벤트 중 중요 알림(침공, 교역, 외교) 반환.
    클라이언트가 last_id를 전달하면 그 이후의 알림만 반환.
    """
    park = current_user.park
    if not park:
        return jsonify({'notifications': []})

    last_id = request.args.get('last_id', 0, type=int)

    # 중요 이벤트 타입만 필터 (battle, trade, diplomacy)
    important_types = ['battle', 'trade', 'diplomacy']
    events = EventLog.query.filter(
        EventLog.park_id == park.id,
        EventLog.id > last_id,
        EventLog.event_type.in_(important_types)
    ).order_by(EventLog.id.asc()).limit(10).all()

    notifications = []
    for evt in events:
        notifications.append({
            'id': evt.id,
            'type': evt.event_type,
            'message': evt.message,
            'turn': evt.turn_number,
        })

    return jsonify({'notifications': notifications})


@game_bp.route('/ranking')
@login_required
def ranking():
    """랭킹 페이지 - 전투력/인구/승수/자원 순위 [v1.7.0] N+1 쿼리 최적화 (audit_report_16.md [ARCH-F005])"""
    from app.models import BattleLog
    from sqlalchemy import func

    park = current_user.park
    sort_by = request.args.get('sort', 'power')

    # 정렬 기준별 라벨
    sort_labels = {
        'power': '⚔️ 전투력',
        'population': '👥 인구',
        'wins': '🏆 승수',
        'resources': '💰 자원'
    }
    sort_label = sort_labels.get(sort_by, '⚔️ 전투력')

    # 모든 비멸망 공원 조회
    all_parks = Park.query.filter_by(is_destroyed=False).all()

    # [v1.7.0] N+1 최적화: 배치 집계 쿼리 4개로 승/패 수 일괄 조회
    park_ids = [p.id for p in all_parks]
    if park_ids:
        attacker_wins = dict(db.session.query(
            BattleLog.attacker_id, func.count(BattleLog.id)
        ).filter(BattleLog.attacker_id.in_(park_ids), BattleLog.result == 'win').group_by(BattleLog.attacker_id).all())
        defender_wins = dict(db.session.query(
            BattleLog.defender_id, func.count(BattleLog.id)
        ).filter(BattleLog.defender_id.in_(park_ids), BattleLog.result == 'lose').group_by(BattleLog.defender_id).all())
        attacker_losses = dict(db.session.query(
            BattleLog.attacker_id, func.count(BattleLog.id)
        ).filter(BattleLog.attacker_id.in_(park_ids), BattleLog.result == 'lose').group_by(BattleLog.attacker_id).all())
        defender_losses = dict(db.session.query(
            BattleLog.defender_id, func.count(BattleLog.id)
        ).filter(BattleLog.defender_id.in_(park_ids), BattleLog.result == 'win').group_by(BattleLog.defender_id).all())
    else:
        attacker_wins = defender_wins = attacker_losses = defender_losses = {}

    win_counts = {}
    loss_counts = {}
    for p in all_parks:
        win_counts[p.id] = attacker_wins.get(p.id, 0) + defender_wins.get(p.id, 0)
        loss_counts[p.id] = attacker_losses.get(p.id, 0) + defender_losses.get(p.id, 0)

    # NPC 성격 이모지
    personality_emojis = {
        'aggressive': '🗡️',
        'defensive': '🛡️',
        'peaceful': '🌿',
        'cunning': '🎭',
        'berserk': '💀',
    }

    # 랭킹 데이터 조립
    rankings = []
    for p in all_parks:
        rankings.append({
            'park': p,
            'wins': win_counts.get(p.id, 0),
            'losses': loss_counts.get(p.id, 0),
            'personality_emoji': personality_emojis.get(p.npc_personality, ''),
        })

    # 정렬
    if sort_by == 'power':
        rankings.sort(key=lambda x: x['park'].total_combat_power, reverse=True)
    elif sort_by == 'population':
        rankings.sort(key=lambda x: x['park'].total_population, reverse=True)
    elif sort_by == 'wins':
        rankings.sort(key=lambda x: x['wins'], reverse=True)
    elif sort_by == 'resources':
        rankings.sort(key=lambda x: x['park'].total_np_available, reverse=True)

    # 내 공원 순위 계산
    power_sorted = sorted(all_parks, key=lambda p: p.total_combat_power, reverse=True)
    pop_sorted = sorted(all_parks, key=lambda p: p.total_population, reverse=True)
    my_power_rank = next((i+1 for i, p in enumerate(power_sorted) if p.id == park.id), 0)
    my_pop_rank = next((i+1 for i, p in enumerate(pop_sorted) if p.id == park.id), 0)

    return render_template('ranking.html',
                           park=park,
                           rankings=rankings,
                           sort_by=sort_by,
                           sort_label=sort_label,
                           my_park_id=park.id,
                           total_parks=len(all_parks),
                           my_power_rank=my_power_rank,
                           my_pop_rank=my_pop_rank,
                           my_wins=win_counts.get(park.id, 0),
                           my_losses=loss_counts.get(park.id, 0))


@game_bp.route('/scout/<int:target_id>')
@login_required
def scout(target_id):
    """정찰 - 감시탑이 있으면 상세 정보, 없으면 기본 정보만"""
    park = current_user.park
    target = Park.query.get_or_404(target_id)

    if target.id == park.id:
        flash(get_text('flash.scout_self'), 'warning')
        return redirect(url_for('game.dashboard'))

    # 감시탑 유무에 따라 정보 수준 결정
    has_watchtower = park.watchtowers > 0
    scout_data = {
        'name': target.name,
        'is_npc': target.is_npc,
        'npc_personality': target.npc_personality if target.is_npc else None,
        'total_population': target.total_population,
        'is_destroyed': target.is_destroyed,
    }

    if has_watchtower:
        # 감시탑 보유: 상세 정보 공개
        scout_data.update({
            'guard_count': target.guard_count,
            'adult_count': target.adult_count,
            'child_count': target.child_count,
            'baby_count': target.baby_count,
            'total_combat_power': target.total_combat_power,
            'defense_power': target.defense_power,
            'walls': target.walls,
            'morale': target.morale,
            'watchtowers': target.watchtowers,
        })

    return jsonify({
        'has_watchtower': has_watchtower,
        'data': scout_data,
        'message': '🗼 감시탑에서 정찰 성공 데스!' if has_watchtower
                   else '👁️ 기본 정보만 파악 가능 데스... 감시탑을 세워달라 데스!'
    })


# ============================================================
# [v0.4.0] Phase 5: 교역 시스템
# ============================================================

@game_bp.route('/trade')
@login_required
def trade_market():
    """교역 시장 - 공개 교역 목록 및 내게 온 제안 표시"""
    from app.models import TradeOffer, Diplomacy
    park = current_user.park
    if not park or park.is_destroyed:
        return redirect(url_for('game.dashboard'))

    # 공개 교역 (receiver_id가 NULL이고 pending인 것, 자기 제안 제외)
    # [v1.8.7] Zombie Trades 방지: 발송자(Sender)가 멸망(is_destroyed == True)한 교역은 노출되지 않도록 Park 조인 가드 탑재 (audit_report_55.md [LOGIC-F022])
    public_trades = TradeOffer.query.join(
        Park, TradeOffer.sender_id == Park.id
    ).filter(
        TradeOffer.status == 'pending',
        TradeOffer.sender_id != park.id,
        TradeOffer.receiver_id == None,
        Park.is_destroyed == False
    ).order_by(TradeOffer.created_at.desc()).limit(20).all()

    # 내게 온 교역 제안 (receiver_id가 내 공원이고 pending)
    # [v1.6.2] DoS 방지: 쿼리 제한
    my_incoming = TradeOffer.query.filter_by(
        receiver_id=park.id, status='pending'
    ).order_by(TradeOffer.created_at.desc()).limit(50).all()

    # 내가 보낸 교역 제안 (pending만)
    # [v1.6.2] DoS 방지: 쿼리 제한
    my_outgoing = TradeOffer.query.filter_by(
        sender_id=park.id, status='pending'
    ).order_by(TradeOffer.created_at.desc()).limit(50).all()

    # 다른 공원 목록 (교역 대상 선택용, NPC 포함)
    other_parks = Park.query.filter(
        Park.id != park.id,
        Park.is_destroyed == False
    ).all()

    # 외교 관계 조회
    alliances = Diplomacy.query.filter(
        ((Diplomacy.park_a_id == park.id) | (Diplomacy.park_b_id == park.id)),
        Diplomacy.relation_type == 'ally',
        Diplomacy.status == 'active'
    ).all()

    enemies = Diplomacy.query.filter(
        ((Diplomacy.park_a_id == park.id) | (Diplomacy.park_b_id == park.id)),
        Diplomacy.relation_type == 'enemy',
        Diplomacy.status == 'active'
    ).all()

    # 동맹 요청 (내게 온 pending)
    alliance_requests = Diplomacy.query.filter(
        Diplomacy.park_b_id == park.id,
        Diplomacy.relation_type == 'ally',
        Diplomacy.status == 'pending'
    ).all()

    return render_template('trade.html',
                           park=park,
                           public_trades=public_trades,
                           my_incoming=my_incoming,
                           my_outgoing=my_outgoing,
                           other_parks=other_parks,
                           alliances=alliances,
                           enemies=enemies,
                           alliance_requests=alliance_requests)


@game_bp.route('/trade/create', methods=['POST'])
@login_required
def trade_create():
    """교역 제안 생성"""
    from app.models import TradeOffer
    from app.game_engine import add_event
    park = current_user.park
    if not park or park.is_destroyed:
        return redirect(url_for('game.dashboard'))

    # [v1.8.1] DB 비관적 락 획득: Gunicorn 등 다중 프로세스 환경에서 TOCTOU 우회 및 교역 초과 등록 차단 (audit_report_48.md [LOGIC-F019])
    Park.query.filter(Park.id == park.id).with_for_update().first()
    db.session.refresh(park)

    # [v1.6.2] 유저당 동시 교역 제한 — 교역 스팸 DoS 방지
    pending_count = TradeOffer.query.filter_by(
        sender_id=park.id, status='pending'
    ).count()
    if pending_count >= 10:
        flash('동시에 10개 이상의 교역을 등록할 수 없는 데스!', 'error')
        return redirect(url_for('game.trade_market'))

    # 폼에서 값 읽기
    receiver_id = request.form.get('receiver_id', type=int)  # 0이면 공개
    offer_konpeito = request.form.get('offer_konpeito', 0, type=int)
    offer_trash = request.form.get('offer_trash', 0, type=int)
    offer_material = request.form.get('offer_material', 0, type=int)
    offer_babies = request.form.get('offer_babies', 0, type=int)
    request_konpeito = request.form.get('request_konpeito', 0, type=int)
    request_trash = request.form.get('request_trash', 0, type=int)
    request_material = request.form.get('request_material', 0, type=int)
    request_babies = request.form.get('request_babies', 0, type=int)

    # [v1.5.1] 음수 자원 차단 — 음수 입력으로 자원 증식 Exploit 방지
    offer_konpeito = max(0, offer_konpeito)
    offer_trash = max(0, offer_trash)
    offer_material = max(0, offer_material)
    offer_babies = max(0, offer_babies)
    request_konpeito = max(0, request_konpeito)
    request_trash = max(0, request_trash)
    request_material = max(0, request_material)
    request_babies = max(0, request_babies)

    # [v1.5.1] 교역 메시지 XSS 방지 — HTML 특수문자 이스케이프
    import html as html_lib
    msg = html_lib.escape(request.form.get('trade_message', '')[:200])

    # 검증: 최소 하나는 제안하고, 최소 하나는 요청해야 함
    total_offer = offer_konpeito + offer_trash + offer_material + offer_babies
    total_req = request_konpeito + request_trash + request_material + request_babies
    if total_offer == 0 or total_req == 0:
        flash(get_text('flash.trade_empty'), 'error')
        return redirect(url_for('game.trade_market'))

    # [v1.6.0] 원자적 에스크로: SQL 레벨에서 보유량 조건 포함 차감
    # 동시 요청 시 WHERE 조건 불일치로 DB가 자동 차단 (Race Condition 방지)
    # @validates가 조용히 음수를 0으로 만드는 역설을 근본 차단
    updated = Park.query.filter(
        Park.id == park.id,
        Park.konpeito >= offer_konpeito,
        Park.trash_food >= offer_trash,
        Park.material >= offer_material,
        Park.baby_count >= offer_babies
    ).update({
        'konpeito': Park.konpeito - offer_konpeito,
        'trash_food': Park.trash_food - offer_trash,
        'material': Park.material - offer_material,
        'baby_count': Park.baby_count - offer_babies,
    })
    db.session.flush()

    if updated == 0:
        # 동시 요청으로 잔액 부족 발생 — 안전하게 차단
        flash(get_text('flash.trade_insufficient'), 'error')
        return redirect(url_for('game.trade_market'))

    # 파이썬 객체 동기화 (DB에서 갱신된 값 반영)
    db.session.refresh(park)

    trade = TradeOffer(
        sender_id=park.id,
        receiver_id=receiver_id if receiver_id and receiver_id > 0 else None,
        offer_konpeito=offer_konpeito,
        offer_trash=offer_trash,
        offer_material=offer_material,
        offer_babies=offer_babies,
        request_konpeito=request_konpeito,
        request_trash=request_trash,
        request_material=request_material,
        request_babies=request_babies,
        message=msg,
    )
    db.session.add(trade)
    add_event(park, 'trade', f'📦 교역 제안 등록! (제공: 🍬{offer_konpeito} 🗑️{offer_trash} 🧱{offer_material} 🐛{offer_babies})')
    db.session.commit()

    flash(get_text('flash.trade_registered'), 'success')
    return redirect(url_for('game.trade_market'))


@game_bp.route('/trade/accept/<int:trade_id>', methods=['POST'])
@login_required
def trade_accept(trade_id):
    """교역 제안 수락 - 자원 교환 실행"""
    from app.models import TradeOffer
    from app.game_engine import add_event
    from datetime import datetime
    park = current_user.park
    if not park or park.is_destroyed:
        return redirect(url_for('game.dashboard'))

    # [v1.5.0] Double Spend 방지: 원자적 UPDATE-WHERE로 동시 수락 차단
    # SQLite 파일 락이 UPDATE 문 단위로 걸리므로, WHERE 조건에 status를 넣으면
    # 경쟁 조건(Race Condition)이 DB 레벨에서 차단됨
    updated = TradeOffer.query.filter_by(
        id=trade_id, status='pending'
    ).update({'status': 'processing'})
    db.session.flush()

    if updated == 0:
        # 이미 다른 요청이 처리했거나 존재하지 않는 교역
        flash(get_text('flash.trade_not_found'), 'error')
        return redirect(url_for('game.trade_market'))

    trade = db.session.get(TradeOffer, trade_id)

    # 자기 자신의 제안은 수락 불가
    if trade.sender_id == park.id:
        trade.status = 'pending'  # 원복
        db.session.commit()
        flash(get_text('flash.trade_self'), 'error')
        return redirect(url_for('game.trade_market'))

    # 지정 교역이면 내가 대상인지 확인
    if trade.receiver_id and trade.receiver_id != park.id:
        trade.status = 'pending'  # 원복
        db.session.commit()
        flash(get_text('flash.trade_not_mine'), 'error')
        return redirect(url_for('game.trade_market'))

    sender = db.session.get(Park, trade.sender_id)
    if not sender or sender.is_destroyed:
        # [v1.5.1] 에스크로 환불 불가 (발송자 멸망) — 자원 소멸 처리
        trade.status = 'expired'
        db.session.commit()
        flash(get_text('flash.trade_sender_dead'), 'warning')
        return redirect(url_for('game.trade_market'))

    # [v1.5.1] 에스크로 적용으로 발송자 보유량 재확인 불필요 (이미 선차감됨)
    # 단, 만료 처리 시에는 환불이 필요하므로 별도 핸들링

    # [v1.7.0] Deadlock 방지: 어떠한 Park UPDATE보다도 락 획득을 최우선으로 실행
    # 수락자의 원자적 UPDATE가 먼저 실행되면 이미 락을 선점하게 되어 정렬 기반 락 획득이 무효화됨
    # (audit_report_22.md [DEADLOCK-F002])
    from sqlalchemy import case
    lock_ids = sorted([park.id, sender.id])
    Park.query.filter(Park.id.in_(lock_ids)).with_for_update().all()
    db.session.refresh(park)
    db.session.refresh(sender)

    # [v1.8.3] 비관적 락 획득 후 멸망 상태 재검증 (Zombie State TOCTOU 방지)
    if park.is_destroyed or sender.is_destroyed:
        if sender.is_destroyed:
            trade.status = 'expired'
            db.session.commit()
            flash(get_text('flash.trade_sender_dead'), 'warning')
        else:
            trade.status = 'pending'
            db.session.commit()
            flash('공원이 멸망하여 교역을 수락할 수 없는 데스...', 'error')
        return redirect(url_for('game.trade_market'))

    # [v1.7.0] 수락자 request 차감을 원자적 UPDATE-WHERE로 처리 (audit_report_5.md [IMP-F003])
    # 동시 다발 수락 시 Lost Update / Double-Spend 방지
    updated_park = Park.query.filter(
        Park.id == park.id,
        Park.konpeito >= trade.request_konpeito,
        Park.trash_food >= trade.request_trash,
        Park.material >= trade.request_material,
        Park.baby_count >= trade.request_babies
    ).update({
        'konpeito': Park.konpeito - trade.request_konpeito,
        'trash_food': Park.trash_food - trade.request_trash,
        'material': Park.material - trade.request_material,
        'baby_count': Park.baby_count - trade.request_babies,
    })
    db.session.flush()

    if updated_park == 0:
        # 동시 수정으로 자원 부족 발생 — 안전하게 원복
        trade.status = 'pending'
        db.session.commit()
        flash(get_text('flash.trade_my_insufficient'), 'error')
        return redirect(url_for('game.trade_market'))

    # DB 갱신값 반영
    db.session.refresh(park)

    # === 자원 교환 실행 ===
    # [v1.7.0] 수락자/발송자 모두 원자적 UPDATE + case() cap 보정 (audit_report_11.md [IMP-F028])

    # 1단계: 수락자가 받을 것을 더함 (offer, 에스크로에서) — 원자적 UPDATE + cap 보정
    # [v1.7.0] baby_cap hybrid_property 사용: 운치굴 0개일 때도 최소 5마리 보장 (audit_report_32.md [STATE-F007])
    Park.query.filter(Park.id == park.id).update({
        'konpeito': case((Park.konpeito + trade.offer_konpeito > Park.konpeito_cap, Park.konpeito_cap), else_=Park.konpeito + trade.offer_konpeito),
        'trash_food': case((Park.trash_food + trade.offer_trash > Park.trash_food_cap, Park.trash_food_cap), else_=Park.trash_food + trade.offer_trash),
        'material': case((Park.material + trade.offer_material > Park.material_cap, Park.material_cap), else_=Park.material + trade.offer_material),
        'baby_count': case((Park.baby_count + trade.offer_babies > Park.baby_cap, Park.baby_cap), else_=Park.baby_count + trade.offer_babies),
    })

    # 2단계: 발송자에게 수락자가 준 것을 더함 — 원자적 UPDATE + cap 보정
    # [v1.7.0] baby_cap hybrid_property 사용: 운치굴 0개일 때도 최소 5마리 보장 (audit_report_32.md [STATE-F007])
    Park.query.filter(Park.id == sender.id).update({
        'konpeito': case((Park.konpeito + trade.request_konpeito > Park.konpeito_cap, Park.konpeito_cap), else_=Park.konpeito + trade.request_konpeito),
        'trash_food': case((Park.trash_food + trade.request_trash > Park.trash_food_cap, Park.trash_food_cap), else_=Park.trash_food + trade.request_trash),
        'material': case((Park.material + trade.request_material > Park.material_cap, Park.material_cap), else_=Park.material + trade.request_material),
        'baby_count': case((Park.baby_count + trade.request_babies > Park.baby_cap, Park.baby_cap), else_=Park.baby_count + trade.request_babies),
    })

    trade.status = 'accepted'
    trade.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)

    add_event(park, 'trade', f'📦 교역 성사! {sender.name}에서 자원 교환 완료 데스!')
    add_event(sender, 'trade', f'📦 교역 성사! {park.name}이 교역을 수락해줬는 데스!')
    db.session.commit()

    flash(get_text('flash.trade_success', name=sender.name), 'success')
    return redirect(url_for('game.trade_market'))


@game_bp.route('/trade/reject/<int:trade_id>', methods=['POST'])
@login_required
def trade_reject(trade_id):
    """교역 제안 거절 [v1.7.0] 원자적 상태 전환 + 에스크로 환불 (audit_report_5.md [IMP-F003])"""
    from app.models import TradeOffer
    from datetime import datetime
    from sqlalchemy import case  # [v1.7.0] 원자적 캡핑용
    park = current_user.park

    # [v1.7.0] 원자적 상태 전환: 동시 거절 중복 환불 Race Condition 방지
    # [v1.8.7] IDOR 방지: 자신이 수신자(receiver_id == park.id)인 교역만 거절 가능 (공개 교역은 receiver_id가 None이므로 거절 불가) (audit_report_55.md [AUTH-F001])
    updated = TradeOffer.query.filter(
        TradeOffer.id == trade_id,
        TradeOffer.status == 'pending',
        TradeOffer.receiver_id == park.id
    ).update({'status': 'rejected', 'resolved_at': datetime.now(timezone.utc).replace(tzinfo=None)})
    db.session.flush()

    if updated == 0:
        flash(get_text('flash.trade_already'), 'error')
        return redirect(url_for('game.trade_market'))

    # 원자적 업데이트 성공 후 환불 (1번만 실행됨)
    trade = db.session.get(TradeOffer, trade_id)
    sender = db.session.get(Park, trade.sender_id)
    if sender and not sender.is_destroyed:
        # [v1.7.0] 원자적 환불 + case() 캡핑: 메모리 덮어쓰기 방지 (audit_report_12.md [IMP-F028])
        # [v1.7.0] baby_cap hybrid_property 사용 (audit_report_32.md [STATE-F007])
        Park.query.filter(Park.id == sender.id).update({
            'konpeito': case((Park.konpeito + trade.offer_konpeito > Park.konpeito_cap, Park.konpeito_cap), else_=Park.konpeito + trade.offer_konpeito),
            'trash_food': case((Park.trash_food + trade.offer_trash > Park.trash_food_cap, Park.trash_food_cap), else_=Park.trash_food + trade.offer_trash),
            'material': case((Park.material + trade.offer_material > Park.material_cap, Park.material_cap), else_=Park.material + trade.offer_material),
            'baby_count': case((Park.baby_count + trade.offer_babies > Park.baby_cap, Park.baby_cap), else_=Park.baby_count + trade.offer_babies),
        })

    db.session.commit()
    flash(get_text('flash.trade_rejected'), 'info')
    return redirect(url_for('game.trade_market'))


@game_bp.route('/trade/cancel/<int:trade_id>', methods=['POST'])
@login_required
def trade_cancel(trade_id):
    """내 교역 제안 취소 [v1.6.3] 원자적 상태 전환"""
    from app.models import TradeOffer
    from datetime import datetime
    from sqlalchemy import case  # [v1.7.0] 원자적 캡핑용
    park = current_user.park

    # [v1.7.0] 원자적 상태 전환 + 환불 (audit_report_10.md [IMP-F021], [IMP-F023])
    # 동일 트랜잭션 내에서 상태 변경과 자원 환불을 원자적으로 처리
    trade = db.session.get(TradeOffer, trade_id)
    if not trade or trade.sender_id != park.id or trade.status != 'pending':
        flash(get_text('flash.trade_cancel_fail'), 'error')
        return redirect(url_for('game.trade_market'))

    # 상태 원자적 변경 + 중복 환불 방지 (audit_report_14.md [IMP-F036])
    updated = TradeOffer.query.filter(
        TradeOffer.id == trade_id,
        TradeOffer.status == 'pending'
    ).update({'status': 'cancelled', 'resolved_at': datetime.now(timezone.utc).replace(tzinfo=None)})

    if updated == 0:
        flash(get_text('flash.trade_already'), 'error')
        return redirect(url_for('game.trade_market'))

    # 자원 원자적 환불 + case() 캡핑: 메모리 덮어쓰기 방지 (audit_report_12.md [IMP-F028])
    # [v1.7.0] baby_cap hybrid_property 사용 (audit_report_32.md [STATE-F007])
    Park.query.filter(Park.id == park.id).update({
        'konpeito': case((Park.konpeito + trade.offer_konpeito > Park.konpeito_cap, Park.konpeito_cap), else_=Park.konpeito + trade.offer_konpeito),
        'trash_food': case((Park.trash_food + trade.offer_trash > Park.trash_food_cap, Park.trash_food_cap), else_=Park.trash_food + trade.offer_trash),
        'material': case((Park.material + trade.offer_material > Park.material_cap, Park.material_cap), else_=Park.material + trade.offer_material),
        'baby_count': case((Park.baby_count + trade.offer_babies > Park.baby_cap, Park.baby_cap), else_=Park.baby_count + trade.offer_babies),
    })

    db.session.commit()
    flash(get_text('flash.trade_cancelled'), 'info')
    return redirect(url_for('game.trade_market'))


# ============================================================
# [v0.4.0] Phase 5: 외교 시스템
# ============================================================

@game_bp.route('/diplomacy/ally/<int:target_id>', methods=['POST'])
@login_required
def diplomacy_ally(target_id):
    """동맹 요청 보내기 [v1.8.5] Canonical Ordering 및 2중 비관적 락 탑재"""
    from app.models import Diplomacy
    from app.game_engine import add_event
    park = current_user.park
    target = db.session.get(Park, target_id)
    if not target or target.is_destroyed or target.id == park.id:
        flash(get_text('flash.diplo_invalid'), 'error')
        return redirect(url_for('game.trade_market'))

    # [v1.8.5] 2중 비관적 락 획득 (ID 오름차순으로 정렬하여 교사 데드락 방지)
    lock_ids = sorted([park.id, target.id])
    Park.query.filter(Park.id.in_(lock_ids)).with_for_update().all()
    db.session.refresh(park)
    db.session.refresh(target)

    # 락 대기 후 멸망 상태 재검증 (TOCTOU 방지)
    if park.is_destroyed or target.is_destroyed:
        flash(get_text('flash.diplo_invalid'), 'error')
        return redirect(url_for('game.trade_market'))

    # [v1.8.5] Canonical Ordering: 항상 park_a_id < park_b_id 보장
    park_a_id = min(park.id, target.id)
    park_b_id = max(park.id, target.id)

    # 이미 관계가 있는지 확인 (띅 획득 후 재검증)
    existing = Diplomacy.query.filter(
        Diplomacy.park_a_id == park_a_id,
        Diplomacy.park_b_id == park_b_id,
        Diplomacy.status.in_(['pending', 'active'])
    ).first()
    if existing:
        flash(get_text('flash.diplo_exists'), 'warning')
        return redirect(url_for('game.trade_market'))

    # NPC에게는 자동 수락
    if target.is_npc:
        diplo = Diplomacy(park_a_id=park_a_id, park_b_id=park_b_id,
                          relation_type='ally', status='active', initiator_id=park.id)
        add_event(park, 'diplomacy', f'🤝 {target.name}과(와) 동맹을 맺었는 데스!')
    else:
        diplo = Diplomacy(park_a_id=park_a_id, park_b_id=park_b_id,
                          relation_type='ally', status='pending', initiator_id=park.id)
        add_event(target, 'diplomacy', f'🤝 {park.name}이 동맹을 제안했는 데스!')
        add_event(park, 'diplomacy', f'🤝 {target.name}에게 동맹 요청을 보냈는 데스!')

    db.session.add(diplo)
    # [v1.7.0] DB unique 제약 위반 시 우아하게 차단 (audit_report_42.md [STATE-F015])
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash(get_text('flash.diplo_exists'), 'warning')
        return redirect(url_for('game.trade_market'))
    flash(get_text('flash.diplo_ally_sent', name=target.name) if not target.is_npc
          else get_text('flash.diplo_ally_auto', name=target.name), 'success')
    return redirect(url_for('game.trade_market'))


@game_bp.route('/diplomacy/accept/<int:diplo_id>', methods=['POST'])
@login_required
def diplomacy_accept(diplo_id):
    """동맹 요청 수락 [v1.8.5] Canonical Ordering 검증 보완"""
    from app.models import Diplomacy
    from app.game_engine import add_event
    from datetime import datetime
    park = current_user.park
    diplo = db.session.get(Diplomacy, diplo_id)

    # [v1.8.5] 자신이 보낸 요청(initiator_id == park.id)이 아니어야 하며, 본인 관련 관계여야 함
    if not diplo or diplo.initiator_id == park.id or (diplo.park_a_id != park.id and diplo.park_b_id != park.id) or diplo.status != 'pending':
        flash(get_text('flash.diplo_accept_fail'), 'error')
        return redirect(url_for('game.trade_market'))

    # [v1.8.5] 2중 비관적 락 획득 (ID 오름차순)
    lock_ids = sorted([diplo.park_a_id, diplo.park_b_id])
    Park.query.filter(Park.id.in_(lock_ids)).with_for_update().all()
    db.session.refresh(park)

    # 락 대기 후 멸망 상태 재검증 (TOCTOU 방지)
    sender_park = diplo.park_a if diplo.park_b_id == park.id else diplo.park_b
    db.session.refresh(sender_park)
    if park.is_destroyed or sender_park.is_destroyed:
        flash(get_text('flash.diplo_accept_fail'), 'error')
        return redirect(url_for('game.trade_market'))

    # [v1.7.0] 원자적 상태 전환: TOCTOU로 인한 중복 이벤트 로그 방지 (audit_report_46.md [STATE-F019])
    updated = Diplomacy.query.filter(
        Diplomacy.id == diplo_id,
        Diplomacy.status == 'pending'
    ).update({
        'status': 'active',
        'resolved_at': datetime.now(timezone.utc).replace(tzinfo=None)
    })

    if updated == 0:
        flash(get_text('flash.diplo_accept_fail'), 'error')
        return redirect(url_for('game.trade_market'))

    add_event(park, 'diplomacy', f'🤝 {sender_park.name}과(와) 동맹 성사!')
    add_event(sender_park, 'diplomacy', f'🤝 {park.name}이 동맹을 수락해줬는 데스!')
    db.session.commit()
    flash(get_text('flash.diplo_ally_success', name=sender_park.name), 'success')
    return redirect(url_for('game.trade_market'))


@game_bp.route('/diplomacy/reject/<int:diplo_id>', methods=['POST'])
@login_required
def diplomacy_reject(diplo_id):
    """동맹 요청 거절 [v1.8.5] Canonical Ordering 검증 보완"""
    from app.models import Diplomacy
    from datetime import datetime
    park = current_user.park
    diplo = db.session.get(Diplomacy, diplo_id)

    # [v1.8.5] 자신이 보낸 요청이 아니어야 하며, 본인 관련 관계여야 함
    if not diplo or diplo.initiator_id == park.id or (diplo.park_a_id != park.id and diplo.park_b_id != park.id) or diplo.status != 'pending':
        flash(get_text('flash.diplo_accept_fail'), 'error')
        return redirect(url_for('game.trade_market'))

    # [v1.7.0] 원자적 상태 전환: TOCTOU로 인한 중복 이벤트 로그 방지 (audit_report_46.md [STATE-F019])
    updated = Diplomacy.query.filter(
        Diplomacy.id == diplo_id,
        Diplomacy.status == 'pending'
    ).update({
        'status': 'rejected',
        'resolved_at': datetime.now(timezone.utc).replace(tzinfo=None)
    })

    if updated == 0:
        flash(get_text('flash.diplo_accept_fail'), 'error')
        return redirect(url_for('game.trade_market'))

    db.session.commit()
    flash(get_text('flash.diplo_reject'), 'info')
    return redirect(url_for('game.trade_market'))


@game_bp.route('/diplomacy/enemy/<int:target_id>', methods=['POST'])
@login_required
def diplomacy_enemy(target_id):
    """적대 선언 (일방적, 즉시 활성) [v1.8.5] 2중 락 및 일괄 상태 해제(Bulk Update) 구현"""
    from app.models import Diplomacy
    from app.game_engine import add_event
    park = current_user.park

    target = db.session.get(Park, target_id)
    if not target or target.is_destroyed or target.id == park.id:
        flash(get_text('flash.diplo_invalid'), 'error')
        return redirect(url_for('game.trade_market'))

    # [v1.7.0] AP 소비는 모든 검증 통과 후에 수행: AP Blackhole 방지 (audit_report_43.md [LOGIC-F016])
    turn_ok, turn_msgs = game_engine.consume_turn(park, ap_cost=1)
    if not turn_ok:
        for msg in turn_msgs:
            flash(msg, 'error')
        return redirect(url_for('game.trade_market'))

    # [v1.8.5] 2중 비관적 락 획득 (ID 오름차순)
    lock_ids = sorted([park.id, target.id])
    Park.query.filter(Park.id.in_(lock_ids)).with_for_update().all()
    db.session.refresh(park)
    db.session.refresh(target)

    # 락 대기 후 멸망 상태 재검증 (TOCTOU 방지)
    # [v1.8.9] AP 블랙홀 방지: 락 대기 후 대상 멸망 예외 분기 시 AP 복구 후 명시적 커밋 집행 (audit_report_58.md)
    if park.is_destroyed or target.is_destroyed:
        game_engine.refund_ap(park, 1)
        db.session.commit()
        flash(get_text('flash.diplo_invalid'), 'error')
        return redirect(url_for('game.trade_market'))

    # [v1.8.5] Canonical Ordering: 항상 park_a_id < park_b_id 보장
    park_a_id = min(park.id, target.id)
    park_b_id = max(park.id, target.id)

    # [v1.8.5] 기존 동맹이 있으면 일괄 해제 (Bulk Update)하여 중복 동맹 오염 청소 및 모순 상태 방어
    Diplomacy.query.filter(
        Diplomacy.park_a_id == park_a_id,
        Diplomacy.park_b_id == park_b_id,
        Diplomacy.relation_type == 'ally',
        Diplomacy.status.in_(['active', 'pending'])
    ).update({'status': 'dissolved'})

    # 이미 적대 관계인지 확인 (띅 획득 후 재검증)
    existing_enemy = Diplomacy.query.filter(
        Diplomacy.park_a_id == park_a_id,
        Diplomacy.park_b_id == park_b_id,
        Diplomacy.relation_type == 'enemy',
        Diplomacy.status == 'active'
    ).first()
    if existing_enemy:
        # [v1.8.2] 이미 적대인 경우에도 consume_turn으로 차감된 1AP를 환불 (보상 트랜잭션)
        # [v1.8.9] AP 블랙홀 방지: 이미 적대 상태 시 AP 복구 후 명시적 커밋 집행 (audit_report_58.md)
        game_engine.refund_ap(park, 1)
        db.session.commit()
        flash(get_text('flash.diplo_exists'), 'warning')
        return redirect(url_for('game.trade_market'))

    diplo = Diplomacy(park_a_id=park_a_id, park_b_id=park_b_id,
                      relation_type='enemy', status='active', initiator_id=park.id)
    db.session.add(diplo)
    add_event(park, 'diplomacy', f'⚔️ {target.name}에 적대를 선언했는 데스!!')
    add_event(target, 'diplomacy', f'⚔️ {park.name}이 적대를 선언했는 데스!! 경계하라 데스!')

    # [v1.7.0] DB unique 제약 위반 시 우아하게 차단 (audit_report_42.md [STATE-F015])
    # 동시에 AP 환불: consume_turn이 이미 커밋되었으므로 rollback으로 복구 불가
    from sqlalchemy.exc import IntegrityError
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # [v1.8.2] game_engine.refund_ap 공용 헬퍼로 환불 처리 통합
        # [v1.8.9] AP 블랙홀 방지: IntegrityError 롤백 직후 AP 복구 후 명시적 커밋 집행 (audit_report_58.md)
        game_engine.refund_ap(park, 1)
        db.session.commit()
        flash(get_text('flash.diplo_exists'), 'warning')
        return redirect(url_for('game.trade_market'))

    flash(get_text('flash.diplo_enemy_sent', name=target.name), 'warning')
    return redirect(url_for('game.trade_market'))


@game_bp.route('/diplomacy/dissolve/<int:diplo_id>', methods=['POST'])
@login_required
def diplomacy_dissolve(diplo_id):
    """외교 관계 해제 (동맹 파기 / 적대 종료) [v1.8.5] 2중 락 및 일괄 해제(Bulk Update) 구현"""
    from app.models import Diplomacy
    from app.game_engine import add_event
    from datetime import datetime
    park = current_user.park

    diplo = db.session.get(Diplomacy, diplo_id)
    if not diplo or diplo.status != 'active':
        flash(get_text('flash.diplo_break_fail'), 'error')
        return redirect(url_for('game.trade_market'))

    # 본인이 관련된 관계인지 확인
    if diplo.park_a_id != park.id and diplo.park_b_id != park.id:
        flash(get_text('flash.diplo_not_mine'), 'error')
        return redirect(url_for('game.trade_market'))

    # [v1.8.5] 2중 비관적 락 획득 (ID 오름차순)
    lock_ids = sorted([diplo.park_a_id, diplo.park_b_id])
    Park.query.filter(Park.id.in_(lock_ids)).with_for_update().all()
    db.session.refresh(park)

    # [v1.7.0] AP 소비는 모든 검증 통과 후에 수행: AP Blackhole 방지 (audit_report_43.md [LOGIC-F016])
    turn_ok, turn_msgs = game_engine.consume_turn(park, ap_cost=1)
    if not turn_ok:
        for msg in turn_msgs:
            flash(msg, 'error')
        return redirect(url_for('game.trade_market'))

    # [v1.8.5] 원자적 외교 관계 일괄 해제 (Bulk Update): 해당 공원 쌍 간의 모든 active 중복 관계들을 일괄 해제하여 잔여 오염 제거
    updated = Diplomacy.query.filter(
        Diplomacy.park_a_id == diplo.park_a_id,
        Diplomacy.park_b_id == diplo.park_b_id,
        Diplomacy.status == 'active'
    ).update({
        'status': 'dissolved',
        'resolved_at': datetime.now(timezone.utc).replace(tzinfo=None)
    })

    if updated == 0:
        Park.query.filter(Park.id == park.id).update({
            'action_points': Park.action_points + 1
        })
        db.session.commit()
        db.session.refresh(park)
        flash(get_text('flash.diplo_break_fail'), 'error')
        return redirect(url_for('game.trade_market'))

    other = diplo.park_b if diplo.park_a_id == park.id else diplo.park_a
    add_event(park, 'diplomacy', f'📜 {other.name}과(와)의 {diplo.relation_type} 관계를 해제했는 데스.')
    if not other.is_destroyed:
        add_event(other, 'diplomacy', f'📜 {park.name}이 {diplo.relation_type} 관계를 해제했는 데스.')
    db.session.commit()

    flash(get_text('flash.diplo_break'), 'info')
    return redirect(url_for('game.trade_market'))


@game_bp.route('/spy/<int:target_id>', methods=['POST'])
@login_required
def spy_send(target_id):
    """[v1.7.0] 밀사 파견 — 1AP + 성체 1마리 소비, 3턴 후 귀환"""
    park = current_user.park

    # [v1.7.0] 밀사 가능 여부 사전 검증: AP Blackhole 방지
    # (audit_report_43.md [LOGIC-F016])
    from app.models import Diplomacy
    target = db.session.get(Park, target_id)
    if not target or target.is_destroyed or target.id == park.id:
        flash(get_text('flash.invalid_target'), 'error')
        return redirect(url_for('game.dashboard'))
    if park.adult_count < 2:
        flash(get_text('flash.spy_no_adults'), 'error')
        return redirect(url_for('game.dashboard'))
    is_ally = Diplomacy.query.filter(
        ((Diplomacy.park_a_id == park.id) & (Diplomacy.park_b_id == target.id)) |
        ((Diplomacy.park_a_id == target.id) & (Diplomacy.park_b_id == park.id)),
        Diplomacy.relation_type == 'ally',
        Diplomacy.status == 'active'
    ).first()
    if is_ally:
        flash(get_text('flash.ally_no_spy', name=target.name), 'error')
        return redirect(url_for('game.dashboard'))

    # [v1.7.0] AP 소비 + 턴 자동 진행 (밀사는 1AP) — 검증 후 호출
    turn_ok, turn_msgs = game_engine.consume_turn(park, ap_cost=GC.SPY_AP_COST)
    if not turn_ok:
        for msg in turn_msgs:
            flash(msg, 'error')
        return redirect(url_for('game.dashboard'))

    success, result, messages = game_engine.action_spy(park, target_id)

    # [v1.7.0] AP 환불: action_spy() 실패 시(원자적 UPDATE가 0 반환) consume_turn으로
    # 이미 차감·커밋된 AP를 복구 (audit_report_46.md [LOGIC-F018])
    # [v1.8.2] game_engine.refund_ap 공용 헬퍼로 환불 처리 통합
    if not success:
        # [v1.8.9] AP 블랙홀 방지: 밀사 파견 실패 시 AP 복구 후 명시적 커밋 집행 (audit_report_58.md)
        game_engine.refund_ap(park, GC.SPY_AP_COST)
        db.session.commit()

    for msg in messages:
        flash(msg, 'success' if success else 'error')

    if success:
        flash(f"🕵️ {result['target']}에 밀사 파견! ({result['turns']}턴 후 귀환)", 'info')

    return redirect(url_for('game.dashboard'))


@game_bp.route('/skills', methods=['GET'])
@login_required
def skills_tree():
    """보스 스킬 트리 터미널 (가상 모크업 이스터에그) [v1.7.0]"""
    park = current_user.park
    return render_template(
        'skills.html',
        park=park
    )


