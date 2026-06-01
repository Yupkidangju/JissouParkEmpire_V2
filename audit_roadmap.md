# 실장석 공원 제국 - 감사 로드맵 (audit_roadmap.md)

> **문서 버전**: v1.8.9
> **마지막 갱신**: 2026-05-31
> **상태**: 동결(Frozen)
> **표준**: `AI_IMPLEMENTATION_DOC_STANDARD.md` 및 `spec.md` 파생

---

## 1. 정합성 감사 (Consistency Audit)

### 1.1 문서-코드 정합성
| 항목 | 확인 방법 | 통과 기준 |
|------|----------|----------|
| `spec.md` 수치 = `config.py` 수치 | diff 비교 | 100% 일치 |
| `spec.md` 타입 = `models.py` 필드 | 스키마 매핑 | 모든 필드 정의됨 |
| `designs.md` 색상 = `style.css` 변수 | CSS `--*` 변수 검색 | 모든 토큰 존재 |
| `implementation_summary.md` 파일 책임 = 실제 코드 | 파일별 주석/함수 매칭 | 불일치 0건 |
| `BUILD_GUIDE.md` 명령 = 실제 실행 | 가상환경에서 재실행 | 오류 0건 |

### 1.2 문서 간 정합성
| 항목 | 확인 방법 | 통과 기준 |
|------|----------|----------|
| `spec.md` 이벤트 타입 = `models.py` EventLog.event_type | enum 비교 | 누락 없음 |
| `spec.md` 건물 목록 = `config.py` BUILDINGS | dict key 비교 | 누락 없음 |
| `spec.md` NPC 성격 = `config.py` NPC_PERSONALITIES | list 비교 | 누락 없음 |
| `designs.md` 버튼 ID = `dashboard.html` ID | HTML id 속성 검색 | 누락 없음 |

---

## 2. 위험요소 감사 (Risk Audit)

### 2.1 보안 위험
| 위험 | 위치 | 심각도 | 검증 방법 |
|------|------|--------|----------|
| SQL Injection | 라우트 전체 | 낮음 | SQLAlchemy ORM 사용, raw SQL 없음 |
| XSS | 교역 메시지, 정찰 모달 | 중간 | `html.escape()`, `escapeHtml()` 적용 확인 |
| CSRF 우회 | POST 폼 전체 | 낮음 | Flask-WTF 전역 적용, meta 태그 확인 |
| Race Condition | 교역 수락/취소 | 중간 | 원자적 UPDATE-WHERE 패턴 코드 리뷰 |
| 음수 Exploit | 자원/인구 감산 | 낮음 | `@validates` 12개 필드 클램핑 확인 |
| 디버그 백도어 | `/debug/next-turn` | 낮음 | DEBUG 가드 코드 확인 |
| 무손실 파밍 | 전투 피해 | 낮음 | `stochastic_round()` 적용 확인 |
| TOCTOU Lost Update | 보호 모드 진입 | 높음 | `check_and_enter_protection` 비관적 락 & refresh 확인 |
| Gunicorn Lock Bypass | 교역 생성 | 중간 | `trade_create` 내부 비관적 락 `with_for_update` 코드 확인 |

### 2.2 안정성 위험
| 위험 | 위치 | 심각도 | 검증 방법 |
|------|------|--------|----------|
| SQLite 병목 | 동시 접속 | 중간 | WAL 모드 확인, 단일 서버 가정 |
| APScheduler 중복 | 서버 재시작 | 낮음 | `replace_existing=True` 확인 |
| 메모리 누수 | 폴링/스케줄러 | 낮음 | 장기 실행 테스트 |
| DB 락 경합 | 교역 동시 요청 | 중간 | 원자적 UPDATE-WHERE 동작 확인 |
| Restart Infinite Loop | 재시작 / 로그인 | 높음 | restart 단일 트랜잭션 및 유실 시 자동 재생성 헬퍼 검증 |
| NPC Stampede | NPC 턴 동기화 | 높음 | `_sync_npc_turns` 내 오름차순 ID 정렬 비관적 락 및 turn_count 가드 검증 |
| NPC Turn Lost Update | NPC 턴 루프 | 높음 | growth 내 case() UPDATE 및 범용 엔진 commit=False 차단 검증 |
| NPC Lock Order Inversion | `_npc_attack` 및 `execute_battle` | 높음 | `process_npc_turn` 최상단 비관적 락 해제 및 execute_battle Canonical Locking 정합성 검증 |

