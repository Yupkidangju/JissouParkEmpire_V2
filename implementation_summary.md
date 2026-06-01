# 실장석 공원 제국 - 구현 요약 (implementation_summary.md)

> **문서 버전**: v1.8.9
> **마지막 갱신**: 2026-05-31
> **상태**: 동결(Frozen)
> **표준**: `AI_IMPLEMENTATION_DOC_STANDARD.md` 및 `spec.md` 파생

---

## 1. 전체 런타임 흐름

### 1.1 서버 시작 흐름
```
run.py → create_app() → db.init_app() → login_manager.init_app() → csrf.init_app()
      → init_i18n() → register_blueprints() → db.create_all() → _init_npc_parks()
      → init_scheduler() → app.run() / gunicorn
```

### 1.2 HTTP 요청 흐름
```
Client Request → Flask Router → @login_required → current_user.park 확인
            → consume_turn(AP 체크/소비) → game_engine/battle_engine 함수
            → db.session.commit() → flash() → redirect(dashboard)
```

### 1.3 백그라운드 턴 처리 흐름
```
APScheduler (10분) → _process_all_turns() → process_turn(park)
                    → if NPC: process_npc_turn(park) → db.session.commit()
```

### 1.4 클라이언트 런타임 흐름
```
DOMContentLoaded → 메시지 자동 소멸 타이머 → confirm 이벤트 바인딩
                 → 콘페이토 반짝임 → AP 0 경고 → NPC 타이핑 효과
                 → 숫자 입력 검증 → 건설 설명 동적 업데이트
                 → 정찰/침공 모달 이벤트 바인딩 → 알림 폴링 시작
                 → 턴 카운트다운 시작
```

---

## 2. 시스템 분해표

| 시스템 | 책임 파일 | 핵심 클래스/함수 |
|--------|----------|----------------|
| **앱 팩토리** | `app/__init__.py` | `create_app()`, `_init_npc_parks()` |
| **설정/밸런스** | `app/config.py` | `Config`, `GameConfig` |
| **인증** | `app/routes/auth_routes.py` | `login()`, `register()`, `logout()` |
| **게임 라우트** | `app/routes/game_routes.py` | `dashboard`, `gather`, `birth`, `build`, `train`, `attack`, `defend`, `trade_*`, `diplomacy_*`, `ranking`, `scout`, `notifications` |
| **모델/DB** | `app/models.py` | `User`, `Park`, `BuildQueue`, `TrainQueue`, `BattleLog`, `EventLog`, `TradeOffer`, `Diplomacy`, `SpyMission` |
| **핵심 게임 로직** | `app/game_engine.py` | `consume_turn()`, `action_gather()`, `action_birth()`, `action_build()`, `action_train()`, `action_cull()`, `process_turn()`, `_process_*()` |
| **전투 로직** | `app/battle_engine.py` | `execute_battle()`, `_calc_*_power()`, `_calc_losses*()`, `_calculate_loot()`, `_apply_loot()` |
| **NPC AI** | `app/npc_engine.py` | `process_npc_turn()`, `_npc_passive_growth()`, `_get_action_priority()`, `_npc_*()` |
| **턴 스케줄러** | `app/turn_scheduler.py` | `init_scheduler()`, `_process_all_turns()`, `force_process_turn()` |
| **대사/i18n** | `app/dialogues.py` | `_DialogueProxy`, `get_random_dialogue()`, `get_random_dialogues()` |
| **번역 시스템** | `app/i18n.py` | `get_text()`, `init_i18n()`, `set_lang()` |
| **UI 스타일** | `app/static/css/style.css` | CSS 변수, 그리드, 반응형, 애니메이션 |
| **클라이언트 로직** | `app/static/js/game.js` | 메시지 소멸, confirm, 반짝임, 타이핑, 입력 검증, 건설 설명, 모달 트랜지션, 스킬 트리 인터랙션 |
| **템플릿** | `app/templates/*.html` | Jinja2 상속 구조 (base → 각 페이지 + skills.html 모크업 추가) |

---

## 3. 경계 계약 요약

### 3.1 라우트 ↔ 엔진 경계
- 라우트는 **검증/권한/AP 소비**만 담당. 실제 로직은 엔진에 위임.
- `consume_turn(park, ap_cost)`를 반드시 먼저 호출 후 엔진 함수 실행.
- 엔진 함수는 `db.session.commit()`을 직접 호출함 (라우트에서 추가 commit 불필요).

### 3.2 엔진 ↔ 모델 경계
- 엔진은 모델 속성을 직접 변경. `@validates`가 음수를 자동 0으로 클램핑.
- `add_event()`는 항상 `EventLog`를 생성하여 감사 추적.
- 관계 필드(`build_queue`, `train_queue`)는 cascade delete-orphan으로 자동 정리.

### 3.3 클라이언트 ↔ 서버 경계
- 클라이언트는 **표시와 입력 검증**만. 게임 상태 계산 불가.
- 정찰/알림만 AJAX. 나머지는 폼 POST + 리다이렉트.
- CSRF 토큰은 meta 태그 + JS 자동 삽입으로 모든 POST에 적용.

---

## 4. 파일 책임

### 4.1 백엔드 파일

