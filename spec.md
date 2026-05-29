# 실장석 공원 제국 (Jissou Park Empire) - 마스터 스펙 (spec.md)

> **문서 버전**: v1.7.0  
> **마지막 갱신**: 2026-05-30  
> **상태**: 동결(Frozen) — 구현 참조용  
> **언어**: 한국어 (기준 문서)

---

## 1. 문서 운영 규칙

- 이 문서는 `AI_IMPLEMENTATION_DOC_STANDARD.md` 기준의 **마스터 스펙**이다.
- 코드베이스와 불일치가 발견되면 코드가 우선이며, 이 문서는 즉시 갱신해야 한다.
- 모든 수치는 `app/config.py`의 `GameConfig`를 Source of Truth로 삼는다.
- 모든 타입은 `app/models.py`의 SQLAlchemy 모델을 Source of Truth로 삼는다.
- 문서 간 불일치가 발생하면 `spec.md` → `designs.md` → `implementation_summary.md` 순으로 우선순위를 적용한다.

---

## 2. 프로젝트 정체성

- **이름**: 실장석 공원 제국 (Jissou Park Empire)
- **장르**: 턴제 전략 웹 게임 (Turn-Based Strategy Web Game)
- **영감**: BBS 도어 게임 (Ant War, Solar Realms Elite)
- **세계관**: 실장석(じっそうせき) — 실장석 군락을 경영하는 보스가 되어 공원을 발전시키고 다른 공원과 경쟁/교류
- **타겟 플랫폼**: 웹 브라우저 (데스크톱 + 모바일 반응형)
- **플레이어 수**: 솔로 (싱글 플레이어) + NPC 멀티 시뮬레이션

---

## 3. 목표와 성공 기준

### 3.1 목표
- 플레이어는 회원가입 후 자신의 공원을 생성하여 실장석 군락을 경영한다.
- 채집 → 출산 → 건설 → 훈련 → 침공의 핵심 루프를 반복하며 공원을 성장시킨다.
- NPC 공원과의 교역/외교/전투를 통해 단기/중기 목표를 달성한다.
- 보스실장이 죽지 않도록 식량과 병력을 관리하며 최대한 많은 턴을 생존한다.

### 3.2 성공 기준
- 회원가입 → 공원 생성 → 첫 채집 → 첫 출산까지 3분 이내 플레이 가능
- 한 세션(15턴) 내에서 게임오버 확률 < 30% (보호 모드 포함)
- NPC 8개 공원과의 상호작용이 10분 간격으로 자연스럽게 진행
- 모바일 브라우저에서도 대시보드 전체 기능 사용 가능

### 3.3 비목표 (Non-Goals)
- 실시간 멀티플레이어 PvP (동시 접속 플레이어 간 실시간 전투 없음)
- 클라이언트 측 계산/저장 (모든 게임 로직은 서버 사이드)
- 3D 그래픽 / Canvas 렌더링 (HTML/CSS 기반 레트로 터미널 UI)
- 결제/프리미엄 콘텐츠
- 서버 간 클러스터링 (단일 인스턴스 SQLite 기반)

---

## 4. 동결된 핵심 결정 (Frozen Decisions)

| 결정 | 값 | 동결 이유 |
|------|-----|----------|
| 백엔드 프레임워크 | Python Flask + SQLAlchemy | 경량, 빠른 프로토타이핑, 라즈베리파이 배포 최적화 |
| 데이터베이스 | SQLite (파일 기반) | 단일 서버, 제로 설정, 백업이 파일 복사 |
| 프론트엔드 | 서버 사이드 렌더링 (Jinja2) + 순수 JS | SEO 불필요, 상태 동기화 단순화, APK 이식 시 로직 재사용 |
| 턴 시스템 | AP(행동포인트) + 턴 쿼터(시간 충전) | 모바일 친화적이며 플레이어 부담 감소 |
| 스케줄러 | APScheduler (백그라운드) | 10분 간격 자동 턴 처리, 경량 |
| 다국어 | JSON 파일 기반 i18n | APK 이식 시 그대로 재사용 가능 |
| UI 테마 | BBS 레트로 터미널 × 실장석 감성 | 브랜드 정체성 |
| UI 프레임워크 | Tailwind CSS CDN | Jinja2 호환성 및 신속한 반응형 레트로 스타일링 구현 |
| 가상 스킬 트리 | skills.html (이스터에그 모크업) | 향후 보스 스킬 시스템 확장을 대비한 백로그 UI 선제공 |
| 난이도 커브 | 보호 모드 + 잔혹 이벤트 | 신규 유저 보호 + 중후반 긴장감 |
| NPC 수 | 8개 (서버 시작 시 자동 생성) | 밸런스 검증된 수치 |
| 게임오버 조건 | 보스 HP ≤ 0 | 단일 명확한 실패 조건 |