### 2.3 밸런스 위험
| 위험 | 위치 | 심각도 | 검증 방법 |
|------|------|--------|----------|
| 보호 모드 과도 | `is_protected()` | 중간 | 신규 유저 15턴 생존률 테스트 |
| NPC 과성장 | `_npc_passive_growth()` | 낮음 | 100턴 후 NPC 전투력 분포 확인 |
| 콘페이토 중독 과도 | `_process_addiction()` | 낮음 | 3턴 연속 섭취 후 채집 패널티 확인 |
| 재해 연쇄 | `_process_disasters()` | 낮음 | 10턴 시뮬레이션 재해 발생 빈도 확인 |

---

## 3. 아키텍처 감사 (Architecture Audit)

### 3.1 단일 책임 원칙 (SRP)
| 파일 | 책임 | 위반 여부 |
|------|------|----------|
| `game_engine.py` | 게임 상태 변경 + 턴 처리 | ⚠️ 1217줄, 분리 고려 대상 |
| `battle_engine.py` | 전투 시뮬레이션만 | ✅ |
| `npc_engine.py` | NPC AI만 | ✅ |
| `game_routes.py` | 라우트 + 검증 | ⚠️ 1045줄, 교역/외교 분리 고려 |

### 3.2 의존성 방향
```
라우트 → 엔진 → 모델 → config
          ↓
         dialogues/i18n
```
- 엔진이 라우트를 import하는 순환 의존성: **없음** 확인.
- `battle_engine.py`가 `game_engine.py`의 `add_event`를 import: **허용** (이벤트 로깅).

### 3.3 상태 관리
- **서버 상태**: SQLAlchemy 모델 (DB + 세션)
- **클라이언트 상태**: 없음 (모든 상태는 서버에서 렌더링)
- **전역 상태**: `turn_scheduler.scheduler` (백그라운드 스레드)

### 3.4 확장성
| 요구사항 | 현재 상태 | 판정 |
|----------|----------|------|
| 새 언어 추가 | JSON 파일 1개 추가 | ✅ 가능 |
| 새 건물 추가 | `BUILDINGS` dict + 템플릿 | ✅ 가능 |
| 새 재해 추가 | `config.py` + `process_turn` | ⚠️ 가능하나 순서 주의 |
| 실시간 PvP | 없음 | ❌ 불가 (설계상) |
| WebSocket 알림 | 없음 | ⚠️ 폴링으로 대체 가능하나 지연 있음 |

---

## 4. 로드맵 감사 (Roadmap Audit)

### 4.1 Phase별 목표 및 검증