| 파일 | 라인수 | 책임 | 변경 시 주의 |
|------|--------|------|-------------|
| `run.py` | 28 | 엔트리 포인트 | Gunicorn `run:app` 참조 유지 |
| `app/__init__.py` | 109 | 앱 팩토리, 초기화 | NPC 초기화/스케줄러 중복 실행 방지 |
| `app/config.py` | 250 | 상수 중앙 관리 | 모든 수치 변경 시 영향 범위 확인 |
| `app/models.py` | 523 | DB 스키마 | 마이그레이션 스크립트 필요 |
| `app/game_engine.py` | 1649 | 핵심 로직 | `process_turn` 순서 변경 시 사이드 이펙트 |
| `app/battle_engine.py` | 400 | 전투 로직 | 약탈 비율 변경 시 밸런스 영향 |
| `app/npc_engine.py` | 355 | NPC AI | 성격별 행동 우선순위 |
| `app/turn_scheduler.py` | 92 | 백그라운드 스케줄 | `app.app_context()` 내에서 DB 접근 |
| `app/dialogues.py` | 169 | 대사 로더 | JSON 파일 경로/인코딩(UTF-8) |
| `app/i18n.py` | 110 | 번역 시스템 | `app.context_processor` 등록 |
| `app/routes/auth_routes.py` | 150 | 인증 라우트 | XSS 입력 검증 유지 |
| `app/routes/game_routes.py` | 1366 | 게임 라우트 | Race Condition 방지 패턴 유지 |

### 4.2 프론트엔드 파일

| 파일 | 라인수 | 책임 | 변경 시 주의 |
|------|--------|------|-------------|
| `app/static/css/style.css` | 1508 | 전체 스타일 | 반응형 미디어 쿼리 3개(768, 480) |
| `app/static/js/game.js` | 203 | 클라이언트 로직 | `confirm()` 메시지 한국어 고정 |
| `app/templates/base.html` | 113 | 기본 레이아웃 | CSRF meta 태그, 언어 선택 |
| `app/templates/dashboard.html` | 746 | 메인 화면 | Jinja2 변수명과 모델 필드 동기화 |
| `app/templates/trade.html` | 451 | 교역/외교 | 폼 action URL 동기화 |
| `app/templates/ranking.html` | 102 | 랭킹 | 정렬 기준 파라미터 |
| `app/templates/battle_logs.html` | 48 | 전투 기록 | 로그 포맷 |
| `app/templates/login.html` | 41 | 로그인 | `t('key')` 키 존재 확인 |
| `app/templates/register.html` | 49 | 회원가입 | 입력 제한(minlength/maxlength) |
| `app/templates/gameover.html` | 83 | 게임오버 | 통계 필드 |
| `app/templates/skills.html` | 277 | 스킬 트리 | [NEW] 가상 스킬 트리 이스터에그 모크업 |

### 4.3 데이터 파일

| 파일 | 책임 |
|------|------|
| `app/lang/*.json` | UI 번역 문자열 |
| `app/lang/dialogues_*.json` | 행동별 랜덤 대사 |
| `requirements.txt` | Python 패키지 의존성 |

---

## 5. 알고리즘 메모

### 5.1 consume_turn (AP + 턴 쿼터 통합)
```
if AP < ap_cost:
    if turn_quota <= 0: return 실패
    turn_quota -= 1
    process_turn(park)      # 식량/건설/재해 등 13단계 처리
    _sync_npc_turns()       # NPC 동기 처리
    db.session.commit()

# AP가 여전히 부족하면 실패
if AP < ap_cost: return 실패

AP -= ap_cost
return 성공
```

### 5.2 process_turn (13단계)
```
1. turn_count += 1; AP = 3
2. 배치 인원 보유 수에 맞춤
3. 식량 소비 (_process_food_consumption)
4. 자동 카니발리즘 (_process_cannibalism)
5. 건설 진행 (_process_building)
6. 훈련 진행 (_process_training)
7. 성장 (_process_growth)
8. 운치굴 번식 (_process_unchi_breeding)
9. 재해 (_process_disasters)
10. 질병 (_process_disease)
11. NPC 악행 (_process_human_events)
12. 반란 (_process_rebellion)
13. 중독 (_process_addiction)
14. 밀사 (_process_spy_missions)
15. 수용 초과 (_process_overcrowding)
```

### 5.3 전투력 계산 (공격자)
```
power = guards*40 + adults*15 + (boss ? 100 : 0)
if boss_only: power *= 0.7
morale_mult = 1.0 + (morale - 50) * 0.1 / 50
power = floor(power * morale_mult)
```

### 5.4 stochastic_round (소수점 불사 방지)
```
base = int(value)
frac = value - base
if frac > 0 and random() < frac: base += 1
return base
```

### 5.5 원자적 에스크로 (교역 생성)
```
UPDATE parks SET konpeito = konpeito - offer_k, ...
WHERE id = park.id AND konpeito >= offer_k AND ...
```
- `updated == 0`이면 잔액 부족 → 차단
- 성공 시 `db.session.refresh(park)`로 객체 동기화

