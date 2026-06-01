# JissouParkEmpire Audit Report - 20차 감사

**작성일시**: 2026-05-30
**감사 대상**: 원자적 업데이트 로직(Capping 적용 부분) 및 게임 엔진 내 자원 소비 로직 전반
**감사 초점**: 이전 감사를 통해 적용된 원자적(Atomic) SQL 쿼리의 문법적 결함 및 락(Lock) 순서 역전에 따른 잔존 TOCTOU(Double Spend) 결함

---

## 1. 발견된 취약점 상세

이전 감사들을 거치면서 발생한 수많은 동시성 이슈(Lost Update, Capping 회피 등)를 방어하기 위해 도입된 **원자적 업데이트 쿼리(`case` 포함)**와 **비관적 락(`with_for_update()`)** 패치에서, **치명적인 파이썬 런타임 크래시**와 락 순서 오류로 인한 **새로운 형태의 Double Spend(이중 지불)** 취약점이 발견되었습니다.

### 1.1. [CRASH-F001] 파이썬 Property를 SQL 쿼리에 사용하여 발생하는 확정적 서버 크래시
- **심각도**: **Critical (서비스 장애)** — **Fixed**
- **위치**:
  - `app/game_engine.py` (351, 362라인 - `action_gather`의 야생 실장석 발견 이벤트)
  - `app/routes/game_routes.py` (847, 855라인 등 - `trade_accept`, `trade_reject`의 저실장 캡핑 로직)
  - `app/battle_engine.py` (328라인 - `execute_battle`의 전리품 저실장 캡핑 로직)
- **문제점**:
  - 동시성 방어와 캡핑(최대치 보정)을 위해 `Park.query...update(...)` 구문 내부에 `Park.total_population`과 `Park.baby_cap`을 조건이나 값으로 명시하여 패치되었습니다.
  - 하지만 `total_population`과 `baby_cap`은 데이터베이스 테이블의 실제 컬럼(Column)이 아니라, `models.py` 내부에서 `@property` 데코레이터로 정의된 파이썬 함수 객체(Property Object)입니다.
  - SQLAlchemy 쿼리의 필터(`filter`)나 케이스(`case()`) 내부에서 클래스 객체를 통해 프로퍼티를 호출할 경우, SQL 표현식(Expression)으로 치환되지 못하고 `TypeError: '<' not supported between instances of 'property' and 'InstrumentedAttribute'` 등 파이썬 레벨의 예외가 즉시 발생합니다.
- **결과 시나리오**:
  - 교역을 수락하거나 취소하는 즉시 100% 확률로 **500 Internal Server Error**가 발생하며 크래시됩니다.
  - 전투에서 승리하여 저실장 전리품을 획득하려는 순간 확정적으로 크래시됩니다.
  - 채집 도중 5% 확률로 "야생 실장석 발견" 이벤트가 터지면 확정적으로 크래시됩니다.
- **수정 결과 (Fixed)**:
  - `Park.total_population` → `(Park.guard_count + Park.adult_count + Park.child_count)`로 치환 (game_engine.py 351라인).
  - `Park.baby_cap` → `(Park.unchi_holes * 10)`로 치환 (game_engine.py 362라인, game_routes.py 4개 라인, battle_engine.py 328라인).
  - SQLAlchemy 쿼리 내부에서 실제 DB 컬럼 표현식만 사용하도록 수정하여 Property 관련 TypeError 완전 해결.

### 1.2. [IMP-F048] 락 획득 전 `_consume_np` 호출에 따른 캡핑(case) 악용 Double Spend (TOCTOU)
- **심각도**: **Critical (자원/인구 복사)** — **Fixed**
- **위치**: `app/game_engine.py`의 `action_birth()` 및 `action_train()`
- **문제점**:
  - NP 차감을 수행하는 `_consume_np()` 함수는 이전 패치를 통해 음수가 되지 않도록 `case((Park.trash_food < use, 0), else_=Park.trash_food - use)` 형태의 원자적 쿼리를 전송하도록 개선되었습니다.
  - 그러나, 메모리에서 파이썬 변수 `use` 값을 계산하는 로직은 `use = min(park.trash_food, remaining)`처럼 락(Lock) 없이 가져온 과거 값을 기반으로 합니다.
  - 결정적으로, `action_birth`와 `action_train` 함수는 **`_consume_np()`로 자원을 차감한 "이후"에야 `with_for_update()` 락을 획득**합니다. (락 획득 순서 지연)
- **발생 시나리오**:
  - 보유 중인 음식물 쓰레기가 정확히 30개(`trash_food = 30`)일 때, 동시에 10번의 출산(`action_birth` - 비용 30 NP)을 요청합니다.
  - 10개의 스레드가 동시에 락 없이 메모리의 `trash_food`가 30임을 확인하고, 차감액을 `use = 30`으로 계산합니다.
  - 10개의 스레드가 동시에 `update` 쿼리를 날립니다. 첫 스레드는 `trash_food`를 0으로 정상 차감하지만, 나머지 9개 스레드는 쿼리가 실행될 때 DB 값이 0이므로 `case` 구문에 의해 `0`으로 세팅(실제 DB 차감량 0)되며 에러 없이 "성공"을 반환합니다.
  - 파이썬 코드는 실제 DB에 얼마가 깎였는지 확인하지 않고 무조건 `remaining -= use` (즉, `remaining -= 30`)을 실행하여 `shortage = 0`을 반환합니다.
  - 결과적으로 **30 NP만 소모하여 10회의 출산을 전부 통과**시키는 악질적인 Double Spend 취약점이 여전히 작동합니다.
- **수정 결과 (Fixed)**:
  - `action_train`: `_consume_np` 호출 이전에 `Park.query.filter(Park.id == park.id).with_for_update().first()`로 비관적 락을 획득하도록 이동. 락 획득 후 `db.session.refresh(park)`로 최신 자원 상태 동기화한 뒤 `_consume_np` 실행.
  - `action_birth`: 동일하게 `with_for_update()` 락을 `_consume_np` 이전으로 이동. 락 + refresh 후 자원 차감.
  - 이로써 동시 출산/훈련 요청 시에도 `_consume_np`의 `use` 계산이 최신 DB 값을 기준으로 수행되어 Double Spend가 원천 차단됨.

---

## 2. 총평 및 판정

20차 감사에서 발견된 2건의 취약점을 모두 수정 완료하였습니다.
- [CRASH-F001] Property in SQL Query Crash: `Park.total_population`을 `(Park.guard_count + Park.adult_count + Park.child_count)`로, `Park.baby_cap`을 `(Park.unchi_holes * 10)`로 치환. SQLAlchemy 쿼리 내부에서 실제 DB 컬럼 표현식만 사용하도록 수정하여 Property 관련 TypeError 완전 해결.
- [IMP-F048] Lock Order TOCTOU: `action_train`과 `action_birth`에서 `with_for_update()` 락을 `_consume_np` 호출 이전으로 이동. 락 획득 후 `refresh`로 최신 자원 상태 동기화하여 Double Spend 원천 차단.

**Final Decision: PASS WITH KNOWN RISKS** — 20차 감사에서 발견된 모든 Critical 결함이 수정되었습니다.
