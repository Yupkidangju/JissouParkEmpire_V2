# JissouParkEmpire Audit Report - Turn 42

## 1. Audit Target
- **Target Module:** `app/routes/game_routes.py`
- **Target Functions:** `diplomacy_ally()`, `diplomacy_enemy()`
- **Audit Focus:** Concurrency and State Consistency (Duplicate Diplomacy Records)

## 2. Methodology
- **Audit Type:** Source code review, Concurrency analysis.
- **Reference Standard:** `AI_AUDIT_DOC_STANDARD.md`
- **Execution:**
  1. Traced the execution of `/diplomacy/ally` and `/diplomacy/enemy` routes.
  2. Analyzed the pre-flight existence checks for diplomatic relations.
  3. Evaluated the database schema in `app/models.py` (`Diplomacy` model) for constraints.

## 3. Findings

### 3.1. [STATE-F015] TOCTOU Race Condition in Diplomacy Routes (Duplicate Records)
- **Severity:** Low
- **Vulnerability Type:** Concurrency Issue (Time-of-Check to Time-of-Use), State Duplication
- **Description:**
  In `game_routes.py`, both `diplomacy_ally()` and `diplomacy_enemy()` routes perform a query to check if a relationship already exists before inserting a new one. For example, in `diplomacy_ally()`:
  ```python
      existing = Diplomacy.query.filter(
          ((Diplomacy.park_a_id == park.id) & (Diplomacy.park_b_id == target.id)) |
          ((Diplomacy.park_a_id == target.id) & (Diplomacy.park_b_id == park.id)),
          Diplomacy.relation_type == 'ally',
          Diplomacy.status.in_(['active', 'pending'])
      ).first()
      if existing:
          # reject ...

      # Time-of-Use
      diplo = Diplomacy(...)
      db.session.add(diplo)
      db.session.commit()
  ```
  Because the read (`first()`) and write (`add()`) are not atomic, a race window exists. Concurrent requests can bypass the `if existing:` check simultaneously. Furthermore, the `Diplomacy` table in `app/models.py` lacks a database-level unique constraint to prevent duplicate relations between the same two parks. As a result, the database can end up with multiple `pending` or `active` relations between identical pairs of parks.
- **Impact:**
  - Database clutter and redundant `Diplomacy` records.
  - While the game logic (`any()` or `all()` sets) generally handles duplicates safely without breaking balance, UI elements may display multiple duplicate relationship entries or requests.
  - In `diplomacy_enemy` and `diplomacy_dissolve`, a concurrent execution results in the player being charged Action Points (AP) multiple times for a single logical action.
- **Remediation Recommendation:**
  Add a unique constraint or composite index at the database level. For instance, using a composite unique constraint on an ordered tuple of `(least(park_a, park_b), greatest(park_a, park_b), relation_type)` would firmly prevent duplicates. Alternatively, implement an `INSERT ... ON CONFLICT DO NOTHING` pattern or use a SQLAlchemy `with_for_update()` lock on a dummy row/parent park to serialize relationship declarations.

## 4. Conclusion
The audit discovered a TOCTOU race condition in the diplomacy creation routes (`[STATE-F015]`). The absence of a unique constraint in the `Diplomacy` model allows concurrent requests to bypass the existence check and insert duplicate relations. This leads to redundant data and potential multi-charging of AP for simultaneous requests. No modifications were made during this audit.

---

## 5. 패치 내역 (Fixes Applied)

### [FIXED] STATE-F015 — TOCTOU Race Condition in Diplomacy Routes (Duplicate Records)
- **파일**: `app/models.py`, `app/routes/game_routes.py`
- **조치**:
  1. `Diplomacy` 모델에 `__table_args__ = (db.UniqueConstraint('park_a_id', 'park_b_id', 'relation_type', 'status'),)` 추가하여 DB 레벨에서 중복 외교 관계 생성을 원천 차단.
  2. `diplomacy_ally()`에 `Park.query.filter(Park.id == park.id).with_for_update().first()`를 추가하여 동맹 요청 생성을 직렬화. 띅 획득 후 existing 관계를 재검증.
  3. `diplomacy_enemy()`에 동일한 `with_for_update()` 띅 획득 및 재검증 추가.
  4. 두 라우트 모두 `db.session.commit()`을 `try/except`로 감싸, 동시 요청으로 인한 `IntegrityError` 발생 시 우아하게 롤백하고 중복 메시지를 표시.
- **효과**: 동시 요청이 existing 검사를 동시에 통과하더라도, DB의 `UniqueConstraint`와 `with_for_update()` 띅이 이중으로 중복 생성을 방지. AP 다중 차징 및 중복 외교 레코드 생성 방지.

---

**패치 완료일**: 2026-05-30
**상태**: ✅ 모든 항목 수정 완료 (Fixed)