### 5.6 비관적 락 & 자동 공원 복구 (v1.8.0)
- **보호 모드 비관적 락**: `check_and_enter_protection(park)` 내부에서 `Park.query.with_for_update().first()`를 호출하여 공원 레코드에 DB 락을 걸고 `db.session.refresh(park)`로 최신 데이터로 강제 새로고침하여 Lost Update 차단.
- **자동 공원 복구 및 통합 생성 (create_default_park)**:
```python
def create_default_park(user, name=None):
    if name is None: name = f"{user.username}의 공원"
    park = Park(user_id=user.id, name=name, ...초기자원...)
    db.session.add(park)
    db.session.commit()
    db.session.refresh(user)
    return park
```
- **원자적 재시작**: 기존 삭제와 새 재생성을 단일 트랜잭션으로 처리.
```python
db.session.delete(park)
game_engine.create_default_park(current_user) # 내부에서 최종 1회 commit()만 호출
```

### 5.7 Gunicorn 안전 비관적 락 & NPC 턴 트랜잭션 격리 (v1.8.1)
- **프로세스 직렬화 비관적 락**: 멀티 워커 프로세스 환경에서 교역 생성 및 `_sync_npc_turns` 실행 시 ID 오름차순으로 정렬하여 `Park.query.with_for_update()` 비관적 락을 획득함으로써 데드락을 방지하고 높은 수준의 프로세스 간 직렬화 지원. (참고: SQLite dialect의 특성상 `with_for_update`는 SQL `FOR UPDATE`를 생성하지 않는 no-op이지만, PostgreSQL/MySQL 등 행 락을 지원하는 RDBMS로의 프로덕션 이주를 대비하여 이 소스 코드 아키텍처 및 2-Way Lock Canonical Order 설계를 전개 및 유지하였습니다. SQLite 모드에서는 WAL 모드 및 DB 파일 수준의 단일 쓰기 lock으로 동시성 정합성을 안전하게 상호 보완합니다.)
- **turn_count 중복 연산(NPC Stampede) 방지 가드**:
```python
if npc_park.turn_count >= player_park.turn_count:
    continue  # 이미 해당 턴 진행이 완료된 NPC는 동기화 연산 스킵
```
- **중간 커밋 억제 (commit=False)**:
```python
def action_gather(park, ..., commit=True):
    # ...연산...
    if commit:
        db.session.commit()
```
- NPC AI 턴 진행 시 `commit=False`로 각 엔진 행동(`action_gather/birth/build/train/cull`)들을 호출하여 파편화된 커밋을 방지하고, 루프 맨 마지막에 단 한 번 `db.session.commit()`을 수행해 예외 시 전체 롤백과 원자성 트랜잭션 격리를 구현.

### 5.8 보상 트랜잭션 및 공용 AP 환불 패턴 (v1.8.2)
- **보상 트랜잭션(Compensating Transaction) 기법**: `consume_turn()`에 의한 선행 차감 및 조기 커밋(Early Commit) 아키텍처로 인해 발생하는 트랜잭션 분할(Split Transaction) 상황에서, 비즈니스 로직(행동) 내부의 추가 검증 실패 시 AP 누수를 막는 예외 처리 복구 모델.
- **공용 AP 환불 함수 (`refund_ap`)**:
```python
def refund_ap(park, ap_cost):
    if park.is_destroyed:
        return
    Park.query.filter(Park.id == park.id).update({
        'action_points': Park.action_points + ap_cost
    })
    db.session.commit()
    db.session.refresh(park)
```
- **라우트 연동**: `/gather`, `/birth`, `/build`, `/train`, `/attack`, `/diplomacy/enemy`, `/spy` 라우트에서 비즈니스 로직 실행 실패(`not success` 또는 유효성 기각) 감지 시 `refund_ap(park, N)`을 명시적으로 트리거하여 AP를 안전하게 복구 및 커밋함.

### 5.9 좀비 상태 및 비관적 락 TOCTOU 방지 (v1.8.3)
- **턴 쿼터 진행 후의 멸망 재검증**:
  - `consume_turn()`에서 턴을 소비하여 `process_turn(park)`가 기동된 후, 보스실장의 굶주림(HP <= 0)이나 재해 등으로 인해 공원이 멸망할 경우 즉시 감지하여 차단.
```python
process_turn(park)
db.session.commit()
db.session.refresh(park)
if park.is_destroyed:
    return False, ['공원이 멸망한 데스...']
```
- **비관적 락 획득 후의 멸망 상태 재확인**:
  - `trade_accept` 및 `execute_battle`에서 `with_for_update()` 비관적 락을 얻고 데이터를 새로고침한 직후, 락 대기 시간 동안 상대방이 멸망 상태로 변했는지 재확인하여 교역을 만료 처리하거나 전투를 즉각 기각 롤백함.
```python
# trade_accept 예시
Park.query.filter(Park.id.in_(lock_ids)).with_for_update().all()
db.session.refresh(park)
db.session.refresh(sender)
if park.is_destroyed or sender.is_destroyed:
    # 예외 상황에 따른 롤백 및 알림 처리
```

### 5.10 Cascade Delete 에스크로 및 유닛 유실 방지 (v1.8.4)
- **DB 이벤트 리스너를 통한 자동 환불**:
  - 상대방 공원이 삭제(/restart)되어 관계된 교역(`TradeOffer`)이나 밀사(`SpyMission`)가 Cascade 연쇄 삭제될 때, `before_delete` 이벤트 리스너에서 삭제 대상을 인터셉트하여 환불을 원자적으로 자동 집행함. (v1.8.4 엣지 패치를 적용해 멸망한 공원도 안전하게 환불되도록 가드 개선)