---

## 5. 기술 스택과 아키텍처 원칙

### 5.1 기술 스택

| 계층 | 기술 | 버전 |
|------|------|------|
| 언어 | Python | 3.9+ |
| 웹 프레임워크 | Flask | >=3.0 |
| ORM | Flask-SQLAlchemy | >=3.1 |
| 인증 | Flask-Login | >=0.6 |
| 보안 | Flask-WTF (CSRF) | >=1.2 |
| 스케줄러 | APScheduler | >=3.10 |
| DB | SQLite | 3 (파일: `game.db`) |
| 템플릿 | Jinja2 | (Flask 내장) |
| CSS/JS | 순수 CSS3 / ES6 + Tailwind CSS CDN | CSS 변수와 유틸리티 클래스의 하이브리드 결합 |
| 폰트 | IBM Plex Mono, Noto Sans KR | Google Fonts CDN |

### 5.2 아키텍처 원칙
- **서버 사이드 진실(Server-Side Truth)**: 모든 게임 상태 변경은 서버에서만 처리. 클라이언트는 표시만 담당.
- **AP + 턴 쿼터 분리**: 행동은 AP를 소비. AP가 부족하면 턴 쿼터 1개를 소비하여 턴을 진행하고 AP를 리셋.
- **원자적 트랜잭션**: 자원 교환(교역/약탈)은 SQL `UPDATE-WHERE` 원자적 연산으로 Race Condition 방지.
- **음수 방어**: 모델 레벨 `@validates` 데코레이터로 DB에 음수 값 저장 불가.
- **NPC 동기화**: 플레이어가 턴 쿼터를 소비할 때만 NPC도 `process_turn` + `process_npc_turn` 실행.

---

## 6. 런타임/빌드 파이프라인

### 6.1 엔트리 포인트
- `run.py` — 개발 서버 (`app.run(host='0.0.0.0', port=5000, debug=True)`)
- Gunicorn — 프로덕션 (`gunicorn --bind 0.0.0.0:8000 "run:app"`)

### 6.2 앱 팩토리 흐름 (`app/__init__.py`)
1. `create_app()` 호출
2. `Config` 로드 → Flask 인스턴스 생성
3. 확장 초기화: `db`, `login_manager`, `csrf`
4. i18n 초기화 (`init_i18n`)
5. 블루프린트 등록: `auth_bp`, `game_bp`
6. 루트 URL 리다이렉트 (로그인 여부)
7. DB 테이블 생성 (`db.create_all`)
8. NPC 공원 자동 생성 (`_init_npc_parks`)
9. 턴 스케줄러 시작 (`init_scheduler`)

### 6.3 자동 초기화
- 서버 시작 시 `is_npc=True`인 공원이 `NPC_INITIAL_COUNT` 미만이면 자동 생성.
- NPC 이름은 `NPC_PARK_NAMES` 풀에서 중복 없이 랜덤 선택.
- NPC 성격은 `NPC_PERSONALITIES` 중 랜덤.

---

## 7. 디렉터리 구조

```
JissouParkEmpire/
├── run.py                    # 엔트리 포인트
├── requirements.txt          # Python 의존성
├── app/
│   ├── __init__.py          # Flask 앱 팩토리, NPC 초기화, 스케줄러
│   ├── config.py            # Flask Config + GameConfig (밸런스 상수)
│   ├── models.py            # SQLAlchemy 모델 (User, Park, BuildQueue, TrainQueue, BattleLog, EventLog, TradeOffer, Diplomacy, SpyMission)
│   ├── game_engine.py       # 핵심 게임 로직 (채집, 출산, 건설, 훈련, 턴 처리)
│   ├── battle_engine.py     # 전투/약탈 시뮬레이션
│   ├── npc_engine.py        # NPC AI 행동 결정
│   ├── turn_scheduler.py    # APScheduler 기반 자동 턴 처리
│   ├── dialogues.py         # i18n 대사 로더 (JSON 기반)
│   ├── i18n.py             # 다국어 번역 시스템
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth_routes.py   # 인증 (회원가입, 로그인, 로그아웃)
│   │   └── game_routes.py   # 게임 행동, 교역, 외교, 랭킹, 정찰, 알림 API
│   ├── templates/           # Jinja2 HTML 템플릿
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   ├── trade.html
│   │   ├── ranking.html
│   │   ├── battle_logs.html
│   │   ├── gameover.html
│   │   └── skills.html      # [NEW] 가상 스킬 트리 모크업 터미널
│   ├── static/
│   │   ├── css/style.css    # 레트로 터미널 스타일시트
│   │   └── js/game.js       # 클라이언트 스크립트 (타이머, 모달, 폴링)
│   └── lang/                # 다국어 JSON 파일
│       ├── ko.json, en.json, ja.json, zh_tw.json, zh_cn.json
│       └── dialogues_ko.json, dialogues_en.json, ...
├── spec.md                  # 이 문서 (마스터 스펙)
├── designs.md               # UI/UX 설계도
├── implementation_summary.md # 시스템 분해 및 구현 순서
├── DESIGN_DECISIONS.md      # 아키텍처 결정 기록
├── audit_roadmap.md         # 감사 기준 및 로드맵
├── lessons_learned.md       # 기술 부채 및 위험 요소
├── BUILD_GUIDE.md          # 빌드 및 배포 가이드
├── CHANGELOG.md             # 변경 이력
└── README.md                # 프로젝트 소개 (다국어)
```

