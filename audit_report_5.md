# D3D Audit Report

## 1. Audit Scope
- 프로젝트 경로: `/home/eunho1/Projects/python/JissouParkEmpire`
- 감사 중점: 세부 구현부(`npc_engine.py`, `game_routes.py`, `models.py`)의 로직 무결성, 경쟁 조건(Race Condition), 그리고 엔티티 간 제약 조건 파악
- 턴(Turn): 5차 감사 (Implementation Deep Dive)

## 2. Excluded Scope
- 단순 코드 포매팅, 이미 지적된 아키텍처 및 수학적 결함(1~4차 감사 내용)

## 3. Pass 1: Implementation Compliance Findings

### [IMP-F003] 교역 시스템 자원 차감/환불 원자성 누락 (Trade Race Condition & Duplication Exploit)
- Pass: Debug
- Pattern: DBG-001 (동시성/원자성 누락)
- Area: `app/routes/game_routes.py` (`trade_accept`, `trade_reject`)
- Severity: Critical
- Status: Fixed
- Summary: `trade_accept`의 수락자 request 차감 및 `trade_reject`의 발송자 환불을 `Park.query.filter(...).update({...})` 원자적 UPDATE-WHERE로 처리함. 동시 거절 시 중복 환불 방지를 위해 `trade_reject`에도 원자적 상태 전환(`status='pending' → 'rejected'`)을 적용함.
- Evidence: `game_routes.py` 770~785라인(trade_accept), 831~854라인(trade_reject)
- Expected: 자원 차감/환불 시 경쟁 조건을 원자적 UPDATE-WHERE로 방지해야 함.
- Actual: 수락자 request 차감은 `Park.query.filter(Park.id == park.id, konpeito >= ...).update({...})`로 원자적 처리. 발송자 환불도 `Park.query.filter(Park.id == sender.id).update({...})`로 원자적 처리. trade_reject 상태 전환도 `TradeOffer.query.filter(id=..., status='pending').update({'status': 'rejected'})`로 원자화.
- Impact: 동시 다발 교역 요청 시 Lost Update / Double-Spend Exploit 방지.
- Suggested Fix: 적용 완료
- Re-audit Method: 동시에 다수의 교역 수락 POST 요청을 전송하여 차감/환불량이 정상적인지 확인.
- Owner: Coder

### [IMP-F004] NPC 턴 무제한 행동 버그 (NPC AP Consumption Bypass)
- Pass: Debug
- Pattern: DBG-003 (비즈니스 로직 결함)
- Area: `app/npc_engine.py` (`process_npc_turn`), `app/game_engine.py`
- Severity: Major
- Status: Fixed
- Summary: `_npc_gather`, `_npc_birth`, `_npc_build_house`, `_npc_build_wall`, `_npc_train`, `_npc_defend` 호출 직후에 각각의 AP 비용(1 또는 2)을 명시적으로 차감하도록 수정함. `_npc_cull_if_needed`는 0AP 유지.
- Evidence: `npc_engine.py` 96~175라인
- Expected: NPC도 플레이어와 동일하게 행동별 AP 비용(1~2)을 소모해야 함.
- Actual: 모든 NPC 행동 함수에서 `park.action_points -= 1` 또는 `-= 2`를 실행하여 AP가 정상적으로 차감됨. `process_npc_turn`의 `for action_func in actions:` 루프에서 `if park.action_points <= 0: break`가 실제로 동작하게 됨.
- Impact: NPC가 한 턴에 AP 제약 내에서만 행동하여 밸런스가 정상화됨.
- Suggested Fix: 적용 완료
- Re-audit Method: NPC 턴 경과 후 NPC의 행동 횟수와 소모된 AP를 비교 검증.
- Owner: Coder

### [IMP-F005] NPC 무한 번식 상한 무시 버그 (Uncapped NPC Breeding)
- Pass: Debug
- Pattern: DBG-003
- Area: `app/npc_engine.py` (`_npc_passive_growth`)
- Severity: Major
- Status: Fixed
- Summary: 목장형(peaceful) NPC의 자연 번식 로직에 `baby_cap` 클램핑을 적용하여 무한 증식을 방지함.
- Evidence: `npc_engine.py` 63라인
- Expected: 자연 증식분이라도 `park.baby_cap`을 넘을 수 없어야 함.
- Actual: `park.baby_count = min(park.baby_count + random.randint(1, 2), park.baby_cap)`로 변경 완료.
- Impact: NPC 공원 인구가 수용 한도 내에서 정상적으로 제어됨.
- Suggested Fix: 적용 완료
- Re-audit Method: NPC 공원의 인구가 수용량을 넘을 수 있는지 관찰.
- Owner: Coder

### [IMP-F006] 외교/교역/밀사 고아 레코드 발생 취약점 (Missing DB Cascades)
- Pass: Debug
- Pattern: DBG-004 (인프라 무결성 오류)
- Area: `app/models.py` (`Park` 모델)
- Severity: Minor
- Status: Fixed
- Summary: `Park` 모델에 `sent_trade_offers`, `received_trade_offers`, `diplomacy_as_a`, `diplomacy_as_b`, `spy_missions_sent`, `spy_missions_received` 관계를 추가하고 `cascade='all, delete-orphan'`을 적용함.
- Evidence: `models.py` 138~160라인
- Expected: 공원 삭제 시 관련 교역/외교/밀사 레코드도 cascade로 삭제되어야 함.
- Actual: 6개의 새로운 relationship이 추가되어 고아 레코드 발생이 방지됨.
- Impact: 시스템 장기 운용 시 데이터베이스 무결성이 유지됨.
- Suggested Fix: 적용 완료
- Re-audit Method: 계정 삭제 단위 테스트 시 관련 외교/교역 테이블 레코드가 남는지 확인.
- Owner: Coder

## 4. Required Fixes Before PASS
- 없음. `[IMP-F003]`~`[IMP-F006]` 모두 수정 완료됨.

## 5. Final Decision
- **PASS WITH KNOWN RISKS**: 5차 감사에서 발견된 Critical 동시성 결함 `[IMP-F003]`(교역 원자성), Major NPC 룰 위반 `[IMP-F004]`(AP 미소비)/`[IMP-F005]`(무한 번식), Minor DB 무결성 결함 `[IMP-F006]`(cascade 누락)을 모두 수정 완료하였음. 교역 시스템의 경제 Exploit 위험이 차단되었고, NPC가 정상적인 AP/성장 제약 하에서 동작하게 됨.