```python
# before_delete 리스너 내 환불 처리 방식 예시
@event.listens_for(TradeOffer, 'before_delete')
def before_trade_delete(mapper, connection, target):
    if target.status == 'pending':
        session = object_session(target)
        if session is not None:
            # 발신자 공원이 세션 내에서 삭제 대상이 아닌 생존 공원인 경우에만 에스크로 자원 환불 (멸망 상태여도 환불 실행)
            sender = session.query(Park).filter(Park.id == target.sender_id).first()
            if sender and sender not in session.deleted:
                sender.konpeito += target.offer_konpeito
                # ... cap 캡핑 처리 ...

@event.listens_for(SpyMission, 'before_delete')
def before_spy_delete(mapper, connection, target):
    if target.status == 'active':
        session = object_session(target)
        if session is not None:
            sender = session.query(Park).filter(Park.id == target.sender_id).first()
            if sender and sender not in session.deleted:
                sender.adult_count += 1
```

### 5.11 교차 외교 중복 생성 및 모순 상태 방지 (v1.8.5)
- **Canonical Ordering 및 2중 비관적 락 강제**:
  - 교차 중복 관계 생성을 차단하기 위해 항상 `park_a_id = min(A, B)`, `park_b_id = max(A, B)`의 정렬 상태로 저장하며, 수락 권한을 판별하기 위해 `initiator_id` 컬럼을 도입함.
  - 외교 상태 변경 시 ID 정렬 오름차순의 2중 비관적 락(`with_for_update()`)을 획득하여 트랜잭션을 철저히 직렬화함.
  - 기존 동맹을 해제하고 적대를 맺거나 관계를 해제할 때, 단일 레코드만 가져와 갱신하는 틈새를 안정적으로 막기 위해 `.update()` 벌크 쿼리를 사용해 두 공원 간의 모든 `active`/`pending` 중복 레코드를 일괄 `dissolved` 해제 처리함.

### 5.12 NPC 개별 트랜잭션 격리 및 Savepoint(Nested) 예외 가드 (v1.8.6)
- **일괄 처리 트랜잭션의 루프 개별 격리**:
  - `_sync_npc_turns`에서 모든 NPC를 한 번에 조회하여 락을 얻는 기존 방식은 루프 내부의 `db.session.commit()`이 실행될 때 아직 처리되지 않은 다른 NPC들의 락도 해제되는 아키텍처적 결함이 있었습니다.
  - 이를 해결하기 위해 루프 외부에서는 단지 정렬된 NPC ID 목록만 추출하고, 루프 내부에서 개별적으로 `with_for_update().first()`를 다시 쿼리하고 독립된 `commit()`을 기동하여 개별 트랜잭션 단위로 완전히 격리되도록 구현했습니다.
- **Nested Transaction (Savepoint)을 통한 비관적 락 보존**:
  - NPC 행동 도중 발생한 예외가 전체 트랜잭션을 롤백하게 되면 락이 유실되고 턴 진행 내역마저 소실되어 무한 스탬피드 버그를 일으켰습니다.
  - 이를 방어하고자 루프 내부의 각 행동 단계마다 `db.session.begin_nested()` 세이브포인트를 생성하여, 예외 발생 시 오직 실패한 그 행동의 상태만 롤백하고 부모 트랜잭션과 비관적 락은 안전하게 보존하도록 조치했습니다.
- **밀사 사보타주 2-Way Lock 격리**:
  - 밀사 임무 처리 시 피해량 산정과 실제 DB UPDATE 간의 TOCTOU 격차를 격리하기 위해 발각 여부 판단 및 산정 시작 전 두 공원에 대해 ID 정렬 2중 비관적 락(`with_for_update()`)을 획득하도록 보강했습니다.

### 5.13 교역 보안 및 좀비 거래 정화 구현 요약 (v1.8.7)
- **교역 거절 IDOR 인가(Authorization) 가드 강제**:
  - `trade_reject(trade_id)` API의 원자적 UPDATE 조건식에 `TradeOffer.receiver_id == park.id` 가드 필터를 탑재하였습니다.
  - 이를 통해 비공개 교역 제안을 받은 당사자(수신자)만이 해당 거래를 거절할 수 있도록 강제하여, 제3자가 거래 ID 변조를 통해 타인의 거래를 임의로 폭파(DoS)시키는 Insecure Direct Object Reference 취약점을 원천 차단했습니다.
- **시장 좀비 거래(Zombie Trades) 선제 정화 조인 필터링**:
  - `trade_market()` 공개 시장 조회 쿼리에 `Park` 모델을 JOIN하고 `Park.is_destroyed == False` 필터를 가드로 강제 탑재하였습니다.
  - 멸망한 발송자(Sender)의 대기 교역 제안이 공개 시장에 계속 노출되어 사용자 경험을 저해하고 수락 시점의 비관적 락 및 TOCTOU 만료 검증 단계에서 불필요한 트랜잭션 경합을 유발하던 현상을 데이터베이스 쿼리 레벨에서 선제 정화하였습니다.