---

## 8. 핵심 동작 정의

### 8.1 게임 핵심 루프
```
[플레이어 접속] → [턴 충전(recharge_turns)] → [AP 소비 행동] → 
[AP 부족 시 턴 소비(consume_turn) → process_turn 실행] → 
[NPC 동기 처리] → [결과 플래시 메시지] → [대시보드 갱신]
```

### 8.2 상태 전이 다이어그램
```
[신규 공원] --(가입)--> [활성 공원]
[활성 공원] --(턴 진행)--> [자원 소비/이벤트 발생]
[활성 공원] --(보스 HP=0)--> [멸망(is_destroyed=True)]
[멸망] --(재시작)--> [신규 공원]
```

### 8.3 행동별 AP 비용
| 행동 | AP 비용 | 턴 쿼터 소비 |
|------|---------|-------------|
| 채집 | 1 | AP 부족 시 1턴 |
| 출산 | 2 | AP 부족 시 1턴 |
| 건설 | 1 | AP 부족 시 1턴 |
| 훈련 | 1 | AP 부족 시 1턴 |
| 침공 | 2 | AP 부족 시 1턴 |
| 방어 배치 | 1 | AP 부족 시 1턴 |
| 솎아내기 | 0 | 없음 (즉시) |
| 적대 선언 | 1 | AP 부족 시 1턴 |
| 관계 해제 | 1 | AP 부족 시 1턴 |
| 질병 치료 | 0 | 없음 |
| 밀사 파견 | 1 | 없음 (별도 시스템) |

---

## 9. 시스템 명세

