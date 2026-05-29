# 실장석 공원 제국 - UI/UX 설계도 (designs.md)

> **문서 버전**: v1.6.3  
> **마지막 갱신**: 2026-05-29  
> **상태**: 동결(Frozen)  
> **표준**: `AI_IMPLEMENTATION_DOC_STANDARD.md` 및 `spec.md` 파생  

---

## 1. 핵심 경험

플레이어는 "공원의 보스실장"이 되어 실장석 군락을 경영한다. 모든 UI는 **BBS 레트로 터미널**을 연상시키는 시각적 언어를 사용하며, 실장석 세계관의 독특한 말투(데스/테츄/레후)가 모든 행동에 녹아 있다.

### 1.1 감성 키워드
- **CRT 모니터**: 스캔라인 오버레이, 녹색 인광 텍스트, 어두운 배경
- **BBS 터미널**: 고정폭 폰트, 테두리 박스, 단순한 그리드 레이아웃
- **실장석**: 콘페이토 황금색 강조, 솎아내기 빨간색 위험, 귀여운 이모지 사용

### 1.2 핵심 인터랙션
- **즉각적인 피드백**: 모든 행동 후 플래시 메시지(8초 후 자동 소멸)
- **수치 가시화**: HP바, 인구바, 사기바, 턴 게이지 바
- **위험 확인**: 솎아내기/침공 시 브라우저 `confirm()` 다이얼로그
- **실시간 알림**: 전투/교역/외교 이벤트 토스트 (10초 폴링)

---

## 2. 전체 화면 흐름

```
[로그인] ←→ [회원가입]
   ↓
[대시보드] ←────────────────────────────┐
   ↓                                    │
[교역소/외교] ←→ [랭킹] ←→ [전투기록]   │
   │                                    │
   └────────────────────────────────────┘
   ↓ (보스 HP = 0)
[게임오버] → [재시작] → [대시보드]
```

### 2.1 화면 전환 규칙
- 모든 내비게이션은 서버 사이드 리다이렉트 (`redirect(url_for(...))`)
- 모달(정찰/침공)은 AJAX + CSS fixed positioning (페이지 이동 없음)
- 언어 전환은 `/set-lang/<code>` → `referrer`로 돌아감

---

## 3. 화면 레이어 구조

### 3.1 전역 레이어 (base.html)
| z-index | 요소 | 설명 |
|---------|------|------|
| 9999 | `.crt-overlay` | CRT 스캔라인 반투명 오버레이 (pointer-events: none) |
| 9999 | `#notif-container` | 실시간 알림 토스트 (fixed, top-right) |
| 100 | `#scout-modal` | 정찰 결과 모달 |
| 100 | `#attack-modal` | 침공 유닛 선택 모달 |
| 99 | `#modal-overlay` | 모달 뒤 어두운 배경 |
| 1 | `.terminal-container` | 메인 콘텐츠 컨테이너 (max-width: 1100px) |

### 3.2 대시보드 레이어 구조 (dashboard.html)
```
┌─ [헤더 박스] ─────────────────────────────┐
│  공원명 | 유저명 | 턴수 | AP | 로그아웃    │
│  [턴 쿼터 게이지] [다음 충전 카운트다운]  │
└───────────────────────────────────────────┘
┌─ [보호 모드 배너] (조건부) ───────────────┐
│  🛡️ 보호 모드 발동! (경호/성체 진행률)    │
└───────────────────────────────────────────┘
┌─ [인사말] ────────────────────────────────┐
│  💬 "랜덤 대사"                             │
└───────────────────────────────────────────┘
┌─ [3열 현황 패널] ─────────────────────────┐
│  [공원 현황] [자원 현황] [시설 현황]       │
└───────────────────────────────────────────┘
┌─ [행동 메뉴] ─────────────────────────────┐
│  [채집] [출산] [건설] [훈련] [솎아내기×2]│
└───────────────────────────────────────────┘
┌─ [전투/방어 메뉴] ────────────────────────┐
│  [방어 배치] [디버그 턴] [전투 기록]      │
└───────────────────────────────────────────┘
┌─ [이벤트 로그] ───────────────────────────┐
│  [턴] 이벤트 메시지 (색상별 구분)         │
└───────────────────────────────────────────┘
┌─ [다른 공원 목록] ────────────────────────┐
│  이름 | 보스 | 전투력 | 성격 | [정찰][침공]│
└───────────────────────────────────────────┘
┌─ [하단 네비게이션] ───────────────────────┐
│  [랭킹] [전투기록] [교역소]               │
└───────────────────────────────────────────┘
```

