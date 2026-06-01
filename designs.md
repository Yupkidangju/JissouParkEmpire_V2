# 실장석 공원 제국 - UI/UX 설계도 (designs.md)

> **문서 버전**: v1.8.9
> **마지막 갱신**: 2026-05-31
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

### 3.4 스킬 트리 레이어 (skills.html) [NEW]
```
┌─ [헤더 바 (TopAppBar)] ────────────────────┐
│  공원명 | AP 상태 | 턴 카운트 | 보유 SP   │
└───────────────────────────────────────────┘
┌───────────────────┬───────────────────────┐
│ [좌측 내비게이션] │ [중앙 스킬 트리]      │
│                   │   (SVG 연결선 및 노드)│
│ - AUTHORITY       │    ○ [공원 관리]      │
│ - BIO-RESOURCES   │   / \                 │
│ - CRUELTY         │  ●   ●                │
│                   │ [솎아내기][진압]      │
├───────────────────┴───────────────────────┤
│ [우측 스킬 상세 패널]                     │
│  이름 | 현재 레벨 | 버프 효과 | [업그레이드]│
└───────────────────────────────────────────┘
┌─ [하단 네비게이션] ───────────────────────┐
│  [COMMAND] [CULL] [PARK] [SKILLS] [SYSTEM]│
└───────────────────────────────────────────┘
```

---

## 4. 컬러/타이포 토큰