### 9.1 인증 시스템
- **User 모델**: `id`, `username` (unique, 2~20자), `password_hash` (werkzeug generate_password_hash), `created_at`, `last_login`
- **Park 모델**: `user_id` (nullable, NPC는 null) — 1:1 관계
- **가입 시**: User 생성 → Park 자동 생성 (초기 자원 적용)
- **XSS 방어**: 가입 시 아이디/공원명에 `<>&"'/\` 문자 차단 (정규식)

### 9.2 턴 쿼터 시스템
- **최대 보유 턴**: `TURN_QUOTA_MAX = 15`
- **초기 턴**: `TURN_QUOTA_INITIAL = 3`
- **충전 속도**: `TURN_REGEN_SECONDS = 1200` (20분)
- **충전 방식**: 접속 시 `last_turn_regen_at` 타임스탬프 기준 온디맨드 계산
- **소비 방식**: `consume_turn(park, ap_cost)` — AP가 부족하면 턴쿼터 1 소비 → `process_turn()` → AP=3 리셋
- **NPC 동기**: `TURN_NPC_SYNC = True` (플레이어 턴 소비 시 NPC도 진행)

### 9.3 보호 모드 시스템
- **진입 조건**: `guard_count < PROTECT_GUARD_MIN(5)` OR `adult_count < PROTECT_ADULT_MIN(15)`
- **효과**: 침공 불가 + 침공당하지 않음
- **자동 리셋**: 진입 시 자원/인구가 리셋값 미만이면 보충
  - `PROTECT_RESET_ADULTS = 5`, `PROTECT_RESET_CHILDREN = 15`, `PROTECT_RESET_BABIES = 8`
  - `PROTECT_RESET_TRASH = 50`, `PROTECT_RESET_KONPEITO = 8`, `PROTECT_RESET_MATERIAL = 80`
  - 사기 최소 30, 보스 HP 최소 50
- **해제**: `guard_count >= 5` AND `adult_count >= 15`

### 9.4 채집 시스템
- **인력 배치**: 성체실장 + 자실장 지정 (보유 수 초과 불가)
- **성체실장 수확**: 음쓰 `random.randint(8, 12)`, 자재 `random.randint(3, 5)`, 콘페이토 5% 확률
- **자실장 수확**: 음쓰 `random.randint(2, 4)`, 자재 `random.randint(1, 2)`, 콘페이토 2% 확률
- **랜덤 이벤트**: 쓰레기통 대박(3%, ×3), 야생 포획(5%), 까마귀 습격(3%, 자실장 -1)
- **패널티**: 쓰레기장 철거(수확 50% 감소), 콘페이토 중독(수확 50% 감소)
- **태업**: `strike_turns > 0` 시 채집 불가

### 9.5 출산 시스템
- **비용**: 2 AP + 30 NP
- **기본 결과**: 자실장 `random.randint(3, 6)`, 저실장 `random.randint(1, 3)`
- **잔혹 이벤트**:
  - 사산 5%: 식량만 소비, 사기 -5
  - 대량 출산 8%: 자실장 8~12마리
  - 기형 출산 10%: 저실장 -1, 사기 -3
  - 모체 사망 2%: 성체 -1, 사기 -10
  - 기아 포식 3%: 자실장 -1~2, 고기로 전환, 사기 -15
- **인구 상한**: `population_cap` 초과 시 자실장 차단
- **저실장 상한**: `baby_cap = unchi_holes * 10`, 최소 `BASE_BABY_CAP = 5` 보장

### 9.6 건설 시스템
- **건물 목록**:
  | ID | 이름 | 자재 | 턴 | 효과 |
  |---|------|------|-----|------|
  | cardboard_house | 골판지집 | 30 | 3 | 수용 인원 +15 |
  | unchi_hole | 운치굴 | 20 | 2 | 저실장 수용 +10 |
  | storage_hole | 저장굴 | 25 | 2 | 콘페이토+25, 음쓰+100, 자재+50 상한 |
  | wall | 방벽 | 40 | 4 | 방어력 20% 보너스 |
  | watchtower | 감시탑 | 35 | 3 | 적 정찰 상세 정보 획득 |
- **태업**: `strike_turns > 0` 시 건설 불가

### 9.7 훈련 시스템
- **비용**: 1 AP + 50 NP
- **기간**: 3턴
- **성공률**: 60% (`TRAIN_SUCCESS_RATE = 0.6`)
- **성공**: 성체 -1 → 경호 +1
- **실패**: 성체 +1 (복귀)

### 9.8 솎아내기 (도살)
- **비용**: 0 AP (즉시)
- **저실장 → 식량**: 고기 1개 (5NP)
- **저실장 → 자재**: 3
- **자실장 → 식량**: 고기 2개 (10NP)
- **자실장 → 자재**: 5

### 9.9 전투 시스템
- **출정 인력**: 경호실장/성체실장 각각 지정 (방어 배치 인원 제외한 가용 인력)
- **보스 참전**: 전투력 +100, 단독 출전 시 전투력 30% 패널티 + 승리해도 HP 3~8 감소
- **전투력 계산**:
  - 공격력: `send_guards * 40 + send_adults * 15 + (boss ? 100 : 0)` × 사기 보정
  - 방어력: `(guards * 40 + adults * 15 + children * 2)` × 방벽 보너스(개당 20%) × 감시탑 보너스(10%) × 사기 보정
  - 사기 보정: `1.0 + (morale - 50) * 0.1 / 50`
- **승패 판정**: 공격력 × random(0.8~1.2) > 방어력 × random(0.8~1.2)
- **피해 계산**:
  - 승자: 5~20% 손실
  - 패자: 20~50% 손실
  - 소수부는 `stochastic_round()` (확률적 반올림)로 처리
- **약탈 비율**:
  - 콘페이토 30~60%, 음쓰 20~40%, 자재 10~30%, 저실장 30~50%, 자실장 10~20%
- **적대 보너스**: 적대 관계 시 약탈 +20%
- **보스 피해**: 패배 시 보스 HP -10~25 (대패 시 추가 피해)

### 9.10 식량/기아 시스템
- **영양 포인트(NP)**:
  - 콘페이토: 10NP/개
  - 음식물 쓰레기: 1NP/개
  - 식용 고기(저실장): 5NP/개
  - 식용 고기(자실장): 10NP/개
- **소비량/턴**:
  - 경호실장: 4NP
  - 성체실장: 3NP
  - 자실장: 1NP
  - 저실장: 0.5NP
- **소비 우선순위**: 음쓰 → 고기 → 콘페이토
- **3턴 연속 음쓰**: 사기 -5
- **기아 시**: 저실장 → 자실장 → 성체 순서로 사망 → 모두 죽으면 보스 HP -10/턴

### 9.11 잔혹 컨텐츠 시스템

#### 재해 (턴마다 확률)
| 재해 | 확률 | 효과 |
|------|------|------|
| 폭우 | 5% | 골판지집 -1, 수용 -15 |
| 한파 | 3% | 저실장 30% + 자실장 10% 동사 (방벽 시 50% 감소) |
| 살충제 | 2% | 운치굴 저실장 50% 사망 |
| 쥐떼 | 4% | 음쓰 30% + 저실장 20% |
| 고양이 | 3% | 자실장 1~3 사망 |
| 쓰레기장 철거 | 1% | 3턴간 채집 -50% |

#### 질병
- **발생 조건**: 수용률 ≥ 90% AND 운치굴 ≥ 3개
- **발생 확률**: 10%/턴
- **지속**: 3~5턴
- **피해**: 저실장 매 턴 15%, 자실장 매 턴 5% 사망
- **치료**: 콘페이토 5개 소비
- **전투력**: -20%

#### 반란
- **자실장 탈주**: 사기 ≤ 20 시 10%/턴, 탈주율 15%
- **성체 태업**: 사기 ≤ 30 시 20%/턴, 2턴간 채집/건설 불가
- **경호 쿠데타**: 사기 ≤ 20 AND 보스 HP ≤ 30 시 10%/턴, 보스 HP -30, 경호 50% 이탈

#### 콘페이토 중독
- **발생**: 3턴 연속 콘페이토만 섭취
- **효과**: 사기 -20 (콘페이토 없을 때), 채집 효율 50% 감소
- **해독**: 3턴 연속 콘페이토 미섭취

#### 자동 카니발리즘
- **발동**: 식량 0 시 자동
- **효과**: 경호실장이 자실장 강제 포식 (경호 1마리당 20%/턴)
- **사기**: -15

#### NPC 악행
| 이벤트 | 확률 | 효과 |
|--------|------|------|
| 학대자 | 2% | 자실장 3~5 납치 |
| 실험체 | 1% | 성체 1 사라짐 |
| 어린이 장난 | 4% | 골판지집 파괴 또는 사기 -5 |
| 착한 인간 | 5% | 콘페이토 3~5 + 음쓰 10~20 선물 |
| 펫샵 | 1% | 자실장 2 납치 |

### 9.12 밀사 시스템
- **비용**: 1 AP + 성체 1마리 (파견)
- **기간**: 3턴 후 귀환
- **발각 확률**: 40% (감시탑 보유 시 +30% 탐지 보너스)
- **성공 시**: 적 식량 10~20% 파괴 + 저실장 5마리 도살, 파견 성체 복귀
- **발각 시**: 밀사 처형, 적에게 알림

### 9.13 교역 시스템
- **자원 종류**: 콘페이토, 음쓰, 자재, 저실장
- **에스크로**: 제안 시 즉시 자원 선차감 (원자적 UPDATE-WHERE)
- **상태 흐름**: `pending` → `accepted`/`rejected`/`cancelled`/`expired`
- **동시 제한**: 유저당 최대 10개 pending 교역
- **쿼리 제한**: incoming/outgoing 각 50개 limit (DoS 방지)
- **수락 로직**: 뺄셈(줄 것) 먼저 → 덧셈(받을 것) 나중 → cap 적용

### 9.14 외교 시스템
- **동맹**: 요청→수락 구조 (NPC는 즉시 수락). 침공 불가.
- **적대**: 일방적 선언 (1AP). 약탈 +20% 보너스.
- **관계 해제**: 1AP 소비. 상태 → `dissolved`.

---

## 10. 경계 타입과 계약

### 10.1 핵심 상태 타입 (Park 모델 주요 필드)

```python
# 인구
boss_hp: int          # 0~100 (0이면 게임오버)
guard_count: int      # 0~
adult_count: int      # 0~
child_count: int      # 0~
baby_count: int       # 0~