### 5.14 consume_turn 슬로우 패스 AP 복제 Lost Update 차단 구현 (v1.8.8)
- **턴 동기화 락 프리 갭(Lock-free Gap) 보안 결함 해결**:
  - 플레이어의 AP가 부족해 슬로우 패스가 수행되면 턴 진행 후 AP가 10으로 강제 충전되며 플레이어 락이 일단 커밋/해제됩니다.
  - 이후 `_sync_npc_turns()`를 통해 모든 NPC의 턴 진행 연산이 순차적으로 실행되는 동안 플레이어 공원의 락은 해제된 상태(Lock-free Gap)로 노출됩니다.
  - 이 지연 갭 동안 concurrent 다중 요청(패스트 패스)이 AP를 안전하게 선차감하고 커밋 완료하더라도, 원래의 슬로우 패스 스레드가 메모리 상의 Stale AP(10)를 기준으로 최종 AP 차감 연산(`park.action_points -= ap_cost`)을 덮어씀으로써 concurrent 요청의 AP 소모 이력을 지워버려(Lost Update) AP가 무상으로 복제되는 취약점을 수정하였습니다.
- **최종 AP 감산 직전 2차 비관적 락 및 refresh 동기화 구현**:
  - `_sync_npc_turns()` 수행이 종료된 즉시이자 최종 AP 감산 연산 기동 직전에 플레이어 공원 레코드에 대해 다시 한 번 `with_for_update()` 비관적 락을 획득하고 `db.session.refresh(park)`를 명시적으로 실행하도록 구현했습니다.
  - 이를 통해 락 프리 상태의 틈새 런타임 동안 다른 비동기 요청(패스트 패스)들에 의해 차감되어 있는 최신 AP 값을 DB로부터 강제로 리프레시하여 세션 메모리에 동기화하였습니다.
  - 동기화된 최신 AP를 기준으로 `if park.action_points < ap_cost` 여부를 정확히 재검증하고 감산 처리 및 커밋하도록 수정함으로써 Lost Update에 의한 AP 복제/탈취 취약점을 성공적으로 차단하였습니다.

### 5.15 NPC 중첩 플러시 2차 예외 통제 구현 요약 (v1.8.9)
- **공격 함수 내부 DB 커밋의 플러시 전환을 통한 세이브포인트 보존**:
  - NPC 행동 도중 `_npc_attack` 및 `_npc_cunning_attack` 내부에서 `db.session.commit()`이 기동되어 세이브포인트가 영구 종결되고 세션이 파괴되어 `ResourceClosedError`를 유발하던 아키텍처적 결함을 수정했습니다.
  - 이를 방어하고자 내부 공격 연산 시 `commit()` 대신 `db.session.flush()`를 적용하여, 트랜잭션 세이브포인트를 깨뜨리지 않고 메모리 변경 정보만 SQL 쿼리로 DB에 방출되도록 개선했습니다.
- **Savepoint 롤백 실패 시 부모 세션 2차 예외 복구 구축**:
  - `process_npc_turn` 예외 처리부에서 `nested.rollback()` 실패 시 상위 NPC 루프가 폭사하는 2차 위험을 차단하기 위해, nested 롤백 예외 발생 시 `db.session.rollback()`을 호출하는 **2차 롤백 예외 방어 가드**를 마련했습니다.

### 5.16 AP 환불 블랙홀 차단 및 라우터 레벨 명시적 커밋 구현 요약 (v1.8.9)
- **환불 복구 데이터 롤백 유실(AP Blackhole) 원천 봉쇄**:
  - `game_engine.refund_ap()` 호출 시 UPDATE 문이 세션에만 반영되고, 이후 라우터 내부에서 예외 분기나 멸망 분기를 만날 때 `db.session.commit()` 없이 HTTP 리다이렉트가 일어나 데이터베이스 트랜잭션 teardown 시점에 소리소문없이 AP 환불 데이터가 롤백 유실되던 치명적인 결함을 해결했습니다.
- **예외 기각 분기 직후 라우터 레벨 명시적 커밋 강제**:
  - `game_routes.py` 라우터 내의 모든 AP 환불 복구 분기(수집, 출산, 건설, 훈련, 공격 무산, 외교 멸망 TOCTOU, 이미 적대인 경우, IntegrityError 롤백 후, 밀사 파견 실패 등 총 8군데)에 대해 `refund_ap` 호출 즉시 `db.session.commit()`을 호출하도록 강제하여, AP가 롤백되지 않고 즉각적으로 영구 커밋되어 복구되도록 무결성을 달성했습니다.

### 5.17 밀사 임무 처리 후 overcrowding 처리의 2차 비관적 락 가드 구현 (v1.8.9)
- **밀사 복귀 인구 수용 한도 초과 처리의 Lost Update 예방**:
  - `_process_spy_missions`의 끝단에서 밀사 귀환 등으로 인한 수용 한도 초과를 연산하기 위해 `_process_overcrowding(park)`을 호출할 때, 비관적 락 없이 단순 `refresh` 및 메모리 변경 후 `commit`을 구동하여 concurrent 요청(채집/교역)에 의한 DB 상태 변경을 메모리 구버전 데이터로 덮어쓰던(Lost Update) 결함을 제거했습니다.