#### Phase 8: 보안/안정화 (현재 완료)
| 항목 | 상태 | 검증 |
|------|------|------|
| 에스크로 교역 | ✅ | 동시 수락 테스트 통과 |
| XSS 방어 | ✅ | 스크립트 주입 시도 시 차단 확인 |
| 음수 방어 | ✅ | `@validates` 단위 테스트 |
| 소수점 불사 방지 | ✅ | 4명 출정 20번 반복 시 평균 0.8명 사망 확인 |
| 보호 모드 Lost Update 방지 | ✅ | with_for_update() 락 획득 후 동시 GET/POST 요청 무결성 테스트 통과 |
| 원자적 재시작 및 자동 복구 | ✅ | restart 단일 트랜잭션 결합 및 공원 유실 시 index/login/dashboard 자동 복구 검증 |
| Gunicorn 프로세스 락 확보 | ✅ | 비관적 락(with_for_update) 획득 및 정렬 락을 통한 우회/데드락 차단 검증 |
| NPC 턴 트랜잭션 원자화 | ✅ | case() 기반 passive_growth 적용 및 commit=False 옵션 도입으로 부분 커밋 누출 차단 |
| AP 누수 차단 및 보상 트랜잭션 | ✅ | 고의적 유효성 실패 유도 시 AP 즉각 환불 복구 및 누수 0건 검증 완료 |
| 좀비 상태 방지 및 TOCTOU 검증 | ✅ | 턴 진행 후 멸망 차단 검증 및 비관적 락 획득 후 멸망 재검증 가드 통과 |
| Cascade 연쇄 삭제 에스크로 방어 | ✅ | 상대방 공원 삭제(재시작) 시 pending 거래 및 active 밀사의 에스크로 원자적 자동 환불 검증 완료 |
| 교차 외교 중복/모순 방어 | ✅ | Canonical Ordering, ID 정렬 2중 락 및 Bulk Update 적용을 통한 교차 중복 생성 및 동맹/적대 모순 상태 차단 검증 완료 |
| NPC 턴 및 밀사 락 격리 무결성 | ✅ | 개별 트랜잭션 단위 격리 조회, Nested Savepoint 예외 가드 및 밀사 2-Way Lock을 통한 락 분실/덮어쓰기 완전 해결 |
| 교역 거절 IDOR 보안 가드 | ✅ | 타인의 교역 ID로 거절 시도 시 조건 검증 실패로 0건 업데이트 및 거절 무산 확인 |
| 시장 좀비 거래 원천 정화 | ✅ | 발송자 멸망 시 교역 상태 pending 유지에도 공개 시장 목록에서 즉시 비노출 검증 |
| 슬로우 패스 AP 복제 Lost Update 방지 | ✅ | 턴 동기화 갭 동안 패스트 패스로 AP 소감 후 슬로우 패스 커밋 시 Stale AP 덮어쓰기 방지 검증 완료 |
| NPC 중첩 Savepoint 깨짐 방지 | ✅ | 공격 행동 내부 commit 대신 flush 사용으로 ResourceClosedError 및 루프 무한 AP 미소모 현상 완치 검증 완료 |
| AP 환불 누출 블랙홀 방지 | ✅ | AP 환불 복구 즉시 라우터 단 명시적 db.session.commit() 집행을 통한 teardown 롤백 유실(AP Blackhole) 원천 차단 검증 완료 |
| 밀사 overcrowding Lost Update 방지 | ✅ | overcrowding 연산 진입 직전 플레이어 공원 2차 비관적 락 및 refresh 동기화를 통한 데이터 덮어쓰기 경쟁상태 차단 검증 완료 |
| NPC 공격 락 순서 역전 데드락 완치 | ✅ | `process_npc_turn` 최상단 `with_for_update` 제거 후 공격 시 Canonical Locking 데드락 해소 검증 완료 |

#### Phase 9: 안드로이드 APK (미래)
| 항목 | 목표 | 알고리즘 메모 |
|------|------|--------------|
| Kivy UI 재작성 | 화면 전환(Screen) 기반 | Flask 라우트 → Kivy Screen 매핑 |
| 로컬 프로필 | SQLite 파일 로컬 저장 | `game.db` → 내부 저장소 경로 |
| NPC 자동 교역 | 기존 TradeOffer 로직 재사용 | receiver_id=NULL 자동 수락 |
| 턴 타이머 | APScheduler → Kivy Clock | `Clock.schedule_interval` |