### 3.3 교역소 레이어 (trade.html)
```
┌─ [현재 자원 표시] ────────────────────────┐
┌─ [교역 제안 생성] ────────────────────────┐
│  [제공] [요청] | 대상 선택 | 메시지       │
┌─ [받은 제안] ─────────────────────────────┐
┌─ [공개 교역 시장] ────────────────────────┐
┌─ [내가 보낸 제안] ────────────────────────┐
┌─ [외교 관계] ─────────────────────────────┐
│  [동맹 요청] [현재 동맹] [현재 적대]      │
│  [새 외교 관계 선택 + 동맹/적대 버튼]     │
└───────────────────────────────────────────┘
```

---

## 4. 컬러/타이포 토큰

### 4.1 CSS 변수 (`:root`)
```css
--bg: #0a0a0a;              /* 메인 배경 (거의 순흑) */
--bg-box: #0d1a0d;          /* 터미널 박스 배경 */
--text: #33ff33;            /* 주 텍스트 (인광 녹색) */
--text-dim: #1a8c1a;        /* 보조/비활성 텍스트 */
--text-bright: #88ff88;     /* 강조 녹색 */
--accent: #ffaa00;          /* 콘페이토 황금 */
--accent-glow: #ffd700;     /* 콘페이토 반짝임 */
--danger: #ff4444;          /* 솎아내기/위험 */
--danger-dim: #8b0000;      /* 어두운 빨강 */
--mint: #00ff88;            /* 헤더/성공 */
--border: #225522;          /* 기본 테두리 */
--border-bright: #33aa33;   /* 호버 테두리 */
--konpeito: #ffd700;        /* 콘페이토 자원색 */
--trash: #888888;           /* 음쓰 자원색 */
--meat: #ff6b35;            /* 고기 자원색 */
--material: #cc8844;        /* 자재색 */
--morale-low: #ff4444;      /* 사기 낮음 */
--morale-mid: #ffaa00;      /* 사기 중간 */
--morale-high: #33ff33;     /* 사기 높음 */
--font-mono: 'IBM Plex Mono', 'D2Coding', 'Consolas', monospace;
--font-ui: 'Noto Sans KR', 'IBM Plex Mono', sans-serif;
```

### 4.2 타이포그래피
- **본문**: `var(--font-mono)`, 14px, line-height 1.6
- **제목/헤더**: `var(--font-ui)`, 13px, weight 700, letter-spacing 0.5px
- **NPC 대사**: italic, 12px, `var(--accent)`, text-shadow glow
- **수치**: `var(--font-mono)`, 12~14px, bold
- **버튼**: `var(--font-mono)`, 13px, weight 600, letter-spacing 0.5px

---

## 5. 레이아웃 기준

### 5.1 그리드 시스템
- **데스크톱**: 3열 현황 패널 (`grid-template-columns: 1fr 1fr 1fr`)
- **태블릿(≤768px)**: 2열 행동 그리드 + 1열 현황 패널
- **모바일(≤480px)**: 1열 모든 그리드, 턴 게이지 세로 배치

### 5.2 여백/간격
- 터미널 박스 마진: 12px (모바일 8px)
- 박스 패딩: 10px 12px (모바일 6px)
- 헤더 패딩: 6px 12px
- 행동 카드 갭: 10px
- 버튼 패딩: 8px 16px (모바일 터치 친화: min-height 48px)

### 5.3 반응형 브레이크포인트
- **768px**: 3열 → 1~2열 전환, 턴 게이지 유지
- **480px**: 1열 전환, 버튼 크기 확대, 폰트 축소

---

## 6. HUD/화면 요소 목록

### 6.1 대시보드 헤더
| 요소 | 데이터 | 비고 |
|------|--------|------|
| 공원명 | `park.name` | 클릭 불가 |
| 유저명 | `current_user.username` | 클릭 불가 |
| 턴수 | `park.turn_count` | 클릭 불가 |
| AP | `park.action_points / 3` | 0일 때 깜빡임 애니메이션 |
| 턴 게이지 | `turn_info.quota / turn_info.max` | gradient fill, 실시간 카운트다운 |

### 6.2 현황 패널

#### 공원 현황
| 요소 | 데이터 | 시각화 |
|------|--------|--------|
| 보스 HP | `park.boss_hp` | `.hp-bar` + `.hp-fill` (width: boss_hp%) |
| 경호실장 | `park.guard_count` | 숫자 |
| 성체실장 | `park.adult_count` | 숫자 |
| 자실장 | `park.child_count` | 숫자 |
| 저실장 | `park.baby_count` | 숫자 + `/ baby_cap` |
| 인구 | `total_population / population_cap` | `.pop-bar` |
| 전투력 | `total_combat_power` | 숫자 (강조) |
| 사기 | `park.morale` | `.morale-bar` (색상: low/mid/high) |