- **인메모리 연산 직전의 2차 비관적 락 및 refresh 동기화 구현**:
  - 과밀도 정화 처리 진입 직전에 플레이어 공원에 대해 다시 한 번 `with_for_update()` 비관적 락을 획득하고 `db.session.refresh(park)`를 명시적으로 실행하여, 데이터 덮어쓰기 레이스 컨디션을 완전히 차단하고 병렬 요청과의 데이터 정합성 무결성을 강제했습니다.

### 5.18 NPC 턴 진행 및 행동 AI 2단계 트랜잭션 경계 분리를 통한 교착 상태(Deadlock) 결함 [DEADLOCK-F005] 완치 요약 (v1.8.9)
- **_sync_npc_turns()의 2단계 트랜잭션 경계 분리 도입**:
  - 턴 동기화 스케줄러 실행 도중 NPC 기본 턴 처리(`process_turn`) 완료 즉시 명시적인 `db.session.commit()`을 수행하여 선점 락을 원천 소멸시킨 후, 깨끗하게 락이 비워진 상태에서 NPC AI 행동 의사결정 및 공격 기동(`process_npc_turn`)에 진입하는 **2단계 트랜잭션 경계 분리 구조**를 전격 도입했습니다.
- **NPC 행동 최상단 비관적 락(Pessimistic Lock) 완화 제거**:
  - `process_npc_turn()` 시작 부분에서 무조건적으로 대상 NPC 공원 레코드를 `with_for_update()`로 락킹하던 구조를 완화하고 영구히 제거했으며, 이를 단순 `db.session.refresh(park)`만 호출하도록 수정하여 선점 락 현상을 원천 소멸시켰습니다.
- **전투 행동 내 Canonical Locking을 통한 영구 교착 상태 강력 예방**:
  - 기존에는 NPC 스레드가 이미 NPC 락을 선점 쥔 상태에서 `execute_battle()`을 호출하여 `Player`와 `NPC` 락을 오름차순으로 획득하려 하여, `Player.id < NPC.id`인 경우 영구적인 락 순서 역전 교착 상태(Deadlock)에 직면하였습니다.
  - 2단계 분리 및 최상단 비관적 락 해제를 통해, NPC가 공격 기동 시 오직 `execute_battle()` 내부에서만 두 공원의 락을 Canonical Ordering(오름차순)으로 안전하게 동시 획득하여 교착 상태 `[DEADLOCK-F005]` 및 DB 커넥션 풀 고갈 결함 발생 위험을 강력히 예방했습니다.
- **설계적 절충(Trade-off) 및 DB별 격리 보증 명문화**:
  - **Lock-free Gap 절충**: 이 2단계 분리 구조로 인해 NPC 행동 의사결정 및 전투 개시 직전에 발생하는 미세한 무락 갭(Lock-free Gap)은, NPC 행동 결정 시점에 플레이어의 자원 수치가 다소 변할 수 있으나 데드락 회피를 위해 감수한 의도된 설계적 절충(Trade-off)입니다.
  - **SQLite WAL 및 busy_timeout pragma 실제 활성화**: 기본 배포 DB인 SQLite 환경에서 발생할 수 있는 no-op `with_for_update()` 제약을 극복하고 Database Locked 오류를 예방하기 위해, `Engine` 커넥션 이벤트 리스너를 수립하여 연결 즉시 `PRAGMA journal_mode=WAL` 및 `PRAGMA busy_timeout=5000` 설정을 데이터베이스 연결 시점에 강제 자동 주입하도록 완치했습니다.
  - **Row-Lock DB 프로덕션 이주 확장성**:
    - 향후 Gunicorn 다중 워커 프로덕션 환경 하에 PostgreSQL/MySQL 등 실제 행 락 RDBMS로의 이주시에도, 소스 코드 변경 없이 높은 수준의 동시성 격리 무결성을 안전하게 확보하고 확장될 수 있도록 설계가 구성되었습니다. (단, E2E 및 실제 인스턴스 환경 하의 row-lock/deadlock 검증은 현재 Accepted Risk로 수용 상태이며 추후 실 DB 부하/교착 검증 스위트 통과 시 해소됩니다.)

---

## 6. 동결된 공식 요약

| 공식 | 파일 | 위치 |
|------|------|------|
| 전투력 | `battle_engine.py` | `_calc_attack_power_selected`, `_calc_defense_power` |
| 채집 수확 | `game_engine.py` | `action_gather` (random 범위) |
| 출산 결과 | `game_engine.py` | `action_birth` (random + 상한) |
| 훈련 성공 | `game_engine.py` | `_process_training` (0.6 확률) |
| 피해 계산 | `battle_engine.py` | `_calc_losses_selected`, `_calc_losses` |
| 약탈 비율 | `battle_engine.py` | `_calculate_loot` |
| 재해 확률 | `config.py` | `DISASTER_*_CHANCE` |
| 질병 발생 | `game_engine.py` | `_process_disease` (수용률 90% + 운치굴 3개) |
| 반란 확률 | `game_engine.py` | `_process_rebellion` (사기/보스 HP 임계) |
| 중독/해독 | `game_engine.py` | `_process_addiction` (3턴 연속) |

