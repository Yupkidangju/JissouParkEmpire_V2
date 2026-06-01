# D3D Audit Report - 32차 재감사

## 1. Audit Scope
- **Target Files**:
  - `app/routes/game_routes.py` (`trade_accept`, `trade_cancel`, `trade_reject`)
  - `app/battle_engine.py` (`_apply_loot`)
  - `app/game_engine.py` (`_process_gather`, `action_birth`, `_process_unchi_breeding`)
  - `app/models.py` (`Park.baby_cap` property)
- **Focus Area**: 자원/인구 상한(Cap) 처리의 원자적(Atomic) 업데이트 정합성, 메모리 프로퍼티와의 일관성, 그리고 `unchi_holes` (운치굴) 기반의 저실장 보유 제한 로직.
- **Reference**: `spec.md` Section 12.3 (출산 상한) 및 Section 9 (건설/수용).

## 2. Excluded Scope
- 전투 로그 출력부, 랭킹 조회 성능 등 렌더링 영역.
- NPC 성격별 액션 우선순위 트리 (정상 작동 확인).

## 3. Pass 1: Implementation Compliance Findings

### [STATE-F007] 원자적 쿼리 내 하드코딩된 Cap으로 인한 저실장 삭제(Data Loss) 결함
- **Severity**: Critical (Data Loss)
- **Status**: Open
- **Evidence**:
  - `spec.md` 12.3: `babies = min(babies, max(5, unchi_holes*10) - baby_count)` (운치굴이 없어도 기본 5마리는 수용 가능).
  - `app/routes/game_routes.py` (교역 수락/취소) 및 `app/battle_engine.py` (전투 약탈) 내 원자적 `UPDATE` 문:
    ```python
    'baby_count': case((Park.baby_count + trade.offer_babies > (Park.unchi_holes * 10), (Park.unchi_holes * 10)), else_=Park.baby_count + trade.offer_babies)
    ```
- **Expected**: SQL `case()` 문 내에서도 `max(5, unchi_holes*10)` 조건이 적용되어 최소 수용량 5마리가 보장되어야 함.
- **Actual**: `(Park.unchi_holes * 10)`로 하드코딩되어 있음. 만약 `unchi_holes`가 0일 경우, Cap이 0으로 계산됨. 즉, 유저가 교역이나 전투로 저실장을 1마리라도 얻게 되면, 조건식(`기존 + 획득 > 0`)이 True가 되어 유저가 기존에 가지고 있던 저실장마저 **모조리 0으로 덮어씌워짐(삭제됨).**
- **Suggested Fix**: SQL `UPDATE` 내 `case` 문에 `func.max(5, Park.unchi_holes * 10)`을 사용하도록 수정해야 함.

### [LOGIC-F007] 하드코딩된 Cap으로 인한 야생 저실장 채집 원천 차단
- **Severity**: Medium
- **Status**: Open
- **Evidence**:
  - `app/game_engine.py`의 `_process_gather()` 내 "야생 실장석 발견" 이벤트 쿼리:
    ```python
    updated = Park.query.filter(
        Park.id == park.id,
        Park.baby_count < (Park.unchi_holes * 10)
    ).update({'baby_count': Park.baby_count + 1})
    ```
- **Expected**: 운치굴이 없어도 기본 5마리까지는 채집으로 야생 저실장을 주울 수 있어야 함.
- **Actual**: `unchi_holes == 0`일 경우 필터 조건이 `Park.baby_count < 0`이 되어버리므로 언제나 거짓(False)이 됨. 초반에 운치굴을 짓지 않은 뉴비는 야생 저실장 이벤트를 절대 받을 수 없음.
- **Suggested Fix**: 채집 이벤트의 `.filter()` 절에도 `func.max(5, Park.unchi_holes * 10)` 로직을 반영해야 함.

## 4. Pass 2: Debug / Engineering Quality Findings

### [STATE-F008] ORM 프로퍼티와 비즈니스 로직 간의 파편화 (Drift)
- **Severity**: High (유지보수 치명적)
- **Status**: Open
- **Evidence**:
  - `models.py`의 `baby_cap` 프로퍼티는 `return self.unchi_holes * 10` 만 정의하고 있음 (기본 5마리 룰 누락).
  - 이에 따라 `app/game_engine.py`의 `action_birth` 등에서는 이를 보정하기 위해 `effective_baby_cap = max(5, park.baby_cap)` 형태로 하드코딩(Monkey Patching)하여 사용 중임.
