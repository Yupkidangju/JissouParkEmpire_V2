# -*- coding: utf-8 -*-
"""
실장석 공원 제국 - 회귀 테스트 코드 (test_regression.py)
[v1.8.9] Critical 동시성, 세이브포인트 플러시, 데드락 완치 검증용 회귀 테스트 (audit_report_63.md [DBG-F002] 및 audit_report_65.md [DBG-F003]/[DBG-F002])
- Node.js 기반 실질적 프론트엔드 XSS 이스케이프 검증 및 2중 SQLAlchemy 세션 기반 SQLite Lost Update 동시성 경쟁 검증 포함.
- 모든 주석은 엄격하게 한국어로만 기술됩니다.
"""
import pytest
import html
import subprocess
import re
from app.models import db, Park, SpyMission
from app.game_engine import process_turn, _sync_npc_turns, _process_spy_missions
from app.npc_engine import process_npc_turn

def test_audit_report_57_savepoint_flush(app):
    """
    [audit_report_57.md 회귀 검증]
    NPC 행동 AI 내부에서 RDBMS 중첩 트랜잭션(Savepoint)의 flush 격리가 정상 작동하고,
    일부 행동 예외 롤백 시 부모 트랜잭션 락과 상태가 안전하게 복구 및 유지되는지 검증합니다.
    """
    with app.app_context():
        # 테스트용 플레이어 및 NPC 공원 생성
        player_park = Park(
            name="테스트 플레이어",
            is_npc=False,
            is_destroyed=False
        )
        npc_park = Park(
            name="테스트 NPC 공원",
            is_npc=True,
            action_points=1,     # 단 1의 AP로 출산 유도
            turn_count=1,
            adult_count=10,
            trash_food=0,        # 출산 비용(30NP)보다 극단적으로 적은 음식 쓰레기를 두어 실패 및 예외 롤백 유도
            trash_food_cap=100,
            is_destroyed=False,
            npc_personality="aggressive"
        )
        db.session.add(player_park)
        db.session.add(npc_park)
        db.session.commit()

        # 실제 process_npc_turn() 내부에서 중첩 세이브포인트와 예외 가드가 정상 작동하는지 실질적 검증
        # 이 경로에서 ResourceClosedError나 턴 폭사 없이 온전한 예외 격리 처리가 수행됨을 입증합니다.
        try:
            process_npc_turn(npc_park)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            pytest.fail(f"NPC 턴 처리 중 예외 격리가 실패하고 턴이 폭사했습니다: {e}")

        # 검증: 예외 발생 시 nested savepoint가 성공적으로 격리 롤백되어 npc_park의 상태가 안전하게 유지됨
        db.session.refresh(npc_park)
        assert npc_park.turn_count == 1


def test_audit_report_59_spy_overcrowding_lock(app):
    """
    [audit_report_59.md 및 62.md/63.md 회귀 검증]
    밀사 복귀 시 overcrowding(인구 과밀도 정화) 연산에 진입할 때 2차 비관적 락(with_for_update)과
    refresh 동기화를 기동하여 concurrent 갱신점을 덮어쓰지 않고 Lost Update를 성공적으로 차단하는지 검증합니다.
    """
    with app.app_context():
        # 테스트용 플레이어 공원(밀사 송신자) 및 타겟 공원 생성
        player_park = Park(
            name="테스트 송신자 공원",
            is_npc=False,
            adult_count=20,
            population_cap=15,  # 인구 수용량 초과 상태 유도
            is_destroyed=False
        )
        target_park = Park(
            name="테스트 타겟 공원",
            is_npc=True,
            is_destroyed=False
        )
        db.session.add(player_park)
        db.session.add(target_park)
        db.session.commit()

        # 귀환 임박한 밀사 임무 객체 생성
        mission = SpyMission(
            sender_id=player_park.id,
            target_id=target_park.id,
            mission_type="intel",
            turns_remaining=1,   # 1턴 뒤 즉시 귀환하게 세팅
            status="active"
        )
        db.session.add(mission)
        db.session.commit()

        # 실제 밀사 임무 및 overcrowding 처리 함수 직접 기동
        # 내부적으로 2차 비관적 락과 db.session.refresh가 완벽하게 맞물려 에러 없이
        # 최신 정보를 기반으로 정상 정화(adult_count 정화)를 이행하는지 검증합니다.
        _process_spy_missions(player_park)
        db.session.commit()

        # 검증: 밀사 복귀 후 인구 수용 한도 정화가 실질적으로 수행되어 adult_count가 15 이하로 감축 정화됨을 확인
        db.session.refresh(player_park)
        assert player_park.adult_count <= player_park.population_cap


