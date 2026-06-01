# JissouParkEmpire 13차 감사 리포트 (Audit Report 13)

**감사 일시**: 2026-05-30
**감사 대상**: 구현 중심 수학적/아키텍처/동시성 로직 재감사 (비용 차감 및 자원 생성 엔드포인트 전반)
**감사 기준**: `AI_AUDIT_DOC_STANDARD.md`
**감사 방향**: Race Condition을 이용한 재화 복사(Double Spend), AP 및 턴 쿼터 무한 우회 취약점, 밀사/훈련/건설을 통한 유닛 증식 버그 분석

---

## 1. 정합성 및 수학적 결함 (Data Integrity & Mathematical Flaws)

### 🔴 [IMP-F031] 턴 및 행동 포인트(AP)의 논리적 우회 (Infinite AP Exploit)
* **발생 위치**: `app/game_engine.py` -> `consume_turn()`
* **결함 내용**:
  게임의 모든 행동(건설, 훈련, 공격, 밀사 파견 등)을 실행할 때 `consume_turn(park, ap_cost)`가 호출되어 `park.action_points`를 검증하고 차감합니다.
  그러나 이 로직은 오로지 **파이썬 메모리** 상에서만 연산(`park.action_points -= ap_cost`)을 수행합니다. 여러 요청이 동시에 들어올 경우, 모든 스레드가 초기의 충분한 AP 상태를 읽어내어 통과한 뒤 각자의 행동을 실행합니다. 그 결과 플레이어는 보유한 AP나 Turn Quota의 제한 없이 수십 번의 행동을 동시에 강제 실행할 수 있는 심각한 경제/시스템 붕괴 취약점을 가집니다.
* **수정 방향**: `consume_turn` 로직은 반드시 DB 레벨에서 원자적 `UPDATE`로 `action_points` 및 `turn_quota`를 차감한 후 갱신된(Row Count) 결과에 따라 성공 여부를 판단하도록 개선해야 합니다.
* **수정 결과 (Fixed)**:
  - AP 차감 시도를 `Park.query.filter(Park.id == park.id, Park.action_points >= ap_cost).update({'action_points': Park.action_points - ap_cost})` 원자적 UPDATE로 변경.
  - AP 부족 시 `turn_quota` 차감도 동일하게 원자적 UPDATE로 변경 (`Park.turn_quota >= 1` 조건).
  - `process_turn()` 호출 후 `db.session.commit()` 및 `db.session.refresh(park)`로 메모리 동기화.
  - 턴 리셋 후 AP 재차감도 원자적 UPDATE로 처리하여, 동시 요청 시에도 AP/turn_quota가 음수로 떨어지거나 초과 소모되지 않음.

### 🔴 [IMP-F032] 건설(Build) 및 훈련(Train) 큐 생성 시 재화 이중 지불 (Double Spend) 취약점
* **발생 위치**: `app/game_engine.py` -> `action_build()`, `action_train()`
* **결함 내용**:
  `action_build`와 `action_train`은 실행 시 비용(자재, 식량)을 메모리 상의 `park` 객체에서만 깎은 후, 별도의 테이블(`BuildQueue`, `TrainQueue`)에 새로운 레코드를 생성(`db.session.add()`)합니다.
  플레이어가 동시에 여러 번의 `/build`나 `/train` 요청을 보낼 경우, 모두 같은 초기 자원량(충분한 값)을 읽고 통과한 뒤 각 스레드가 `BuildQueue`나 `TrainQueue`를 DB에 삽입합니다. 마지막에 커밋되는 트랜잭션이 한 번의 자원 차감 값을 덮어쓰게 되어, **단 1회분의 비용(AP 1, 자재 10 등)만으로 건물 10채, 경호실장 10마리를 동시에 얻을 수 있는 무한 증식(Duplication) 취약점**이 발생합니다.
* **수정 방향**: 비용 차감을 수행할 때 `Park` 모델에 대해 원자적 `UPDATE` 구문을 실행하고, 성공(차감 반영)한 경우에만 큐 모델 인스턴스를 `db.session.add()` 하도록 결제 원자성을 보장해야 합니다.
* **수정 결과 (Fixed)**:
  - `action_build`: `Park.query.filter(Park.id == park.id, Park.material >= cost).update({'material': Park.material - cost})`로 원자적 자재 차감. `updated == 0`이면 실패 반환, 성공 시에만 `BuildQueue` 생성.
  - `action_train`: `Park.query.filter(Park.id == park.id, Park.adult_count >= 1).update({'adult_count': Park.adult_count - 1})`로 원자적 성체 차감. 성공 시에만 `TrainQueue` 생성.
  - 동시 요청 시에도 자원이 1회만 차감되고, 자원 부족 시 큐 생성이 완전히 차단됨.