#### 자원 현황
| 요소 | 데이터 | 시각화 |
|------|--------|--------|
| 콘페이토 | `konpeito / konpeito_cap` | `.konpeito-line` + 반짝임 효과 |
| 음쓰 | `trash_food / trash_food_cap` | `.trash-line` |
| 고기 | `meat_stock` | `.meat-line` |
| 자재 | `material / material_cap` | 숫자 |
| 총 NP | `total_np_available` | `.np-value` (금색) |
| 턴당 NP 소비 | `total_np_per_turn` | `.np-cost` (빨강) |

#### 시설 현황
| 요소 | 데이터 |
|------|--------|
| 골판지집 | `cardboard_houses` |
| 운치굴 | `unchi_holes` |
| 저장굴 | `storage_holes` |
| 방벽 | `walls` |
| 감시탑 | `watchtowers` |
| 건설 대기열 | `build_queue` (emoji + 이름 + 남은 턴) |
| 훈련 대기열 | `train_queue` (남은 턴) |

### 6.3 행동 카드 (6개)
| 카드 | AP | 버튼 ID | disabled 조건 |
|------|-----|---------|--------------|
| 채집 | 1 | `#btn-gather` | `AP < 1 AND turn_quota < 1` |
| 출산 | 2 | `#btn-birth` | `(AP < 2 AND turn_quota < 1) OR adult < 1` |
| 건설 | 1 | `#btn-build` | `AP < 1 AND turn_quota < 1` |
| 훈련 | 1 | `#btn-train` | `(AP < 1 AND turn_quota < 1) OR adult < 1` |
| 솎아내기(저) | 0 | `#btn-cull-baby` | `baby < 1` |
| 솎아내기(자) | 0 | `#btn-cull-child` | `child < 1` |

### 6.4 전투/방어 카드 (3개)
| 카드 | AP | 설명 |
|------|-----|------|
| 방어 배치 | 1 | 경호/성체 숫자 입력 → 배치 |
| 디버그 턴 | 0 | 턴 강제 진행 (DEBUG 모드 전용) |
| 전투 기록 | 0 | `battle_logs.html` 링크 |

---

## 7. 데이터 연결 기준

### 7.1 템플릿 ↔ 모델 매핑
- **Flask-Login**: `current_user` → `current_user.park` (1:1)
- **Jinja2 전역**: `t('key')`, `current_lang()`, `supported_langs`
- **CSRF**: `{{ csrf_token() }}` → meta 태그 → JS 자동 form 삽입

### 7.2 클라이언트 ↔ 서버 데이터 흐름
```
[POST form] → 라우트(Flash 메시지) → redirect(dashboard) → 템플릿 렌더링
[AJAX 정찰] → /game/scout/<id> → JSON → 모달 DOM 업데이트
[AJAX 알림] → /game/api/notifications → JSON → 토스트 DOM 생성
```

### 7.3 실시간 업데이트
- **턴 카운트다운**: 클라이언트 JS `setInterval` (1초), 0 도달 시 `location.reload()`
- **알림 폴링**: `setInterval` 10초, `last_id` 기반 증분 조회
- **모달 전투력 미리보기**: `oninput` 이벤트 → JS 즉시 계산

---

## 8. 화면별 버튼 정책

### 8.1 버튼 공통 규칙
- **기본 클래스**: `.terminal-btn`
- **주요 행동**: `.btn-primary` (녹색 계열)
- **보조 행동**: `.btn-secondary` (어두운 녹색)
- **위험 행동**: `.btn-cull` (빨간색 계열)
- **액션 버튼**: `.btn-action` (민트색, width: 100%)
- **비활성**: `opacity: 0.3`, `cursor: not-allowed`

### 8.2 버튼별 활성화/후속 상태

| 버튼 | 활성화 조건 | 누르면 | 상태 갱신 |
|------|------------|--------|----------|
| 채집 실행 | `AP >= 1 OR turn_quota >= 1` | POST `/game/gather` | 자원 ↑, AP ↓, EventLog 추가 |
| 출산 실행 | `(AP >= 2 OR turn_quota >= 1) AND adult >= 1` | POST `/game/birth` | 인구 ↑, AP ↓, EventLog 추가 |
| 건설 실행 | `AP >= 1 OR turn_quota >= 1` | POST `/game/build` | 자재 ↓, BuildQueue 추가 |
| 훈련 실행 | `(AP >= 1 OR turn_quota >= 1) AND adult >= 1` | POST `/game/train` | NP ↓, adult ↓, TrainQueue 추가 |
| 솎아내기(저) | `baby >= 1` | POST `/game/cull` | baby ↓, meat/material ↑ |
| 솎아내기(자) | `child >= 1` | POST `/game/cull` | child ↓, meat/material ↑ |
| 방어 배치 | `AP >= 1 OR turn_quota >= 1` | POST `/game/defend` | defending_* 갱신 |
| 침공 모달 열기 | `AP >= 2 OR turn_quota >= 1` | JS 모달 열기 | — |
| 침공 실행 | 출정 인원 > 0 OR 보스 참전 | POST `/game/attack` | 양측 자원/인구 변동, BattleLog |
| 정찰 | — | AJAX GET | 모달 표시 (감시탑 유무에 따라 상세/기본) |
| 교역 제안 | 제공>0 AND 요청>0 | POST `/game/trade/create` | 자원 선차감, TradeOffer 추가 |
| 동맹 요청 | 기존 관계 없음 | POST `/diplomacy/ally` | Diplomacy pending 추가 |
| 적대 선언 | 기존 동맹 해제 + 1AP | POST `/diplomacy/enemy` | Diplomacy active 추가 |