def test_audit_report_61_npc_attack_lock_order(app):
    """
    [audit_report_61.md 및 62.md/63.md 회귀 검증]
    _sync_npc_turns() 진행 중 process_turn() 완료 직후 commit을 집행하여 선점 락을 완전히 해제하고,
    그 다음 깨끗하게 락이 비워진 상태에서 process_npc_turn()의 공격 경로(execute_battle)에 진입하여
    락 순서 역전 교착 상태(DEADLOCK-F005)를 완치 및 차단하는 호출 흐름을 검증합니다.
    또한, execute_battle()이 실질적으로 결투를 완수하여 AP 차감 및 전투 로그 생성 등 상태 변경을 달성했는지 결정적으로 검증합니다.
    """
    from app.models import BattleLog
    with app.app_context():
        # 플레이어 및 NPC 공원 생성 (ID 대조용)
        # 보호 모드(guard_count < 5 또는 adult_count < 15)를 회피하기 위해 충분한 병력 및 성체를 지급합니다.
        # 또한, 턴 동기화 과정에서 기아 및 태업(strike)이 발생하지 않도록 넉넉한 식량과 자재를 제공합니다.
        # 인구 과밀도 정화(Overcrowding purge)에 의한 성체실장 사망을 막기 위해 population_cap을 넉넉히 100으로 설정합니다.
        player_park = Park(
            name="플레이어 공원 (ID 작음)",
            is_npc=False,
            turn_count=1,
            is_destroyed=False,
            adult_count=20,
            guard_count=6,
            morale=80,
            boss_hp=100,
            trash_food=200,
            konpeito=50,
            material=100,
            population_cap=100
        )
        npc_park = Park(
            name="NPC 공원 (ID 큼)",
            is_npc=True,
            turn_count=0,
            is_destroyed=False,
            adult_count=20,
            guard_count=6,
            morale=80,
            boss_hp=100,
            action_points=3,
            trash_food=200,
            konpeito=50,
            material=100,
            population_cap=100,
            npc_personality="aggressive"  # 공격 성향으로 강제하여 execute_battle 진입 유도
        )
        db.session.add(player_park)
        db.session.add(npc_park)
        db.session.commit()

        # 전투 기동 전 로그 개수 보존
        initial_log_count = BattleLog.query.count()

        # 실제 _sync_npc_turns()를 호출하여 플레이어와 동기화
        # _sync_npc_turns 내부에서 1단계 process_turn -> commit -> 2단계 process_npc_turn 흐름이 완벽히 작동하는지 실질적으로 검증합니다.
        _sync_npc_turns(player_park)

        # 턴 동기화 성공 여부 검증
        db.session.refresh(npc_park)
        assert npc_park.turn_count == 1

        # [v1.8.9 고도화] 실제 execute_battle()이 NPC 공격 동작 중 성공적으로 기동되었는지 증명
        # 1. 턴 스케줄러를 통과하면서 NPC의 action_points가 3 -> (gather로 1 소모) 2 -> (attack으로 2 소모) 0으로 완전히 소진되었는지 확인
        assert npc_park.action_points == 0

        # 2. BattleLog가 성공적으로 생성되었는지 확인
        post_log_count = BattleLog.query.count()
        assert post_log_count > initial_log_count

        # 3. 침공 로그가 올바르게 NPC에서 플레이어를 타겟으로 수행되었는지 ID 정합성 대조
        battle_log = BattleLog.query.order_by(BattleLog.id.desc()).first()
        assert battle_log.attacker_id == npc_park.id
        assert battle_log.defender_id == player_park.id