---

## 7. 첫 플레이어블의 최소 범위

플레이어블 버전을 만들기 위해 필요한 최소 파일 세트:

### 7.1 핵심 (없으면 게임 불가)
1. `run.py`
2. `requirements.txt`
3. `app/__init__.py`
4. `app/config.py`
5. `app/models.py` (User, Park, EventLog만)
6. `app/game_engine.py` (채집, 턴 처리, 기아)
7. `app/turn_scheduler.py`
8. `app/routes/auth_routes.py`
9. `app/routes/game_routes.py` (dashboard, gather, debug_next_turn)
10. `app/templates/base.html`
11. `app/templates/login.html`
12. `app/templates/register.html`
13. `app/templates/dashboard.html`
14. `app/static/css/style.css`
15. `app/static/js/game.js`
16. `app/lang/ko.json`

### 7.2 1차 확장 (전투/교역/외교)
- `app/battle_engine.py`
- `app/npc_engine.py`
- `app/templates/trade.html`
- `app/templates/ranking.html`
- `app/templates/battle_logs.html`
- `app/templates/gameover.html`

### 7.3 2차 확장 (다국어/잔혹 컨텐츠)
- `app/dialogues.py`
- `app/i18n.py`
- `app/lang/*.json` (en, ja, zh_tw, zh_cn)
- `app/lang/dialogues_*.json`

---

## 8. 구현 순서 권장

새로운 개발자가 프로젝트를 이해하고 수정하기 위한 권장 순서:

### Phase A: 이해 (1~2시간)
1. `spec.md` 섹션 3~4 읽기 (목표/비목표/동결 결정)
2. `designs.md` 섹션 2~3 읽기 (화면 흐름/레이아웃)
3. `app/config.py` 읽기 (밸런스 상수 파악)
4. `app/models.py` 읽기 (데이터 구조 파악)

### Phase B: 실행 (30분)
5. `python3 -m venv venv && source venv/bin/activate`
6. `pip install -r requirements.txt`
7. `python run.py`
8. 브라우저에서 회원가입 → 채집 → 턴 진행 확인

### Phase C: 핵심 로직 탐색 (2~3시간)
9. `app/game_engine.py`의 `process_turn()` 읽기 (13단계 흐름)
10. `app/game_engine.py`의 `consume_turn()` 읽기 (AP+턴쿼터 통합)
11. `app/battle_engine.py`의 `execute_battle()` 읽기
12. `app/npc_engine.py`의 `process_npc_turn()` 읽기

### Phase D: UI 탐색 (1시간)
13. `app/templates/dashboard.html` 읽기
14. `app/static/css/style.css`의 변수/그리드/반응형 부분 읽기
15. `app/static/js/game.js` 읽기

### Phase E: 수정/확장
16. 밸런스 수정 → `app/config.py`만 변경
17. 새 행동 추가 → `game_engine.py` 함수 + `game_routes.py` 라우트 + `dashboard.html` 폼
18. 새 UI 추가 → `dashboard.html` 또는 별도 템플릿 + CSS

### Phase F: UI/UX 리팩토링 및 Gore-Terminal 최적화
19. `base.html`에 Tailwind CSS CDN 및 커스텀 격자/글로우 설정 반영
20. `dashboard.html` 그리드 재배치 및 실장석 도트 아바타, 6단 AP 게이지 구현
21. `trade.html` 교역소/외교 BBS 고밀도 탭 UI 마이그레이션
22. `skills.html` 가상 스킬 트리 이스터에그 템플릿 추가 및 JS SP 카운터 연결
23. 브라우저 크기 조절을 통한 반응형 적합성 및 정합성 검증

---

## 9. 유지보수 규칙

### 9.1 밸런스 수정
- **무조건** `app/config.py`의 `GameConfig`에서만 수정.
- 하드코딩된 수치 발견 시 `GameConfig`로 이동 후 리팩토링.

### 9.2 DB 스키마 변경
- `app/models.py` 수정 → `migrate_vX_X.py` 스크립트 작성 → 실행 → 문서화.
- SQLite 마이그레이션은 수동 `ALTER TABLE` 또는 테이블 재생성.

### 9.3 버그 수정
- `game_engine.py`의 버그 수정 시 `process_turn` 순서 변경은 **금지** (사이드 이펙트).
- `battle_engine.py`의 버그 수정 시 약탈/피해 공식 변경은 밸런스 팀과 협의.

### 9.4 다국어 추가
- `app/lang/ko.json`에 키 추가 → 나머지 4개 언어 파일에 동일 키 추가 (번역).
- `dialogues_*.json`에 대사 추가 → `dialogues.py`는 자동 로드 (수정 불필요).

### 9.5 보안 수정
- Race Condition 의심 시 `UPDATE-WHERE` 원자적 패턴 적용.
- 사용자 입력은 `request.form.get(type=int)` + `max(0, value)` + `html.escape()` 3중 검증.
- CSRF 토큰 누락 시 `base.html` meta 태그 및 JS 자동 삽입 확인.

---

## 10. 동시성 지원 매트릭스 (Concurrency Support Matrix)