---

## 9. 타격감/모션 규칙

### 9.1 플래시 메시지
- **슬라이드 인**: `translateX(-10px) → 0`, `opacity: 0 → 1`, 0.3s ease-out
- **자동 소멸**: 8초 후 `opacity: 0`, `translateX(10px)`, 0.5s → 제거
- **색상 구분**: success(녹색), error(빨강), warning(주황), info(민트)

### 9.2 바 애니메이션
- **HP/인구/사기 바**: `width` 변화 시 `transition: width 0.3s`
- **턴 게이지**: `transition: width 0.5s ease`

### 9.3 미세 애니메이션
- **로고 박스**: `animation: flicker 4s infinite alternate` (CRT 깜빡임)
- **콘페이토 반짝임**: `text-shadow` 3초 주기 펄스
- **AP 0 경고**: `animation: gameoverPulse 1.5s infinite`, 색상 `#ff4444`
- **NPC 대사 타이핑**: 30ms/글자 `setInterval` 타이핑 효과
- **버튼 호버**: `translateY(-1px)`, `box-shadow` 증가, 0.2s ease
- **박스 헤더 글로우**: hover 시 `text-shadow` 펄스

---

## 10. React/Canvas 또는 UI/코어 역할 분리

### 10.1 역할 분리
| 계층 | 기술 | 책임 |
|------|------|------|
| UI/템플릿 | Jinja2 + HTML/CSS | 화면 렌더링, 폼, 플래시 메시지 |
| 클라이언트 로직 | 순수 JS (game.js) | 모달, 카운트다운, 폴링, 전투력 미리보기, 입력 검증 |
| 서버 라우트 | Flask Blueprint | 요청 검증, 권한 확인, flash 메시지, 리다이렉트 |
| 게임 엔진 | Python (game_engine.py) | 상태 변경, 랜덤 판정, 이벤트 로그 |
| 데이터 | SQLAlchemy + SQLite | 영속화, 트랜잭션, cascade 삭제 |

### 10.2 UI ↔ 서버 경계
- **UI는 절대 게임 로직을 계산하지 않는다.** (전투력 미리보기는 예외적으로 클라이언트에서 근사값 계산)
- **모든 상태 변경은 POST 요청 후 서버 응답(리다이렉트)으로 반영된다.**
- **AJAX는 정찰/알림만 사용.** (상태 변경 없는 조회 전용)

---

## 11. 동결된 디자인 결정

| 결정 | 값 | 근거 |
|------|-----|------|
| 폰트 | IBM Plex Mono + Noto Sans KR | 고정폭 + 한글 지원 |
| 최대 폭 | 1100px | 데스크톱 가독성 + 모바일 여백 |
| CRT 오버레이 | `repeating-linear-gradient` | CSS 단일 요소, 성능 영향 없음 |
| 모달 방식 | CSS fixed + JS display toggle | 라이브러리 의존성 제거 |
| 이모지 사용 | Unicode 이모지 (🍬🗑️⚔️ 등) | 이미지 에셋 불필요 |
| 색맹 대응 | 텍스트 + 이모지 + 위치 3중 정보 | 접근성 최소 확보 |
| 모바일 터치 | 버튼 min-height 48px | iOS/Android 터치 타겟 규격 |
| 폼 확대 방지 | `input[type="number"] font-size: 16px` | iOS 자동 확대 방지 |

---

## 12. 모바일 특화 규칙

### 12.1 턴 게이지 (모바일)
- `.turn-quota-bar`: `flex-direction: column` (세로 배치)
- `.turn-gauge`: `width: 100%`, `height: 26px`
- `.turn-gauge-text`: `font-size: 14px`

### 12.2 행동 버튼 (모바일)
- `.action-card`, `.terminal-btn`, `button[type="submit"]`: `min-height: 48px`
- `.action-grid`: `grid-template-columns: 1fr`
- `.gather-form input`: `width: 60px`, `font-size: 16px`

### 12.3 현황 패널 (모바일)
- `.status-panels`: `grid-template-columns: 1fr`
- `.stat-line`: `font-size: 11px`

---

*문서 끝*