### 🔴 [IMP-F033] 밀사(Spy) 파견을 통한 성체실장 무한 증식 버그 (Unit Duplication)
* **발생 위치**: `app/game_engine.py` -> `action_spy()`, `_process_spy_missions()`
* **결함 내용**:
  `action_spy` 역시 파견할 성체실장을 메모리에서만 차감(`park.adult_count -= 1`)하고 `SpyMission` 객체를 생성합니다.
  동시성 요청을 통해 성체실장 1마리 분량의 비용만 깎이고 10개의 `SpyMission`이 등록될 수 있습니다. 심각한 점은, 일정 턴이 지나 `_process_spy_missions`가 실행될 때 귀환하는 10개의 미션이 각각 `park.adult_count += 1`을 실행하여, **결과적으로 1마리의 성체실장이 10마리로 불어나서 돌아오는** 치명적인 유닛 증폭 수학적 결함을 일으킵니다.
* **수정 방향**:
  1. 밀사 파견 시 성체실장 차감을 원자적 `UPDATE`로 변경.
  2. 밀사 복귀 시에도 파이썬 메모리가 아닌, 원자적 `UPDATE`로 성체를 증가시키도록 수정해야 합니다.
* **수정 결과 (Fixed)**:
  - `action_spy`: `Park.query.filter(Park.id == park.id, Park.adult_count >= 2).update({'adult_count': Park.adult_count - 1})`로 원자적 성체 차감. 성공 시에만 `SpyMission` 생성.
  - `_process_spy_missions` 대상 멸망/성공 시 성체 복귀도 `Park.query.filter(Park.id == park.id).update({'adult_count': Park.adult_count + 1})`로 원자적 처리.
  - 동시 파견 시 1마리당 1개의 `SpyMission`만 생성되며, 귀환 시에도 정확히 1마리씩만 복귀함.

---

## 2. 아키텍처 결함 (Architecture & Implementation Flaws)

### 🔴 [IMP-F034] 밀사 사보타주 피해 계산 시 과거 메모리 상태 참조로 인한 타겟 피해량 오차
* **발생 위치**: `app/game_engine.py` -> `_process_spy_missions()`
* **결함 내용**:
  밀사 사보타주 성공 시 상대 공원의 자원을 파괴할 때, `food_destroyed = int(target.trash_food * food_ratio)`를 사용하여 파괴할 양을 산정합니다. 이때 사용하는 `target.trash_food`는 DB의 최신 값이 아닌, (스케줄러나 턴 처리가 시작될 때 로드된) 메모리 상태의 값입니다. 만약 해당 턴 중에 타겟 공원이 대량의 채집을 완료했더라도, 사보타주는 낡은 소량의 데이터를 기준으로 피해를 산정하고 깎아내게 되어 실제 설정된 `food_ratio`만큼의 파괴를 수행하지 못하는 수학적/논리적 오차를 발생시킵니다.
* **수정 방향**: 사보타주의 비율 차감은 가급적 파이썬 단이 아닌 SQL 쿼리 레벨(`trash_food = trash_food - (trash_food * ratio)`)로 위임하거나, 차감 직전에 대상 공원의 최신 상태를 강제로 새로고침(`refresh`)해야 합니다.
* **수정 결과 (Fixed)**:
  - `_process_spy_missions`에서 사보타주 피해 계산 직전 `db.session.refresh(target)`를 호출하여 최신 `trash_food` 값을 DB로부터 동기화.
  - 이로써 타겟 공원이 턴 중 채집 등으로 자원이 변경되었더라도, 사보타주 피해가 최신 데이터를 기준으로 정확히 계산됨.

---

## 3. 총평 및 판정
13차 감사에서 발견된 4건의 취약점을 모두 수정 완료하였습니다.
- [IMP-F031] Infinite AP Exploit: `consume_turn`의 AP/turn_quota 차감을 원자적 UPDATE로 변경하여 동시 요청 시 무한 행동 방지.
- [IMP-F032] Build/Train Double Spend: `action_build` 자재 차감 및 `action_train` 성체 차감을 원자적 UPDATE로 변경. 차감 성공 시에만 BuildQueue/TrainQueue 생성.
- [IMP-F033] Spy Unit Duplication: `action_spy` 성체 차감 및 `_process_spy_missions` 성체 복귀를 모두 원자적 UPDATE로 변경.
- [IMP-F034] Spy Sabotage Stale Data: `_process_spy_missions`에서 사보타주 피해 계산 직전 `db.session.refresh(target)`로 최신 데이터 동기화.

**Final Decision: PASS WITH KNOWN RISKS** — 13차 감사에서 발견된 모든 Critical/High/Medium/Low 결함이 수정되었습니다.
