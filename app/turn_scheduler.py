# -*- coding: utf-8 -*-
"""
실장석 공원 제국 - 턴 스케줄러 (turn_scheduler.py)
[v0.2.0] APScheduler를 이용한 자동 턴 처리.

매 TURN_INTERVAL(기본 10분)마다 모든 공원의 턴을 자동 처리한다.
- 플레이어 공원: 식량 소비, 건설 진행, 훈련 판정, 성장, 기아
- NPC 공원: 위 + AI 행동 (채집, 건설, 침공 등)
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

# 전역 스케줄러 인스턴스
scheduler = BackgroundScheduler(daemon=True)


def init_scheduler(app):
    """
    [v1.7.0] 비활성화됨 — consume_turn 기반 단일화로 인해 스케줄러 시작 로직 중단.
    이중 턴 처리(Double-Tick) 방지: 기존 APScheduler는 제거되었으며,
    모든 턴 처리는 플레이어의 행동(AP 소비/턴 쿼터 소진)에 의한 consume_turn()으로만 수행됨.
    참조: audit_report_3.md [ARCH-F001]
    """
    app.logger.info("[스케줄러] 비활성화됨 — consume_turn 기반 단일 턴 처리 모드")


def _process_all_turns(app):
    """
    모든 활성 공원의 턴을 일괄 처리.
    Flask 앱 컨텍스트 내에서 실행해야 DB 접근 가능.
    """
    with app.app_context():
        from app.models import db, Park
        from app.game_engine import process_turn
        from app.npc_engine import process_npc_turn

        # 멸망하지 않은 모든 공원
        active_parks = Park.query.filter_by(is_destroyed=False).all()

        player_count = 0
        npc_count = 0

        for park in active_parks:
            try:
                # 공통 턴 처리 (식량 소비, 건설, 훈련, 성장 등)
                process_turn(park)

                # NPC 공원은 추가로 AI 행동 실행
                if park.is_npc:
                    process_npc_turn(park)
                    npc_count += 1
                else:
                    player_count += 1

            except Exception as e:
                app.logger.error(f"[턴 처리 오류] 공원 '{park.name}': {e}")
                db.session.rollback()
                continue

        db.session.commit()
        app.logger.info(
            f"[턴 완료] 플레이어 {player_count}개, NPC {npc_count}개 공원 처리 완료"
        )


def force_process_turn(app, park_id):
    """디버그/테스트용: 특정 공원의 턴을 강제 처리"""
    with app.app_context():
        from app.models import db, Park
        from app.game_engine import process_turn
        from app.npc_engine import process_npc_turn

        park = db.session.get(Park, park_id)
        if park and not park.is_destroyed:
            process_turn(park)
            if park.is_npc:
                process_npc_turn(park)
            db.session.commit()
            return True
    return False
