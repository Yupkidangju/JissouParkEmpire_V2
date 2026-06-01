# 변경 이력 (Changelog)

이 프로젝트의 모든 주요 변경사항을 기록한다.
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)를 따르며,
버전 관리는 [Semantic Versioning](https://semver.org/lang/ko/)을 준수한다.

## [Unreleased]

### 예정됨 (Planned)
- **Phase 9: 안드로이드 솔플 APK 빌드** (Kivy/BeeWare 기반)

## [1.8.9] - 2026-06-01

### 추가됨 (Added)
- **Node.js 런타임 융합형 프론트엔드 XSS 헬퍼 교차 검증 및 정적 innerHTML 안전성 스캔 회귀 테스트 도입**: `tests/test_regression.py` 하단에 로컬 Node.js `v24.14.1` 런타임을 `subprocess`로 결합 기동하여 `app/static/js/game.js`로부터 추출한 `escapeHtml` 헬퍼의 치환 정합성을 교차 확인하고, `game.js` 내의 주요 `innerHTML` 동적 대입문 및 데이터 빌더 블록 내부의 백틱 템플릿 리터럴 보간 항목에서 `escapeHtml` 등 안전 가드가 누락되었는지를 정밀 Regex로 정적 분석하는 신규 회귀 검증 테스트를 수립하여 보안 안전성을 보완했습니다.
- **SQLite 2중 SQLAlchemy 세션 기반 Lost Update Race Condition 회귀 테스트 도입**: SQLite의 `with_for_update()` 비관적 락 no-op 한계를 극복하고 stale read/stale write-back 상황에서의 논리적 lost update 가드(`session.refresh` 및 트랜잭션 격리)를 실질적으로 검증할 수 있도록, 두 개의 독립된 세션을 동시에 가동하여 lost update 방지를 그린 패스로 증명하는 신규 동시성 테스트를 추가했습니다.
- **감사 보고서 대응 표준 조치 기록 템플릿(4-Tier) 도입**: Hold 지적 사항에 대해 '조치내용/처리방법/남은위협/감사에게 요청할 사항'을 상세 기록하고 Status를 `Verified / Fixed`로 변경하도록 규격화하여 `lessons_learned.md`에 영구 표준으로 정립했습니다.

### 수정됨 (Fixed)
- **개발 서버 바인딩 루프백 락다운 및 환경변수 opt-in 적용**: clean env 실행 시 `run.py`가 Flask 개발 서버를 `0.0.0.0`으로 기동하여 로컬 LAN 네트워크상에 debug console 백도어가 노출되던 보안 결함을 수정하여 기본 바인딩 host를 `127.0.0.1`로 락다운하고, 외부 바인딩이 필요할 때만 `FLASK_RUN_HOST` 환경변수로 opt-in 하도록 개편했습니다.
- **프로덕션 환경변수 감지 시 하드 락다운(Fail-Closed/Hard Lockdown) 적용**: `FLASK_ENV=production` 또는 `ENV_TYPE=production` 설정이 감지되는 경우, 개발자가 실수로 `DEBUG=true`를 활성화하더라도 디버거를 강제로 차단(False)하고, `SECRET_KEY`가 누락된 경우 임시 난수 fallback 없이 즉각 `ValueError`를 발생시키며 안전 실패(Fail-Closed) 상태로 구동을 강제 정지시키는 논리 장벽을 강화했습니다.
- **품질 게이트 whitespace/공백 고도 정제**: `git diff --check` 검증 시 실패를 야기하던 `BUILD_GUIDE.md`, `app/config.py` 등 모든 파일의 불필요한 trailing whitespace 및 EOF blank line을 전수 제거하여 품질 품질 게이트를 통과시켰습니다.
- **NPC 턴 진행 2단계 트랜잭션 경계 분리를 통한 교착 상태(Deadlock) 및 DB 커넥션 고갈 고도 예방**: 턴 동기화 스케줄러 `_sync_npc_turns()` 레벨에서 NPC 기본 턴 처리(`process_turn`) 완료 즉시 명시적인 `db.session.commit()`을 강제하여 선점 락을 원천 소멸한 뒤, 독립된 트랜잭션 경계 하에 `process_npc_turn()`을 구동하는 **2단계 트랜잭션 경계 분리 구조**를 전격 채택 및 적용했습니다. 또한 `process_npc_turn()` 시작 시점에서의 무조건적 락 선점을 영구 배제하고 단순 `db.session.refresh(park)`로 완화하여, NPC 공격 행동 기동 시 오직 `execute_battle()` 내부에서만 두 공원의 락을 ID 오름차순(Canonical Ordering) 순으로 안전하게 동시 획득하도록 보장함으로써 락 순서 역전 교착 상태 취약점`[DEADLOCK-F005]`과 DB 커넥션 풀 고갈 결함 발생 위험을 강력히 예방했습니다.
- **SQLite Engine Pragma 이벤트 리스너 기반 WAL/busy_timeout pragma 자동 주입**: 기본 배포 DB인 SQLite 환경에서 `with_for_update()` no-op(FOR UPDATE SQL 미생성) 제약을 극복하고 Database Locked(DB 잠금) 오류를 예방하기 위해, SQLAlchemy `Engine` 'connect' 이벤트 리스너를 수립하여 SQLite 연결 즉시 `PRAGMA journal_mode=WAL` 및 `PRAGMA busy_timeout=5000` pragma를 데이터베이스 연결 시점에 자동으로 강제 주입 활성화하였습니다.
- **프로덕션 안전 실패(Fail-Closed) 비밀키 보안 정책 탑재**: 프로덕션(DEBUG=False) 환경에서 `SECRET_KEY` 또는 `FLASK_SECRET_KEY` 환경변수가 누락되었을 경우, 기존처럼 무작위 난수 키 fallback으로 구동하여 Gunicorn 다중 워커 간의 세션 불일치와 미지정 구동 취약점을 방치하는 대신, 즉각 `ValueError` 예외를 터뜨리고 가동을 강제 중단하는 안전 실패(Fail-Closed) 보안 모델을 탑재했습니다. (개발/테스트 환경에서는 기존 난수 자동 생성 fallback 유지)
- **NPC 공격 행동의 Commit 플러시(Flush) 대체 및 Savepoint 복구 보강**: NPC AI의 공격 행동(`_npc_attack`, `_npc_cunning_attack`) 내부에서 실행되던 `db.session.commit()`이 RDBMS 트랜잭션을 강제 종료시켜 nested 세이브포인트를 파괴하고 `ResourceClosedError` 및 AP 미소모 무한 루프 폭사를 유발하던 결함을 해결했습니다. `commit()`을 `db.session.flush()`로 전환하여 세이브포인트 손상 없이 변경점만 SQL로 방출되도록 개선했습니다. 또한 `process_npc_turn` 예외 처리부에서 `nested.rollback()` 실패 시 `db.session.rollback()`을 기동하는 2중 롤백 예외 방어를 도입하여 세션을 온전히 보존하도록 조치했습니다. (audit_report_57.md)
- **AP 환불 보상 트랜잭션의 롤백 누출(AP Blackhole) 차단**: 라우터(`game_routes.py`) 레벨의 예외 분기나 기각 분기에서 `game_engine.refund_ap()`를 호출해 AP 복구 UPDATE를 작동시켜도, 최종 `db.session.commit()` 없이 HTTP 리다이렉트를 반환할 경우 Flask 세션 소멸 시점에 AP 환불 데이터가 조용히 롤백 유실되던 자원 블랙홀 취약점을 치료했습니다. 환불을 기동하는 모든 기각 분기(총 8군데) 뒤에 `db.session.commit()`을 명시적으로 집행하도록 보강하여 무결성을 달성했습니다. (audit_report_58.md)
- **밀사 귀환 후 인구 초과 처리의 2차 비관적 락 가드 확보 및 Lost Update 경쟁 상태 차단**: 밀사 임무 처리(`_process_spy_missions`) 종료 후 밀사 귀환 등으로 인한 수용 한도 초과 인구 정화(`_process_overcrowding`)를 실행할 때, 비관적 락 없이 단순 `refresh` 및 메모리 변경 후 `commit`을 구동하여 concurrent 요청(채집, 교역 등)에 의한 DB 상태 변경을 메모리 구버전 데이터로 덮어쓰던 동시성 결함을 수정했습니다. 과밀도 연산 진입 직전에 플레이어 공원에 대해 다시 한 번 `with_for_update()` 비관적 락을 획득하고 `refresh`를 수행하여, 병렬 요청과의 데이터 정합성 무결성을 달성했습니다. (audit_report_59.md)

## [1.8.8] - 2026-05-31

### 수정됨 (Fixed)
- **턴 소비 슬로우 패스(Slow-path) AP 복제 Lost Update 취약점 차단**: `consume_turn()`에서 AP 부족으로 슬로우 패스가 수행될 때, 턴 쿼터 차감 및 턴 진행(`process_turn`) 후 AP가 10으로 고도로 리셋된 상태에서 일시적으로 락이 풀리는 현상을 악용하여 다중 비동기 요청(패스트 패스)으로 AP를 선차감한 이력을 Stale AP 정보로 덮어쓰던 동시성 결함을 해결했습니다. 슬로우 패스의 모든 턴 진행 및 `_sync_npc_turns()` 동기화 처리가 끝난 직후이자 최종 AP 차감 직전에 **플레이어 공원에 대해 2차 비관적 락(`with_for_update()`) 및 `db.session.refresh(park)`를 명시적으로 실행**하도록 아키텍처를 개선하여, 동기화 갭 동안 차감된 최신 AP 수치를 DB로부터 새로고침한 뒤 최종 AP 연산이 원자적으로 수행되도록 보장했습니다. (audit_report_56.md [STATE-F029])

## [1.8.7] - 2026-05-31

### 수정됨 (Fixed)
- **교역 거절 IDOR 인가(Authorization) 취약점 차단**: `trade_reject(trade_id)` API의 원자적 UPDATE 조건식에 `TradeOffer.receiver_id == park.id` 가드 필터를 추가하였습니다. 이를 통해 로그인한 사용자가 해당 교역의 정당한 수신자(receiver)인지 DB 레벨에서 검증하도록 강제하여, 악의적인 유저가 임의의 거래 ID를 변조하여 POST 요청을 보냄으로써 타인의 비공개 거래 제안이나 공개 거래를 함부로 폭파(DoS)시키는 Insecure Direct Object Reference 취약점을 차단했습니다. (audit_report_55.md [AUTH-F001])
- **시장 좀비 거래(Zombie Trades) 노출 정화 및 리소스 낭비 차단**: `trade_market()` 공개 시장 목록을 불러오는 데이터베이스 쿼리 단계에서 `Park` 모델을 JOIN하고 `Park.is_destroyed == False` 필터를 가드로 추가하였습니다. 멸망한 발송자(Sender)의 대기 교역 제안이 시장 화면에 계속 노출되어 사용자 경험을 저해하고, 다른 유저가 이를 수락 시도할 때서야 비관적 락 단계에서 멸망을 확인해 만료 처리되던 쿼터 및 트랜잭션 경합 리소스 낭비 현상을 원천 치료하였습니다. (audit_report_55.md [LOGIC-F022])

## [1.8.6] - 2026-05-31

### 수정됨 (Fixed)
- **NPC 턴 동기화 루프 내 DB 커밋으로 인한 비관적 락 유실 및 Lost Update 차단**: `_sync_npc_turns`에서 모든 NPC를 일괄 `with_for_update().all()`로 가져온 뒤 루프 내에서 `commit()`하는 기존 구조로 인해, 첫 번째 NPC 커밋 시 나머지 NPC들의 락이 조기 해제되어 타 스레드가 개입해 턴을 중복 수행하는 결함을 수정함. 루프 외부에서는 ID 목록만 추출하고, 루프 내부에서 **개별 트랜잭션 단위로 각 NPC 공원을 비관적 락 조회(`with_for_update()`) 및 commit**하도록 트랜잭션 경계를 고도로 분리 격리하여 Lost Update를 차단함. (audit_report_54.md [STATE-F028])
- **NPC AI 행동 내부 예외 발생 시 비관적 락 유실 및 무한 턴(Stampede) 방어**: NPC의 개별 행동 시도 중 예외 발생 시 전체 트랜잭션을 `rollback()`하여 진입 시 획득했던 공원의 비관적 락까지 유실되고 턴 충전 수치가 소실되던 아키텍처적 결함을 해결함. 행동 호출 부에 **Nested Transaction (Savepoint, `begin_nested()`)** 격리망을 구축하여 예외 발생 시 오직 실패한 그 행동의 상태만 롤백하고 부모 트랜잭션과 비관적 락, 그리고 이전 단계의 턴 정보(`turn_count`)를 유실 없이 완전 보존하도록 보강함. (audit_report_54.md [TRANSACTION-F005])
- **밀사 사보타주 피해량 산정 TOCTOU 방지 및 2-Way Lock 격리**: 밀사가 적 공원에 사보타주를 기동하여 자원/유닛 피해를 유발할 때, 피해 산정 시점과 실제 쿼리 실행 간의 격차로 인해 로그 상의 소실량과 실제 반영 데이터가 불일치하는 결함을 해결함. 임무 성공 여부 판단 및 피해량 연산 시작 전 두 공원에 대해 ID 정렬 2중 비관적 락을 먼저 획득하도록 보완하여 무결성을 강제함. (audit_report_54.md [LOGIC-F021])

## [1.8.5] - 2026-05-31

### 수정됨 (Fixed)
- **교차 외교 동시 선언 시 중복 관계 생성 및 Concurrency 데드락 방지**: 두 공원이 동시 교차로 동맹이나 적대를 제안하는 경우, 기존 Unique 제약이 `(A, B)`와 `(B, A)`를 별개의 고유한 쌍으로 판단하여 중복 삽입되는 문제를 해결함. 항상 `park_a_id < park_b_id`를 강제하는 **표준 순서 규격(Canonical Ordering)**을 적용하였으며, 외교 제안의 원래 주체를 판별하기 위해 `initiator_id` 컬럼을 도입함. 더불어, 교차 요청 시 발생할 수 있는 데이터베이스 데드락 및 동시성 충돌을 원천 방어하기 위해 관련 외교 라우터 진입 시 두 공원의 ID를 오름차순으로 정렬하여 **2중 비관적 락(`with_for_update()`)**을 일괄 획득하도록 보완함. (audit_report_53.md [STATE-F027])
- **중복 외교 관계로 인한 동맹/적대 모순 상태 및 관계 해제 누락 차단**: 이전 턴에서의 중복이나 동시성 레이스로 인해 한 쌍의 공원 간에 여러 개의 active/pending 관계가 존재할 경우, 관계 해제나 적대 선언 시 `.first()`로 단일 레코드만 갱신하여 나머지 좀비 레코드가 잔존해 '동맹이자 적대'인 상태 논리 오염을 원천 치료함. 적대 선언(`diplomacy_enemy`) 및 관계 해제(`diplomacy_dissolve`) 시 **일괄 벌크 업데이트(`.update()`)** 쿼리를 도입하여 기존의 모든 중복 관계들을 일괄 `dissolved` 처리하도록 구현함으로써 데이터 정합성 무결성을 달성함. (audit_report_53.md [LOGIC-F020])

## [1.8.4] - 2026-05-31

### 수정됨 (Fixed)
- **Cascade Delete 연쇄 삭제로 인한 에스크로 자원 및 유닛 영구 유실 방지**: 수신자/타겟 공원 삭제(/restart 등) 시, 교역(`TradeOffer`) 및 밀사(`SpyMission`) 모델의 Cascade `delete-orphan` 연쇄 삭제로 인해 발신자(Sender)가 선차감했던 에스크로 자원과 유닛이 환불되지 않고 영구 유실(Resource Leakage)되던 결함을 해결함. `app/models.py` 최하단에 SQLAlchemy `before_delete` 이벤트 리스너를 도입하여, 삭제 전 pending 상태인 교역 자원(Cap 캡핑 보정 포함) 및 active 상태인 밀사의 성체실장을 자동으로 발신자 공원에 원자적으로 복구 환불 처리하도록 설계함으로써 데이터 무결성을 보장함. (audit_report_51.md [STATE-F025])

## [1.8.3] - 2026-05-31

### 수정됨 (Fixed)
- **좀비 상태 행동 차단 및 턴 경과 멸망 유효성 재검사**: `consume_turn()`에서 AP가 부족하여 `process_turn()`을 실행한 뒤 굶주림 등으로 보스 HP가 0이 되어 공원이 멸망(`is_destroyed=True`)할 경우, 즉시 행동 처리를 중단하고 실패 리턴하도록 검증 가드를 신설하여 멸망한 상태에서 건설/침공 등 좀비 액션(Zombie Action)을 취할 수 있던 결함을 차단함 (audit_report_50.md [STATE-F024])
- **비관적 락 획득 후 TOCTOU 멸망 상태 재검증**: 교역 수락(`trade_accept`) 및 전투 엔진(`execute_battle`)에서 `with_for_update()` 비관적 락을 획득하고 객체를 리프레시한 직후, 락 대기 시간 동안 상대방 또는 자아가 멸망했는지(`is_destroyed` 여부)를 재검사하여 교역을 즉각 취소(만료) 또는 전투를 중단 롤백하도록 설계하여, 멸망한 좀비 공원과 자원 거래를 하거나 침공하는 TOCTOU 논리 무결성 붕괴 취약점을 완벽 해결함.

## [1.8.2] - 2026-05-31

### 수정됨 (Fixed)
- **비원자적 행동 실패 시 AP 누수 해결을 위한 보상 트랜잭션 구현**: `consume_turn()`에서 AP를 선행 차감 및 커밋한 후 실제 행동(채집, 출산, 건설, 훈련, 침공)의 내부 유효성 검사 실패나 자원 차감 실패 등으로 행동이 중단(`not success`)될 때, 이미 차감된 AP를 안전하게 복구해주는 `game_engine.refund_ap()` 공용 보상 트랜잭션 헬퍼를 도입하여 각 행동 라우트에 긴밀하게 연동함. 이를 통해 AP 누수(AP Leakage / Ghost Deduction) 현상을 고도로 해결함 (audit_report_49.md [STATE-F023])
- **외교 및 밀사 환불 로직의 공용 헬퍼 일원화**: 기존 `/diplomacy/enemy` 및 `/spy` 라우트 내부에서 SQL `update` 문을 직접 수행하여 개별 처리하던 환불 코드를 `game_engine.refund_ap()` 호출로 리팩토링하여 복구 정합성을 획기적으로 개선함. 특히 적대 선언 시 이미 적대 관계인 경우(`existing_enemy` 존재 시)에도 AP가 정상 복구되도록 보안 취약점을 추가적으로 차단함.

## [1.8.1] - 2026-05-31

### 수정됨 (Fixed)
- **프로세스 장벽 동시성 제어 확보 및 Gunicorn 락 우회 차단**: 다중 워커 프로세스 환경에서 스레드 락(`threading.Lock()`)의 무력함을 극복하고, 교역 생성(`trade_create`) 및 NPC 동기 턴 진행(`_sync_npc_turns`) 시에 데이터베이스 레벨의 **비관적 락(`with_for_update()`)** 및 일관된 id 정렬(데드락 방지)을 획득하도록 개편하여 교역 등록 제한 우회 및 동일 NPC의 턴 중복 처리(NPC Stampede) 밸런스 붕괴를 완벽하게 차단함 (audit_report_48.md [LOGIC-F019])
- **NPC 턴 트랜잭션 원자화 및 Lost Update 수정**: NPC의 소규모 자연 성장(`_npc_passive_growth`)을 `case()` 기반의 단일 원자적 `UPDATE`로 전환하여 `autoflush` 발동 시 메모리 상의 구버전 데이터로 플레이어의 공격/약탈 결과를 덮어쓰는(Lost Update) 문제를 해결하였고, 범용 엔진 함수(`action_gather`, `action_birth`, `action_build`, `action_train`, `action_cull`)에 `commit=True` 매개변수를 도입하여 NPC 행동 시 중간 커밋을 억제하고 단일 NPC 턴 전체가 고도로 원자적인 트랜잭션 안에서 수행 및 롤백될 수 있도록 구조를 개편함 (audit_report_48.md [STATE-F022])

## [1.8.0] - 2026-05-31

### 수정됨 (Fixed)
- **보호 모드 Lost Update 방지**: `check_and_enter_protection(park)` 실행 시 `Park.query.with_for_update()` 비관적 락을 획득하고 `db.session.refresh(park)`를 강제하여, GET `/dashboard` 진입과 비동기 POST 액션 간의 TOCTOU Race Condition 및 구버전 메모리 상태 커밋으로 인한 자원/인구 Lost Update 문제를 근원적으로 해결 (audit_report_47.md [STATE-F020])
- **재시작(Restart) 로직 원자성 확보 및 무한 리다이렉트 해결**: `/restart` 라우트의 2단계 트랜잭션 커밋(`delete` 후 `add` 커밋) 구조를 단일 트랜잭션으로 통합하여 원자성(Atomicity)을 보장하였고, 공원이 없는 유저가 `/login`이나 루트 `/` 혹은 `/dashboard`에 진입할 경우 자동으로 기본 공원을 재생성 복구해주는 `game_engine.create_default_park()` 통합 헬퍼를 도입하여 `ERR_TOO_MANY_REDIRECTS` 무한 핑퐁 리다이렉트 에러를 해결 (audit_report_47.md [STATE-F021])

## [1.7.0] - 2026-05-30

### 추가됨 (Added)
- **가상 스킬 트리 터미널**: 향후 시스템 확장을 대비해 SP 자동 충전 라이브 카운터가 탑재된 이스터에그 모크업 페이지 `skills.html` 신설 및 네비게이션 연동

### 변경됨 (Changed)
- **디자인 시스템 갱신**: Tailwind CSS CDN을 `base.html`에 전격 도입하고 고밀도 인광 메인프레임 감성의 **Gore-Terminal** 테마 구축
- **대시보드 리팩토링**: `dashboard.html`을 3열 반응형 그리드로 전면 개편하고 실장석 도트 아바타와 6단 AP 게이지 바 탑재
- **교역/외교 UI 고도화**: `trade.html`을 고밀도 BBS 탭 UI로 마이그레이션하여 모달 및 게이지 비주얼 텐션 강화
- **멸망 화면 리팩토링**: `gameover.html`을 시스템 에러 붉은 글리치 비주얼로 리디자인

### 문서화 (Documentation)
- **리팩토링 계획 설계 및 구현 완료 동기화**: `spec.md`, `designs.md`, `DESIGN_DECISIONS.md`, `implementation_summary.md`, `audit_roadmap.md`, `lessons_learned.md`에 최종 마일스톤 구현 라인수 및 CRT 렌더링 성능 최적화와 가상 스킬 트리 이스터에그의 디자인 교훈을 100% 동기화함

## [1.6.3] - 2026-02-21

### 수정됨 (Fixed)
- **거절의 블랙홀**: `trade_reject`에 에스크로 환불 추가 (거절=자원 소멸 방지)
- **취소 중복 환불**: `trade_cancel`에 원자적 `UPDATE-WHERE` 상태 전환
  - 동시 10회 취소 시 1건만 성공, 나머지 9건은 `updated=0`으로 차단
- **외교 0AP 무한 반복**: `max(0, AP-1)` → `consume_turn(ap_cost=1)`로 교체
  - AP=0일 때도 제대로 턴쿼터 소비됨

## [1.6.2] - 2026-02-21

### 수정됨 (Fixed)
- **소수점 불사 부대**: `int()` 절사 → `stochastic_round()` 확률적 반올림
  - 이전: `int(4 * 0.2) = 0` → 4명 이하 출전 시 사상자 0 고정 (무손실 파밍)
  - 이후: `0.8` → 80% 확률로 1명 사망 (확률적 공정 처리)

### 보안 (Security)
- **교역소 DoS 방지**: `my_incoming`/`my_outgoing` 쿼리에 `.limit(50)` 추가
- **교역 스팸 방지**: 유저당 동시 대기 교역 10개 제한

## [1.6.1] - 2026-02-21

### 수정됨 (Fixed)
- **Soft-Lock 수정**: 버튼 disabled 조건을 `AP < N AND turn_quota < 1` 복합 조건으로 변경
  - 이전: AP=0이면 모든 버튼 비활성화 → consume_turn 자동 턴 진행 호출 불가 → 영구 정지
  - 이후: AP=0이어도 턴쿼터 남아있으면 버튼 활성 → 클릭 시 consume_turn이 자동 턴 진행

### 보안 (Security)
- **외교 0AP Exploit 차단**: 적대 선언/관계 해제에 1AP 비용 추가
  - 적대 선언(20% 약탈 버프) → 침공 → 적대 해제를 무비용 반복하는 얌체짓 방지

### 변경됨 (Changed)
- **AP 시스템 근본 재설계**: `consume_turn()`을 AP 소비 래퍼로 전환
  - 이전: 매 행동마다 턴 진행 → AP 무력화(Ghost AP 버그)
  - 이후: AP 충분하면 AP만 감소, AP 부족 시에만 턴 진행 + AP 리셋
  - `action_gather/birth/build/train` 내부 중복 AP 체크/소비 제거
  - 각 라우트에서 `consume_turn(park, ap_cost=N)` 호출로 통일

### 보안 (Security)
- **원자적 에스크로**: `trade_create`에서 SQL 레벨 `UPDATE-WHERE` 차감
  - `@validates` 음수 클램핑 역설 근본 차단 (동시 100 요청에도 DB가 1건만 통과)
  - Python 객체 `db.session.refresh()` 동기화

### 수정됨 (Fixed)
- **교역 연산 순서 수정**: 뺄셈(줄 것) 먼저 → 덧셈(받을 것) 나중
  - 이전: 더하기 → cap 잘림 → 빼기 = 자원 증발
  - 이후: 빼기 → 더하기 → cap 적용 = 정확한 교환

## [1.5.1] - 2026-02-21

### 보안 (Security)
- **디버그 백도어 차단**: `debug/next-turn` 라우트에 `DEBUG` 모드 전용 가드 추가 (프로덕션 무한 턴 Exploit 차단)
- **교역 에스크로 시스템**: 교역 등록 시 제안 자원을 즉시 선차감, 취소 시 환불 (유령 자원 복사 Exploit 차단)
- **음수 자원 교역 차단**: offer/request 값에 `max(0, ...)` 적용 (음수 역전 Exploit 방지)
- **교역 메시지 XSS 차단**: `html.escape()` 적용
- **int() 크래시 방지**: `request.form.get(type=int)` 안전 파싱으로 전환 (5곳)

### 수정됨 (Fixed)
- **보스 단독 무손실 파밍**: 보스 단독 출전 시 승리해도 HP 3~8 감소 + 전투력 30% 패널티
- **교역 수락 로직**: 에스크로 반영으로 발송자 이중 감산 제거

## [1.5.0] - 2026-02-21

### 보안 (Security)
- **XSS 취약점 차단**: Toast 알림 + 정찰 모달에서 `innerHTML` → `textContent`/`escapeHtml()` 전환
  - `escapeHtml()` 글로벌 유틸 함수 추가 (HTML 특수문자 이스케이프)
  - 정찰 데이터 숫자값 `Number()` 캐스팅으로 타입 안전성 확보
- **공원 이름 특수문자 차단**: 가입 시 `<>&"'/\` 포함 이름 거부 (XSS 근본 원인 차단)
- **교역 Double Spend 방지**: 원자적 `UPDATE-WHERE` 패턴으로 동시 수락 차단
  - `status='pending'` → `status='processing'` 원자적 전환 후 교환 실행
  - 실패 시 상태 원복 로직 추가
- **자원 음수 방어**: 교역 자원 감산에 `max(0, ...)` 클램핑 적용

### 수정됨 (Fixed)
- **저실장 무한 번식 Exploit**: 출산 시 `baby_cap` 검사 추가
  - 운치굴 없어도 최소 5마리(BASE_BABY_CAP) 보유 가능
  - 운치굴 수용량 초과 시 저실장 출산 차단
- **모델 레벨 음수 방어**: `Park` 모델에 `@validates` 데코레이터 적용
  - 인구(guard/adult/child/baby), 자원(konpeito/trash/meat/material), boss_hp, morale, AP, 턴 12개 필드
  - 어디서든 음수 설정 시 자동 0 클램핑 (DB 무결성 보호)
  - 멀티플레이 요소 제거 (인증/교역/외교 → NPC 자동화)
  - Python 게임 로직 100% 재사용 (game_engine, battle_engine, npc_engine, dialogues)
  - SQLite + JSON i18n 그대로 이식
  - Kivy 위젯 기반 네이티브 UI 재작성
  - Google Play 스토어 등록 (무료 배포)
  - 틈새시장 타겟: 일본/중국 실장석 팬층

## [1.4.0] - 2026-02-17

### 추가됨 (Added)
- **UI 전면 i18n 적용**: HTML 템플릿 + Python flash 메시지 완전 국제화
  - `register.html`: NPC 대사, 헤더, 초기자원 안내 → `{{ t('key') }}`
  - `login.html`: 태그라인, 제목, 헤더 → `{{ t('key') }}`
  - `gameover.html`: 게임오버 대사, 스탯 라벨, 멸망 안내 → `{{ t('key') }}`
  - `ranking.html`: 정렬 탭, 테이블 헤더, 내 공원 요약 → `{{ t('key') }}`
  - `battle_logs.html`: 전투 결과 배지, 빈 로그 메시지 → `{{ t('key') }}`
  - `base.html`: 기본 title 하드코딩 제거
  - `auth_routes.py`: 13개 flash 메시지 → `get_text()` 호출
  - `game_routes.py`: 40+개 flash 메시지 → `get_text()` 호출
- **i18n 키 대폭 확장**: 5개 언어 파일 모두 258키로 동기화
  - `flash.auth_*` (인증), `flash.reg_*` (가입), `gameover.*` (게임오버)
  - `ranking.*` (랭킹), `battle.*` (전투), `diplo.*` (외교), `dash.*` (대시보드)

## [1.3.0] - 2026-02-17

### 추가됨 (Added)
- **보호 모드 시스템**: 약한 공원(경호<5 OR 성체<15) 자동 보호
  - 보호 중: 침공 불가 + 침공 당하지 않음
  - 진입 시 자원/인구 최소 보장 수준으로 재배치 (성체5, 자실장15, 저실장8, 음쓰50, 콘페이토8, 자재80)
  - 보스 HP 50↑, 사기 30↑ 최소 보장
  - NPC도 보호 대상 건너뜀
  - 대시보드에 🛡️ 보호 모드 배너 표시 (경호/성체 진행률)
  - 해제 조건: 경호 ≥ 5 AND 성체 ≥ 15
- **대사 다국어 시스템(i18n)**: 619줄 하드코딩 대사를 JSON 기반으로 추상화
  - 5개 언어 대사 파일: dialogues_ko.json, dialogues_en.json, dialogues_ja.json, dialogues_zh_tw.json, dialogues_zh_cn.json
  - Python 3.7+ 모듈 __getattr__ 기반 프록시로 기존 코드 100% 호환
  - Flask 세션 언어 자동 감지, 폴백(ko) 지원
  - 말투: ko(~데스), ja(~でち), en(~desu), zh(~的說/的说)

## [1.2.0] - 2026-02-17

### 추가됨 (Added)
- **모바일 턴 쿼터 시스템**: 글로벌 타이머 → 개인별 턴 스태미나 전환
  - 최대 15턴 보유, 20분당 1턴 자동 충전
  - 접속 시 타임스탬프 기반 온디맨드 충전 (서버 부담 0)
  - 턴 게이지 바 + 실시간 카운트다운 타이머 UI
  - 행동 시 턴 1개 소비 → `process_turn()` 실행
  - NPC 동기 처리 (플레이어 턴 소비 시 NPC도 진행)
- **반응형 모바일 CSS**: 768px/480px 브레이크포인트 미디어 쿼리
  - 단일 컬럼 레이아웃 (모바일)
  - 터치 친화적 버튼 (min-height 48px)
  - iOS 폼 확대 방지 (font-size: 16px)
  - 턴 게이지 모바일 세로 배치
- **DB 마이그레이션**: `migrate_v1_2.py` (turn_quota, last_turn_regen_at)

### 변경됨 (Changed)
- 모든 행동(채집/출산/건설/훈련/침공)에 턴 소비 로직 적용
- 대시보드 접속 시 턴 자동 충전 + 턴 정보 표시
- CSS 중복 미디어 쿼리 정리 (v0.3.0 잔여 → v1.2.0 통합)


## [1.1.0] - 2026-02-17

### 추가됨 (Added)
- **재해 & 환경 이벤트**: 폭우(골판지집 파괴), 한파(동사), 살충제(저실장 사망),
  쥐떼(식량+저실장), 고양이(자실장), 쓰레기장 철거(채집 패널티)
- **출산 잔혹 이벤트**: 사산(5%), 기형(10%), 대량출산(8%),
  모체 사망(2%), 기아 시 출산 포식(3%)
- **자동 카니발리즘**: 식량 0 시 경호실장이 자실장 강제 포식 + 사기 대폭 감소
- **질병 시스템**: 과밀(90%+운치굴3개) 시 전염병 발생, 콘페이토 5개로 치료
- **NPC 악행 이벤트**: 학대자(납치), 실험체(포획), 어린이(장난), 착한 인간(선물), 펫샵(포획)
- **밀사/침투 시스템**: 1AP+성체1로 적 공원 사보타주, 40% 발각 확률, 감시탑 방어 보너스
- **반란 시스템**: 사기 20↓ 시 자실장 탈주/성체 태업, 보스HP 30↓ 시 경호 쿠데타
- **콘페이토 중독**: 3턴 연속 섭취 → 중독, 채집 50% 감소, 3턴 미섭취 시 해독
- **SpyMission 모델**: `spy_missions` 테이블 추가 (밀사 임무 추적)
- **DB 마이그레이션**: `migrate_v1_1.py` (새 필드 6개 + SpyMission 테이블)

### 변경됨 (Changed)
- `process_turn`: 13단계 처리 순서로 확장 (기존 6단계 → 13단계)
- `action_gather`: 태업/채집패널티/중독 효과 적용
- `action_build`: 태업 시 건설 불가
- `action_birth`: 출산 잔혹 이벤트 5종 통합

## [1.0.0] - 2026-02-17

### 추가됨 (Added)
- **다국어 지원 (i18n)**: JSON 기반 경량 번역 시스템
  - 지원 언어: 한국어, 영어, 일본어, 중국어 번체, 중국어 간체
  - 세션 기반 언어 저장 + 즉시 전환
  - 모든 페이지 상단에 언어 선택 바 추가
  - 템플릿에서 `{{ t('key') }}` 함수로 번역 텍스트 사용
  - `app/lang/` 디렉토리에 JSON 파일로 관리
- **배포 가이드** (`BUILD_GUIDE.md`): 라즈베리파이 프로덕션 배포
  - Gunicorn WSGI 서버 설정
  - systemd 서비스 등록 스크립트
  - Nginx 리버스 프록시 설정 (정적 파일 직접 서빙)
  - 방화벽, 성능 최적화, 트러블슈팅 가이드
- **i18n 모듈** (`app/i18n.py`): Flask 앱 팩토리와 통합

## [0.4.0] - 2026-02-17

### 추가됨 (Added)
- **교역 시스템** (`/game/trade`): 공원 간 자원 교환
  - 공개 교역 (아무나 수락 가능) / 지정 교역 (특정 공원 대상)
  - 자원 종류: 콘페이토, 음쓰, 자재, 저실장
  - 교역 제안 생성, 수락, 거절, 취소 기능
  - 보유량 검증 (양측 자원 부족 시 자동 만료)
  - 교역 메시지 기능
- **외교 시스템**: 동맹/적대 관계 관리
  - 🤝 동맹: NPC는 즉시 수락, 플레이어는 요청→수락 구조
  - ⚔️ 적대: 일방적 선언, 즉시 활성화
  - 동맹 파기 / 적대 해제 기능
  - 동맹인 공원 침공 차단
  - 적대 공원 침공 시 약탈 +20% 보너스
- **교역/외교 통합 UI** (`trade.html`): 교역소 & 외교관 페이지
- **대시보드 하단 네비게이션에 교역/외교 바로가기 추가**
- **DB 모델**: `TradeOffer`, `Diplomacy` 테이블 추가

- **실시간 알림 시스템**: 대시보드에서 10초 폴링으로 침공/교역/외교 이벤트 토스트 알림
  - 타입별 색상/아이콘 구분 (전투: 빨강, 교역: 주황, 외교: 파랑)
  - 클릭 시 닫기 + 5초 후 자동 사라짐
  - API: `/game/api/notifications?last_id=N`

## [0.3.0] - 2026-02-17

### 추가됨 (Added)
- **전투 유닛 선택 시스템**: 침공 시 경호실장/성체실장 출정 인원을 직접 지정
  - 침공 모달 UI (경호·성체 인원 입력 + 가용 수 표시)
  - 예상 전투력 실시간 미리보기
  - 출정 인원 0명이면 버튼 비활성화
- **보스실장 참전**: 보스 직접 출전 옵션 (전투력 +100)
  - 패배 시 보스 HP -10~25 (보스 사망 = 게임오버)
  - 참전 위험도 경고 + 현재 보스 HP 표시
- **게임오버 재시작**: 멸망 후 새 공원 생성으로 재시작
  - 최종 생존 통계 표시 (턴 수, 잔존 인구)
  - 랭킹 보기 버튼
- **전투 사기 연동**: 승리 시 사기 +8 / 패배 시 사기 -8
  - 방어 성공 시 사기 +5
- **랭킹 시스템** (`ranking.html`, `/game/ranking`): 전체 공원 순위 조회
  - 정렬 기준: 전투력 / 인구 / 승수 / 자원 (탭 전환)
  - 내 공원 강조 + 순위 요약 표시
  - NPC 성격별 색상 표시
- **정찰 시스템** (`/game/scout/<id>`): AJAX 기반 적 공원 정보 조회
  - 감시탑 유무에 따라 정보 수준 차등 (기본 vs 상세)
  - 팝업 모달 UI
- **채집 인원 기억 기능**: 성체/자실장 배치 수를 DB에 저장 + 턴 리셋 없이 유지
- **대시보드 하단 네비게이션**: 랭킹 + 전투기록 바로가기

### 변경됨 (Changed)
- 침공 UI: 바로 전투 → 유닛 선택 모달 → 출정 구조로 변경
- 전투 엔진: 전체 병력 출정 → 지정 유닛만 출정으로 개선
- 전투 로그에 출정 편성 정보 (경호 N + 성체 N + 보스 참전 여부) 기록
- 건설 UI 개선: 자재 부족 표시 + 건물 설명 동적 업데이트
- 턴 처리 시 채집/방어 인원을 보유 수에 맞게 자동 조정
- NPC 성격별 패시브 성장 차등화 (목장=인구, 야만=군사, 교활=콘페이토)
- NPC 침공 시 유닛 선택 로직 추가 (교활형은 경호만 소수 파견)

### 보안 (Security)
- Flask-WTF CSRFProtect 전역 적용 (모든 POST 요청에 CSRF 토큰 필수)
- base.html에서 meta 태그로 CSRF 토큰 주입 + JS 자동 삽입

### UI/UX
- 반응형 CSS 미디어 쿼리 추가 (768px 태블릿, 480px 모바일)
- 버튼 호버 마이크로 애니메이션 (translateY + box-shadow)
- 플래시 메시지 슬라이드-인 효과
- 박스 헤더 글로우 펄스, 전투력 수치 펄스 애니메이션
- 게임오버 화면 전용 CSS (death-pulse 애니메이션)
- 침공 모달 입력 필드 스타일링 (.num-input)

## [0.2.0] - 2026-02-17

### 추가됨 (Added)
- **턴 스케줄러** (`turn_scheduler.py`): APScheduler 기반 자동 턴 처리
  - 매 TURN_INTERVAL(기본 10분)마다 모든 공원의 턴을 일괄 처리
  - 디버그용 수동 턴 진행 기능 (`/game/debug/next-turn`)
- **NPC AI 엔진** (`npc_engine.py`): 5종 성격별 자동 행동 시스템
  - aggressive: 침공 우선, defensive: 방벽 건설 우선
  - peaceful: 채집/출산 우선, cunning: 약한 공원만 침공
  - berserk: 무조건 침공, 식량 없으면 솎아내기
- **전투 엔진** (`battle_engine.py`): 침공/방어 전투 시뮬레이션
  - 전투력 계산 (사기/방벽/감시탑 보정)
  - 랜덤 승패 판정 및 양측 사상자 계산
  - 약탈 시스템 (자원 + 인구 포획)
  - 전투 로그 기록 및 대사 연동
- **방어 배치 시스템** (`/game/defend`): 경호/성체 실장을 방어에 배치
- **전투 기록 페이지** (`battle_logs.html`): 과거 전투 결과 조회
- **전투 대사 확장** (`dialogues.py`): 출정/승리/패배/약탈/방어 대사 추가
- **대시보드 전투 UI**: 침공 버튼, 방어 배치 패널, 디버그 턴 버튼
- **CSS 로고 박스**: ASCII 박스 대신 CSS border + glow 로고 (한글 깨짐 방지)

### 변경됨 (Changed)
- 로그인/회원가입 로고를 CSS 기반 `.logo-box`로 교체
- 게임오버 화면 ASCII 아트를 CSS + `<pre>` 분리 구조로 개선
- `Park` 모델에 `consecutive_trash_turns` 필드 추가 (사기 페널티)
- `__init__.py`에 루트 URL 리다이렉트 및 스케줄러 초기화 추가

## [0.1.0] - 2026-02-17

### 추가됨 (Added)
- 프로젝트 초기 설정
- 게임 기획서 (spec.md) 작성
  - 실장석 세계관 기반 턴제 전략 게임 설계
  - 5단계 실장석 계급 체계 (보스/경호/성체/자실장/저실장)
  - 3종 식량 시스템 (콘페이토 10NP / 음식물 쓰레기 1NP / 저실장 5NP / 자실장 10NP)
  - 솎아내기(마비키) 시스템 - 저실장 및 자실장 도살 가능
  - 전투 시스템 설계 (침공/방어/약탈)
  - NPC 공원 5종 성격 (야만/요새/목장/교활/파괴자)
  - 사기 시스템 (콘페이토 보너스 / 쓰레기 패널티)
- 디자인 문서 (designs.md) 작성
  - BBS 레트로 터미널 × 실장석 감성 UI 설계
  - 아스키 기반 화면 레이아웃 (로그인/대시보드/채집/전투)
  - 실장석 대사 데이터베이스 (행동별 랜덤 2~3개)
  - 말투 규칙 확립 (성체=데스, 자실장=테츄, 저실장=레후)
  - 색상 팔레트 정의
- 필수 문서 일괄 생성 (README, CHANGELOG, BUILD_GUIDE 등)
