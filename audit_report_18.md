# JissouParkEmpire Audit Report - 18차 감사

**작성일시**: 2026-05-30
**감사 대상**: 전체 게임 아키텍처 및 ORM 커밋 패턴
**감사 초점**: 이전 17차 감사 패치(TOCTOU 방어, 원자적 업데이트) 적용 후의 시스템 아키텍처 충돌 및 잔존 논리 결함

---

## 1. 발견된 취약점 상세

이전 17차 감사에서 지적된 훈련/출산 시의 NP 차감 우회 버그([IMP-F044]) 및 `_consume_np` 로직은 완벽하게 수정되었으며, `action_cull` 등 대부분의 행동이 원자적(Atomic) SQL 업데이트로 전환된 것을 확인했습니다.

그러나 이로 인해 **ORM 패턴과 원자적 쿼리가 섞이면서 발생하는 근본적인 아키텍처 레벨의 충돌 결함**이 명확하게 드러났습니다.

### 1.1. [ARCH-F006] ORM 커밋과 원자적 쿼리의 혼용으로 인한 범용적 갱신 유실 (Universal Lost Update)
- **심각도**: **Critical** — **Fixed**
- **위치**: `app/game_engine.py`의 `action_birth`, `action_cure_disease`, 및 `process_turn` 내부 함수들(`_process_starvation`, `_process_training`, `_process_disease` 등)
- **문제점**:
  - 최근 동시성 방어를 위해 `trade_accept`, `execute_battle`, `action_cull`, `_consume_np` 등 많은 주요 자원 변동이 `Park.query...update(...)`를 이용한 DB 레벨의 원자적 처리로 수정되었습니다.
  - 그러나 턴 종료 로직인 `process_turn`과 출산 `action_birth` 등에서는 **여전히 파이썬 메모리 상에서 객체 속성을 변경한 뒤 `db.session.commit()`을 호출**하여 저장하고 있습니다. (예: `park.baby_count -= 1`, `park.guard_count += 1`)
- **공격/발생 시나리오**:
  - **시나리오 1 (자원/인구 증발)**: 스레드 A가 `action_birth`를 실행하며 메모리에서 저실장을 10마리에서 15마리로 수정합니다. 동시에 스레드 B가 `trade_accept`를 통해 원자적 쿼리로 저실장 10마리를 획득하여 DB 상으로는 20마리가 됩니다. 직후 스레드 A가 `commit()`을 호출하면 SQLAlchemy는 `UPDATE park SET baby_count = 15`를 실행해버립니다. 교역으로 얻은 **10마리의 저실장(또는 자원)이 허공으로 증발**합니다.
  - **시나리오 2 (부활 버그)**: 스레드 A가 전투 로직(`execute_battle`)으로 방어 측 경호실장을 원자적으로 3마리에서 0마리로 차감(전멸)시킵니다. 동시에 방어 측의 턴이 돌아가 스레드 B가 `_process_training`을 처리하며 메모리에 있던 3마리 기준에 1마리를 더해 4마리로 변경하고 커밋합니다. 전멸했던 **경호실장 3마리가 훈련 수료 효과와 함께 부활**합니다.
- **결과**: 두 가지 패러다임(Atomic SQL vs ORM Commit)이 동일 테이블(Park)에서 섞여 있어, 데이터베이스의 일관성이 완전히 파괴됩니다.
- **수정 결과 (Fixed)**:
  - `process_turn`: 시작 시 `Park.query.filter(Park.id == park.id).with_for_update().first()`로 비관적 락을 획득하고 `db.session.refresh(park)`로 최신 상태 동기화. 턴 처리 중 다른 원자적 UPDATE가 개입하지 못하게 함.
  - `action_birth`: NP 소비 성공 후 동일하게 `with_for_update()` + `refresh`로 락 획득. 출산 중 ORM 커밋과 원자적 UPDATE가 충돌하지 않도록 보장.
  - `action_cure_disease`: `park.konpeito -= 5` 메모리 연산을 `Park.query.filter(..., Park.konpeito >= 5).update({'konpeito': Park.konpeito - 5, 'disease_turns': 0})` 원자적 UPDATE로 변경.