# 자원
konpeito: int         # 0~konpeito_cap
trash_food: int       # 0~trash_food_cap
meat_stock: int       # 0~
material: int         # 0~material_cap

# 상한
konpeito_cap: int     # 기본 50
trash_food_cap: int   # 기본 200
material_cap: int     # 기본 100
population_cap: int   # 기본 20 (골판지집 추가 시 +15/동)

# 게임 상태
action_points: int    # 0~3 (턴 시작 시 3 리셋)
turn_count: int       # 0~
turn_quota: int       # 0~15
last_turn_regen_at: datetime
is_destroyed: bool    # False/True
morale: int           # 0~100

# 잔혹 컨텐츠 상태
disease_turns: int         # 0=건강, 1~5=감염
is_addicted: bool          # 콘페이토 중독
konpeito_consecutive: int   # 연속 콘페이토 섭취 턴
addiction_clean_turns: int  # 해독 중 미섭취 턴
gather_penalty_turns: int  # 채집 패널티 남은 턴
strike_turns: int          # 태업 남은 턴
```

### 10.2 EventLog 타입
- `event_type`: `gather`, `build`, `birth`, `cull`, `battle`, `starve`, `train`, `npc`, `trade`, `diplomacy`, `disease`, `cannibalism`, `rebellion`, `addiction`, `spy`, `sabotage`, `human_evil`, `human_good`, `gameover`, `morale`, `overcrowd`, `growth`, `breeding`, `protect`, `birth_fail`, `birth_death`

### 10.3 TradeOffer 타입
- `status`: `pending`, `accepted`, `rejected`, `expired`, `cancelled`, `processing`
- `offer_*` / `request_*`: konpeito, trash, material, babies (모두 음수 불가)

### 10.4 Diplomacy 타입
- `relation_type`: `ally`, `enemy`
- `status`: `pending`, `active`, `rejected`, `dissolved`

### 10.5 SpyMission 타입
- `mission_type`: `sabotage`, `intel`
- `status`: `active`, `success`, `detected`, `returned`

---

## 11. 저장/설정/진행 정책

### 11.1 데이터베이스
- **엔진**: SQLite (`sqlite:///game.db`)
- **ORM**: SQLAlchemy 2.0 (`db = SQLAlchemy()` → `db.init_app(app)`)
- **세션**: Flask 요청 컨텍스트 내에서 `db.session` 사용. 스케줄러 작업은 `app.app_context()` 내에서 실행.
- **마이그레이션**: 수동 Python 스크립트 (`migrate_v1_1.py`, `migrate_v1_2.py`)