본 프로젝트는 초경량 zero-setup 및 간편 호스팅을 위해 기본 데이터베이스로 SQLite를 적용했으나, 다중 프로세스(Gunicorn) 운영 모델 및 다중 워커 규모의 대규모 프로덕션 환경 동시성을 견디도록 코드를 설계하였습니다. 구체적인 동시성 대응 지원 규격은 다음과 같습니다.

| 운영 조합 | 지원 여부 | 아키텍처 대응 및 완화 전략 |
|-----------|-----------|---------------------------|
| **SQLite + 단일 워커 (Single Worker)** | **공식 권장 (Supported)** | 개발 및 소형 호스팅에서 안정적으로 데이터 일관성(Consistency)이 보장됩니다. SQLite WAL 활성화 및 내부 sequential lock으로 동시 쓰기 정합성을 소화합니다. 다만 SQLite 환경에서 `with_for_update()`는 실제 DB 행 락(Row Lock)을 걸지 않는 무효(no-op) 상태이므로, Flask 개발 서버 구동 시 thread 1개와 단일 동시 쓰기 조건 하에서만 정합성이 온전히 유지됩니다. |
| **SQLite + 다중 워커 (Multi Worker)** | **제한 지원 (Accepted Risk / Limited)** | 다중 프로세스 환경의 동시 다발적 쓰기 요동 시, SQLite 고유의 파일 락 제약으로 인해 `Database Locked` (busy_timeout 초과) 리스크가 존재합니다. 이벤트 리스너를 통한 `PRAGMA busy_timeout=5000` 주입 및 2단계 트랜잭션 경계 분리로 병목을 줄이나, 부하 상황에서의 락 경합은 수용해야 할 한계(Accepted Risk)로 정의합니다. <br>※ **Accepted Risk 상세 규격**:<br>- **책임자(Owner)**: `Project Lead Architect / Eunho Lim`<br>- **수용 사유**: 초경량 zero-setup 및 호스팅 간소화를 위해 SQLite의 태생적 파일 락 제약 및 동시성 쓰기 경합 병목을 수용함.<br>- **운영 제한**: Gunicorn workers는 최대 2개로 제한하며, sync worker 모델 및 단일 thread(thread=1) 기동을 강제함.<br>- **만료 조건**: 동시 활성 유저(DAU) 100명 초과 또는 초당 평균 10회 이상의 DB 쓰기 요청 유발 시.<br>- **재검토 조건**: `Database Locked` (busy_timeout 초과) 에러가 주 3회 이상 감지되거나 동시성 레이스로 인한 유저 데이터 정합성 유실 사고 발생 시 PostgreSQL로의 즉각 강제 전환 프로파일 가동. |
| **PostgreSQL/MySQL + 다중 워커** | **공식 프로덕션 대상 (Target Production / Accepted Risk)** | 상용 대규모 접속 및 배포의 대상 조합입니다. ORM 수준의 2중 ID 정렬(Canonical Order) `with_for_update()` 락 획득 설계를 구현해 두었기 때문에, 실제 RDBMS로 이주 시 네이티브 행 락(Row Lock)이 가동하여 교착 상태(Deadlock) 발생 위험을 고도로 예방한 동시 처리를 지원하도록 설계되었습니다. <br>※ **Accepted Risk 상세 규격 (PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증)**:<br>- **책임자(Owner)**: `Project Lead Architect / Eunho Lim`<br>- **수용 사유**: 현재 개발/테스트 인프라 제약으로 인해 실제 PostgreSQL/MySQL 인스턴스를 통한 다중 worker 부하 및 row-lock/deadlock E2E 검증은 수행하지 않았으며, ID Canonical Ordering 설계적 안전성만을 확보한 상태에서 운영 위험을 잠재적으로 수용함.<br>- **만료 조건**: 프로덕션 DB로 실제 PostgreSQL/MySQL 이주 완료 및 해당 DB 상상 다중 스레드 부하 테스트/교착 검증 스위트를 최초로 수행 및 통과하는 시점.<br>- **재검토 조건**: 실제 RDBMS 프로덕션 이주 후 lock timeout 또는 deadlock 경보가 시스템 상에서 최초로 주 1회 이상 감지되는 시점. |

---

*문서 끝*


---

## 7. 동시성 지원 및 Accepted Risks 추가 규격

### 7.1 PostgreSQL/MySQL 실 DB row-lock/deadlock 미검증 (Accepted Risk)
- **책임자(Owner)**: `Project Lead Architect / Eunho Lim`
- **수용 사유**: 현재 개발/테스트 인프라 제약으로 인해 실제 PostgreSQL/MySQL 인스턴스를 통한 다중 worker 부하 및 row-lock/deadlock E2E 검증은 수행하지 않았으며, ID Canonical Ordering 설계적 안전성만을 확보한 상태에서 운영 위험을 잠재적으로 수용함.
- **만료 조건**: 프로덕션 DB로 실제 PostgreSQL/MySQL 이주 완료 및 해당 DB 상에서 다중 스레드 부하 테스트/교착 검증 스위트를 최초로 수행 및 통과하는 시점.
- **재검토 조건**: 실제 RDBMS 프로덕션 이주 후 lock timeout 또는 deadlock 경보가 시스템 상에서 최초로 주 1회 이상 감지되는 시점.