- **Expected**: 모델 레이어(`models.py`)의 `baby_cap` 자체에 비즈니스 룰(`max(5, ...)`)이 온전히 캡슐화되어야 하며, 이를 Python 메모리 로직과 SQL 쿼리 로직(hybrid property 등) 양쪽에서 일관되게 접근해야 함.
- **Actual**: 모델 속성이 룰을 절반만 구현하고, 호출부(Python)에서는 임시 땜질을, 호출부(SQL)에서는 땜질조차 잊어버리는 치명적 파편화가 발생함.
- **Suggested Fix**: `models.py`의 `baby_cap`을 `@hybrid_property`로 변경하여 `max(5, unchi_holes*10)` 룰을 구현하고, SQL `UPDATE` 및 `.filter` 문에서도 `Park.baby_cap`을 직접 호출할 수 있도록 리팩토링.

## 5. Pass 3: Security Findings
- 본 감사에서 발견된 권한 상승, 인젝션, DoS 등 외부 공격 표면 상의 보안 취약점은 없음 (교역 취소/거절 시 Lock 및 원자적 검증 정상).

## 6. Final Decision
- **Status**: `REJECTED` (Needs Implementation fix)
- `unchi_holes`가 0일 때 데이터 손실(저실장 증발) 및 시스템 이벤트 차단(야생 채집 불가)이 발생하는 중대한 결함을 확인.
- 코드를 수정하지 않고 현 상태를 문서화하여 리포트로 남김. 다음 개발 단계에서 Data Loss 방지를 위한 즉각적인 리팩토링 및 핫픽스가 필요함.

---

## 7. 패치 내역 (Fixes Applied)

### [FIXED] STATE-F008 — ORM 프로퍼티와 비즈니스 로직 간의 파편화 (Drift)
- **파일**: `app/models.py`
- **조치**: `baby_cap`을 `@property`에서 `@hybrid_property`로 변경. Python 인스턴스 접근 시 `max(5, self.unchi_holes * 10)`를 반환하고, SQL 표현식(`@baby_cap.expression`)에서는 `case((cls.unchi_holes * 10 > 5, cls.unchi_holes * 10), else_=5)`를 생성.
- **효과**: `baby_cap`의 `max(5, ...)` 룰이 모델 레이어에 온전히 캡슐화되어, Python 메모리 로직과 SQL 쿼리 로직 양쪽에서 일관되게 접근 가능. 더 이상 호출부에서 `max(5, park.baby_cap)` 같은 땜집(Monkey Patching)이 필요 없음.

### [FIXED] STATE-F007 — 원자적 쿼리 내 하드코딩된 Cap으로 인한 저실장 삭제(Data Loss) 결함
- **파일**: `app/routes/game_routes.py`, `app/battle_engine.py`
- **조치**: `trade_accept`, `trade_reject`, `trade_cancel`의 `baby_count` 원자적 `UPDATE` case() 문, 및 `_apply_loot()`의 `baby_count` case() 문에서 하드코딩된 `(Park.unchi_holes * 10)`을 `Park.baby_cap`(hybrid_property)로 교체.
- **효과**: `unchi_holes == 0`일 때 Cap이 0이 되어 기존 저실장이 모두 0으로 덮어씌워지는 Data Loss 현상 해소. 운치굴 0개일 때도 최소 5마리 수용이 SQL UPDATE 단에서 보장됨.

### [FIXED] LOGIC-F007 — 하드코딩된 Cap으로 인한 야생 저실장 채집 원천 차단
- **파일**: `app/game_engine.py`
- **조치**: `action_gather()` 내 "야생 실장석 발견" 이벤트의 저실장 필터 조건 `Park.baby_count < (Park.unchi_holes * 10)`을 `Park.baby_count < Park.baby_cap`로 교체.
- **효과**: `unchi_holes == 0`일 때도 `Park.baby_cap`이 5를 반환하므로, `baby_count < 5` 조건이 성립하여 초반 운치굴 미건설 뉴비도 야생 저실장 이벤트를 받을 수 있음.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
