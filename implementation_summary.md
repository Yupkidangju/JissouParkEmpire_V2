# 실장석 공원 제국 - 구현 요약 (implementation_summary.md)

> **문서 버전**: v1.7.0  
> **마지막 갱신**: 2026-05-30  
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
| `app/models.py` | 369 | DB 스키마 | 마이그레이션 스크립트 필요 |
| `app/game_engine.py` | 1217 | 핵심 로직 | `process_turn` 순서 변경 시 사이드 이펙트 |
| `app/battle_engine.py` | 331 | 전투 로직 | 약탈 비율 변경 시 밸런스 영향 |
| `app/npc_engine.py` | 248 | NPC AI | 성격별 행동 우선순위 |
| `app/turn_scheduler.py` | 92 | 백그라운드 스케줄 | `app.app_context()` 내에서 DB 접근 |
| `app/dialogues.py` | 169 | 대사 로더 | JSON 파일 경로/인코딩(UTF-8) |
| `app/i18n.py` | 110 | 번역 시스템 | `app.context_processor` 등록 |
| `app/routes/auth_routes.py` | 150 | 인증 라우트 | XSS 입력 검증 유지 |
| `app/routes/game_routes.py` | 1057 | 게임 라우트 | Race Condition 방지 패턴 유지 |

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

*문서 끝*