#### Phase 10: UI/UX 리팩토링 및 Gore-Terminal 디자인 시스템 반영 (완료)
| 마일스톤 | 구현 항목 | 디자인/UX 적합성 검증 방법 | 데이터 정합성 통과 기준 |
|---------|----------|--------------------------|----------------------|
| **MS 1: Base & CRT** | - Tailwind CSS 및 Material Symbols CDN 도입<br>- `base.html`에 CRT 스캔라인 및 0.15s 플리커링 탑재<br>- `--bg`, `--text-bright` 등 커스텀 변수 정의 | 브라우저 F12 성능 탭에서 플리커 애니메이션의 CPU 과부하 여부 체크 | `style.css` 내 컬러 토큰이 `designs.md` 명세서와 100% 일치 |
| **MS 2: Dashboard** | - Tailwind 기반 3열 반응형 그리드 적용<br>- 인사말 좌측에 픽셀 도트 실장석 아바타 탑재<br>- 6단 AP 게이지 바 및 카운트다운 타이머 연동 | 1200px -> 768px -> 480px 화면 축소 시 그리드가 3열->2열->1열로 깨짐 없이 자동 전환되는지 확인 | `current_user.park` 모델 데이터가 현황 패널 및 아바타에 올바르게 바인딩 |
| **MS 3: Actions & Modals** | - 액션 버튼 호버/클릭(active:scale-95) 애니메이션<br>- 솎아내기 Crimson 경고 점멸<br>- 정찰/침공 모달을 Combat Analyzer 테마로 고도화 | 솎아내기 시 confirm 창이 정상적으로 뜨며, 모달 팝업 시 뒷배경 흐림 효과(`backdrop-filter: blur`)가 미려하게 먹히는지 검증 | 모달의 폼 전송 데이터가 `game_routes.py` 라우트 파라미터와 오차 없이 통신 |
| **MS 4: Trade & Diplomacy** | - `trade.html`을 고밀도 BBS 탭 UI로 전환<br>- 외교 관계 및 교역 시장 현황을 Phosphor Green/Crimson 컬러 바로 텐션 극대화 | 탭 전환 시 화면 깜빡임 없이 DOM 콘텐츠가 동적으로 스위칭되는지 확인 | 교역 시장 자원 아이콘과 NP 수치가 모델 스펙과 온전히 일치 |
| **MS 5: Collapse & Skills** | - `gameover.html` 에러 글리치 효과<br>- `skills.html` 가상 스킬 트리 추가<br>- 1초 주기 SP 요동 카운터 및 SVG 연결망 시각화 | 보스 사망 시 붉은 화면 및 글리치 연출 확인. 스킬 노드 클릭 시 상세 카드가 팝업되는지 확인 | `skills.html` 내의 다국어 텍스트가 번역 헬퍼 `t()`와 정상 연동되는지 체크 |

---

## 5. 체크포인트 정책

### 5.1 코드 변경 시 필수 체크포인트
```
[코드 수정] → [단위 테스트] → [통합 테스트] → [문서 동기화] → [커밋]
```

### 5.2 필수 테스트 시나리오

