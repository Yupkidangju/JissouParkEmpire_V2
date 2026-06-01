# Audit Report 59: Unprotected State Modification in Spy Mission Resolution (Lost Update Race Condition)

## 1. 개요 (Overview)
- **발견 일시**: 2026-05-31
- **심각도**: **High (고위험 - 경쟁 상태로 인한 자원 복제/유실)**
- **컴포넌트**: `app/game_engine.py` (`_process_spy_missions`)
- **핵심 문제**: 밀사 임무 처리 후 인구 초과를 검증하기 위해 `_process_overcrowding`을 호출할 때, **비관적 락(`with_for_update()`) 없이 단순 `refresh()`만 수행한 뒤 인메모리 데이터를 변경하고 커밋**합니다. 이 짧은 틈새(Gap) 동안 들어온 병렬 요청의 데이터 변경사항(채집, 교역 등)이 덮어쓰기되어 유실(Lost Update)되는 치명적인 결함이 발견되었습니다.

## 2. 세부 분석 (Detailed Analysis)

### 2.1. 문제의 발단 (Root Cause Context)
`app/game_engine.py`의 `_process_spy_missions`는 임무 단위로 데드락을 방지하기 위해 루프 내에서 개별적으로 `db.session.commit()`을 수행하여 락을 해제합니다.
그리고 모든 임무가 끝난 뒤, 밀사 귀환으로 인해 인구가 수용량을 초과했는지 점검하기 위해 다음 코드를 실행합니다.
```python
    # _process_spy_missions 마지막 부분
    db.session.refresh(park)     # 락 없이 단순 SELECT로 갱신
    _process_overcrowding(park)  # 인메모리에서 child_count, adult_count 등 차감 연산
    db.session.commit()          # 연산 결과를 DB에 UPDATE (덮어쓰기)
```

### 2.2. 결함 메커니즘 (Bug Mechanism)
`_process_overcrowding`은 SQL 원자적 쿼리가 아니라 파이썬 메모리에서 인스턴스 속성(`park.child_count -= 1` 등)을 조작하는 로직입니다. 이 방식은 반드시 트랜잭션 락 보호 아래에서 실행되어야 안전합니다.
하지만 위 로직에서는 락이 해제된 상태로 `refresh`를 수행하므로 전형적인 **Read-Modify-Write (Lost Update)** 문제가 발생합니다.

1. **Read**: `db.session.refresh(park)`가 DB에서 현재 상태를 읽어옵니다. (락 없음)
2. **Concurrent Write (경쟁)**: 이 시점(수 밀리초 이내)에 다른 탭이나 매크로가 채집(`action_scavenge`)이나 교역 수락(`trade_accept`)을 실행하여 `child_count`나 `adult_count`를 수정하고 커밋합니다. DB에는 이 새로운 값이 저장됩니다.
3. **Modify**: `_process_overcrowding`이 이전에 읽어온(이제는 구버전이 된) 데이터를 기반으로 `child_count -= 1` 연산을 파이썬 메모리에서 수행합니다.
4. **Write**: `db.session.commit()`이 호출되면서, 파이썬 메모리에 있던 구버전 데이터가 DB에 강제로 덮어써집니다.
   - **결과**: 병렬로 실행된 채집/교역의 획득물이 소멸하거나 반대로 지불한 자원이 복구되는(Dupe Exploit) 현상이 발생합니다.

## 3. 재현 경로 (Reproduction Steps)
1. 밀사가 성공적으로 귀환하여 공원의 총 인구가 수용량 한도를 초과할 예정인 턴을 기다립니다.
2. 밀사가 처리되는 `_process_spy_missions`가 백그라운드나 턴 소모로 호출됩니다.
3. 밀사 루프가 끝나고 `refresh()`가 호출된 직후의 미세한 타이밍에, 사용자가 별도의 API 요청으로 "자실장 10마리 판매(교역)"를 실행합니다.
4. 교역 트랜잭션이 성공하여 DB의 `child_count`가 10 감소합니다.
5. 그러나 `_process_overcrowding`은 교역 이전의 메모리 스냅샷을 들고 솎아내기 연산을 마친 뒤 `commit()`을 때립니다.
6. DB의 `child_count`가 교역 이전 상태로 덮어써지며, 사용자는 교역 대금(자재, 콘페이토 등)은 얻으면서 자실장도 그대로 유지하는 무한 복사 버그가 발생합니다.

## 4. 해결 방안 (Recommended Fixes)
- `_process_spy_missions`의 마지막 블록에서 `refresh()`를 호출하기 전에 **다시 비관적 락을 획득**해야 합니다.
```python
    # 락 획득 후 안전한 환경에서 인메모리 갱신 및 커밋
    Park.query.filter(Park.id == park.id).with_for_update().first()
    db.session.refresh(park)
    _process_overcrowding(park)
    db.session.commit()
```
- 이는 `consume_turn`의 `v1.8.8` 패치(AP 복제 방지)와 동일한 접근법이며, 인메모리 연산을 수행하는 모든 곳에서 필수적으로 적용되어야 하는 패턴입니다.