### 11.2 초기 저장값 (신규 가입 시)
```python
boss_hp = 100
guard_count = 0
adult_count = 3
child_count = 10
baby_count = 5
konpeito = 5
trash_food = 30
meat_stock = 0
material = 50
konpeito_cap = 50
trash_food_cap = 200
material_cap = 100
population_cap = 20
morale = 50
action_points = 3
turn_quota = 3
```

### 11.3 NPC 초기값 (랜덤 범위)
```python
boss_hp = 100
guard_count = random.randint(1, 3)
adult_count = random.randint(3, 8)
child_count = random.randint(5, 15)
baby_count = random.randint(3, 10)
konpeito = random.randint(2, 8)
trash_food = random.randint(20, 50)
meat_stock = random.randint(0, 5)
material = random.randint(30, 80)
morale = random.randint(40, 70)
```

### 11.4 게임오버/재시작
- **조건**: `boss_hp <= 0` → `is_destroyed = True`
- **화면**: `gameover.html` (멸망 턴 수, 잔존 인구 표시)
- **재시작**: 기존 Park 삭제(cascade) → 새 Park 생성 (default 값 자동 적용)

---

## 12. 동결된 공식

### 12.1 전투력
```
total_combat_power = floor(
    (100 + guards*40 + adults*15 + children*2) * (1.0 + (morale-50)*0.1/50)
)

defense_power = floor(
    (def_guards*40 + def_adults*15) * (1.0 + walls*0.2)
)
```

### 12.2 채집 수확 (성체 1마리 기준)
```
trash = random(8, 12)
material = random(3, 5)
konpeito = 1 if random() < 0.05 else 0
```

### 12.3 출산
```
children = random(3, 6)  # 기본
babies = random(1, 3)    # 기본

# 대량 출산 (8%): children = random(8, 12)
# 기형 (10%): babies -= 1

# 인구 상한 적용
children = min(children, population_cap - total_population)
babies = min(babies, max(5, unchi_holes*10) - baby_count)
```

### 12.4 훈련
```
success = random() < 0.6
if success: guard += 1
else: adult += 1  # 복귀
```

### 12.5 전투 피해 (승자/패자)
```
# 공격자 출정 유닛
loss_rate = random(0.05, 0.2)  # 승자
loss_rate = random(0.2, 0.5)   # 패자

guard_loss = stochastic_round(send_guards * loss_rate)
adult_loss = stochastic_round(send_adults * loss_rate)

# stochastic_round: int(value) + (1 if random() < frac else 0)
```

### 12.6 약탈
```
loot_konpeito = floor(defender.konpeito * random(0.3, 0.6))
loot_trash    = floor(defender.trash_food * random(0.2, 0.4))
loot_material = floor(defender.material * random(0.1, 0.3))
loot_babies   = floor(defender.baby_count * random(0.3, 0.5))
loot_children = floor(defender.child_count * random(0.1, 0.2))
```