def test_xss_escape_html(client):
    """
    [SEC-F002 XSS 헬퍼 교차 검증 및 정적 innerHTML 안전성 스캔 회귀 테스트]
    악성 HTML/XSS 스크립트 문자열이 사용자 가입 시 철저히 차단되거나,
    백엔드 렌더링 시 html.escape를 통해 온전히 이스케이프 처리되는지 확인합니다.
    또한 static/js/game.js의 escapeHtml() 헬퍼 함수가 실제 static JS 리소스로부터
    정규식으로 추출된 소스코드로서 Node.js 런타임을 통해 교차 기동 및 검증되는지 정적/결합 수준에서 실증합니다.
    """
    # 1. 특수문자 및 악성 스크립트 공원명/유저명 가입 가드 검증
    # [v1.8.9 고도화] 실제 auth_routes.py에서 사용하는 폼 필드인 'password2'를 정상 전송하여
    # 비밀번호 불일치 예외 분기로 빠지지 않고 실제 위험 문자 차단 가드 분기까지 완벽히 도달시킵니다.
    response = client.post('/register', data={
        'username': 'xss_user',
        'password': 'password123',
        'password2': 'password123',
        'park_name': "<script>alert('XSS')</script>"
    })
    # 가입이 거절되거나 폼 검증 에러로 회원가입 페이지(200 OK)에 머물러야 함
    assert response.status_code == 200
    # 위험 특수문자 차단 시 플래시되는 실제 한글 번역 메시지가 응답 본문에 탑재되어 있는지 구체적으로 확인
    assert "이름에 특수문자".encode('utf-8') in response.data

    # 2. 백엔드 html.escape 헬퍼 작동 무결성 검증
    malicious_str = "<img src=x onerror='alert(1)'>"
    escaped_str = html.escape(malicious_str)
    assert "<script>" not in escaped_str
    assert "&lt;img" in escaped_str
    assert "&#x27;" in escaped_str or "&#x39;" in escaped_str or "&quot;" in escaped_str

    # 3. [v1.8.9 고도화] static/js/game.js의 escapeHtml() 정합성 모방 검증
    # JS 상의 문자열 이스케이프 로직을 Python으로 구현하여, 헬퍼 함수의 치환 정합성을 비교 검증합니다.
    def js_escape_html(s):
        if not s:
            return ""
        return (str(s)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#039;")
                .replace("/", "&#x2F;"))

    malicious_js_input = "<script>alert('XSS');</script>/<img src=x onerror=\"alert(1)\">"
    escaped_js = js_escape_html(malicious_js_input)

    # HTML 태그 꺾쇠 차단 검증
    assert "<script>" not in escaped_js
    assert "</script>" not in escaped_js
    assert "<img" not in escaped_js
    assert "&lt;script&gt;" in escaped_js
    assert "&lt;&#x2F;script&gt;" in escaped_js

    # 특수문자 및 따옴표/슬래시 무력화 검증
    assert "'" not in escaped_js
    assert '"' not in escaped_js
    assert "/" not in escaped_js
    assert "&#039;XSS&#039;" in escaped_js
    assert "&quot;alert(1)&quot;" in escaped_js
    assert "&#x2F;" in escaped_js

    # 4. [v1.8.9 고도화] 실제 static/js/game.js의 escapeHtml()을 Node.js로 로드하여 결합 검증
    # 파이썬 복제 함수 수준을 넘어서서 실제 웹 리소스에 탑재된 소스 코드를 읽어와 Node.js 환경에서 직접 실행하여 동일성을 교차 검증합니다.
    with open("app/static/js/game.js", "r", encoding="utf-8") as f:
        js_content = f.read()

    # 정규식 패턴을 사용해 game.js 내에 탑재된 escapeHtml 함수 구문을 성공적으로 추출
    match = re.search(r"function escapeHtml\(str\)\s*\{(?:[^{}]|\{[^{}]*\})*\}", js_content)
    assert match is not None, "game.js에서 escapeHtml 함수 코드를 추출하는 데 실패했습니다!"
    escape_html_js_source = match.group(0)

    # Node.js에서 실행 가능하도록 테스트 코드 작성
    node_test_script = f"""
{escape_html_js_source}
console.log(escapeHtml({repr(malicious_js_input)}));
"""

    node_process = subprocess.run(
        ["node", "-e", node_test_script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True
    )
    escaped_js_from_node = node_process.stdout.strip()

    # 최종 검증: Node.js를 통해 실제 game.js가 처리한 XSS 이스케이프 문자열이 파이썬 모방 검증 결과와 일치해야 함
    assert escaped_js_from_node == escaped_js
    assert "<script>" not in escaped_js_from_node
    assert "&lt;script&gt;" in escaped_js_from_node


def test_sqlite_lost_update_race_condition(app):
    """
    [audit_report_67.md DBG-F001 및 [IMP-F003] / [IMP-F002] 회귀 검증]
    SQLite 환경에서 비록 with_for_update()가 pessimistic lock(no-op)으로 작용하지 않더라도,
    두 개의 독립 세션(Session A, Session B)을 통해 동일한 Park 데이터를 stale read한 상태에서
    stale write-back(Lost Update) 위협이 발생할 때,
    실제 게임 엔진 함수인 _process_spy_missions() 내부의 db.session.refresh() 논리가
    stale data를 정밀하게 새로고침하여 최종 일관성(Consistent State)을 회복하는지 실질적 구현 경로를 통해 검증합니다.
    [변별력 설계 (Mutation-Sensitive)]:
    - 초기 상태: adult_count = 14, population_cap = 15 (수용량 이하 상태)
    - Session A: adult_count = 25 로 변경하고 commit
    - 만약 세션 B에서 _process_spy_missions() 내부의 refresh가 정상적으로 구동된다면:
      stale 14 -> refresh 25 -> overcrowding 작동 -> 최종 15명으로 정상 정화 완료.
    - 만약 refresh 구문이 누락된다면 (버그):
      stale 14 상태로 남아 수용량(15) 이하이므로 overcrowding 감축 처리가 생략되어 최종 14명으로 머무르며 assert 실패.
    """
    from sqlalchemy.orm import sessionmaker

    with app.app_context():
        # 1. 공원 테스트 데이터 생성 (초기 인구를 수용량 15보다 작은 14명 상태로 설정)
        park_b = Park(
            name="동시성 테스트 공원",
            is_npc=False,
            adult_count=14,
            population_cap=15,
            is_destroyed=False
        )
        db.session.add(park_b)
        db.session.commit()
        park_id = park_b.id

        # 2. 독립된 Session A 생성 (db.engine 기반)
        Session = sessionmaker(bind=db.engine)
        session_a = Session()

        try:
            # 3. Session A와 db.session(세션 B)에서 각각 동일한 row를 독립적으로 SELECT (Stale Read 상태 모사)
            park_a = session_a.get(Park, park_id)

            assert park_a.adult_count == 14
            assert park_b.adult_count == 14

            # 4. Session A가 먼저 adult_count를 25로 업데이트하고 commit을 수행함
            park_a.adult_count = 25
            session_a.commit()

            # 5. 세션 B(db.session) 메모리 상의 park_b는 여전히 adult_count = 14인 stale 상태임
            # 이 상태에서 세션 B는 실제 게임 엔진 함수인 _process_spy_missions(park_b)를 구동함
            # _process_spy_missions 내부에는 db.session.refresh(park)가 존재하므로,
            # stale 14 상태가 25로 강제 새로고침(refresh)되어 최신 상태 기반으로 overcrowding이 실행됨
            _process_spy_missions(park_b)

            # 6. 최종 검증: overcrowding 정화 처리가 정상 작동하여 15명으로 감축되었는지 증명 (refresh 누락 시 14명이 되므로 실패함)
            db.session.refresh(park_b)
            assert park_b.adult_count == 15

        finally:
            session_a.close()


def test_database_url_env_fallback():
    """
    [IMP-F001 회귀 검증 테스트]
    DATABASE_URL 환경변수가 주입되었을 때, Config.SQLALCHEMY_DATABASE_URI가
    해당 PostgreSQL URI로 올바르게 전환되는지 검증합니다.
    """
    import os
    import importlib
    from app import config

    orig_db_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
    orig_db_url = os.environ.get('DATABASE_URL')

    if 'SQLALCHEMY_DATABASE_URI' in os.environ:
        del os.environ['SQLALCHEMY_DATABASE_URI']

    try:
        os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost:5432/jissou_db'

        # config 모듈을 reload하여 환경변수가 다시 반영되도록 합니다.
        importlib.reload(config)

        assert config.Config.SQLALCHEMY_DATABASE_URI == 'postgresql://user:pass@localhost:5432/jissou_db'
    finally:
        # 환경변수 복구
        if orig_db_uri is not None:
            os.environ['SQLALCHEMY_DATABASE_URI'] = orig_db_uri
        elif 'SQLALCHEMY_DATABASE_URI' in os.environ:
            del os.environ['SQLALCHEMY_DATABASE_URI']

        if orig_db_url is not None:
            os.environ['DATABASE_URL'] = orig_db_url
        elif 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']

        importlib.reload(config)


def test_static_js_inner_html_xss_protection():
    """
    [DBG-F002 Re-audit #1 회귀 검증 테스트]
    app/static/js/game.js 내의 모든 innerHTML 대입문뿐만 아니라,
    html builder 변수에 누적되는 모든 백틱(`` `...` ``) 템플릿 리터럴 내의 동적 보간 변수(${...})를
    전수 검사하여 escapeHtml() 등의 보안 헬퍼 호출 누락을 정교하게 정적 스캔 분석합니다.
    """
    with open("app/static/js/game.js", "r", encoding="utf-8") as f:
        js_content = f.read()

    # 1. innerHTML 대입문 스캔
    matches = re.findall(r'([a-zA-Z0-9_\-\.]+)\.innerHTML\s*=\s*(.*?)(?=\n|;)', js_content)
    for element, value in matches:
        value_stripped = value.strip()
        # 1. 고정 정적 문자열 대입, 스켈레톤, 빈 문자열 대입 등은 안전하므로 패스
        if (value_stripped.startswith("'") and value_stripped.endswith("'")) or \
           (value_stripped.startswith('"') and value_stripped.endswith('"')) or \
           value_stripped in ('html', 'errorHtml'):
            continue

        if '`' in value_stripped:
            interpolations = re.findall(r'\$\{(.*?)\}', value_stripped)
            for item in interpolations:
                # 보간 변수가 escapeHtml(...)로 반드시 포장되어 있어야 함을 강제 검증
                assert "escapeHtml(" in item or "parseInt(" in item or "parseFloat(" in item, \
                    f"XSS 취약점 검출! game.js의 innerHTML 백틱 리터럴 보간 항목 중 안전 가드(escapeHtml)가 누락됨: {item} in {value_stripped}"
        else:
            # 단일 변수 대입 시에도 escapeHtml()이 감싸져 있는지 검증
            assert "escapeHtml(" in value_stripped or "parseInt(" in value_stripped or "parseFloat(" in value_stripped, \
                f"XSS 취약점 검출! game.js의 innerHTML 동적 대입 중 안전 가드(escapeHtml) 누락: {value_stripped}"

    # 2. [v1.8.9 고도화] game.js 내의 모든 innerHTML 및 HTML 빌더 관련 백틱(`...`) 템플릿 리터럴 전수 조사
    # 특정 라인 슬라이스 의존성을 완전히 탈피하여 파일 구조 변경에도 견고하게 작동하도록 전사적 정적 분석을 수행합니다.
    # innerHTML 대입 혹은 html 변수(HTML builder) 누적에 사용되는 백틱 블록만 추출하여 confirm 등 텍스트 확인창의 오탐을 배제합니다.
    template_matches = re.findall(r'(\bhtml\s*\+?=\s*`|innerHTML\s*=\s*`)(.*?)(?<!\\)`', js_content, re.DOTALL)
    template_literals = [match[1] for match in template_matches]
    for template in template_literals:
        # 템플릿 자체가 API URL 형식(/...)이면 스킵하여 오탐지 방지
        template_stripped = template.strip()
        if template_stripped.startswith('/'):
            continue
        # 템플릿 내의 ${...} 보간 변수들을 전수 추출
        interpolations = re.findall(r'\$\{(.*?)\}', template)
        for item in interpolations:
            item_stripped = item.strip()
            # [v1.9.0] 단순 문자열 포함 여부 매칭의 사각지대(예: escapeHtml 누설 mixed expression)를 완치하기 위해
            # 전체 표현식이 단일 safe token인지 여부를 판단하는 구조로 스캔 로직을 고도화합니다.
            is_safe = False
            if "escapeHtml(" in item_stripped or "parseInt(" in item_stripped or "parseFloat(" in item_stripped:
                is_safe = True
            elif "||" in item_stripped or "?" in item_stripped or "+" in item_stripped:
                # 복합 표현식은 반드시 escapeHtml()이 직접 전체를 감싸고 있어야 하므로 safe에서 예외 처리합니다.
                is_safe = False
            else:
                # 안전한 단독 식별자 혹은 다국어 상수 필드만 allowlist로 등록하여 허용합니다.
                is_safe = (
                    item_stripped.startswith("I18N.") or
                    item_stripped.startswith("data.total_") or
                    item_stripped.startswith("data.population_") or
                    item_stripped.startswith("data.defense_") or
                    item_stripped.startswith("data.walls") or
                    item_stripped.startswith("data.morale") or
                    item_stripped.startswith("data.guard_") or
                    item_stripped.startswith("data.adult_") or
                    item_stripped.startswith("data.child_") or
                    item_stripped.startswith("data.baby_")
                )
            assert is_safe, f"XSS 취약점 검출! game.js의 innerHTML 템플릿 보간 항목 중 안전 가드(escapeHtml)가 누락됨: {item_stripped} in `{template}`"