| # | 시나리오 | 명령/방법 | 통과 기준 |
|---|----------|----------|----------|
| T1 | 신규 가입 → 채집 | 회원가입 → 채집 버튼 클릭 | 자원 증가, AP 감소 |
| T2 | AP 소진 → 턴 진행 | 채집 3회 → 4회 시도 | 턴쿼터 1 소비, AP 3 리셋 |
| T3 | 보호 모드 진입 | 성체/경호 0으로 조작 | 🛡️ 배너, 침공 버튼 비활성 |
| T4 | 교역 수락 Race | 두 브라우저에서 동시 수락 | 1건만 성공, 다른 1건은 실패 |
| T5 | 음수 입력 차단 | 솎아내기 count = -5 입력 | 0으로 처리 또는 거부 |
| T6 | XSS 시도 | 교역 메시지에 `<script>` 입력 | 이스케이프되어 텍스트로 표시 |
| T7 | 전투 피해 | 4명 출정 100회 반복 | 평균 사상자 0.8 ± 0.1 |
| T8 | 10턴 생존 | 디버그 턴 10회 실행 | 게임오버 없음 (보호 모드) |
| T9 | 다국어 전환 | `/set-lang/en` → 대시보드 | 모든 텍스트 영어로 변경 |
| T10 | NPC 동작 | 디버그 턴 10회 실행 | NPC 자원/인구 변동 확인 |
| T11 | 보호 모드 Lost Update 검증 | 대시보드 로드(GET) 중 동시에 다른 창에서 POST 호출 시 자원 덮어쓰기 여부 확인 | 대시보드 커밋이 POST 변경점을 덮어쓰지 않고 최신 값 유지 |
| T12 | 공원 유실 자동 복구 검증 | 유저 공원을 DB에서 강제 삭제 후 `/dashboard` 또는 `/login` 진입 | 무한 리다이렉트 없이 즉시 기본 사양 공원으로 자동 재생성 복구 완료 |
| T13 | Gunicorn 교역 제한 우회 검증 | 4개 워커 기동 하에 동일 유저가 동시에 20개의 교역 생성 API 동시 호출 시도 | 10개 한도를 넘어가는 추가 등록건이 철저히 차단되고 직렬화되어 처리됨 |
| T14 | NPC 턴 예외 시 롤백 정합성 | NPC AI 행동 루프 진행 도중 임의의 예외(Exception) 유발 및 복구 | AP 감소 및 자원 변경 등의 중간 데이터가 누출 커밋 없이 완전 롤백됨 |
| T15 | AP 누수 및 보상 트랜잭션 정합성 | `park.strike_turns = 1`(파업) 상태에서 채집/건설 등을 호출하여 고의적 유효성 실패 유도 | 행동 실행은 무산되지만 이미 consume_turn으로 선행 차감된 AP(1)가 즉시 복구(환불)되어 보존됨 |
| T16 | 좀비 액션 및 TOCTOU 멸망 정합성 | 턴 소모 중 보스 HP=0 멸망 유발 또는 교역 수락 비관적 락 중 대기 중에 멸망 유도 | 턴 도중 멸망 시 즉시 차단 리턴되며, 교역 수락 및 전투 실행 도중 락 획득 후에도 즉시 무산 및 롤백됨 |
| T17 | Cascade Delete 에스크로 환불 검증 | B유저가 A유저에게 교역 제안(에스크로) 및 밀사 파견 후 A유저가 공원 삭제(/restart) 실행 | B유저가 묶어둔 거래 자원 및 파견된 성체실장이 영구 유실 없이 B유저 공원으로 자동 환불 처리 완료 |
| T18 | 교차 외교 및 모순 상태 방어 검증 | A, B 공원이 서로에게 동시 동맹/적대 요청 및 적대 선언 후 동맹 해제 누락 여부 검증 | 중복 생성 없이 1건만 생성되며, 적대 선언 시 기존 동맹이 일괄 해제(Bulk Update)되어 모순 상태(동맹이자 적대) 방지 |
| T19 | NPC 개별 트랜잭션 격리 및 Savepoint 무결성 검증 | Gunicorn 다중 프로세스 동기화 중 NPC AI 행동 내부 예외 유발 후 락 및 턴 소모 여부 검증 | 예외 발생 시 Nested Transaction만 롤백되어 비관적 락 및 turn_count는 안전하게 유지 및 커밋됨 |
| T20 | 교역 거절 IDOR 보안 가드 | A유저의 비공개 거래 제안 ID를 B유저가 변조하여 거절 API POST 요청 전송 | receiver_id가 일치하지 않아 DB UPDATE가 무산(0건)되고 거절 오류 메시지 반환 |
| T21 | 시장 좀비 거래 원천 정화 | 공개 거래를 등록한 유저가 멸망(is_destroyed=True)된 상태에서 타 유저의 교역 시장 페이지 진입 | is_destroyed가 True인 유저의 대기 교역은 JOIN 쿼리에 의해 시장에 노출되지 않음 |
| T22 | 슬로우 패스 AP 복제 Lost Update 방지 | 턴쿼터 소모 턴 진행 중 무락 갭(Lock-free Gap) 하에 concurrent 액션을 기동해 AP를 선차감 시킨 후 슬로우 패스 최종 커밋 실행 | concurrent 요청으로 소모된 AP가 슬로우 패스의 최종 AP 2차 락 & refresh 감산 연산으로 덮어쓰기 없이 정상 반영됨 |
| T23 | NPC 중첩 Savepoint 깨짐 방지 검증 | NPC AI 턴 진행 중 공격(`_npc_attack` 또는 `_npc_cunning_attack`) 행동을 유도하고, 행동 성공/실패 시 예외를 고의로 일으켜 Savepoint 깨짐 여부 검증 | `ResourceClosedError` 없이 세이브포인트가 정상 작동하여 해당 공격 행동만 롤백되고 NPC 턴 진행 루프는 지속됨 |
| T24 | AP 환불 블랙홀 방지 검증 | 채집/출산 등 행동 시도 시 고의적으로 유효성 실패를 유도하여 `refund_ap` 분기 태운 후, HTTP 리다이렉션 직전 트랜잭션 롤백 여부 검증 | 라우터 단에서 즉각 명시적 커밋을 집행하여 AP 환불 수치가 유실 없이 DB에 영구적으로 반영됨 |
| T25 | 밀사 overcrowding Lost Update 방지 검증 | 밀사 복귀 턴을 세팅하고 복귀 임무 진행 중 무락 갭 하에 concurrent 액션을 기동해 자원/인구 상태를 변동시킨 후 밀사 최종 overcrowding 검사 및 커밋 실행 | concurrent 요청으로 변경된 최신 DB 상태가 밀사의 최종 2차 락 & refresh 동기화 검사 연산으로 인해 Stale Overwrite 덮어쓰기 없이 안전하게 보존됨 |
| T26 | NPC 공격 락 순서 역전 데드락 완치 검증 | NPC 턴 진행 도중 공격 행동을 유발하는 동시에, 플레이어가 해당 NPC를 향해 공격/교역/외교를 동시 기동하여 DB 락 충돌 유도 | 교착 상태(Deadlock)나 DB 커넥션 풀 고갈 없이 두 요청 모두 Canonical Ordering 정렬에 의해 순차적으로 또는 즉시 롤백 처리 완료됨 |

---

## 6. 현재 남은 핵심 리스크

| 리스크 | Phase | 영향 | 대응 계획 |
|--------|-------|------|----------|
| 밀사 UI 미흡 | Phase 6 | 밀사 기능 숨겨짐 | 대시보드에 밀사 버튼 추가 (후순위) |
| `game_engine.py` 과대 | 현재 | 유지보수 어려움 | `process_turn` 단계별 함수 분리 완료, 추가 분리 검토 |
| `game_routes.py` 과대 | 현재 | 라우트 혼잡 | 교역/외교 블루프린트 분리 검토 |
| APK 이식 복잡도 | Phase 9 | 일정 지연 | 핵심 로직 분리 완료, UI만 재작성 |
| 모바일 턴 게이지 정확도 | Phase 7 | 1~2초 오차 | 클라이언트 카운트다운, 서버는 타임스탬프 기준 |
| 다국어 번역 품질 | Phase 5 | 일부 표현 어색 | 번역자 리뷰 필요 |
| SQLite 동시 쓰기 | 현재 | 턴 처리 지연 | WAL 모드 및 busy_timeout 5000ms 강제 자동 주입 활성화 완료 (Engine 커넥션 이벤트 리스너 완비), 단일 서버 운영 |

---

*문서 끝*
