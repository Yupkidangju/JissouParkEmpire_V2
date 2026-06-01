# 47차 코드 감사 보고서 (audit_report_47.md)

## 1. 감사 개요
*   **감사 대상**: `game_engine.py`, `game_routes.py`, `auth_routes.py`
*   **감사 기준**: `AI_AUDIT_DOC_STANDARD.md`의 [STATE] 및 [LOGIC] 파트
*   **감사 목적**: 보호 모드(Protection) 처리 과정에서의 동시성 문제 파악 및 공원 멸망 후 재시작(`restart`) 로직의 원자성(Atomicity) 검증

## 2. 주요 발견 사항

### [STATE-F020] TOCTOU Race Condition in Protection Mode Bailout (Lost Update)
*   **위험도**: High (동시 다발적인 데이터 무결성 훼손 / Lost Update)
*   **위치**: `game_engine.py` -> `check_and_enter_protection(park)`, `game_routes.py` -> `dashboard()`
*   **내용 및 원인**:
    *   `/dashboard` 라우트는 호출될 때마다 `check_and_enter_protection(park)`을 실행합니다.
    *   해당 함수 내부에서는 `park.adult_count`, `park.boss_hp`, `park.cardboard_houses` 등 다수의 모델 필드를 메모리 상에서 덮어쓴 후, 비관적 락(Pessimistic Lock)이나 원자적 UPDATE(`case()`) 없이 `db.session.commit()`을 호출합니다.
    *   대시보드 접속(GET)과 동시에 다른 브라우저 창이나 백그라운드에서 특정 행동(POST, 예: `/attack`, `/build`)이 처리되어 DB 값이 원자적으로 변경되더라도, **`dashboard` 라우트의 커밋이 해당 변경 사항(감소된 자원이나 인구)을 메모리에 들고 있던 구버전 데이터로 덮어씌워버리는 문제(Lost Update)**가 발생합니다.

### [STATE-F021] Non-Atomic Restart Route Leads to Infinite Redirect Loop
*   **위험도**: High (계정 접속 불가 / 무한 리다이렉트 발생)
*   **위치**: `game_routes.py` -> `restart()`, `auth_routes.py` -> `login()`
*   **내용 및 원인**:
    *   `/restart` 라우트에서는 기존 공원을 삭제하고 새 공원을 생성하는 과정을 **두 개의 독립된 트랜잭션**(`db.session.commit()` 2회 호출)으로 처리합니다.
    *   만약 유저가 버튼을 중복 클릭하여 Race Condition이 발생하거나, 첫 번째 커밋(삭제) 이후 두 번째 커밋(생성) 도중 서버 오류(DB Timeout 등)가 발생하면, 유저는 `Park` 엔티티가 없는 상태로 남게 됩니다.
    *   이 상태로 `/dashboard`에 접근하면 `if not park:` 조건에 걸려 `/login`으로 리다이렉트되지만, `/login` 라우트는 유저가 이미 인증(Authenticated)되어 있음을 확인하고 다시 `/dashboard`로 리다이렉트합니다. 결과적으로 **무한 리다이렉트(`ERR_TOO_MANY_REDIRECTS`) 핑퐁**이 발생하여 유저 계정이 완전히 먹통(Bricked)이 됩니다.

## 3. 권고 사항
1.  **[STATE-F020] 수정 방향**:
    *   `check_and_enter_protection()` 실행 시 `process_turn()`과 같이 원자적 UPDATE 구문을 사용하여 상태를 조정하거나, `dashboard` 라우트에서 해당 함수 진입 전 `with_for_update()`로 비관적 락을 걸어야 합니다.
2.  **[STATE-F021] 수정 방향**:
    *   `/restart` 내부의 2개의 `db.session.commit()`을 맨 마지막에 **1개로 통합**하여 롤백 가능한 단일 트랜잭션(Atomic)으로 묶어야 합니다.
    *   유저가 공원이 없는 상태(`user.park is None`)로 `/login`에 도착했을 때, 단순히 로그인된 상태라고 무조건 대시보드로 보낼 것이 아니라, 공원 존재 여부를 함께 체크하여 없을 경우 생성 로직을 호출하거나 에러 페이지로 유도하도록 예외 처리를 보강해야 합니다.