### 12.7 재해
```
# 폭우 (5%): cardboard_houses -= 1; population_cap = max(5, cap-15)
# 한파 (3%): baby_dead = floor(babies*0.3); child_dead = floor(children*0.1)
#           if walls > 0: baby_dead //= 2; child_dead //= 2
# 쥐떼 (4%): trash -= floor(trash*0.3); babies -= floor(babies*0.2)
```

---

## 13. 실데이터 기준표

### 13.1 초기 플레이어 공원 (가입 시)
```json
{
  "name": "(플레이어 입력)",
  "boss_hp": 100,
  "guard_count": 0,
  "adult_count": 3,
  "child_count": 10,
  "baby_count": 5,
  "konpeito": 5,
  "trash_food": 30,
  "meat_stock": 0,
  "material": 50,
  "konpeito_cap": 50,
  "trash_food_cap": 200,
  "material_cap": 100,
  "population_cap": 20,
  "morale": 50,
  "action_points": 3,
  "turn_quota": 3,
  "cardboard_houses": 1
}
```

### 13.2 NPC 공원 예시 ("콘페이토 동산")
```json
{
  "name": "콘페이토 동산",
  "is_npc": true,
  "npc_personality": "peaceful",
  "boss_hp": 100,
  "guard_count": 2,
  "adult_count": 5,
  "child_count": 8,
  "baby_count": 6,
  "konpeito": 4,
  "trash_food": 35,
  "meat_stock": 0,
  "material": 55,
  "morale": 55
}
```

### 13.3 1턴 소비 시뮬레이션 (성체3/자실장10/저실장5, 아무 행동 안 함)
```
NP 필요량: 3*3 + 10*1 + 5*0.5 = 21.5 NP
보유: 30 음쓰 (30NP)
→ 음쓰 22개 남음 (30 - 21 = 9, 0.5NP는 음쓰 1개로 커버)
→ 실제로는 _consume_np가 정수 우선 소비: 21NP = 음쓰 21개 소비
```

### 13.4 건설 완료 시뮬레이션 (골판지집)
```
비용: 자재 30, 3턴
→ 3턴 후 population_cap += 15
→ cardboard_houses += 1
```

---

## 14. 단계별 로드맵 (구현 순서)

### Phase 0: 기반 (완료)
1. Flask 앱 팩토리 + SQLite 연결
2. User/Park 모델 + 인증 라우트
3. 기본 대시보드 템플릿

### Phase 1: 핵심 루프 (완료)
4. 채집/출산/건설/훈련 엔진 (`game_engine.py`)
5. 턴 스케줄러 (`turn_scheduler.py`)
6. 기본 CSS/JS 레트로 UI

### Phase 2: 전투 (완료)
7. 전투 엔진 (`battle_engine.py`)
8. 침공/방어 라우트
9. 전투 기록 페이지

### Phase 3: NPC (완료)
10. NPC 엔진 (`npc_engine.py`)
11. 5종 성격별 AI 행동
12. 랭킹/정찰 시스템

### Phase 4: 교역/외교 (완료)
13. TradeOffer/Diplomacy 모델
14. 교역소 UI (`trade.html`)
15. 실시간 알림 API

### Phase 5: 다국어 (완료)
16. i18n 모듈 + JSON 번역 파일
17. 템플릿 전체 i18n 적용

### Phase 6: 잔혹 컨텐츠 (완료)
18. 재해/질병/반란/중독/카니발리즘
19. 밀사 시스템
20. 출산 잔혹 이벤트

### Phase 7: 모바일/밸런스 (완료)
21. 턴 쿼터 시스템 (모바일 친화)
22. 보호 모드 시스템
23. 반응형 CSS

### Phase 8: 보안/안정화 (완료)
24. 에스크로 교역 (원자적 UPDATE)
25. XSS 방어 (escapeHtml)
26. 음수 방어 (@validates)
27. 소수점 불사 부대 방지 (stochastic_round)

### Phase 9: 미래 (미정)
28. 안드로이드 APK 빌드 (Kivy/BeeWare)

### Phase 10: UI/UX 리팩토링 및 Gore-Terminal 디자인 시스템 반영 (완료)
29. [Base] Tailwind CSS CDN 도입 및 `base.html` CRT 효과 레이어 탑재
30. [Dashboard] 대시보드 그리드 리팩토링, 실장석 도트 아바타 영역 추가, 액션 카드 고도화
31. [Trade/Diplomacy] 교역/외교 UI의 고밀도 BBS 탭 인터페이스 전환
32. [Collapse] 보스 사망 시 붉은색 글리치 시스템 크래시 화면 개선
33. [Skills] 가상 스킬 트리 템플릿(`skills.html`) 및 이스터에그 인터랙션 추가

---

## 15. 명령어와 검증 기준