### 1.2. [ARCH-F007] 테이블 무한 증가 구조 (Unbounded Table Growth)
- **심각도**: **High** — **Fixed**
- **위치**: `app/game_engine.py`의 `add_event()`, `app/battle_engine.py`의 전투 로그
- **문제점**:
  - `EventLog`와 `BattleLog`, `SpyMission` 등을 생성(`INSERT`)하기만 할 뿐, 오래된 로그를 주기적으로 정리하거나 삭제(Pruning/Cleanup)하는 로직이 전무합니다.
  - 게임이 장기화되거나 다수 유저가 스크립트 봇 등으로 매 턴 행동을 수행할 경우, 로그 테이블의 레코드 수가 기하급수적으로 폭증하여 결국 서버 스토리지 고갈 및 DB I/O 성능 마비를 초래합니다.
- **수정 결과 (Fixed)**:
  - `_prune_old_logs(park)` 함수 추가: 30일 이상 지난 `EventLog`, `BattleLog` 레코드 및 완료된 `SpyMission` 삭제.
  - `process_turn` 종료 시 100턴당 1회 확률로 `_prune_old_logs` 호출. 과도한 I/O 방지를 위해 빈번한 실행은 피함.
  - `synchronize_session=False`를 사용한 배치 삭제로 메모리 부하 최소화.

### 1.3. [IMP-F046] 질병 치료 시 자원 소모 TOCTOU 취약점 (Double Spend)
- **심각도**: **High** — **Fixed**
- **위치**: `app/game_engine.py`의 `action_cure_disease()`
- **문제점**:
  - 질병을 치료할 때 요구되는 5개의 콘페이토를 여전히 파이썬 메모리 검사 및 뺄셈 연산(`park.konpeito -= GC.DISEASE_CURE_KONPEITO`)으로 처리하고 있습니다.
  - 5개의 콘페이토를 보유한 상태에서 해당 행동과 `trade_create`(콘페이토 5개 제안)를 동시에 전송하면, 두 스레드 모두 초기 메모리 검사를 통과하여 **단 5개의 콘페이토만으로 교역 제안과 질병 치료를 동시에 성공**시키는 이중 지불(Double Spend) 악용이 가능합니다.
- **수정 결과 (Fixed)**:
  - `action_cure_disease`의 콘페이토 차감을 `Park.query.filter(Park.id == park.id, Park.konpeito >= 5).update({'konpeito': Park.konpeito - 5, 'disease_turns': 0})` 원자적 UPDATE로 변경.
  - `updated == 0`이면 콘페이토 부족으로 실패 반환. 동시 요청 시에도 정확히 1회만 차감되고 이중 지불이 원천 차단됨.

---

## 2. 총평 및 판정

18차 감사에서 발견된 3건의 취약점을 모두 수정 완료하였습니다.
- [ARCH-F006] Universal Lost Update: `process_turn`과 `action_birth` 시작 시 `with_for_update()` 비관적 락을 획득하여 ORM 커밋과 원자적 UPDATE 혼용으로 인한 갱신 유실 방지.
- [ARCH-F007] Unbounded Table Growth: `_prune_old_logs()` 함수 추가. 30일 이상 지난 로그 및 완료된 밀사 임무를 100턴당 1회 확률로 청소.
- [IMP-F046] Double Spend in cure_disease: `action_cure_disease`의 콘페이토 차감을 `Park.query.filter(...).update(...)` 원자적 UPDATE로 변경하여 TOCTOU 이중 지불 방지.

**Final Decision: PASS WITH KNOWN RISKS** — 18차 감사에서 발견된 모든 Critical/High 결함이 수정되었습니다.