### 4.1 CSS 변수 (`:root`)
```css
--bg: #050505;              /* 메인 배경 (순흑에 가까운 모니터 섀도우) */
--bg-box: #131313;          /* 터미널 박스 배경 (고밀도 다크그레이) */
--text: #eeffe4;            /* 기본 전경색 (인광 연록) */
--text-dim: #85967d;        /* 비활성/보조 텍스트 (딤 그린) */
--text-bright: #33ff33;     /* 강조 및 주 텍스트 (강렬한 인광 녹색) */
--accent: #ffaa00;          /* 콘페이토/Amber 황금 */
--accent-glow: #ffd700;     /* 콘페이토 반짝임 */
--danger: #ff4444;          /* 솎아내기/위험/Crimson */
--danger-dim: #93000a;      /* 어두운 Crimson 경고 배경 */
--mint: #00e61b;            /* 활성 상태 전용 밸류 */
--border: #3c4b36;          /* 기본 구조 테두리 (슬러지 브라운/그린) */
--border-bright: #85967d;   /* 호버 및 활성 테두리 */
--konpeito: #ffd700;        /* 콘페이토 자원색 */
--trash: #baccb1;           /* 음쓰 자원색 */
--meat: #ffb4ab;            /* 고기 자원색 (테라코타 핑크/레드) */
--material: #ffcf90;        /* 자재 자원색 (골드 오커) */
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
| 최대 폭 | 1100px (대시보드는 max-w-7xl 1280px) | 데스크톱 가독성 + 모바일 반응형 최적화 |
| UI 프레임워크 | Tailwind CSS CDN | Jinja2 호환성 및 신속한 반응형 그리드 구축 |
| CRT 오버레이 | CSS 그라디언트 + flicker 0.15s + scanline 8s | 고도화된 하드웨어 mainframe 섀이딩 구현 |
| 모달 방식 | CSS fixed + JS display toggle | 라이브러리 의존성 제거 및 Tailwind 트랜지션 결합 |
| 스킬 트리 모크업 | skills.html 템플릿 추가 | 백로그 기능 이스터에그 시각화 (SP 카운터 1초 주기 0.05% 변동) |
| 이모지 사용 | Unicode 이모지 (🍬🗑️⚔️ 등) | 이미지 에셋 불필요 |
| 색맹 대응 | 텍스트 + 이모지 + 위치 3중 정보 | 접근성 최소 확보 |
| 모바일 터치 | 버튼 min-height 48px | iOS/Android 터치 타겟 규격 |
| 폼 확대 방지 | `input[type="number"] font-size: 16px` | iOS 자동 확대 방지 |
| 보상 트랜잭션 AP 복구 | 실패 (`not success`) 시 AP 즉시 자동 환불 복구 | 분할 트랜잭션 선행 커밋으로 인한 AP 증발 및 누수 위험 완화 |

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

## 13. 신규 템플릿(skills.html) 모크업 명세 [NEW]

보스 실장의 미래 성장 스킬 시스템을 보여주기 위해 구현되는 가상의 고밀도 메인프레임 터미널입니다.

### 13.1 화면 영역 분할
1.  **헤더 (TopAppBar):**
    *   `AP STATUS`: 기존 `park.action_points` 데이터를 활용하여 `124/150` 등의 고용량 메인프레임 배터리 게이지 형식으로 변조 시각화.
    *   `TURN COUNT`: `DAY-{{ park.turn_count }}` 형식으로 BBS 날짜처럼 표기.
    *   `SP (스킬 포인트)`: `4,200 SP`에서 1초 주기로 `Math.random() > 0.95` 확률로 1~50 SP가 미세하게 요동치며 충전되는 화려한 라이브 카운터 인터랙션 적용.
2.  **좌측 사이드바 (스킬 카테고리):**
    *   `AUTHORITY` (지배): 진압, 강제 솎아내기 관련.
    *   `BIO-RESOURCES` (생체 자원): 채집 효율, 콘페이토 중독 치료 관련.
    *   `CRUELTY` (가학): 고기 생산량, 솎아내기 속도 향상 관련.
3.  **중앙 스킬 그리드 (격자 격리구역):**
    *   배경: 40px 간격의 고정폭 도트 격자 배경 레이아웃 (`radial-gradient`).
    *   스킬 노드: 날카로운 각진 사각형(0px) 모양에 Material Symbols 아이콘(shield_with_heart, hardware, local_police, military_tech 등) 배치.
    *   연결선: 노드 간 SVG `<line>` 요소를 그려 Phosphor Green 인광 색선 및 점선(`stroke-dasharray="5,5"`) 렌더링.
    *   상태 표시: 잠금(`LOCKED` 회색 필터) 노드와 활성(`ACTIVE` 외부 네온 빛) 노드의 확실한 분리.
4.  **우측 스킬 상세 패널:**
    *   스킬 클릭 시 해당 노드의 이름, 배경 설명(실장석 말투 주석 - 한국어 전용), 버프 수치, 업그레이드 비용(`UPGRADE COST`)을 로드하여 상세 설명.
    *   하단에 `[UPGRADE]` 단추 배치. (클릭 시 "오마에, SP가 부족한 레후!" 혹은 "미구현 프로토콜 데스!" 팝업/토스트 출력).

### 13.2 다국어(i18n) 통합 방침
*   모든 카테고리명(AUTHORITY, SKILLS) 및 텍스트 요소는 다른 파일들과 마찬가지로 다국어 지원을 위해 `t('skills.category_authority')` 등으로 처리.
*   다국어 번역 키가 존재하지 않는 디테일한 설명은 이스터에그의 특성을 살려 `app/lang/ko.json` 및 `en.json` 등 각 다국어 파일에 키를 명시적으로 정의하여 반영.

---

## 14. 보상 트랜잭션 및 AP 복구 UX 사양 [NEW]

행동 실행 실패 시 이미 선행 커밋되어 차감된 AP를 즉시 되돌려주어 사용자에게 리소스 무손실에 가까운 경험을 제공합니다.

### 14.1 리소스 무손실 예외 흐름
1.  **사용자 행동 트리거:** 플레이어가 채집/건설/출산 등의 행동 버튼을 클릭.
2.  **선행 AP 감산 및 커밋:** 서버의 `consume_turn()`에서 AP를 미리 깎고 데이터베이스에 즉시 커밋하여 트랜잭션을 조기 종료함 (Ghost AP 차단 및 동시성 락 충돌 우회).
3.  **행동 로직 검증 및 실패:** 비즈니스 엔진(`game_engine.py` 등)에서 자재 부족, 사기 부족, 파업(`strike_turns > 0`) 등의 예외로 인해 행동 처리 실패(`success == False`)가 리턴됨.
4.  **보상 트랜잭션 작동:** `game_engine.refund_ap(park, cost)` 가 호출되어 DB에 플레이어의 AP를 차감된 만큼 복구(증가) 및 재커밋 처리.
5.  **사용자 피드백 (Flash Message):** 화면 상단에 해당 행동의 실패 메시지가 **붉은색 경고(error)** 플래시 메시지로 렌더링되나, 대시보드의 AP 수치는 차감되지 않고 그대로 보존됨.

### 14.2 침공(Attack) 무산 시의 복구 사양
- 플레이어가 침공(`/attack`) 실행 단추를 눌렀으나 동시성 레이스로 인해 가용 유닛(성체/경호)이 전투 개시 전에 0명으로 유실된 경우:
  - 전투 시뮬레이션(`execute_battle`)은 "아무도 안 보내면 침공할 수 없는 데스!"라는 전투 기각 판정을 내림.
  - 이 경우, 침공 비용인 2AP를 즉각 환불해주며, 사용자에게는 붉은색 글리치 테두리의 에러 플래시로 전투 무산을 강력하게 피드백하여 리소스 유실이 없었음을 확실히 인지시킴.

## 15. Cascade Delete 에스크로 및 유닛 유실 방지 설계 [NEW]

상대방 공원이 데이터베이스에서 폭파(삭제)되어 연쇄 삭제(Cascade Delete)가 발생할 때, 아직 종료되지 않은 상호작용의 에스크로 자원 및 유닛을 발신자 공원에 자동으로 복구하는 안전 메커니즘을 설계합니다.

### 15.1 Cascade 연쇄 환불 안전 흐름
1. **타겟/수신자 공원 삭제 트리거**: 특정 플레이어가 회원 탈퇴 또는 게임오버 후 재시작(`/restart`)을 눌러 공원(`Park`) 레코드가 `db.session.delete()` 처리됨.
2. **연쇄 삭제 감지**: 해당 공원과 관계 맺고 있던 `TradeOffer` (수신 거래) 및 `SpyMission` (타겟 스파이) 레코드가 SQLAlchemy Cascade `delete-orphan` 제약에 의해 연쇄적으로 삭제되기 직전에 돌입함.
3. **SQLAlchemy Event Listener 발동**:
   - `TradeOffer` 삭제 전 (`before_delete`): 삭제 대상이 `status == 'pending'`인 경우, `object_session`을 통해 발신자 공원(`sender_id`)이 함께 삭제 중(`session.deleted`)인지 재검사한 후, 삭제되지 않는 공원이라면 에스크로된 제공 자원(콘페이토, 음쓰, 자재, 저실장)을 원자적으로 환불하고 캡핑(Cap Clamping)을 실행함.
   - `SpyMission` 삭제 전 (`before_delete`): 삭제 대상이 `status == 'active'`인 경우, 발신자 공원(`sender_id`)이 함께 삭제 중인지 재검사한 후, 삭제되지 않는 공원이라면 파견되었던 에스크로 유닛(성체실장)을 `adult_count += 1` 처리하여 돌려줌.
4. **트랜잭션 무결성 커밋**: 복구된 자원 및 성체실장 정보는 공원 삭제 트랜잭션의 커밋(`db.session.commit()`) 단계에서 함께 원자적으로 영속화되어, 어떤 유실도 남기지 않고 동기화됨.

## 16. 외교 시스템 중복 방지 및 2중 비관적 락 설계 [NEW]

두 공원이 동시에 교차 요청을 보내거나 중복 관계를 생성함으로써 일어나는 논리적 모순 상태(동맹이자 적대 등)를 차단하고, 동시성 환경에서의 직렬화 안정성을 극대화합니다.

### 16.1 Canonical Ordering을 통한 Unique 제약 강제
1.  **동적 정렬 저장**: 두 공원의 ID 쌍에 대해 항상 `park_a_id = min(A, B)`, `park_b_id = max(A, B)`로 정렬하여 DB에 저장합니다.
2.  **Unique 제약 작동**: 이로 인해 `(A, B)`와 `(B, A)`라는 두 개의 별도 레코드로 교차 저장되던 빈틈이 줄어들고, 데이터베이스 수준의 UniqueConstraint가 동일 공원 쌍에 대해 단 하나의 관계 상태만 존재하도록 강제합니다.
3.  **발송자 식별**: `initiator_id` 컬럼을 외래키로 추가하여, ID가 min/max로 정렬되더라도 원래 어떤 공원이 이 외교를 요청했는지를 정확하게 식별하고 수락/거절 권한 검증에 활용합니다.

### 16.2 2-Way Pessimistic Lock 및 Bulk Update 흐름
1.  **2중 비관적 락**: 외교 라우터 진입 시 `park.id`와 `target.id` 두 ID를 오름차순으로 정렬하여 `with_for_update()` 락을 획득합니다. 교차 요청이 있더라도 동일한 순서로 순차 대기하게 되므로 교착 상태(Deadlock) 위험이 크게 줄어듭니다.
2.  **Bulk Update 일괄 해제**: 관계를 변경(적대 선언 시 기존 동맹 파기, 외교 해제 등)할 때 `.first()`로 개별 레코드만 찾아서 바꾸는 대신, `.update()` 벌크 쿼리를 사용해 해당 공원 쌍 간의 모든 active/pending 중복 관계를 한 번에 `dissolved` 상태로 변경하여 잠재적 상태 오염을 자동 복구/예방합니다.

---

## 17. NPC 공격 시 락 순서 역전 교착 상태 방지 및 통제 완화 설계 [NEW]

NPC가 다른 공원을 공격할 때 락 획득 순서가 뒤틀려 영구적인 교착 상태(Deadlock)에 빠지고 데이터베이스 커넥션이 고갈되는 설계 결함 `[DEADLOCK-F005]`을 크게 완화합니다.

### 17.1 NPC 턴 진행 및 행동 AI 2단계 트랜잭션 경계 분리 설계
1.  **선점 락 해제**: 턴 동기화 스케줄러 `_sync_npc_turns()` 레벨에서 NPC 기본 턴 처리(`process_turn`) 완료 즉시 명시적인 `db.session.commit()`을 집행하여 선점 락을 해제합니다.
2.  **독립된 2단계 트랜잭션 AI 기동**: 선점 락이 비워진 상태에서 비로소 NPC AI 행동 의사결정 및 침공 기동(`process_npc_turn()`)에 진입하도록 **2단계 트랜잭션 경계 분리 구조**를 채택했습니다.
3.  **최상단 락 선점 제거 및 역할 위임**: `process_npc_turn()` 시작 부분에서 무조건적으로 대상 NPC 공원 레코드를 `with_for_update()`로 락킹하던 선점 락을 제거하고 단순 `db.session.refresh(park)`만 호출하도록 완화했습니다. 이로 인해 전투(`execute_battle()`) 등 개별 행동 단위가 독자적으로 Canonical Ordering 락을 순서대로 획득하도록 역할을 위임하였습니다.

### 17.2 Canonical Locking 및 SQLite WAL/busy_timeout Pragma 주입 설계
1.  **오름차순 순차 대기 유지**: 최상단의 락 선점이 제거됨에 따라, NPC가 공격 성향에 의해 `execute_battle()`을 호출할 때만 비로소 공격자(NPC)와 방어자(Player)의 락이 작동합니다.
2.  **교착 대기 억제**: 두 공원의 ID를 오름차순 정렬하여 `Park.id.in_(lock_ids)` 조건 하에 `with_for_update()` 비관적 락을 동시에 획득하므로, 플레이어 스레드와 NPC 스레드가 교차 락 획득을 시도하더라도 정렬된 순서에 따라 순차적으로 락을 양보하고 획득하며 교착 상태 및 커넥션 풀 고갈 위험을 줄입니다.
3.  **SQLite WAL 및 busy_timeout pragma 실제 활성화**: 기본 배포 DB인 SQLite 환경에서 `with_for_update()` no-op(FOR UPDATE SQL 미생성) 한계를 극복하고 동시성 쓰기 병목 및 Database Locked 예외를 방어하기 위해, `Engine` 'connect' 이벤트 리스너를 구축하여 SQLite 연결 즉시 `PRAGMA journal_mode=WAL` 및 `PRAGMA busy_timeout=5000`을 강제 자동 주입하도록 설정했습니다.
4.  **Lock-free Gap 설계적 절충 및 Row-Lock DB 확장성 매핑**: 2단계 분리 구조로 인해 NPC 행동 AI 기동 시점에 생기는 일시적 무락 갭(Lock-free Gap)은, 행동 결정 시점에 플레이어의 자원 수치가 다소 변할 수 있으나 데드락 회피를 위해 감수한 설계적 절충(Trade-off)입니다. 이 설계는 향후 PostgreSQL, MySQL 등 실제 행 락(Row Lock) RDBMS 환경으로 전환하여 Gunicorn 다중 워커 프로덕션 서버를 대규모로 수평 확장할 때도 소스 코드 변경 없이 높은 정합성과 격리 안정성을 유지하도록 돕습니다.

---

*문서 끝*