### 15.1 로컬 개발 실행
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
# 브라우저: http://localhost:5000
```

### 15.2 검증 체크포인트

| # | 검증 항목 | 명령/방법 | 통과 기준 |
|---|----------|----------|----------|
| 1 | 서버 기동 | `python run.py` | `http://localhost:5000` 응답 200 |
| 2 | 회원가입 | POST `/register` | DB에 User + Park 생성 |
| 3 | 채집 | POST `/game/gather` | 자원 증가 + EventLog 생성 |
| 4 | 턴 진행 | POST `/game/debug/next-turn` (DEBUG 모드) | turn_count +1, AP 리셋 |
| 5 | 전투 | POST `/game/attack` | BattleLog 생성, 양측 자원 변동 |
| 6 | 교역 | POST `/game/trade/create` → `/trade/accept` | TradeOffer status 변경, 자원 이동 |
| 7 | NPC 동작 | 스케줄러 10분 대기 또는 디버그 | NPC Park 자원/인구 변동 |
| 8 | 다국어 | `/set-lang/en` → 대시보드 확인 | UI 텍스트 영어로 변경 |
| 9 | 음수 방어 | `park.baby_count = -5; db.session.commit()` | DB에 0으로 저장 |
| 10 | 보호 모드 | 성체/경호를 0으로 조작 → 대시보드 | 🛡️ 배너 표시 + 침공 버튼 비활성 |
| 11 | CRT 이펙트 및 플리커 | 대시보드 페이지 로드 | 8초 주기 스캔라인 및 0.15s 플리커 작동 |
| 12 | 반응형 브레이크포인트 | 1200px / 768px / 480px 화면 축소 | Grid 컬럼이 3열 → 2열 → 1열로 자동 전환 |
| 13 | 스킬 트리 이스터에그 | 대시보드 하단 네비게이션 `[SKILLS]` 클릭 | SP 충전 카운터 연동 가상 스킬 트리 모크업 출력 |
| 14 | 다국어 일관성 | ko / en / ja / zh_tw / zh_cn 언어 전환 | 번역 헬퍼 `t()`가 깨짐 없이 정상 출력됨 |

---

## 16. 보안/구현 경계

### 16.1 입력 검증
- **XSS**: `html.escape()` (교역 메시지), `escapeHtml()` JS 함수 (정찰 모달), 가입 시 특수문자 차단
- **CSRF**: Flask-WTF `CSRFProtect` 전역 적용, base.html meta 태그 + JS 자동 삽입
- **int 파싱**: `request.form.get('field', 0, type=int)` (ValueError 방지)
- **음수 입력**: `max(0, value)` 적용 (교역 offer/request)

### 16.2 Race Condition 방지
- **교역 생성**: 원자적 `UPDATE-WHERE` (보유량 조건 + 차감 동시 수행)
- **교역 수락**: `status='pending'` → `status='processing'` 원자적 전환 후 교환
- **교역 취소/거절**: `UPDATE-WHERE`로 상태 원자적 변경 후 환불

### 16.3 디버그 백도어
- `/game/debug/next-turn`은 `current_app.config.get('DEBUG')`가 True일 때만 접근 가능
- 프로덕션 환경에서 무한 턴 Exploit 차단

### 16.4 DoS 방지
- 교역 incoming/outgoing 쿼리 `.limit(50)`
- 유저당 동시 pending 교역 10개 제한
- 알림 API `.limit(10)`

---

## 17. 잔여 리스크

| 리스크 | 영향 | 완화책 | 상태 |
|--------|------|--------|------|
| SQLite 동시 쓰기 병목 | 턴 처리 지연 | WAL 모드 (자동), 단일 서버 | 수용 가능 |
| APScheduler 중복 실행 | 턴 중복 처리 | `replace_existing=True`, daemon 스레드 | 수용 가능 |
| 모바일 브라우저 폼 확대 | UX 저하 | font-size: 16px (iOS 방지) | 완화됨 |
| APK 이식 복잡도 | Phase 9 지연 | 핵심 로직 분리 완료 (game_engine, battle_engine, npc_engine) | 계획 중 |
| 다국어 번역 누락 | 일부 UI 영어 노출 | 폴백(ko) 지원, 키 자체 반환 | 수용 가능 |
| 보호 모드 밸런스 | 너무 강하거나 약음 | 상수 조정 가능 (GameConfig 중앙 관리) | 지속 튜닝 |
| NPC AI 단순함 | 예측 가능 | 성격별 행동 + 랜덤 요소 | 수용 가능 |
| 밀사/스파이 UI 미흡 | 대시보드에 밀사 버튼 없음 | API는 존재, UI 미구현 | 잔여 리스크 |

---

*문서 끝*
